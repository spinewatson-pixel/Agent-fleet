"""Setup gate for the ecosystem stack. Run it before trusting anything here.

The point is to separate two very different kinds of "it doesn't work":

  CORE      this folder is self-contained and must stand on its own — every
            module imports, every schema applies, the agent contract actually
            refuses what it claims to refuse, and the mechanical scorers
            discriminate. A failure here is a bug in this folder.
  EXTERNAL  serve.py, nursing_api and the claude CLI are deliberately not in
            this folder. Their absence is a wiring gap, not a defect, so it is
            reported and does not fail the gate.

Exit code is 0 when CORE holds, 1 when it does not — so this can sit in front of
a run the same way `pnpm smoke` sits in front of the MVP's product path.

Standard library only, and it never touches ecosystem.db: every schema check
runs against a throwaway database in a temp directory.
"""
import importlib, os, re, shutil, sqlite3, sys, tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
MODULES = ["llm", "agentkit", "loops", "learner", "foundations", "textbook",
           "intake", "world", "nursing_agents"]
# Every module except llm owns part of the schema.
SCHEMA_MODULES = [m for m in MODULES if m != "llm"]
# Tables this folder does not create: nursing_api owns them.
FOREIGN_TABLES = ["nursing_items", "nursing_answers"]

_ok, _fail, _warn = [], [], []


def ok(msg):
    _ok.append(msg); print(f"  ok    {msg}")


def fail(msg):
    _fail.append(msg); print(f"  FAIL  {msg}")


def warn(msg):
    _warn.append(msg); print(f"  warn  {msg}")


def core_imports():
    print("\nCORE · module imports")
    mods = {}
    for name in MODULES:
        try:
            mods[name] = importlib.import_module(name)
            ok(f"{name} imports")
        except Exception as e:
            fail(f"{name}: {type(e).__name__}: {e}")
    return mods


def core_schema(mods, tmpdir):
    """Apply every schema to a throwaway DB, so the real one is never touched."""
    print("\nCORE · schema")
    db = os.path.join(tmpdir, "check.db")
    for name in SCHEMA_MODULES:
        mod = mods.get(name)
        if not mod:
            continue
        try:
            mod.DB = db                    # redirect before init, not after
            mod.init()
        except Exception as e:
            fail(f"{name}.init(): {type(e).__name__}: {e}")
            return
    with sqlite3.connect(db) as c:
        tables = sorted(r[0] for r in c.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'"))
    if len(tables) < 20:
        fail(f"only {len(tables)} tables created — expected the full schema")
    else:
        ok(f"{len(tables)} tables created across {len(SCHEMA_MODULES)} modules")


def core_contract(agentkit):
    """The contract has to refuse things, or it is decoration (rules 3, 6, 7)."""
    print("\nCORE · agent contract")
    roster = [
        agentkit.Agent("EXPERT", "Subject Expert", "p", "Write the chapter body.",
                       fn="textbook.write_chapter"),
        agentkit.Agent("GHOST", "Ghost", "p", "Look important.", fn=""),
    ]
    sound, problems = agentkit.validate(roster)
    if sound or not any("furniture" in p for p in problems):
        fail("rule 3: an agent with no callable was accepted")
    else:
        ok("rule 3: furniture rejected")

    _, err = agentkit.chain("check", roster[:1], "brief", verify=roster[0])
    if not err or "rule 6" not in err:
        fail("rule 6: an agent was allowed to verify its own work")
    else:
        ok("rule 6: self-verification refused")

    if agentkit.UNCHECKED != "unchecked":
        fail("rule 7: the default verdict is not UNCHECKED")
    else:
        ok("rule 7: UNCHECKED is the default verdict")


def core_scoring(loops):
    """A scorer that cannot tell a real review from a refusal is worthless."""
    print("\nCORE · mechanical scoring")
    real = {"body": ("word " * 1200) + "\n\n## At the bedside\n\nfindings",
            "notes": "this is inaccurate; that is an oversimplif; overstate the risk",
            "visuals": "| a | b |\n|---|---|\n| 1 | 2 |"}
    refusal = {"body": "short", "visuals": "",
               "notes": "no chapter text was included, please paste it"}
    hi, _ = loops.score_chapter(real, items=3)
    lo, _ = loops.score_chapter(refusal, items=0)
    if hi <= lo:
        fail(f"chapter scorer does not discriminate ({hi} vs {lo})")
    else:
        ok(f"chapter scorer separates a real review from a refusal ({hi} vs {lo})")

    tagged = [{"topic": "acid-base", "category": "Physiological", "stem": "a",
               "rationale": "x" * 200, "options": [1, 2, 3, 4]}]
    untagged = [{"topic": "general", "category": "Unclassified", "stem": "a",
                 "rationale": "", "options": [1, 2]}]
    if loops.score_questions(tagged)[0] <= loops.score_questions(untagged)[0]:
        fail("question scorer does not discriminate")
    else:
        ok("question scorer rewards tagged, rationalised items")

    for kind in ("chapter", "questions"):
        names = list(loops.catalogue(kind))
        if len(names) < 2:
            fail(f"{kind}: fewer than two variants — nothing to compare")
        else:
            ok(f"{kind}: {len(names)} variants in rotation ({', '.join(names)})")


def external(mods, tmpdir):
    """Everything this folder deliberately does not ship."""
    print("\nEXTERNAL · not shipped in this folder")
    try:
        importlib.import_module("nursing_api")
        ok("nursing_api importable")
    except Exception:
        warn("nursing_api not importable — courses, items and the catalogue are "
             "unavailable, so roster/terms/cycle and every course-facing call fail")

    if shutil.which("claude"):
        ok("claude CLI on PATH")
    else:
        warn("claude CLI not on PATH — every llm.ask() returns "
             "'claude CLI not found on PATH' and no agent can produce anything")

    db = os.path.join(HERE, "ecosystem.db")
    if os.path.exists(db):
        with sqlite3.connect(db) as c:
            have = {r[0] for r in c.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        missing = [t for t in FOREIGN_TABLES if t not in have]
        if missing:
            warn(f"tables owned by nursing_api are absent: {', '.join(missing)} — "
                 "tutor chat, revision and Examiner rank read these")
        else:
            ok(f"nursing_api tables present: {', '.join(FOREIGN_TABLES)}")
    else:
        warn("ecosystem.db does not exist yet — it is created on first init()")

    page = os.path.join(HERE, "study.html")
    if os.path.exists(page):
        with open(page, encoding="utf-8") as f:
            eps = sorted(set(re.findall(r"['\"](/api/[a-zA-Z0-9_/\-]+)", f.read())))
        ok(f"study.html calls {len(eps)} endpoints that serve.py must provide")
        for e in eps:
            print(f"          {e}")
    else:
        fail("study.html missing")


def main():
    print(f"ecosystem setup check · python {sys.version.split()[0]}")
    if sys.version_info < (3, 8):
        fail("python 3.8+ required")
    sys.path.insert(0, HERE)
    with tempfile.TemporaryDirectory() as tmpdir:
        mods = core_imports()
        if len(mods) == len(MODULES):
            core_schema(mods, tmpdir)
            core_contract(mods["agentkit"])
            core_scoring(mods["loops"])
        else:
            fail("skipping the rest — not every module imports")
        external(mods, tmpdir)

    print(f"\n{len(_ok)} ok · {len(_warn)} wiring gaps · {len(_fail)} failures")
    if _fail:
        print("CORE BROKEN — this folder does not stand on its own:")
        for f in _fail:
            print("  · " + f)
        return 1
    print("CORE OK" + (" — wiring gaps above are external and expected here"
                       if _warn else ""))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
