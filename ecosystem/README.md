# Nursing OS / Ecosystem

Study + agent stack for an accelerated BSN program. **Python standard library only** — no pip installs.

## Layout

| File | Role |
| --- | --- |
| `llm.py` | Shared Claude CLI plumbing. Read first — prompting rules here are why the rest works. |
| `agentkit.py` | Agent contract (nine failure modes → helpers). Build on `Agent` + `chain()`. |
| `loops.py` | Chain variants, mechanical scoring, Mentor. |
| `nursing_agents.py` | 15 roles × courses; rank counted from the DB. |
| `learner.py` | Learner model: profile, per-topic depth, chat / notes / revise. |
| `foundations.py` | Science each course assumes but never teaches. |
| `textbook.py` | Per-course textbook author chain. |
| `intake.py` | Uploads → curate → extract → verify → knowledge cards. |
| `world.py` | Scouts search the live web for real problems, then work them. |
| `study.html` | UI: terms → courses → agent count → agent squares. |

## Setup check

```bash
python3 ecosystem/setup_check.py
```

Exits `0` when this folder stands on its own and `1` when it does not. It separates two
different failures: **core** (a bug in this folder) from **wiring gaps** (the pieces
deliberately not shipped here). It runs schema checks against a throwaway database, so
`ecosystem.db` is never touched.

Verified on this machine (Python 3.12.3): 9/9 modules import, 23 tables apply across 8
modules, the contract refuses furniture and self-verification, `UNCHECKED` is the default
verdict, and both mechanical scorers discriminate (chapter 1.0 vs 0.088 for a refusal).

## Pre-existing dependencies (not in this folder)

| Dependency | What breaks without it |
| --- | --- |
| `serve.py` | Nothing serves the 26 endpoints `study.html` calls, so the UI cannot load. |
| `nursing_api` | `COURSES`, item generation, weak areas and expert Q&A are missing, so roster / terms / cycle and every course-facing call fail. |
| `nursing_items`, `nursing_answers` tables | Owned by `nursing_api`. Tutor chat, item revision and Examiner rank read them. |
| `claude` CLI on `PATH` | Every `llm.ask()` returns `claude CLI not found on PATH`, so no agent produces anything. |

`setup_check.py` prints the full endpoint list `serve.py` must provide.

## Two rules everything obeys

1. **Task, context, and JSON schema go in the USER turn**, never only in `--append-system-prompt`. Appended system text gets diluted and ignored.
2. **In a multi-stage chain the carry ACCUMULATES.** Replacing it means a later agent never sees what earlier ones produced.

## Local data (created at runtime)

- `ecosystem.db` — SQLite state for agents, loops, learner, foundations, textbooks, intake, world
- `library/` — filed upload copies
- `assets/` — chapter media
- `textbook_<CODE>.html` — rendered books

## Operator-initiated only

Nothing schedules. Cycles, intake, sweeps, and ingest run when called and then stop.
