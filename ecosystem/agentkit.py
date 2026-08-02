"""The agent contract, written from what actually broke.

Every failure in this system so far has been one of nine things. This module is
those nine mistakes turned into a contract that new agents cannot violate,
because the helpers here are the only sanctioned way to build and run one.

Build anything new on `Agent` + `chain()`. Do not hand-roll another loop.

  1  SYSTEM-PROMPT DILUTION
     `--append-system-prompt` competes with Claude Code's own system prompt and
     loses. Three separate agents failed on this: one replied "no target
     structure has been provided" with the schema in its system prompt (and then
     invented a catalogue that was never in the input), an Editor returned a
     chatty menu instead of the review it was briefed for, and a Subject Expert
     wrote 138 words because the chapter brief never reached it.
     -> `run()` puts persona in system; brief, prior work and task all in USER.

  2  CARRY THAT REPLACES INSTEAD OF ACCUMULATING
     The Editor received only the Illustrator's visual specs and replied "no
     chapter text was included".
     -> `chain()` owns the carry. Every stage sees everything before it.

  3  FURNITURE
     An agent with a role description and no callable is a label on a box.
     -> `Agent.fn` is required, and `validate()` refuses a roster containing an
        agent whose function does not resolve.

  4  SELF-GRADING
     A model scoring its own output grades fluency and rewards confident prose,
     which is the exact failure mode of exam material.
     -> scoring is mechanical (`loops.py`) and lives outside the agent.

  5  ASSERTED SENIORITY
     Rank cannot be a string in a config file.
     -> `Agent.evidence` is a SQL count. Rank is derived, never written.

  6  ONE AGENT CHECKING ITSELF
     -> `verify=` names a DIFFERENT agent, and `chain()` refuses if the verifier
        is the same agent that produced the work.

  7  FAILURE READ AS SUCCESS
     A verifier that errors must not leave claims looking approved.
     -> `UNCHECKED` is the default verdict and never coerces to verified.

  8  TOOL CALLS THAT RETURN PROSE
     After using a tool the model reports back conversationally and ignores
     every format contract.
     -> reading and structuring are separate calls (`llm.read_then_json`).

  9  ANYTHING RUNNING UNATTENDED
     -> nothing here schedules. `chain()` runs when called and then stops.
        There is no daemon, no thread, no timer in this module by design.
"""
import json, os, sqlite3, threading, time

import llm

HERE = os.path.dirname(os.path.abspath(__file__))
DB = os.path.join(HERE, "ecosystem.db")
LOCK = threading.Lock()

SCHEMA = """
CREATE TABLE IF NOT EXISTS ak_run(
  id INTEGER PRIMARY KEY AUTOINCREMENT, chain TEXT, agent TEXT, subject TEXT,
  ok INTEGER, chars INTEGER, seconds REAL, note TEXT, created INTEGER);
CREATE INDEX IF NOT EXISTS ix_ak_run ON ak_run(chain, agent);
"""

UNCHECKED = "unchecked"          # the only safe default. Never means "fine".

# Applied to every agent built here. A domain adds to it; nothing removes it.
BASE_GUARD = (
    "State uncertainty rather than resolving it with confident prose. Never invent "
    "a source, a statistic, a dose or a citation. You cannot read, write or execute "
    "anything on the operator's machine."
)


def _c():
    c = sqlite3.connect(DB, timeout=20); c.row_factory = sqlite3.Row; return c


def init():
    with LOCK, _c() as c:
        c.executescript(SCHEMA)


class Agent:
    """One post. Persona, a real callable, and a countable record of work.

    `fn` is 'module.callable' and must resolve — an agent that cannot act is
    rejected by validate() rather than shipped as decoration.
    `evidence` is (sql, param_style) counting completed work from the database.
    """

    def __init__(self, key, title, persona, task, fn="", evidence=None,
                 guard="", tools=(), web=False, reads=(), timeout=300):
        self.key, self.title = key, title
        self.persona = persona                 # who it is  -> system turn
        self.task = task                       # what to do -> USER turn (rule 1)
        self.fn = fn
        self.evidence = evidence
        self.guard = guard
        self.tools = list(tools)
        self.web = web
        self.reads = list(reads)               # which earlier stages it must see
        self.timeout = timeout

    # -- rule 3: an agent must be able to act -------------------------------
    def resolves(self):
        if not self.fn:
            return False
        mod, _, attr = self.fn.rpartition(".")
        try:
            m = __import__(mod)
            for part in mod.split(".")[1:]:
                m = getattr(m, part)
            return callable(getattr(m, attr, None))
        except Exception:
            return False

    # -- rule 5: seniority is counted, not claimed --------------------------
    def work(self, subject=""):
        if not self.evidence:
            return 0
        sql, style = self.evidence
        arg = (f'%"{subject}"%',) if style == "like" else (subject,)
        try:
            with LOCK, _c() as c:
                r = c.execute(sql, arg).fetchone()
            return int(r[0]) if r and r[0] is not None else 0
        except Exception:
            return 0

    def rank(self, subject=""):
        n = self.work(subject)
        return ("principal" if n >= 25 else "seasoned" if n >= 10
                else "active" if n >= 3 else "commissioned")

    # -- rule 1: the task never lives in the system prompt -------------------
    def run(self, brief, prior="", extra=""):
        system = f"{self.persona}\n\n{BASE_GUARD}" + (f"\n{self.guard}" if self.guard else "")
        user = f"BRIEF\n{brief}\n\n"
        if prior:
            user += prior + "\n\n"
        user += "---\n\nYOUR TASK\n" + self.task + (f"\n{extra}" if extra else "")
        return llm.ask(system, user, web=self.web, timeout=self.timeout,
                       tools=",".join(self.tools))


def validate(agents):
    """Refuse furniture. Returns (ok, problems)."""
    problems = []
    seen = set()
    for a in agents:
        if a.key in seen:
            problems.append(f"{a.key}: duplicate key")
        seen.add(a.key)
        if not a.fn:
            problems.append(f"{a.key} ({a.title}): no function bound — furniture")
        elif not a.resolves():
            problems.append(f"{a.key}: fn '{a.fn}' does not resolve")
        if not a.task.strip():
            problems.append(f"{a.key}: no task")
    return (not problems), problems


def chain(name, agents, brief, subject="", verify=None, on_stage=None):
    """Run agents in order. The carry accumulates (rule 2).

    `verify` is an Agent that checks the others' output and must not be one of
    them (rule 6). Its failure leaves the result UNCHECKED, never approved
    (rule 7).
    """
    if verify and any(a.key == verify.key for a in agents):
        return None, f"verifier '{verify.key}' is also a producer — rule 6"

    out, done, t0 = {}, [], time.time()
    for a in agents:
        st = time.time()
        # rule 2: build the carry from everything produced so far, in order
        wanted = a.reads or [x.key for x in agents if x.key in out]
        parts = [f"[{k} produced]\n{out[k]}" for k in wanted if k in out]
        text, err = a.run(brief, "\n\n".join(parts))
        secs = round(time.time() - st, 1)
        _log(name, a.key, subject, not err, len(text or ""), secs, (err or "")[:200])
        entry = {"agent": a.key, "title": a.title, "ok": not err,
                 "chars": len(text or ""), "seconds": secs, "error": err}
        done.append(entry)
        on_stage and on_stage(entry)
        if err:
            return None, f"{a.key}: {err}"
        out[a.key] = text

    result = {"chain": name, "subject": subject, "stages": done, "output": out,
              "verdict": UNCHECKED, "seconds": round(time.time() - t0, 1)}

    if verify:
        body = "\n\n".join(f"[{k}]\n{v}" for k, v in out.items())
        vtext, verr = verify.run(brief, f"[work to check]\n{body}")
        _log(name, verify.key, subject, not verr, len(vtext or ""), 0,
             (verr or "")[:200])
        # rule 7: a failed check is not a pass
        result["verification"] = vtext if not verr else None
        result["verdict"] = "checked" if not verr else UNCHECKED
        result["verify_error"] = verr
    return result, None


def _log(chain_name, agent, subject, ok, chars, secs, note=""):
    with LOCK, _c() as c:
        c.execute("""INSERT INTO ak_run(chain,agent,subject,ok,chars,seconds,note,created)
                     VALUES(?,?,?,?,?,?,?,?)""",
                  (chain_name, agent, subject, 1 if ok else 0, chars, secs, note,
                   int(time.time())))


def runs(chain_name=None, limit=40):
    q = "SELECT * FROM ak_run"; a = []
    if chain_name:
        q += " WHERE chain=?"; a = [chain_name]
    with LOCK, _c() as c:
        return [dict(r) for r in c.execute(q + " ORDER BY id DESC LIMIT ?", a + [limit])]


def report(agents, subject=""):
    """What this roster is, and whether any of it is furniture."""
    ok, problems = validate(agents)
    return {"agents": [{"key": a.key, "title": a.title, "fn": a.fn,
                        "resolves": a.resolves(), "work": a.work(subject),
                        "rank": a.rank(subject), "web": a.web,
                        "tools": a.tools} for a in agents],
            "sound": ok, "problems": problems}


if __name__ == "__main__":
    init()
    # A live self-check: build a roster against the real modules and validate it.
    demo = [
        Agent("EXPERT", "Subject Expert", "You are the Subject Expert.",
              "Write the chapter body.", fn="textbook.write_chapter",
              evidence=("SELECT COUNT(*) FROM tb_chapters WHERE course=? "
                        "AND status='drafted'", "eq")),
        Agent("SCOUT", "Scout", "You are a Scout.", "Find real problems.",
              fn="world.scout", web=True,
              evidence=("SELECT COUNT(*) FROM w_problem WHERE domain=?", "eq")),
        Agent("GHOST", "Ghost", "You are furniture.", "Look important.", fn=""),
    ]
    r = report(demo, "A205")
    print(json.dumps(r, indent=2))
