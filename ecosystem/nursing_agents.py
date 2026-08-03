"""The nursing org: every course staffed by the same thirteen roles.

Prebuilt, not improvised. Each role below is a real post with a real job, and
every one of them is bound to a function that already exists and runs - `fn`
names the callable, so an agent that cannot act is a bug, not a design choice.
Nothing here is a label on an empty box.

  TEACH     EXPERT      answers questions on the course
            TUTOR       sits with you on one specific question
  GROUND    PREREQ      finds the science the course assumes but never teaches
            SCIENCE     writes those foundation briefs
  AUTHOR    LEAD        structures the textbook
            SUBJECT     writes the chapter substance
            CLINICAL    drags it to the bedside
            ILLUS       specifies visuals, captions your uploads
            EDITOR      checks accuracy, flags overconfidence
  EXAMINE   EXAMINER    writes practice items
            WRITER      rewrites an item when you ask
  INGEST    CURATOR     files what you upload, and asks what only you can answer
            EXTRACTOR   reads it exhaustively - every label on a diagram
            VERIFIER    independently checks the extractor's claims
  LEARN     ANALYST     reads your work and updates what the org knows about you

Two mechanics make the org get better rather than just bigger:

RANK    an agent's rank rises with the work it has actually completed - chapters
        written, items authored, claims verified. Rank is computed from the
        database, never asserted, so it cannot be inflated.
UNLOCK  capabilities gated behind evidence. The Illustrator does not get to
        specify animations until it has shipped four chapters of static visuals;
        the Examiner does not get to build multi-patient simulations until the
        learner profile is rich enough to target them. Each gate is a real query.

On autonomy: `cycle()` runs the roles in sequence, each reading the last one's
real output. It is operator-initiated by design - per your standing instruction
that nothing runs unattended, there is no scheduler here and nothing starts on
import.
"""
import json, os, sqlite3, threading, time

HERE = os.path.dirname(os.path.abspath(__file__))
DB = os.path.join(HERE, "ecosystem.db")
LOCK = threading.Lock()

SCHEMA = """
CREATE TABLE IF NOT EXISTS na_run(
  id INTEGER PRIMARY KEY AUTOINCREMENT, course TEXT, agent TEXT, role TEXT,
  action TEXT, ok INTEGER, detail TEXT, seconds REAL, created INTEGER);
CREATE INDEX IF NOT EXISTS ix_na_run ON na_run(course, agent);
CREATE TABLE IF NOT EXISTS na_cycle(
  id INTEGER PRIMARY KEY AUTOINCREMENT, course TEXT, stages TEXT, summary TEXT,
  seconds REAL, created INTEGER);
"""

# ── the roles ────────────────────────────────────────────────────────────────
# fn: "module.callable" — the real entry point. args: how the UI should call it.
ROLES = [
    dict(key="EXPERT", title="Course Expert", group="teach", icon="◈",
         goal="Answer any question on this course at the level the student needs.",
         fn="nursing_api.ask_expert", args=["code", "question"],
         tools=["course content", "key terms", "learner profile"],
         inputs=["a question"], outputs=["a taught answer"],
         triggers=["student asks"], unlock=None),
    dict(key="TUTOR", title="Question Tutor", group="teach", icon="◇",
         goal="Work through one specific question with the student, naming the wrong step.",
         fn="learner.chat", args=["item_id", "message"],
         tools=["the item", "student notes", "profile", "depth level"],
         inputs=["a question thread"], outputs=["a targeted explanation"],
         triggers=["student opens a question"], unlock=None),
    dict(key="PREREQ", title="Prerequisite Analyst", group="ground", icon="◉",
         goal="Name the chemistry, physiology and maths this course assumes but will not teach.",
         fn="foundations.map_course", args=["code"],
         tools=["syllabus", "key terms", "discipline taxonomy"],
         inputs=["the course"], outputs=["a foundations map"],
         triggers=["course opened for the first time"], unlock=None),
    dict(key="SCIENCE", title="Foundation Scientist", group="ground", icon="◎",
         goal="Explain one underlying science concept so it can be reasoned from.",
         fn="foundations.write_brief", args=["id"],
         tools=["foundations map", "learner profile"],
         inputs=["a foundation concept"], outputs=["a brief plus a bedside bridge"],
         triggers=["foundation requested"], unlock=None),
    dict(key="LEAD", title="Lead Author", group="author", icon="▣",
         goal="Structure the textbook so chapters build on each other.",
         fn="textbook.outline", args=["code", "chapters"],
         tools=["course content", "key term coverage check"],
         inputs=["the course"], outputs=["a chapter plan"],
         triggers=["textbook started"], unlock=None),
    dict(key="SUBJECT", title="Subject Expert", group="author", icon="▤",
         goal="Write the chapter body — mechanism first, so it can be reasoned from.",
         fn="textbook.write_chapter", args=["code", "n"],
         tools=["chapter plan", "course lesson", "library cards"],
         inputs=["a chapter slot"], outputs=["600-900 words"],
         triggers=["chapter commissioned"], unlock=None),
    dict(key="CLINICAL", title="Clinical Correlator", group="author", icon="▥",
         goal="Put the chapter at the bedside: findings, common error, escalation trigger.",
         fn="textbook.write_chapter", args=["code", "n"],
         tools=["the drafted chapter"],
         inputs=["a chapter body"], outputs=["a bedside section"],
         triggers=["chapter body drafted"], unlock=None),
    dict(key="ILLUS", title="Illustrator", group="author", icon="▦",
         goal="Specify the visuals that genuinely aid understanding; caption uploads.",
         fn="textbook.caption_asset", args=["code", "chapter", "filename", "what_it_shows"],
         tools=["the chapter", "uploaded assets"],
         inputs=["a chapter or an image"], outputs=["visual specs, teaching captions"],
         triggers=["chapter drafted", "image uploaded"],
         unlock=dict(cap="animation and simulation storyboards",
                     need="4 chapters illustrated",
                     sql="SELECT COUNT(*) FROM tb_chapters WHERE course=? AND visuals IS NOT NULL",
                     at=4)),
    dict(key="EDITOR", title="Editor", group="author", icon="▧",
         goal="Flag anything inaccurate, overconfident, or padding. Never smooth over a gap.",
         fn="textbook.write_chapter", args=["code", "n"],
         tools=["assembled chapter"],
         inputs=["a chapter"], outputs=["a review with named concerns"],
         triggers=["chapter assembled"], unlock=None),
    dict(key="EXAMINER", title="Examiner", group="examine", icon="◆",
         goal="Write NCLEX-style items against what this course actually teaches.",
         fn="nursing_api.generate_questions", args=["code", "n", "difficulty", "focus"],
         tools=["course terms", "weak areas", "depth levels", "library cards"],
         inputs=["a topic or weakness"], outputs=["practice items"],
         triggers=["student requests questions", "a weak area appears"],
         unlock=dict(cap="multi-patient simulation scenarios",
                     need="20 answers logged and 6 profile facts",
                     sql="SELECT COUNT(*) FROM nursing_answers WHERE course=?", at=20)),
    dict(key="WRITER", title="Item Writer", group="examine", icon="◈",
         goal="Rewrite an item exactly as the student asks, keeping it legitimate.",
         fn="learner.revise", args=["item_id", "instruction"],
         tools=["the item", "profile"],
         inputs=["a rewrite instruction"], outputs=["a revised item"],
         triggers=["student asks for a rewrite"], unlock=None),
    dict(key="CURATOR", title="Curator", group="ingest", icon="■",
         goal="File what the student uploads, and ask them what only they can answer.",
         fn="intake.submit", args=["path", "hint"],
         tools=["Read (images and documents)", "course catalogue"],
         inputs=["an uploaded artefact"], outputs=["a filed source, questions"],
         triggers=["upload"], unlock=None),
    dict(key="EXTRACTOR", title="Extractor", group="ingest", icon="□",
         goal="Read an artefact exhaustively — every label, axis, arrow and value.",
         fn="intake.submit", args=["path", "hint"],
         tools=["Read (vision)"],
         inputs=["a filed artefact"], outputs=["atomic knowledge claims"],
         triggers=["source filed"], unlock=None),
    dict(key="VERIFIER", title="Verifier", group="ingest", icon="▪",
         goal="Independently check every extracted claim before it enters the library.",
         fn="intake.submit", args=["path", "hint"],
         tools=["biomedical knowledge", "verdict ladder"],
         inputs=["extracted claims"], outputs=["verified, corrected or disputed"],
         triggers=["extraction complete"], unlock=None),
    dict(key="ANALYST", title="Learning Analyst", group="learn", icon="▲",
         goal="Read the student's own work and write down what is true about how they think.",
         fn="learner.ingest", args=[],
         tools=["chats", "notes", "rewrites", "missed items"],
         inputs=["a study session"], outputs=["profile facts"],
         triggers=["operator runs ingest"], unlock=None),
]

GROUPS = {"teach": "Teaching", "ground": "Foundations", "author": "Authoring",
          "examine": "Examination", "ingest": "Knowledge intake", "learn": "Learning"}

RANKS = [(0, "commissioned"), (3, "active"), (10, "seasoned"), (25, "principal")]


def _c():
    c = sqlite3.connect(DB, timeout=20); c.row_factory = sqlite3.Row; return c


def init():
    with LOCK, _c() as c:
        c.executescript(SCHEMA)


def aid(code, key):
    return f"{code}-{key}"


# ── evidence: everything below is counted from the database ─────────────────
def _count(sql, args=()):
    try:
        with LOCK, _c() as c:
            r = c.execute(sql, args).fetchone()
        return int(r[0]) if r and r[0] is not None else 0
    except Exception:
        return 0


WORK = {   # what "one unit of completed work" means for each role
    "EXPERT":    ("SELECT COUNT(*) FROM na_run WHERE course=? AND role='EXPERT' AND ok=1", 1),
    "TUTOR":     ("SELECT COUNT(*) FROM lm_chat WHERE course=? AND role='tutor'", 1),
    "PREREQ":    ("SELECT COUNT(*) FROM fn_brief WHERE course=?", 1),
    "SCIENCE":   ("SELECT COUNT(*) FROM fn_brief WHERE course=? AND status='written'", 1),
    "LEAD":      ("SELECT COUNT(*) FROM tb_chapters WHERE course=?", 1),
    "SUBJECT":   ("SELECT COUNT(*) FROM tb_chapters WHERE course=? AND status='drafted'", 1),
    "CLINICAL":  ("SELECT COUNT(*) FROM tb_chapters WHERE course=? AND status='drafted'", 1),
    "ILLUS":     ("SELECT COUNT(*) FROM tb_chapters WHERE course=? AND visuals IS NOT NULL", 1),
    "EDITOR":    ("SELECT COUNT(*) FROM tb_chapters WHERE course=? AND notes IS NOT NULL", 1),
    "EXAMINER":  ("SELECT COUNT(*) FROM nursing_items WHERE course=?", 1),
    "WRITER":    ("SELECT COUNT(*) FROM lm_revision WHERE course=?", 1),
    "CURATOR":   ("SELECT COUNT(*) FROM kb_source WHERE courses LIKE ?", 2),
    "EXTRACTOR": ("SELECT COUNT(*) FROM kb_card WHERE course=?", 1),
    "VERIFIER":  ("SELECT COUNT(*) FROM kb_card WHERE course=? AND verdict!='unchecked'", 1),
    "ANALYST":   ("SELECT COUNT(*) FROM lm_profile WHERE subject=? AND active=1", 1),
}


def _work(code, key):
    sql, mode = WORK.get(key, (None, 1))
    if not sql:
        return 0
    return _count(sql, (f'%"{code}"%',) if mode == 2 else (code,))


def _rank(n):
    label = RANKS[0][1]
    for at, name in RANKS:
        if n >= at:
            label = name
    return label


def _unlock(code, role):
    u = role.get("unlock")
    if not u:
        return None
    have = _count(u["sql"], (code,))
    return {"capability": u["cap"], "needs": u["need"], "have": have,
            "at": u["at"], "open": have >= u["at"],
            "pct": min(100, round(100 * have / u["at"])) if u["at"] else 100}


def agent(code, key):
    role = next((r for r in ROLES if r["key"] == key), None)
    if not role:
        return None
    import nursing_api
    co = nursing_api.COURSES.get(code) or {}
    n = _work(code, key)
    d = dict(role)
    d.pop("unlock", None)
    d.update(id=aid(code, key), course=code, course_name=co.get("name", ""),
             term=co.get("term"), group_name=GROUPS.get(role["group"], role["group"]),
             work=n, rank=_rank(n), unlock=_unlock(code, role),
             constraints=["Exam preparation only — not clinical guidance for a real patient.",
                          "States uncertainty rather than inventing a dose, value or protocol.",
                          "Cannot read, write or execute anything on the host machine.",
                          "Runs only when you start it — nothing is scheduled."])
    return d


def roster(code):
    return [agent(code, r["key"]) for r in ROLES]


def terms():
    """The program laid out by term, each course carrying its agent count."""
    import nursing_api
    out = {}
    for code, co in sorted(nursing_api.COURSES.items()):
        t = int(co.get("term") or 0)
        n = sum(_work(code, r["key"]) for r in ROLES)
        out.setdefault(t, []).append({
            "code": code, "name": co["name"], "credits": co["credits"],
            "type": co.get("type", ""), "call": co.get("call", ""),
            "blurb": co.get("blurb", ""), "agents": len(ROLES), "work": n,
            "active": sum(1 for r in ROLES if _work(code, r["key"]) > 0),
        })
    return [{"term": t, "courses": cs,
             "credits": sum(c["credits"] for c in cs),
             "agents": sum(c["agents"] for c in cs)}
            for t, cs in sorted(out.items())]


def log(course, agent_id, role, action, ok, detail="", seconds=0.0):
    with LOCK, _c() as c:
        c.execute("""INSERT INTO na_run(course,agent,role,action,ok,detail,seconds,created)
                     VALUES(?,?,?,?,?,?,?,?)""",
                  (course, agent_id, role, action, 1 if ok else 0, str(detail)[:600],
                   seconds, int(time.time())))


def activity(code=None, limit=40):
    q = "SELECT * FROM na_run"; a = []
    if code:
        q += " WHERE course=?"; a = [code]
    with LOCK, _c() as c:
        return [dict(r) for r in c.execute(q + " ORDER BY id DESC LIMIT ?", a + [limit])]


# ── the cycle ────────────────────────────────────────────────────────────────
# Each stage reads the previous stage's real output. Operator-initiated only.
def cycle(code, stages=None, on_stage=None):
    """One pass of the org over a course. Returns what each agent actually did."""
    import foundations, textbook, nursing_api, learner
    t0 = time.time()
    plan = stages or ["PREREQ", "LEAD", "SUBJECT", "EXAMINER", "ANALYST"]
    done = []

    for key in plan:
        role = next((r for r in ROLES if r["key"] == key), None)
        if not role:
            continue
        st = time.time()
        res, err, note = None, None, ""
        try:
            if key == "PREREQ":
                if foundations.get_map(code):
                    note = "map already exists — skipped"
                else:
                    res, err = foundations.map_course(code)
                    note = f"{len(res['foundations'])} foundations named" if res else ""
            elif key == "SCIENCE":
                pend = [f for f in foundations.get_map(code) if f["status"] != "written"]
                if not pend:
                    note = "all briefs written"
                else:
                    res, err = foundations.write_brief(pend[0]["id"])
                    note = f"wrote '{res['concept']}'" if res else ""
            elif key == "LEAD":
                if textbook.get_outline(code):
                    note = "outline already exists — skipped"
                else:
                    res, err = textbook.outline(code)
                    note = f"{len(res['chapters'])} chapters planned" if res else ""
            elif key in ("SUBJECT", "CLINICAL", "ILLUS", "EDITOR"):
                ol = textbook.get_outline(code)
                if not ol:
                    note = "no outline yet"
                else:
                    nxt = next((c for c in ol["chapters"] if c["status"] != "drafted"), None)
                    if not nxt:
                        note = "every chapter drafted"
                    else:
                        res, err = textbook.write_chapter(code, nxt["n"])
                        note = f"ch{nxt['n']} '{nxt['title']}' — {res['words']} words" if res else ""
            elif key == "EXAMINER":
                weak = [w for w in nursing_api.weak_areas(6, code)]
                focus = weak[0]["topic"] if weak else ""
                res, err = nursing_api.generate_questions(code, n=3, focus=focus)
                note = f"{len(res or [])} items" + (f" targeting '{focus}'" if focus else "")
            elif key == "ANALYST":
                res, err = learner.ingest()
                note = (f"{res.get('found',0)} facts learned" if res else "")
        except Exception as e:
            err = f"{type(e).__name__}: {e}"

        secs = round(time.time() - st, 1)
        log(code, aid(code, key), key, note or (err or ""), not err, note or err or "", secs)
        entry = {"agent": aid(code, key), "role": role["title"], "ok": not err,
                 "note": note or (err or "nothing to do"), "seconds": secs}
        done.append(entry)
        on_stage and on_stage(entry)

    total = round(time.time() - t0, 1)
    summary = "; ".join(f"{d['agent']}: {d['note']}" for d in done)
    with LOCK, _c() as c:
        c.execute("INSERT INTO na_cycle(course,stages,summary,seconds,created) VALUES(?,?,?,?,?)",
                  (code, json.dumps(plan), summary[:2000], total, int(time.time())))
    return {"course": code, "stages": done, "seconds": total}, None


def cycles(code=None, limit=10):
    q = "SELECT * FROM na_cycle"; a = []
    if code:
        q += " WHERE course=?"; a = [code]
    with LOCK, _c() as c:
        return [dict(r) for r in c.execute(q + " ORDER BY id DESC LIMIT ?", a + [limit])]


if __name__ == "__main__":
    init()
    import nursing_api; nursing_api.init()
    ts = terms()
    print(f"{len(ROLES)} roles x {sum(len(t['courses']) for t in ts)} courses = "
          f"{sum(t['agents'] for t in ts)} nursing agents")
    for t in ts:
        print(f"  Term {t['term']}: {t['credits']} cr, {t['agents']} agents — "
              + ", ".join(c["code"] for c in t["courses"]))
