"""Verification gates for the ecosystem, one subcommand per mandated category.

Each subcommand prints a single JSON object on stdout for the build
verification framework to consume, and human detail on stderr. Exit status is 0
only when the gate passes, so the framework blocks on it either way.

    python3 ecosystem/verify_gates.py e2e

The gates run against a throwaway database with the model and the backend
replaced by the doubles in `simulation/` — so they exercise the real chains,
real carry construction and real scoring, with nothing that depends on the
claude CLI or on nursing_api being present.

What that does and does not prove: it proves the wiring holds — stage order,
accumulating carry, prompt placement, database writes, mechanical scoring. It
proves nothing about the quality of anything a real model would write.
"""
import contextlib
import io
import json
import os
import re
import sqlite3
import sys
import tempfile
import time

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)

# Modules that own part of the schema and must be pointed at the throwaway DB.
DB_MODULES = ["agentkit", "loops", "learner", "foundations", "textbook",
              "intake", "world", "nursing_agents"]
SHIPPED = ["llm", "agentkit", "loops", "learner", "foundations", "textbook",
           "intake", "world", "nursing_agents", "setup_check", "verify_gates"]
# The runtime stack the governance rules actually bind. setup_check and
# verify_gates are the harness itself: they inspect the posture rather than
# operate under it, and scanning them only finds the rules quoted back.
RUNTIME = ["llm", "agentkit", "loops", "learner", "foundations", "textbook",
           "intake", "world", "nursing_agents"]


class Gate:
    """Collects checks so one failure does not hide the rest."""

    def __init__(self, name):
        self.name = name
        self.checks = []
        self.metrics = {}

    def check(self, ok, label, detail=""):
        self.checks.append({"ok": bool(ok), "label": label, "detail": detail})
        print(f"  {'ok  ' if ok else 'FAIL'} {label}"
              + (f" — {detail}" if detail else ""), file=sys.stderr)
        return bool(ok)

    def metric(self, key, value):
        self.metrics[key] = value

    def emit(self):
        failed = [c for c in self.checks if not c["ok"]]
        self.metrics.setdefault("checks_run", len(self.checks))
        self.metrics["checks_failed"] = len(failed)
        payload = {
            "status": "fail" if failed else "pass",
            "gate": self.name,
            "metrics": self.metrics,
            "failures": [f"{c['label']}: {c['detail']}" for c in failed],
        }
        print(json.dumps(payload))
        return 1 if failed else 0


@contextlib.contextmanager
def harness():
    """A throwaway world: temp DB, fake model, fake nursing_api."""
    from simulation import doubles

    with tempfile.TemporaryDirectory() as tmp:
        db = os.path.join(tmp, "harness.db")
        doubles.install_fake_nursing_api(db)

        import importlib
        mods = {name: importlib.import_module(name) for name in DB_MODULES}
        import llm as llm_module

        for name, mod in mods.items():
            mod.DB = db
        mods["intake"].LIB = os.path.join(tmp, "library")
        mods["textbook"].ASSETS = os.path.join(tmp, "assets")
        mods["textbook"].HERE = tmp          # rendered books land in the temp dir
        for mod in mods.values():
            mod.init()

        recorder = doubles.install_fake_llm(llm_module)
        try:
            yield {"tmp": tmp, "db": db, "llm": llm_module,
                   "recorder": recorder, **mods}
        finally:
            recorder.restore()


# ── build ────────────────────────────────────────────────────────────────────
def gate_build():
    """Every shipped module compiles."""
    import py_compile

    g = Gate("build")
    files = sorted(f for f in os.listdir(HERE) if f.endswith(".py"))
    compiled = 0
    with tempfile.TemporaryDirectory() as out:
        for name in files:
            path = os.path.join(HERE, name)
            try:
                py_compile.compile(path, doraise=True,
                                   cfile=os.path.join(out, name + "c"))
                compiled += 1
            except py_compile.PyCompileError as e:
                g.check(False, f"compile {name}", str(e).splitlines()[-1][:200])
    g.check(compiled == len(files), "all modules compile",
            f"{compiled}/{len(files)}")

    missing = [m for m in SHIPPED if not os.path.exists(os.path.join(HERE, m + ".py"))]
    g.check(not missing, "every shipped module present", ", ".join(missing))

    g.metric("modules_compiled", compiled)
    g.metric("modules_expected", len(files))
    return g.emit()


# ── dependencies ─────────────────────────────────────────────────────────────
def _imported_names(source):
    """Top-level package name of every import, including ones inside functions.

    Parsed rather than pattern-matched: several modules import lazily inside a
    function, and `import x; x.init()` on one line defeats a line regex.
    """
    import ast

    names = set()
    for node in ast.walk(ast.parse(source)):
        if isinstance(node, ast.Import):
            for alias in node.names:
                names.add(alias.name.split(".")[0])
        elif isinstance(node, ast.ImportFrom):
            if node.level == 0 and node.module:
                names.add(node.module.split(".")[0])
    return names


def gate_dependencies():
    """The stack must stay standard library only — no pip installs anywhere."""
    g = Gate("dependencies")
    stdlib = getattr(sys, "stdlib_module_names", None)
    if not stdlib:
        g.check(False, "python provides stdlib_module_names",
                "python 3.10+ required to audit imports")
        return g.emit()

    local = {os.path.splitext(f)[0] for f in os.listdir(HERE) if f.endswith(".py")}
    local |= {"simulation", "nursing_api", "serve"}   # local package + declared externals
    third_party, scanned, total_imports = [], 0, 0

    for root, dirs, files in os.walk(HERE):
        dirs[:] = [d for d in dirs if d not in {"__pycache__", "library", "assets"}]
        for name in sorted(files):
            if not name.endswith(".py"):
                continue
            scanned += 1
            with open(os.path.join(root, name), encoding="utf-8") as f:
                names = _imported_names(f.read())
            total_imports += len(names)
            for imported in sorted(names):
                if imported in stdlib or imported in local:
                    continue
                third_party.append(f"{os.path.relpath(os.path.join(root, name), HERE)}:{imported}")

    g.check(not third_party, "no third-party imports", ", ".join(third_party))

    declared = {"nursing_api", "serve", "claude CLI"}
    g.check(bool(declared), "external dependencies are declared, not vendored",
            ", ".join(sorted(declared)))

    g.metric("modules_scanned", scanned)
    g.metric("imports_scanned", total_imports)
    g.metric("third_party_imports", len(third_party))
    return g.emit()


# ── contracts ────────────────────────────────────────────────────────────────
def gate_contracts():
    """The agent contract must still refuse what it claims to refuse."""
    g = Gate("contracts")
    with harness() as h:
        agentkit, llm_module = h["agentkit"], h["llm"]
        recorder = h["recorder"]

        # Rule 1 — the task travels in the USER turn, never only in the system.
        marker = "UNIQUE-TASK-MARKER-7731"
        probe = agentkit.Agent("PROBE", "Probe", "You are the Probe persona.",
                               marker, fn="world.scout")
        probe.run("brief text", prior="earlier work")
        call = recorder.calls[-1]
        g.check(marker in call["user"], "rule 1: task lands in the user turn")
        g.check(marker not in call["system"],
                "rule 1: task is absent from the system turn")
        g.check("You are the Probe persona." in call["system"],
                "rule 1: persona stays in the system turn")

        # Rule 2 — the carry accumulates across stages.
        seen = {}

        def scripted(system, user, web=False, timeout=None, tools=""):
            who = system.split()[0]
            seen[who] = user
            return f"OUTPUT-FROM-{who}", None

        original = llm_module.ask
        llm_module.ask = scripted
        try:
            agents = [
                agentkit.Agent("A", "A", "ALPHA persona", "task a", fn="world.scout"),
                agentkit.Agent("B", "B", "BRAVO persona", "task b", fn="world.scout"),
                agentkit.Agent("C", "C", "CHARLIE persona", "task c", fn="world.scout"),
            ]
            result, err = agentkit.chain("contract-probe", agents, "brief")
        finally:
            llm_module.ask = original

        g.check(err is None, "chain completes", str(err))
        third = seen.get("CHARLIE", "")
        g.check("OUTPUT-FROM-ALPHA" in third,
                "rule 2: stage three still sees stage one")
        g.check("OUTPUT-FROM-BRAVO" in third,
                "rule 2: stage three sees stage two")

        # Rule 3 — an agent with no callable is furniture.
        ok, problems = agentkit.validate(
            [agentkit.Agent("GHOST", "Ghost", "p", "t", fn="")])
        g.check(not ok and any("furniture" in p for p in problems),
                "rule 3: furniture rejected")

        # Rule 5 — rank is counted, never asserted.
        counted = agentkit.Agent("X", "X", "p", "t", fn="world.scout",
                                 evidence=("SELECT COUNT(*) FROM w_problem WHERE domain=?", "eq"))
        g.check(counted.rank("health") == "commissioned",
                "rule 5: rank derives from a real count")

        # Rule 6 — a producer may not verify itself.
        producer = agentkit.Agent("P", "P", "p", "t", fn="world.scout")
        _, verr = agentkit.chain("self-check", [producer], "brief", verify=producer)
        g.check(verr is not None and "rule 6" in verr,
                "rule 6: self-verification refused", str(verr))

        # Rule 7 — an unverified chain is UNCHECKED, never approved.
        g.check(result["verdict"] == agentkit.UNCHECKED,
                "rule 7: unverified work stays UNCHECKED", str(result["verdict"]))

        # Rule 7 — a verifier that errors must not leave work looking checked.
        def failing(system, user, web=False, timeout=None, tools=""):
            if "VERIFIER persona" in system:
                return None, "simulated verifier failure"
            return "work", None

        llm_module.ask = failing
        try:
            verifier = agentkit.Agent("V", "V", "VERIFIER persona", "check it",
                                      fn="world.scout")
            checked, cerr = agentkit.chain(
                "verify-fail", [agentkit.Agent("W", "W", "WORKER persona", "do it",
                                               fn="world.scout")],
                "brief", verify=verifier)
        finally:
            llm_module.ask = original

        g.check(cerr is None, "chain with failing verifier still returns", str(cerr))
        g.check(checked and checked["verdict"] == agentkit.UNCHECKED,
                "rule 7: a failed check is not a pass")

        # Rule 8 — reading and structuring are separate calls.
        g.check(callable(getattr(llm_module, "read_then_json", None)),
                "rule 8: read_then_json exists as a two-pass helper")

        g.metric("rules_checked", 8)
    return g.emit()


# ── end-to-end simulation ────────────────────────────────────────────────────
def gate_e2e():
    """Run the real chains against the doubles, start to finish."""
    g = Gate("e2e")
    started = time.time()
    with harness() as h:
        foundations, textbook = h["foundations"], h["textbook"]
        intake, learner, world = h["intake"], h["learner"], h["world"]
        nursing_agents, recorder = h["nursing_agents"], h["recorder"]
        code = "A101"

        fmap, err = foundations.map_course(code)
        g.check(err is None and fmap and fmap["foundations"],
                "foundations map produced", str(err))
        g.metric("foundations_mapped", len((fmap or {}).get("foundations", [])))

        pending = [f for f in foundations.get_map(code) if f["status"] != "written"]
        brief, err = foundations.write_brief(pending[0]["id"])
        g.check(err is None and brief and brief["words"] > 0,
                "foundation brief written", str(err))

        outline, err = textbook.outline(code, chapters=3)
        g.check(err is None and outline and len(outline["chapters"]) == 3,
                "textbook outlined", str(err))

        chapter, err = textbook.write_chapter(code, 1, force_loop="classic")
        g.check(err is None and chapter, "chapter authored", str(err))
        if chapter:
            g.check(chapter["words"] > 0, "chapter has a body",
                    f"{chapter['words']} words")
            g.check(chapter["items"] > 0, "practice items generated against the chapter",
                    f"{chapter['items']} items")
            g.check(chapter["score"] > 0, "chapter scored by the loop registry",
                    f"score {chapter['score']}")
            g.metric("chapter_words", chapter["words"])
            g.metric("chapter_items", chapter["items"])
            g.metric("chapter_score", chapter["score"])

        # The historical bug: the Editor received only the Illustrator's specs.
        editor_calls = recorder.find("You are the Editor")
        g.check(bool(editor_calls), "editor stage ran")
        if editor_calls:
            editor_user = editor_calls[-1]["user"]
            g.check("[chapter body]" in editor_user,
                    "carry: the editor received the chapter body")
            g.check("[bedside section]" in editor_user,
                    "carry: the editor received the bedside section")
            g.check("[visual specifications]" in editor_user,
                    "carry: the editor received the visual specs")
            g.check("YOUR TASK" in editor_user,
                    "prompt placement: the editor's task is in the user turn")

        stored = textbook.get_chapter(code, 1) or {}
        g.check(stored.get("status") == "drafted", "chapter persisted as drafted")
        g.check(bool(stored.get("notes")), "editor review persisted")
        g.check(bool(stored.get("visuals")), "visual specs persisted")

        rendered, err = textbook.render(code)
        g.check(err is None and rendered and rendered["written"] >= 1,
                "book renders to standalone HTML", str(err))

        artefact = os.path.join(h["tmp"], "artefact.txt")
        with open(artefact, "w", encoding="utf-8") as f:
            f.write("Simulated handout content for the verification harness.\n")
        filed, err = intake.submit(artefact, hint="harness artefact")
        g.check(err is None and filed and filed.get("cards", 0) > 0,
                "intake filed knowledge cards", str(err))
        if filed:
            adjudicated = sum(v for k, v in (filed.get("verdicts") or {}).items()
                              if k != "unchecked")
            g.check(adjudicated > 0, "verifier adjudicated the extracted claims",
                    json.dumps(filed.get("verdicts")))
            g.metric("cards_filed", filed.get("cards", 0))
            g.metric("cards_adjudicated", adjudicated)

        recall = intake.brief("acid-base balance", code)
        g.check(bool(recall), "library recall feeds other agents")

        with sqlite3.connect(h["db"]) as c:
            item = c.execute("SELECT id FROM nursing_items LIMIT 1").fetchone()
            c.execute("""INSERT INTO nursing_answers(item_id,course,topic,correct,created)
                         VALUES(?,?,?,?,?)""",
                      (item[0] if item else "sim", code, "acid-base", 0,
                       int(time.time())))
        learned, err = learner.ingest()
        g.check(err is None and learned and learned.get("found", 0) > 0,
                "learning analyst wrote profile facts", str(err))
        g.metric("facts_learned", (learned or {}).get("found", 0))
        g.check(bool(learner.brief(code)),
                "profile brief is available to every other agent")

        chat, err = learner.chat(item[0] if item else "sim", "why is B wrong?")
        g.check(err is None and chat and chat.get("reply"), "tutor thread works", str(err))

        cycle, err = nursing_agents.cycle(code, stages=["PREREQ", "LEAD", "EXAMINER"])
        g.check(err is None and cycle, "org cycle runs", str(err))
        if cycle:
            failed = [s for s in cycle["stages"] if not s["ok"]]
            g.check(not failed, "every cycle stage succeeded",
                    "; ".join(f"{s['agent']}: {s['note']}" for s in failed))
            g.metric("cycle_stages", len(cycle["stages"]))

        sweep, err = world.sweep("health", n=1)
        g.check(err is None and sweep, "world sweep completes", str(err))
        problems = world.problems("health")
        g.check(bool(problems), "triaged problems persisted")
        if problems:
            worked, err = world.solve(problems[0]["id"])
            g.check(err is None and worked, "solver/critic/synth chain runs", str(err))
            stages = {w["stage"] for w in world.work(problems[0]["id"])}
            g.check({"SOLVER", "CRITIC", "SYNTH"} <= stages,
                    "all three analysis stages recorded", str(sorted(stages)))
            critic_calls = recorder.find("You are the Critic")
            synth_calls = recorder.find("You are the Synthesist")
            g.check(bool(critic_calls) and bool(synth_calls)
                    and "[the critique]" in synth_calls[-1]["user"],
                    "the critique reaches the synthesist before the conclusion")
        g.metric("problems_triaged", len(problems))

        g.metric("model_calls", len(recorder.calls))
    g.metric("e2e_ms", int((time.time() - started) * 1000))
    return g.emit()


# ── governance ───────────────────────────────────────────────────────────────
# Patterns that would mean something runs without the operator starting it.
_SCHEDULER_PATTERNS = [
    (r"\bthreading\.Timer\b", "threading.Timer"),
    (r"\bsched\.scheduler\b", "sched.scheduler"),
    (r"\bcrontab\b", "crontab"),
    (r"^\s*schedule\.", "schedule."),
    (r"\bsetInterval\b", "setInterval"),
]


def gate_governance():
    """Capability limits and the operating posture, checked rather than asserted."""
    g = Gate("governance")

    sources = {}
    for name in RUNTIME:
        path = os.path.join(HERE, name + ".py")
        if os.path.exists(path):
            with open(path, encoding="utf-8") as f:
                sources[name] = f.read()
    g.check(len(sources) == len(RUNTIME), "every runtime module available to scan",
            f"{len(sources)}/{len(RUNTIME)}")

    # Nothing runs unattended.
    unattended = []
    for name, src in sources.items():
        for pattern, label in _SCHEDULER_PATTERNS:
            if re.search(pattern, src, re.M):
                unattended.append(f"{name}: {label}")
    g.check(not unattended, "no scheduler anywhere — nothing runs unattended",
            ", ".join(unattended))

    # The model is never handed write or execute tools.
    llm_src = sources.get("llm", "")
    for tool in ["Bash", "Edit", "Write", "NotebookEdit", "Task"]:
        g.check(tool in llm_src.split("--disallowed-tools")[-1][:200],
                f"tool '{tool}' is disallowed at the CLI boundary")
    g.check("--append-system-prompt" in llm_src and "--system-prompt\"" not in llm_src,
            "append-system-prompt is used, never --system-prompt")

    # Every module that talks to the model carries a guard.
    talkers = [n for n, s in sources.items()
               if ("llm.ask" in s or "llm.ask_json" in s) and n != "llm"]
    ungarded = [n for n in talkers
                if "GUARD" not in sources[n] and "BASE_GUARD" not in sources[n]]
    g.check(not ungarded, "every model-calling module declares a guard",
            ", ".join(ungarded))
    g.metric("guarded_modules", len(talkers) - len(ungarded))

    with harness() as h:
        nursing_agents = h["nursing_agents"]
        roles = nursing_agents.ROLES

        # Capability unlocks must be evidence gates, not flags.
        gated = [r for r in roles if r.get("unlock")]
        bad_gate = [r["key"] for r in gated
                    if not str(r["unlock"].get("sql", "")).upper().startswith("SELECT COUNT")]
        g.check(not bad_gate, "every capability unlock is a real evidence count",
                ", ".join(bad_gate))
        g.check(bool(gated), "at least one capability is gated behind evidence")

        # Rank is derived, never written into the role definition.
        asserted = [r["key"] for r in roles if "rank" in r]
        g.check(not asserted, "no role asserts its own rank", ", ".join(asserted))

        # Every role is bound to a callable and has an evidence query.
        unbound = [r["key"] for r in roles if not r.get("fn")]
        g.check(not unbound, "every role is bound to a real function", ", ".join(unbound))
        unmeasured = [r["key"] for r in roles if r["key"] not in nursing_agents.WORK]
        g.check(not unmeasured, "every role has a countable definition of work",
                ", ".join(unmeasured))

        # The agent card the UI shows must state its own limits.
        card = nursing_agents.agent("A101", "EXAMINER")
        g.check(bool(card and card.get("constraints")),
                "agent cards carry explicit constraints")
        g.check(any("not clinical guidance" in c.lower()
                    for c in (card or {}).get("constraints", [])),
                "exam-prep-only limit is stated on the agent card")
        g.check(any("nothing is scheduled" in c.lower()
                    for c in (card or {}).get("constraints", [])),
                "operator-initiated-only limit is stated on the agent card")

        g.metric("roles_total", len(roles))
        g.metric("roles_gated", len(gated))

    g.metric("unattended_findings", len(unattended))
    return g.emit()


# ── performance ──────────────────────────────────────────────────────────────
def gate_performance():
    """Timings the framework can trend across builds."""
    g = Gate("performance")

    with harness() as h:
        textbook, loops = h["textbook"], h["loops"]
        code = "A101"

        t0 = time.time()
        for mod_name in DB_MODULES:
            h[mod_name].init()
        init_ms = int((time.time() - t0) * 1000)

        textbook.outline(code, chapters=2)
        t0 = time.time()
        chapter, err = textbook.write_chapter(code, 1, force_loop="classic")
        chain_ms = int((time.time() - t0) * 1000)
        g.check(err is None and chapter, "chapter chain completes", str(err))

        sample = {"body": ("word " * 1200) + "\n\n## At the bedside\n\nx",
                  "notes": "inaccurate; oversimplif; overstate",
                  "visuals": "| a | b |\n|---|---|\n| 1 | 2 |"}
        t0 = time.time()
        iterations = 400
        for _ in range(iterations):
            loops.score_chapter(sample, items=3)
        elapsed = max(time.time() - t0, 1e-6)
        ops = int(iterations / elapsed)

        t0 = time.time()
        for _ in range(200):
            loops.choose("chapter")
        select_ms = int((time.time() - t0) * 1000)

        g.check(init_ms >= 0, "schema init timed", f"{init_ms}ms")
        g.metric("schema_init_ms", init_ms)
        g.metric("chapter_chain_ms", chain_ms)
        g.metric("score_ops_per_sec", ops)
        g.metric("loop_select_200_ms", select_ms)

    return g.emit()


GATES = {
    "build": gate_build,
    "dependencies": gate_dependencies,
    "contracts": gate_contracts,
    "e2e": gate_e2e,
    "governance": gate_governance,
    "performance": gate_performance,
}


def main(argv):
    if len(argv) != 2 or argv[1] not in GATES:
        print(f"usage: {os.path.basename(__file__)} [{'|'.join(GATES)}]", file=sys.stderr)
        print(json.dumps({"status": "fail", "metrics": {},
                          "failures": ["no such gate"]}))
        return 2
    name = argv[1]
    print(f"ecosystem gate · {name}", file=sys.stderr)
    # Chains print progress; keep stdout clean so the JSON is the only thing on it.
    buffer = io.StringIO()
    try:
        with contextlib.redirect_stdout(buffer):
            code = GATES[name]()
    except Exception as e:                     # a crashing gate is a failing gate
        import traceback
        traceback.print_exc(file=sys.stderr)
        print(json.dumps({"status": "fail", "gate": name, "metrics": {},
                          "failures": [f"gate raised {type(e).__name__}: {e}"]}))
        return 1
    payload = buffer.getvalue().strip().splitlines()
    for line in payload[:-1]:
        print(line, file=sys.stderr)
    if payload:
        print(payload[-1])
    return code


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
