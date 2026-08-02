"""The science underneath each course - what it assumes you already know.

A nursing course title tells you the clinical surface, not the load-bearing
science. "Medical-Surgical Nursing II" is really acid-base chemistry, renal
physiology and cellular transport wearing a clinical coat. "Pharmacology" is
receptor biochemistry, first-order kinetics and hepatic enzyme induction. The
course will teach the clinical layer and quietly assume the rest.

Students who struggle usually aren't failing the nursing content - they're
failing the chemistry three levels below it, and nobody named the gap.

So each course gets a foundations map:

  PREREQ   names the underlying science the course assumes, by discipline,
           and says WHY the course needs it (the link is the whole point)
  SCIENCE  writes a brief on each foundation concept - pitched at someone who
           needs to understand it, not pass a chemistry exam
  BRIDGE   makes the connection explicit: this chemistry -> that nursing action

Disciplines covered: chemistry, biology, anatomy, physiology, microbiology,
pathophysiology, pharmacology basics, maths and statistics, psychology.
"""
import json, os, sqlite3, threading, time

import llm

HERE = os.path.dirname(os.path.abspath(__file__))
DB = os.path.join(HERE, "ecosystem.db")
LOCK = threading.Lock()

SCHEMA = """
CREATE TABLE IF NOT EXISTS fn_map(
  course TEXT PRIMARY KEY, items TEXT, created INTEGER, updated INTEGER);
CREATE TABLE IF NOT EXISTS fn_brief(
  id TEXT PRIMARY KEY, course TEXT, discipline TEXT, concept TEXT, why TEXT,
  body TEXT, bridge TEXT, level TEXT, status TEXT, created INTEGER);
CREATE INDEX IF NOT EXISTS ix_fn_brief ON fn_brief(course, discipline);
CREATE TABLE IF NOT EXISTS fn_check(
  id INTEGER PRIMARY KEY AUTOINCREMENT, course TEXT, concept TEXT,
  confident INTEGER, created INTEGER);
"""

DISCIPLINES = ["chemistry", "biology", "anatomy", "physiology", "microbiology",
               "pathophysiology", "pharmacology", "maths", "psychology"]

GUARD = ("This is study support for a nursing student. Be accurate; if you are not "
         "confident about a specific value or mechanism, say so rather than stating "
         "it. This is exam preparation, not clinical guidance for a real patient.")


def _c():
    c = sqlite3.connect(DB, timeout=20); c.row_factory = sqlite3.Row; return c


def init():
    with LOCK, _c() as c:
        c.executescript(SCHEMA)


def _course(code):
    import nursing_api
    return nursing_api.COURSES.get(code)


def _cid(code, concept):
    import re
    return code + "-" + re.sub(r"[^a-z0-9]+", "-", concept.lower()).strip("-")[:36]


# Words that reliably indicate a discipline when the model's own label misses.
# "biochemistry", "chemistry/physiology" and similar are common returns, and
# defaulting all of them to physiology collapsed the map into one bucket.
_HINTS = {
    "chemistry": ("acid", "base", "ph ", "buffer", "ion", "osmolar", "molecul", "bond",
                  "solut", "electrolyte", "biochem", "oxidat", "chemic"),
    "microbiology": ("bacteri", "virus", "viral", "microb", "pathogen", "antibiotic",
                     "infect", "flora", "fungal"),
    "anatomy": ("anatom", "structure", "vascular", "circulation", "nerve", "muscle",
                "skeletal", "landmark"),
    "pharmacology": ("pharmac", "drug", "dose", "dosing", "receptor bind", "adme",
                     "bioavail", "half-life"),
    "maths": ("kinetic", "math", "calculat", "statistic", "exponential", "logarith",
              "conversion", "ratio", "probabilit"),
    "psychology": ("psycholog", "behavio", "cognitive", "developmental", "motivat",
                   "grief", "coping"),
    "pathophysiology": ("pathophys", "patholog", "disease process", "inflammat",
                        "compensat", "maladapt"),
    "biology": ("cell", "genetic", "dna", "mitosis", "tissue", "organelle", "immun"),
    "physiology": ("physiolog", "perfusion", "gfr", "nephron", "cardiac output",
                   "homeostas", "metabolis", "transport"),
}


def _discipline(label, concept=""):
    """Resolve a model's discipline label to one of ours, falling back on the text."""
    s = str(label or "").lower().strip()
    for d in DISCIPLINES:                       # exact, then substring either way
        if s == d:
            return d
    for d in DISCIPLINES:
        if d in s or (s and s in d):
            return d
    hay = (s + " " + str(concept)).lower()
    best, hits = "", 0
    for d, words in _HINTS.items():
        n = sum(1 for w in words if w in hay)
        if n > hits:
            best, hits = d, n
    return best or "physiology"


# ──────────────────────────────────────────────────────────── mapping
def map_course(code, n=8):
    """PREREQ names the science the course assumes but will not teach."""
    co = _course(code)
    if not co:
        return None, f"unknown course {code!r}"
    terms = ", ".join(t[0] for t in (co.get("terms") or [])[:14])
    system = (
        "You are the prerequisite analyst for an accelerated BSN program. Your job is "
        "to look past a course title to the science it silently assumes.\n" + GUARD + "\n\n"
        f"COURSE: {co['name']} ({code}), {co['credits']} credits, term {co.get('term')}\n"
        f"Focus: {co.get('blurb','')}\n"
        f"Content: {(co.get('lesson') or '')[:1000]}\n"
        f"Key terms: {terms}\n\n"
        f"Name up to {n} foundation concepts this course requires but will NOT teach - "
        "the chemistry, biology, anatomy, physiology, microbiology, maths or psychology "
        "underneath it. Be concrete: 'osmolarity and fluid shifts across membranes', not "
        "'basic chemistry'. For each, state plainly why THIS course needs it - which "
        "clinical topic collapses without it.\n\n"
        'Return ONLY JSON: [{"discipline":"chemistry|biology|anatomy|physiology|'
        'microbiology|pathophysiology|pharmacology|maths|psychology",'
        '"concept":"...","why":"the course topic that depends on it",'
        '"level":"assumed|refresher|deep"}]')
    data, err = llm.ask_json(system, f"Map the foundations for {code}.", want="array", timeout=240)
    if err:
        return None, err
    items = []
    for d in data:
        concept = llm.pick(d, "concept", "name", "title", "topic")
        if not concept:
            continue
        why = llm.pick(d, "why", "why_needed", "reason", "rationale", "needed_for",
                       "depends_on", "course_topic", "application", "used_for", "relevance")
        items.append({"discipline": _discipline(llm.pick(d, "discipline", "subject", "field",
                                                         "area", "domain", "category"), concept),
                      "concept": str(concept)[:120],
                      "why": str(why)[:300],
                      "level": str(llm.pick(d, "level", "depth", default="assumed"))[:10]})
    if not items:
        return None, "no foundations parsed"
    now = int(time.time())
    with LOCK, _c() as c:
        c.execute("""INSERT INTO fn_map(course,items,created,updated) VALUES(?,?,?,?)
                     ON CONFLICT(course) DO UPDATE SET items=?,updated=?""",
                  (code, json.dumps(items), now, now, json.dumps(items), now))
        for it in items:
            c.execute("""INSERT OR IGNORE INTO fn_brief
                         (id,course,discipline,concept,why,level,status,created)
                         VALUES(?,?,?,?,?,?,?,?)""",
                      (_cid(code, it["concept"]), code, it["discipline"], it["concept"],
                       it["why"], it["level"], "planned", now))
    return {"course": code, "name": co["name"], "foundations": items}, None


def get_map(code):
    with LOCK, _c() as c:
        rows = [dict(r) for r in c.execute(
            """SELECT id,discipline,concept,why,level,status FROM fn_brief
               WHERE course=? ORDER BY discipline,concept""", (code,))]
    return rows


# ──────────────────────────────────────────────────────────── writing
def write_brief(brief_id):
    """SCIENCE writes the concept; BRIDGE ties it to the nursing action."""
    with LOCK, _c() as c:
        r = c.execute("SELECT * FROM fn_brief WHERE id=?", (brief_id,)).fetchone()
    if not r:
        return None, f"no brief {brief_id!r}"
    co = _course(r["course"]) or {}
    try:
        import learner
        prof = learner.brief(r["course"])
    except Exception:
        prof = ""

    system = (
        f"You are the {r['discipline']} specialist supporting a nursing student in "
        f"{co.get('name', r['course'])}.\n{GUARD}\n\n"
        f"CONCEPT: {r['concept']}\n"
        f"WHY THE COURSE NEEDS IT: {r['why']}\n"
        + (prof + "\n\n" if prof else "") +
        "Explain this concept in 350-500 words for someone who needs to USE it, not "
        "pass a chemistry exam. Start from what makes intuitive sense and build. Give "
        "the mechanism, not just the rule - they have to reason from it under exam "
        "pressure. Bold key terms with **term**. No headers, no bullet lists.")
    body, err = llm.ask(system, f"Explain {r['concept']}.", timeout=240)
    if err:
        return None, err

    bsys = (
        f"You are the Bridge author. A student has just read this {r['discipline']} "
        f"explanation. Make the link to {co.get('name', r['course'])} explicit and "
        f"concrete.\n{GUARD}\n\n"
        "In 150-250 words: name two or three specific nursing situations where this "
        "concept decides what you do - the assessment finding it explains, the "
        "intervention it justifies, the exam question that is really testing it. "
        "Concrete cases, not 'this is important for patient care'.")
    bridge, berr = llm.ask(bsys, f"CONCEPT: {r['concept']}\n\nEXPLANATION:\n{body}", timeout=240)
    if berr:
        bridge = ""

    with LOCK, _c() as c:
        c.execute("UPDATE fn_brief SET body=?,bridge=?,status=? WHERE id=?",
                  (body, bridge, "written", brief_id))
    return {"id": brief_id, "concept": r["concept"], "discipline": r["discipline"],
            "words": len(body.split()), "bridged": bool(bridge)}, None


def get_brief(brief_id):
    with LOCK, _c() as c:
        r = c.execute("SELECT * FROM fn_brief WHERE id=?", (brief_id,)).fetchone()
    return dict(r) if r else None


def self_check(code, concept, confident):
    """Student flags whether they already have a foundation. Feeds the profile."""
    with LOCK, _c() as c:
        c.execute("INSERT INTO fn_check(course,concept,confident,created) VALUES(?,?,?,?)",
                  (code, concept, 1 if confident else 0, int(time.time())))
    if not confident:
        try:
            import learner
            learner.add_fact("gap", code, f"self-reported gap in foundation: {concept}",
                             "foundations self-check", 0.75)
        except Exception:
            pass
    return {"course": code, "concept": concept, "confident": bool(confident)}


def status(code=None):
    q = """SELECT course, COUNT(*) total, SUM(status='written') written
           FROM fn_brief"""
    a = []
    if code:
        q += " WHERE course=?"; a = [code]
    with LOCK, _c() as c:
        return [dict(r) for r in c.execute(q + " GROUP BY course ORDER BY course", a)]


if __name__ == "__main__":
    init()
    print("disciplines:", ", ".join(DISCIPLINES))
    print("mapped:", status() or "none")
