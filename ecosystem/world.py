"""Agents that go looking for real problems in the world, then work them.

Everything else in this system studies a fixed corpus - a syllabus, a slide you
uploaded, a price series. This module points agents outward: search what is
actually happening right now, find problems worth solving, and take a real run
at solving them.

The chain, and why each link exists separately:

  SCOUT    searches the live web for concrete, current problems in a domain.
           Must cite what it found. A problem with no source is a guess.
  TRIAGE   scores each on scale, tractability, neglectedness and evidence, and
           says which is worth work. Scouts are bad at killing their own finds,
           so this is a different agent.
  SOLVER   takes one problem and proposes approaches - mechanism, what it would
           take, what would have to be true.
  CRITIC   attacks the proposal. Names the failure mode, the thing already tried
           that did not work, and the strongest objection.
  SYNTH    writes the honest position after the attack: what survives, what the
           real uncertainty is, what would resolve it.

Design constraints that matter:

  - SCOUT is the only stage with web access. Downstream stages reason over what
    it brought back, so a claim cannot enter as fact just because a later agent
    sounded confident about it.
  - CRITIC runs before SYNTH, never after. A critique written after the
    conclusion tends to rationalise it.
  - Nothing here recommends action in the world. It produces analysis with its
    uncertainty stated. Speculative research, not a plan to execute.
  - No scheduler. A sweep runs when you start one.
"""
import json, os, sqlite3, threading, time

import llm

HERE = os.path.dirname(os.path.abspath(__file__))
DB = os.path.join(HERE, "ecosystem.db")
LOCK = threading.Lock()

SCHEMA = """
CREATE TABLE IF NOT EXISTS w_problem(
  id TEXT PRIMARY KEY, domain TEXT, title TEXT, summary TEXT, why_now TEXT,
  who TEXT, sources TEXT, scale REAL, tractable REAL, neglected REAL,
  evidence REAL, rank REAL, verdict TEXT, status TEXT, created INTEGER);
CREATE INDEX IF NOT EXISTS ix_w_problem ON w_problem(domain, rank);
CREATE TABLE IF NOT EXISTS w_work(
  id INTEGER PRIMARY KEY AUTOINCREMENT, problem TEXT, stage TEXT, body TEXT,
  seconds REAL, created INTEGER);
CREATE INDEX IF NOT EXISTS ix_w_work ON w_work(problem);
CREATE TABLE IF NOT EXISTS w_sweep(
  id INTEGER PRIMARY KEY AUTOINCREMENT, domain TEXT, found INTEGER,
  kept INTEGER, seconds REAL, created INTEGER);
"""

# Domains the scouts sweep. Deliberately broad and concrete rather than themed -
# "antimicrobial resistance" surfaces real problems; "innovation" surfaces essays.
DOMAINS = {
    "health": "global and public health, disease burden, care delivery, drug resistance",
    "climate": "climate adaptation, emissions, energy systems, resource scarcity",
    "biotech": "biotechnology, genomics, diagnostics, therapeutics pipelines",
    "compute": "computing, AI systems, semiconductors, infrastructure and its failures",
    "materials": "materials science, manufacturing, supply chains, critical minerals",
    "food": "food systems, agriculture, nutrition, water",
    "infrastructure": "transport, grids, housing, ageing physical infrastructure",
    "society": "education, labour, ageing populations, institutional capacity",
}

GUARD = (
    "This is speculative research and analysis, not operational guidance. Do not "
    "produce actionable protocols for synthesising compounds, editing human genomes, "
    "or dosing humans. State uncertainty rather than resolving it with confident "
    "prose. Never invent a source, a statistic, or a study."
)


def _c():
    c = sqlite3.connect(DB, timeout=20); c.row_factory = sqlite3.Row; return c


def init():
    with LOCK, _c() as c:
        c.executescript(SCHEMA)


def _pid(domain, title):
    import re
    return domain[:4] + "-" + re.sub(r"[^a-z0-9]+", "-", title.lower()).strip("-")[:32]


# ── SCOUT ────────────────────────────────────────────────────────────────────
def scout(domain, n=5):
    """Search the live web for real, current problems. The only web-enabled stage."""
    desc = DOMAINS.get(domain)
    if not desc:
        return None, f"unknown domain {domain!r}; try one of: {', '.join(DOMAINS)}"
    system = (
        "You are a Scout. You search the live web for real, specific, currently "
        "unsolved problems, and you report only what you actually found.\n" + GUARD + "\n\n"
        f"DOMAIN: {desc}\n\n"
        "Search now. Find concrete problems being reported in the last year or two - "
        "a named failure, a measured shortfall, a bottleneck people are writing about. "
        "Not themes ('climate change is hard'), not vague trends. Each must be something "
        "you could point at. For each, say who is affected and why it is unresolved, and "
        "name the sources you actually read. If your searches turn up little, report "
        "fewer problems rather than padding with things you already believed.")
    seen, err = llm.ask(system, f"Find up to {n} real current problems in: {desc}",
                        web=True, timeout=420)
    if err:
        return None, err

    shape = ('A JSON array: [{"title":"short specific name","summary":"two sentences on '
             'what the problem actually is","why_now":"what makes it current","who":"who '
             'is affected","sources":["domain.com","other.org"]}]')
    data, jerr = llm.ask_json(
        "You convert research notes into JSON. Use ONLY what is present in the notes. "
        "If the notes name no sources for an item, give an empty list — never supply "
        "a plausible-looking source that was not mentioned.",
        "TARGET STRUCTURE:\n" + shape + "\n\nRESEARCH NOTES:\n" + seen[:14000],
        want="array", timeout=240)
    if jerr:
        return None, jerr

    found = []
    for d in data:
        title = llm.pick(d, "title", "name", "problem")
        if not title:
            continue
        found.append({
            "title": str(title)[:160],
            "summary": str(llm.pick(d, "summary", "description", "what"))[:800],
            "why_now": str(llm.pick(d, "why_now", "whynow", "urgency", "current"))[:400],
            "who": str(llm.pick(d, "who", "affected", "stakeholders"))[:300],
            "sources": [str(s)[:80] for s in (llm.pick(d, "sources", "source",
                                                       default=[]) or [])][:6]})
    return {"domain": domain, "found": found, "notes": seen[:2000]}, None


# ── TRIAGE ───────────────────────────────────────────────────────────────────
def triage(domain, found):
    """A different agent scores them. Scouts don't kill their own finds."""
    listing = "\n\n".join(
        f"{i}. {p['title']}\n   {p['summary']}\n   why now: {p['why_now']}\n"
        f"   sources: {', '.join(p['sources']) or 'NONE GIVEN'}"
        for i, p in enumerate(found))
    system = (
        "You are Triage. You decide which problems are worth an analyst's time, and "
        "you are hard to impress.\n" + GUARD + "\n\n"
        "Score each on four axes, 0 to 1:\n"
        "  scale      how many are affected, how badly\n"
        "  tractable  whether progress is actually possible from outside\n"
        "  neglected  whether serious effort is already saturating it\n"
        "  evidence   how well sourced the claim is — an item with no sources scores "
        "low here no matter how plausible it sounds\n\n"
        "Then a one-line verdict: work it, watch it, or drop it, and why.")
    shape = ('A JSON array, one entry per numbered problem: '
             '[{"i":0,"scale":0.0,"tractable":0.0,"neglected":0.0,"evidence":0.0,'
             '"verdict":"work|watch|drop","why":"one line"}]')
    data, err = llm.ask_json(
        system, "PROBLEMS:\n" + listing[:13000] + "\n\nTARGET STRUCTURE:\n" + shape,
        want="array", timeout=300)
    if err:
        return None, err

    by_i = {}
    for d in data:
        try:
            by_i[int(llm.pick(d, "i", "index", default=-1))] = d
        except (TypeError, ValueError):
            pass

    now, kept = int(time.time()), []
    with LOCK, _c() as c:
        for i, p in enumerate(found):
            d = by_i.get(i) or {}
            def num(k):
                try:
                    return max(0.0, min(1.0, float(llm.pick(d, k, default=0.4) or 0.4)))
                except (TypeError, ValueError):
                    return 0.4
            s, t, ne, e = num("scale"), num("tractable"), num("neglected"), num("evidence")
            rank = round(0.3 * s + 0.3 * t + 0.2 * ne + 0.2 * e, 3)
            verdict = str(llm.pick(d, "verdict", default="watch")).lower()
            if verdict not in ("work", "watch", "drop"):
                verdict = "watch"
            pid = _pid(domain, p["title"])
            c.execute("""INSERT INTO w_problem(id,domain,title,summary,why_now,who,sources,
                         scale,tractable,neglected,evidence,rank,verdict,status,created)
                         VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
                         ON CONFLICT(id) DO UPDATE SET rank=?,verdict=?""",
                      (pid, domain, p["title"], p["summary"], p["why_now"], p["who"],
                       json.dumps(p["sources"]), s, t, ne, e, rank, verdict, "triaged",
                       now, rank, verdict))
            kept.append({"id": pid, "title": p["title"], "rank": rank,
                         "verdict": verdict, "why": str(llm.pick(d, "why", "reason"))[:200],
                         "sources": p["sources"]})
    kept.sort(key=lambda x: -x["rank"])
    return kept, None


def sweep(domain, n=5):
    """SCOUT then TRIAGE. One operator-initiated pass over a domain."""
    t0 = time.time()
    found, err = scout(domain, n)
    if err:
        return None, "scout: " + err
    if not found["found"]:
        return {"domain": domain, "found": 0, "problems": [],
                "note": "the search turned up nothing concrete"}, None
    kept, err = triage(domain, found["found"])
    if err:
        return None, "triage: " + err
    secs = round(time.time() - t0, 1)
    with LOCK, _c() as c:
        c.execute("INSERT INTO w_sweep(domain,found,kept,seconds,created) VALUES(?,?,?,?,?)",
                  (domain, len(found["found"]), len(kept), secs, int(time.time())))
    return {"domain": domain, "found": len(found["found"]), "problems": kept,
            "seconds": secs}, None


# ── SOLVE ────────────────────────────────────────────────────────────────────
def solve(problem_id):
    """SOLVER → CRITIC → SYNTH. The critique lands before the conclusion."""
    with LOCK, _c() as c:
        p = c.execute("SELECT * FROM w_problem WHERE id=?", (problem_id,)).fetchone()
    if not p:
        return None, f"no problem {problem_id!r}"
    brief = (f"PROBLEM: {p['title']}\n{p['summary']}\n"
             f"Why now: {p['why_now']}\nAffected: {p['who']}\n"
             f"Sources the scout used: {', '.join(json.loads(p['sources'] or '[]')) or 'none'}\n"
             f"Triage: rank {p['rank']}, verdict {p['verdict']}")

    stages = [
        ("SOLVER", "You are the Solver. You propose real approaches, not aspirations.",
         "Propose two or three distinct approaches to this problem. For each: the "
         "mechanism by which it would actually work, what it would take to try, and the "
         "single assumption it rests on that would sink it if false. Be specific enough "
         "to argue with. 400-600 words."),
        ("CRITIC", "You are the Critic. Your job is to attack the proposals, not to be "
                   "even-handed about them.",
         "Below are the proposed approaches. For each, name the most likely failure "
         "mode, anything close to it that has already been tried and did not work, and "
         "the strongest objection a domain expert would raise. If an approach is "
         "unsalvageable, say so plainly. Do not propose alternatives — attack only."),
        ("SYNTH", "You are the Synthesist. You write the honest position after the "
                  "attack has landed.",
         "Given the proposals and the critique, write the position that actually "
         "survives. State: what still looks worth trying and why, what the critique "
         "genuinely killed, the real uncertainty that remains, and the specific "
         "observation or result that would resolve it. Do not restore optimism the "
         "critique removed. 300-450 words."),
    ]

    out, carry, t0 = {}, "", time.time()
    for role, who, task in stages:
        user = f"{brief}\n\n"
        if carry:
            user += carry + "\n\n"
        user += "---\n\nYOUR TASK\n" + task
        text, err = llm.ask(f"{who}\n\n{GUARD}", user, timeout=360)
        if err:
            return None, f"{role}: {err}"
        out[role] = text
        parts = [f"[proposed approaches]\n{out['SOLVER']}"]
        if out.get("CRITIC"):
            parts.append(f"[the critique]\n{out['CRITIC']}")
        carry = "\n\n".join(parts)
        with LOCK, _c() as c:
            c.execute("INSERT INTO w_work(problem,stage,body,seconds,created) VALUES(?,?,?,?,?)",
                      (problem_id, role, text, round(time.time() - t0, 1), int(time.time())))

    with LOCK, _c() as c:
        c.execute("UPDATE w_problem SET status='worked' WHERE id=?", (problem_id,))
    return {"problem": problem_id, "title": p["title"],
            "seconds": round(time.time() - t0, 1),
            "stages": {k: v[:400] for k, v in out.items()}}, None


# ── reading ──────────────────────────────────────────────────────────────────
def problems(domain=None, verdict=None, limit=60):
    q = "SELECT * FROM w_problem WHERE 1=1"; a = []
    if domain:
        q += " AND domain=?"; a.append(domain)
    if verdict:
        q += " AND verdict=?"; a.append(verdict)
    with LOCK, _c() as c:
        rows = [dict(r) for r in c.execute(q + " ORDER BY rank DESC LIMIT ?", a + [limit])]
    for r in rows:
        r["sources"] = json.loads(r["sources"] or "[]")
    return rows


def work(problem_id):
    with LOCK, _c() as c:
        return [dict(r) for r in c.execute(
            "SELECT * FROM w_work WHERE problem=? ORDER BY id", (problem_id,))]


def dashboard():
    with LOCK, _c() as c:
        tot = c.execute("SELECT COUNT(*) n FROM w_problem").fetchone()["n"]
        by_d = {r["domain"]: r["n"] for r in c.execute(
            "SELECT domain, COUNT(*) n FROM w_problem GROUP BY domain")}
        by_v = {r["verdict"]: r["n"] for r in c.execute(
            "SELECT verdict, COUNT(*) n FROM w_problem GROUP BY verdict")}
        worked = c.execute("SELECT COUNT(*) n FROM w_problem WHERE status='worked'").fetchone()["n"]
        sweeps = [dict(r) for r in c.execute(
            "SELECT * FROM w_sweep ORDER BY id DESC LIMIT 6")]
    return {"problems": tot, "by_domain": by_d, "by_verdict": by_v,
            "worked": worked, "domains": DOMAINS, "sweeps": sweeps}


if __name__ == "__main__":
    init()
    print("domains:", ", ".join(DOMAINS))
    print(json.dumps(dashboard(), indent=2)[:600])
