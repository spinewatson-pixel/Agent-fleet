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

## Pre-existing dependencies (not in this folder)

- **`serve.py`** — backend that hosts `/api/study/*` (and related nursing) routes and serves `study.html`.
- **`nursing_api`** — course catalogue (`COURSES`), question generation, weak areas, expert Q&A.

Runtime also expects the `claude` CLI on `PATH`.

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
