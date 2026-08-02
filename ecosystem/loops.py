"""Loops that try things, get scored, and remember what worked.

The chains elsewhere in this system are fixed: EXPERT then CLINICAL then ILLUS
then EDITOR, one phrasing each, forever. That is a guess frozen into code. This
module lets the org run the same job several different ways and keep the way
that measurably worked better.

Three moving parts:

  VARIANT   a different phrasing of one stage's instruction. The Examiner can be
            asked plainly, or told to lead with a case, or told to force a
            priority decision. Same role, different prompt.
  CHAIN     a different ordering, or a different set of stages entirely. Writing
            visuals before the bedside section is a different chain. Adding a
            REDTEAM stage that attacks the draft is a different chain.
  SCORE     what came back, measured. This is the part that has to be honest.

Scoring is deliberately **not** an LLM judging its own work - that grades fluency
and rewards confident prose, which is the opposite of what exam prep needs. Every
signal below is a property of the artefact that can be computed:

  a chapter   - is the body in the target band, did the Editor actually raise
                specific concerns (a real review quotes text; a refusal or a
                chatty menu does not), are visuals present, did items generate
  questions   - how many parsed, how many got a real topic instead of "general",
                how many were classified, how many duplicate a recent stem
  intake      - cards extracted, share the Verifier could actually adjudicate,
                share that was file-mechanics noise

Selection is epsilon-greedy: mostly use the best-scoring loop so far, but a
fixed slice of runs go to something else so a variant that was unlucky once is
not written off forever. With few runs it explores more, which is correct - two
data points are not evidence.

Nothing here runs on a schedule. Loops are tried when work is requested anyway;
the experiment rides along with work you wanted done regardless.
"""
import json, os, random, re, sqlite3, threading, time

HERE = os.path.dirname(os.path.abspath(__file__))
DB = os.path.join(HERE, "ecosystem.db")
LOCK = threading.Lock()

SCHEMA = """
CREATE TABLE IF NOT EXISTS loop_run(
  id INTEGER PRIMARY KEY AUTOINCREMENT, kind TEXT, loop TEXT, subject TEXT,
  score REAL, metrics TEXT, seconds REAL, created INTEGER);
CREATE INDEX IF NOT EXISTS ix_loop_run ON loop_run(kind, loop);
CREATE TABLE IF NOT EXISTS loop_stat(
  kind TEXT, loop TEXT, runs INTEGER, total REAL, best REAL, worst REAL,
  updated INTEGER, PRIMARY KEY(kind, loop));
CREATE TABLE IF NOT EXISTS loop_variant(
  kind TEXT, name TEXT, spec TEXT, rationale TEXT, origin TEXT, created INTEGER,
  PRIMARY KEY(kind, name));
"""

EXPLORE = 0.25          # share of runs that deliberately try something else

# The Mentor is the one agent in this module that calls the model, so the same
# guard every other agent carries applies to it too.
GUARD = ("State uncertainty rather than resolving it with confident prose. Never "
         "invent a source, a statistic or a measurement. This is exam preparation "
         "for a nursing student, not clinical guidance for a real patient. You "
         "cannot read, write or execute anything on the operator's machine.")


def _c():
    c = sqlite3.connect(DB, timeout=20); c.row_factory = sqlite3.Row; return c


def init():
    with LOCK, _c() as c:
        c.executescript(SCHEMA)


# ── the loops on offer ───────────────────────────────────────────────────────
# Each entry is a real, runnable configuration. `stages` names roles that
# textbook.write_chapter knows how to run; `notes` says what the variant is
# actually testing, so a result can be interpreted rather than just ranked.
CHAPTER_LOOPS = {
    "classic": dict(
        stages=["EXPERT", "CLINICAL", "ILLUS", "EDITOR"],
        notes="the default order — teach, then bedside, then visuals, then check"),
    "visuals-first": dict(
        stages=["EXPERT", "ILLUS", "CLINICAL", "EDITOR"],
        notes="visuals specified before the bedside section, so the correlator "
              "can write to the figures rather than around them"),
    "redteam": dict(
        stages=["EXPERT", "CLINICAL", "REDTEAM", "ILLUS", "EDITOR"],
        notes="an adversarial pass attacks the draft before it is illustrated"),
    "lean": dict(
        stages=["EXPERT", "CLINICAL", "EDITOR"],
        notes="no visuals — tests whether the illustrator is earning its call"),
}

QUESTION_LOOPS = {
    "plain": dict(prompt="", notes="the default item request"),
    "case-first": dict(
        prompt="Lead every item with a short patient vignette — age, presenting "
               "problem, one or two relevant findings — before asking the question.",
        notes="vignette-led, closer to how the NCLEX actually reads"),
    "priority": dict(
        prompt="Every item must force a priority or 'first action' decision among "
               "options that are all defensible. No item where three options are "
               "obviously wrong.",
        notes="tests judgement rather than recall"),
    "distractor": dict(
        prompt="Build each item around the single most common student "
               "misconception on this topic, and make that misconception the most "
               "tempting distractor.",
        notes="targets the specific error rather than the fact"),
}

REGISTRY = {"chapter": CHAPTER_LOOPS, "questions": QUESTION_LOOPS}

# Variants written by the Mentor rather than by hand. Merged into REGISTRY on
# load so they compete on exactly the same scoreboard as the built-in ones - a
# proposal earns its place by scoring, not by being newer.
def learned(kind):
    try:
        with LOCK, _c() as c:
            rows = c.execute("SELECT name,spec,rationale FROM loop_variant WHERE kind=?",
                             (kind,)).fetchall()
    except Exception:
        return {}
    out = {}
    for r in rows:
        try:
            spec = json.loads(r["spec"])
        except Exception:
            continue
        spec["notes"] = (spec.get("notes") or r["rationale"] or "")[:200]
        spec["learned"] = True
        out[r["name"]] = spec
    return out


def catalogue(kind):
    """Built-in variants plus anything the Mentor has written."""
    return {**(REGISTRY.get(kind) or {}), **learned(kind)}


# ── scoring ──────────────────────────────────────────────────────────────────
# A real Editor review quotes the text it objects to and names a concern. A
# refusal ("no chapter text was included"), or a chatty offer of help, does not.
_REVIEW_REAL = ("inaccurate", "oversimplif", "overstate", "misleading", "should be cut",
                "padding", "confiden", "imprecise", "unsupported", "ambiguous",
                "sound", "accurate", "correct as written", "no concerns")
_REVIEW_FAKE = ("no chapter text", "please paste", "what would you like",
                "let me know", "pick any option", "i'll run", "just say the word",
                "could you clarify", "was not included")


def score_chapter(ch, items=0):
    """Measure a written chapter. Returns (score 0-1, metrics dict)."""
    body = ch.get("body") or ""
    notes = (ch.get("notes") or "").lower()
    vis = ch.get("visuals") or ""
    words = len(body.split())
    m = {}

    # length: full credit inside the band, tapering outside rather than a cliff
    lo, hi = 900, 2200
    m["words"] = words
    m["length"] = 1.0 if lo <= words <= hi else max(0.0, 1 - abs(
        (lo - words) if words < lo else (words - hi)) / 1500)

    real = sum(1 for w in _REVIEW_REAL if w in notes)
    fake = sum(1 for w in _REVIEW_FAKE if w in notes)
    m["review_signals"], m["review_refusal"] = real, fake
    m["review"] = 0.0 if (fake or not notes) else min(1.0, real / 3)

    m["bedside"] = 1.0 if "## At the bedside" in body else 0.0
    # a table or a numbered figure list is a specified visual; a paragraph is not
    m["visuals"] = 1.0 if (vis and ("|" in vis or re.search(r"^\s*\d+[\.\)]", vis, re.M))) \
        else (0.5 if vis else 0.0)
    m["items"] = min(1.0, items / 3)

    score = (0.22 * m["length"] + 0.30 * m["review"] + 0.16 * m["bedside"]
             + 0.16 * m["visuals"] + 0.16 * m["items"])
    return round(score, 3), m


def score_questions(items, code=""):
    """Measure a batch of generated items."""
    n = len(items or [])
    m = {"count": n}
    if not n:
        return 0.0, m
    real_topic = sum(1 for i in items if (i.get("topic") or "general") != "general")
    classified = sum(1 for i in items if (i.get("category") or "Unclassified") != "Unclassified")
    with_rat = sum(1 for i in items if len((i.get("rationale") or "")) > 120)
    four = sum(1 for i in items if len(i.get("options") or []) >= 4)
    stems = [re.sub(r"[^a-z ]", "", (i.get("stem") or "").lower())[:60] for i in items]
    m["topic_tagged"] = round(real_topic / n, 2)
    m["classified"] = round(classified / n, 2)
    m["rationale"] = round(with_rat / n, 2)
    m["four_options"] = round(four / n, 2)
    m["distinct"] = round(len(set(stems)) / n, 2)
    score = (0.24 * m["topic_tagged"] + 0.16 * m["classified"] + 0.24 * m["rationale"]
             + 0.16 * m["four_options"] + 0.20 * m["distinct"])
    return round(score, 3), m


def score_intake(result):
    """Measure one intake chain run."""
    v = (result or {}).get("verdicts") or {}
    total = sum(v.values()) or 0
    m = {"cards": total, **{k: v[k] for k in v}}
    if not total:
        return 0.0, m
    adjudicated = total - v.get("unchecked", 0)
    m["adjudicated"] = round(adjudicated / total, 2)
    m["verified"] = round(v.get("verified", 0) / total, 2)
    m["volume"] = min(1.0, total / 12)
    score = 0.45 * m["adjudicated"] + 0.25 * m["verified"] + 0.30 * m["volume"]
    return round(score, 3), m


SCORERS = {"chapter": score_chapter, "questions": score_questions, "intake": score_intake}


# ── selection and memory ─────────────────────────────────────────────────────
def stats(kind):
    with LOCK, _c() as c:
        rows = [dict(r) for r in c.execute(
            "SELECT * FROM loop_stat WHERE kind=? ORDER BY total/runs DESC", (kind,))]
    for r in rows:
        r["mean"] = round(r["total"] / r["runs"], 3) if r["runs"] else 0
    return rows


def choose(kind, force=None):
    """Pick a loop: mostly the best so far, sometimes something else."""
    loops = catalogue(kind)
    if not loops:
        return None, "no loops registered for " + kind
    if force and force in loops:
        return force, "forced"
    seen = {r["loop"]: r for r in stats(kind)}
    untried = [k for k in loops if k not in seen]
    if untried:                                  # try everything once first
        return random.choice(untried), "untried"
    if random.random() < EXPLORE:
        return random.choice(list(loops)), "exploring"
    best = max(seen.values(), key=lambda r: r["total"] / max(1, r["runs"]))
    return best["loop"], f"best so far ({round(best['total']/max(1,best['runs']),3)})"


def record(kind, loop, subject, score, metrics, seconds=0.0):
    now = int(time.time())
    with LOCK, _c() as c:
        c.execute("""INSERT INTO loop_run(kind,loop,subject,score,metrics,seconds,created)
                     VALUES(?,?,?,?,?,?,?)""",
                  (kind, loop, subject, score, json.dumps(metrics), seconds, now))
        r = c.execute("SELECT * FROM loop_stat WHERE kind=? AND loop=?", (kind, loop)).fetchone()
        if r:
            c.execute("""UPDATE loop_stat SET runs=runs+1,total=total+?,best=MAX(best,?),
                         worst=MIN(worst,?),updated=? WHERE kind=? AND loop=?""",
                      (score, score, score, now, kind, loop))
        else:
            c.execute("INSERT INTO loop_stat VALUES(?,?,?,?,?,?,?)",
                      (kind, loop, 1, score, score, score, now))
    return {"kind": kind, "loop": loop, "score": score, "metrics": metrics}


def leaderboard(kind=None):
    kinds = [kind] if kind else list(REGISTRY) + ["intake"]
    out = {}
    for k in kinds:
        rows = stats(k)
        for r in rows:
            spec = (REGISTRY.get(k) or {}).get(r["loop"]) or {}
            r["notes"] = spec.get("notes", "")
            r["stages"] = spec.get("stages")
        out[k] = rows
    return out


def history(kind, limit=30):
    with LOCK, _c() as c:
        rows = [dict(r) for r in c.execute(
            "SELECT * FROM loop_run WHERE kind=? ORDER BY id DESC LIMIT ?", (kind, limit))]
    for r in rows:
        try:
            r["metrics"] = json.loads(r["metrics"])
        except Exception:
            r["metrics"] = {}
    return rows


# ── the Mentor ───────────────────────────────────────────────────────────────
# A senior agent whose job is other agents. It reads the scoreboard AND the real
# artefacts behind it - what the high scorer produced versus the low one - works
# out what actually distinguished them, and writes a new variant for its
# colleagues to run. The proposal is not trusted: it enters the rotation as an
# untried loop and has to out-score the incumbents on the same measured axes.
#
# This is the honest version of "agents improving agents". No agent grades its
# own work, and no proposal is adopted because it sounded good.
MENTOR_SUBJECT = {
    "chapter": ("textbook chapter authoring",
                "stages available: EXPERT (writes the body), CLINICAL (bedside "
                "section), ILLUS (visual specs), REDTEAM (attacks the draft), "
                "EDITOR (final accuracy review). A variant is an ORDERING of these."),
    "questions": ("NCLEX practice-item generation",
                  "a variant is an extra instruction appended to the item writer's "
                  "brief. It cannot change the output format, only what is asked for."),
}


def _artefacts(kind, limit=6):
    """The real outputs behind the scores, so the Mentor reasons from evidence."""
    rows = history(kind, limit * 3)
    if not rows:
        return ""
    rows.sort(key=lambda r: -(r["score"] or 0))
    best, worst = rows[:2], rows[-2:]
    out = []
    for label, group in (("HIGHEST SCORING", best), ("LOWEST SCORING", worst)):
        for r in group:
            out.append(f"[{label}] loop '{r['loop']}' on {r['subject']} scored "
                       f"{r['score']}\n  measured: " +
                       ", ".join(f"{k}={v}" for k, v in (r["metrics"] or {}).items()))
    return "\n".join(out)


def mentor(kind):
    """Read what worked, write a new variant for the other agents to try."""
    import llm
    subject, stages = MENTOR_SUBJECT.get(kind, (kind, ""))
    rows = stats(kind)
    if sum(r["runs"] for r in rows) < 2:
        return None, ("not enough runs to learn from yet — run the work a few times "
                      "first, then the Mentor has something to read")

    board = "\n".join(
        f"  '{r['loop']}' — mean {r['mean']} over {r['runs']} runs "
        f"(best {round(r['best'],3)}, worst {round(r['worst'],3)})" for r in rows)
    existing = catalogue(kind)
    known = "\n".join(f"  '{k}': {v.get('notes','')}" for k, v in existing.items())

    system = (
        "You are the Mentor. You do not do the work yourself — you study how other "
        "agents perform it and write better instructions for them. You are evaluated "
        "the same way they are: your proposal will be run and scored against theirs, "
        "so a clever-sounding variant that does not measurably help is a failure.\n"
        + GUARD + "\n\n"
        f"THE WORK: {subject}\n{stages}\n\n"
        "The scoring is mechanical, not aesthetic. Chapters score on: body length in "
        "band, whether the Editor raised specific quoted concerns rather than refusing "
        "or offering help, whether a bedside section exists, whether visuals are "
        "concretely specified, whether practice items generated. Items score on: real "
        "topic tags, classification, rationale depth, four options, distinctness.")
    user = (
        f"CURRENT SCOREBOARD\n{board}\n\nVARIANTS ALREADY IN ROTATION\n{known}\n\n"
        f"EVIDENCE FROM ACTUAL RUNS\n{_artefacts(kind)}\n\n"
        "---\n\nYOUR TASK\nWork out what actually separated the high scores from the "
        "low ones — cite the measured numbers, not your impression. Then propose ONE "
        "new variant that should beat the current leader, and say which measured axis "
        "you expect it to move. It must be genuinely different from everything already "
        "in rotation; if you cannot find a real improvement, say so by returning an "
        "empty proposal rather than inventing a cosmetic reshuffle.\n\n"
        + ('TARGET STRUCTURE: {"name":"short-kebab-name","stages":["EXPERT","CLINICAL",'
           '"ILLUS","EDITOR"],"notes":"what this variant is testing","reasoning":"what '
           'the numbers showed","expect":"which measured axis should move"}'
           if kind == "chapter" else
           'TARGET STRUCTURE: {"name":"short-kebab-name","prompt":"the extra instruction",'
           '"notes":"what this variant is testing","reasoning":"what the numbers showed",'
           '"expect":"which measured axis should move"}')
        + '\nReturn {"name":""} if you have no real proposal.')

    data, err = llm.ask_json(system, user, want="object", timeout=300)
    if err:
        return None, err
    name = re.sub(r"[^a-z0-9\-]", "", str(llm.pick(data, "name")).lower().replace(" ", "-"))[:28]
    if not name:
        return {"proposed": None,
                "note": "the Mentor found no improvement worth trying — that is a "
                        "legitimate answer, not a failure"}, None
    if name in existing:
        return {"proposed": None, "note": f"'{name}' is already in rotation"}, None

    if kind == "chapter":
        stages_out = [str(s).upper() for s in (llm.pick(data, "stages", default=[]) or [])
                      if str(s).upper() in ("EXPERT", "CLINICAL", "ILLUS", "REDTEAM", "EDITOR")]
        if "EXPERT" not in stages_out:
            return None, "proposal omitted EXPERT — rejected, nothing would write the chapter"
        spec = {"stages": stages_out, "notes": str(llm.pick(data, "notes"))[:200]}
    else:
        prompt = str(llm.pick(data, "prompt", "instruction"))[:600]
        if not prompt:
            return None, "proposal had no instruction text"
        spec = {"prompt": prompt, "notes": str(llm.pick(data, "notes"))[:200]}

    with LOCK, _c() as c:
        c.execute("""INSERT OR REPLACE INTO loop_variant(kind,name,spec,rationale,origin,created)
                     VALUES(?,?,?,?,?,?)""",
                  (kind, name, json.dumps(spec),
                   str(llm.pick(data, "reasoning", "rationale"))[:600], "mentor",
                   int(time.time())))
    return {"proposed": name, "spec": spec,
            "reasoning": str(llm.pick(data, "reasoning", "rationale"))[:600],
            "expect": str(llm.pick(data, "expect"))[:200],
            "note": "added to the rotation as untried — it must now out-score the "
                    "incumbents on the same measured axes"}, None


def verdict(kind):
    """Plain-language read on what has actually been learned so far."""
    rows = stats(kind)
    if not rows:
        return "no runs yet — nothing learned"
    if len(rows) == 1:
        return f"only '{rows[0]['loop']}' has run ({rows[0]['runs']}x) — no comparison yet"
    top, bot = rows[0], rows[-1]
    if min(r["runs"] for r in rows) < 2:
        return (f"'{top['loop']}' leads at {top['mean']} but some loops have run once — "
                "not enough to call it")
    gap = top["mean"] - bot["mean"]
    if gap < 0.05:
        return f"no meaningful difference yet (spread {round(gap,3)}) — keep sampling"
    return (f"'{top['loop']}' is ahead at {top['mean']} vs '{bot['loop']}' at "
            f"{bot['mean']} over {sum(r['runs'] for r in rows)} runs")


if __name__ == "__main__":
    init()
    for k in REGISTRY:
        print(f"{k}: {', '.join(REGISTRY[k])}")
        print("   ", verdict(k))
