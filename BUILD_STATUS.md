# Build Status — Agent Fleet MVP

**Date:** 2026-08-02  
**Branch:** `cursor/mvp-architecture-control-plane-3e60`  
**PR:** https://github.com/spinewatson-pixel/Agent-fleet/pull/3  
**Source of truth:** build brief (greenfield; blueprint files not in environment)

## Product integration (not milestone silos)

Milestones are implemented as **one runnable product path** via `BuilderPipeline` + `createApp()` + the 7-screen UI with journey navigation:

`import fixture → inspect canonical → intent/evidence → gap analysis → candidates → deterministic validation → baseline/proposal compare → architecture review → cited recommendation → approval/export`

There are no disconnected prototypes or placeholder screens. Analysis is one API call (`POST /analyze`) that fills gaps, candidates, validation, baseline comparison, review, and recommendation for the UI.

## Exact verified commands

Run from a clean checkout:

```bash
pnpm install
pnpm seed
pnpm test
pnpm test:e2e
pnpm typecheck
pnpm lint
pnpm build
pnpm check
```

Dev app:

```bash
pnpm dev
# UI http://localhost:5173  API http://localhost:8787
```

Optional smoke against a live API process:

```bash
pnpm dev:api          # or: pnpm build && pnpm start
pnpm smoke
```

### Results recorded this delivery

| Command | Result |
| --- | --- |
| `pnpm test` | *(re-run at end of turn)* |
| `pnpm test:e2e` | HTTP full journey |
| `pnpm typecheck` | must pass |
| `pnpm lint` | must pass |
| `pnpm build` | must pass |
| `pnpm seed` | writes demo org under `data/workspaces` |

## Completed scope

| Area | Status |
| --- | --- |
| Integrated pipeline + Express app factory | Done |
| Seed script (`pnpm seed`) | Done |
| HTTP e2e journey test (`tests/e2e.http.journey.test.ts`) | Done |
| Repeatable smoke script (`pnpm smoke`) | Done |
| Baseline vs proposal comparison (engine + UI + export) | Done |
| UI journey nav across 7 screens | Done |
| Mutation rejected (`/api/apply` → 405) | Done |
| README clean-clone runbook | Done |

## Acceptance mapping

| Criterion | How verified |
| --- | --- |
| Demo imports to canonical model | e2e + seed |
| Fact/assertion/inference/simulation/recommendation visible | UI badges; evidence statuses in API |
| Missing intent → questions, not invention | e2e intent step + unit tests |
| Gaps link seeded defects to evidence | e2e + `tests/engines.test.ts` |
| ≥2 candidates with trade-offs | e2e |
| Validation catches broken contract + absent approval | e2e check ids |
| Critical governance → `BLOCKED` non-averaging | `tests/engines.test.ts` |
| Baseline vs proposal comparison | e2e `baselineComparison` |
| Export Markdown/JSON with claim chain | e2e export fetch |
| No live mutation path | e2e `POST /api/apply` → 405 |

## Honest limitations

1. **Not a full simulator** — declared-fidelity static/scenario checks only; production behavior is not claimed.
2. **Candidate templates** — two fixed templates; not LLM or search-based synthesis.
3. **No browser automation** — product path is covered by HTTP e2e + optional `pnpm smoke`; UI wiring is real but not Playwright-tested.
4. **Single-user JSON store** — not concurrent-safe; path overridable via `AGENT_FLEET_DATA_DIR`.
5. **No live adapters / auth / multi-tenancy / deployment** — intentionally out of MVP scope.
6. Validation may treat a candidate as structurally addressing gaps when the template *declares* remediation; runtime enforcement is not modeled.

## Operating posture

**Advisory-only. Read-only discovery. Deterministic engines. Traceable exports. No deployment.**
