"""The doubles themselves: a fake model and a fake nursing_api.

Two things are being stood in for:

  llm.ask       the real one shells out to the claude CLI. The fake answers from
                the system turn — it looks at which persona is asking and hands
                back canned text of roughly the right shape. Every call is
                recorded, which is what makes the prompt-placement contract
                (task in the USER turn, carry accumulates) checkable.
  nursing_api   the real one is the pre-existing backend. The fake supplies a
                two-course catalogue and the two tables the stack reads but does
                not own (nursing_items, nursing_answers).

The text these return is synthetic and is never written anywhere a student
would see it — the verification harness runs against a throwaway database.
"""
import json
import sqlite3
import sys
import types

# Long enough to land inside loops.score_chapter's 900-2200 word band.
_BODY_WORDS = 1100


class Recorder:
    """Every model call, so the contract gate can inspect what was actually sent."""

    def __init__(self):
        self.calls = []

    def add(self, system, user, kwargs):
        self.calls.append({"system": system or "", "user": user or "", "kwargs": kwargs})

    def systems(self):
        return [c["system"] for c in self.calls]

    def find(self, needle):
        return [c for c in self.calls if needle in c["system"]]


def _chapter_body():
    lead = ("Synthetic chapter body produced by the verification harness. "
            "The **mechanism** is stated first so it can be reasoned from. ")
    filler = "placeholder teaching sentence for the simulated chapter. " * 200
    return (lead + filler).strip()


def _json(payload):
    return json.dumps(payload)


def _answer(system, user):
    """Pick a canned reply from who is asking. Order matters: check the most
    specific personas before the generic JSON-distiller."""
    s = system or ""
    u = user or ""

    # --- the distiller: llm.read_then_json / world.scout second pass ---------
    if "convert descriptions into JSON" in s or "convert research notes into JSON" in s:
        if '"claim"' in u:
            return _json([
                {"kind": "fact", "topic": "acid-base",
                 "claim": "Simulated claim one from the harness artefact.",
                 "detail": "Synthetic supporting detail.", "confidence": 0.8},
                {"kind": "mechanism", "topic": "acid-base",
                 "claim": "Simulated claim two describing a cause and effect.",
                 "detail": "Synthetic supporting detail.", "confidence": 0.7},
            ])
        if '"title":"short descriptive title"' in u or '"discipline"' in u:
            return _json({"title": "Harness artefact", "kind": "diagram",
                          "summary": "Synthetic artefact used by the verification harness.",
                          "courses": ["A101"], "discipline": "physiology",
                          "topics": ["acid-base"]})
        if '"n":1' in u or '"covers"' in u:
            return _json(_chapters())
        if '"why_now"' in u or '"sources"' in u:
            return _json([{"title": "Simulated current problem",
                           "summary": "Synthetic problem used by the harness.",
                           "why_now": "Recently reported in the simulated notes.",
                           "who": "Simulated affected population",
                           "sources": ["example.org"]}])
        return _json({})

    if "Lead Author" in s:
        return _json(_chapters())
    if "Subject Expert" in s:
        return _chapter_body()
    if "Clinical Correlator" in s:
        return ("Simulated bedside section. Assessment findings, the error students "
                "make, and the finding that would prompt escalation.")
    if "Illustrator" in s:
        return "| finding | meaning |\n|---|---|\n| synthetic | harness only |"
    if "Red Team" in s:
        return "1. Simulated objection one.\n2. Simulated objection two."
    if "Editor" in s:
        # Wording the mechanical scorer recognises as a real review.
        return ("The claim quoted above is inaccurate as written; the following "
                "paragraph is an oversimplif of the mechanism, and the summary "
                "sentences overstate what the evidence supports.")
    if "prerequisite analyst" in s:
        return _json([
            {"discipline": "chemistry", "concept": "buffer systems and pH",
             "why": "acid-base balance", "level": "assumed"},
            {"discipline": "physiology", "concept": "nephron transport",
             "why": "fluid and electrolyte topics", "level": "assumed"},
        ])
    if "specialist supporting a nursing student" in s:
        return "Simulated foundation brief explaining the **mechanism** plainly."
    if "Bridge author" in s:
        return "Simulated bridge tying the concept to two nursing situations."
    if "Verifier" in s:
        return _json([
            {"i": 0, "verdict": "verified", "note": "Simulated check."},
            {"i": 1, "verdict": "corrected", "note": "Simulated correction.",
             "corrected_claim": "Simulated corrected claim two."},
        ])
    if "Curator" in s and "already read and filed" in s:
        return _json([{"q": "Which lecture was this from?",
                       "why": "provenance cannot be inferred", "suggest": ["week 3"]}])
    if "Curator" in s:
        return ("Simulated read of the artefact: it is a diagram covering acid-base "
                "balance and it serves course A101.")
    if "Extractor" in s:
        return ("Simulated exhaustive read. 1. First labelled relationship. "
                "2. Second labelled relationship with units.")
    if "learning analyst" in s:
        return _json([{"kind": "misconception", "subject": "A101",
                       "fact": "Simulated specific misconception from the harness.",
                       "evidence": "harness fixture", "confidence": 0.7}])
    if "item writer" in s:
        return _json({"stem": "Simulated revised stem?",
                      "options": ["a", "b", "c", "d"], "correct": 1,
                      "rationale": "Simulated rationale " * 20,
                      "topic": "acid-base", "difficulty": "medium"})
    if "You are a Scout" in s:
        return "Simulated scout notes naming one concrete problem and its source."
    if "You are Triage" in s:
        return _json([{"i": 0, "scale": 0.6, "tractable": 0.5, "neglected": 0.4,
                       "evidence": 0.7, "verdict": "work", "why": "simulated"}])
    if "You are the Solver" in s:
        return "Simulated approaches, each with a mechanism and a load-bearing assumption."
    if "You are the Critic" in s:
        return "Simulated critique naming the failure mode of each approach."
    if "You are the Synthesist" in s:
        return "Simulated position after the critique landed."
    if "sitting with the student" in s:
        return "Simulated tutor reply naming the specific wrong step."
    return "Simulated reply from the verification harness."


def _chapters(n=3):
    return [{"n": i, "title": f"Simulated chapter {i}",
             "summary": "Synthetic chapter summary.",
             "covers": ["acid-base", "buffers"]} for i in range(1, n + 1)]


def install_fake_llm(llm_module):
    """Replace llm.ask. Returns the Recorder; call restore() to undo."""
    recorder = Recorder()
    original = llm_module.ask

    def fake_ask(system, user, web=False, timeout=None, tools=""):
        recorder.add(system, user,
                     {"web": web, "timeout": timeout, "tools": tools})
        return _answer(system, user), None

    llm_module.ask = fake_ask
    recorder.restore = lambda: setattr(llm_module, "ask", original)
    return recorder


COURSES = {
    "A101": {"name": "Simulated Foundations of Nursing", "credits": 3, "term": 1,
             "type": "core", "call": "SIM-101",
             "blurb": "Harness-only course used to exercise the chains.",
             "lesson": "Synthetic lesson content for the verification harness.",
             "terms": [("acid-base", "definition"), ("buffers", "definition")]},
    "A102": {"name": "Simulated Pharmacology", "credits": 3, "term": 2,
             "type": "core", "call": "SIM-102",
             "blurb": "Second harness course, so multi-course paths are exercised.",
             "lesson": "Synthetic pharmacology lesson content.",
             "terms": [("half-life", "definition")]},
}


def install_fake_nursing_api(db_path):
    """Register a `nursing_api` module backed by the harness database."""
    module = types.ModuleType("nursing_api")
    module.COURSES = COURSES
    module.__doc__ = "Verification harness double. Not the real nursing_api."

    def _connect():
        c = sqlite3.connect(db_path, timeout=20)
        c.row_factory = sqlite3.Row
        return c

    def init():
        with _connect() as c:
            c.executescript("""
              CREATE TABLE IF NOT EXISTS nursing_items(
                id TEXT PRIMARY KEY, course TEXT, stem TEXT, options TEXT,
                correct INTEGER, rationale TEXT, topic TEXT, difficulty TEXT,
                category TEXT, created INTEGER);
              CREATE TABLE IF NOT EXISTS nursing_answers(
                id INTEGER PRIMARY KEY AUTOINCREMENT, item_id TEXT, course TEXT,
                topic TEXT, correct INTEGER, created INTEGER);
            """)

    def generate_questions(code, n=3, difficulty="medium", focus=""):
        init()
        made = []
        with _connect() as c:
            for i in range(n):
                item_id = f"sim-{code}-{abs(hash((code, focus, i))) % 10**8}"
                c.execute("""INSERT OR REPLACE INTO nursing_items
                             (id,course,stem,options,correct,rationale,topic,
                              difficulty,category,created)
                             VALUES(?,?,?,?,?,?,?,?,?,?)""",
                          (item_id, code, f"Simulated stem {i} for {focus or code}?",
                           json.dumps(["a", "b", "c", "d"]), 1,
                           "Simulated rationale explaining why the others are wrong. " * 4,
                           "acid-base", difficulty, "Physiological Integrity", 0))
                made.append({"id": item_id, "course": code, "topic": "acid-base",
                             "stem": f"Simulated stem {i}?",
                             "options": ["a", "b", "c", "d"], "correct": 1,
                             "category": "Physiological Integrity",
                             "rationale": "Simulated rationale " * 30})
        return made, None

    def weak_areas(limit=6, code=""):
        return [{"topic": "acid-base", "missed": 3}]

    def ask_expert(code, question):
        return {"course": code, "answer": "Simulated expert answer."}, None

    module.init = init
    module.generate_questions = generate_questions
    module.weak_areas = weak_areas
    module.ask_expert = ask_expert
    sys.modules["nursing_api"] = module
    init()
    return module
