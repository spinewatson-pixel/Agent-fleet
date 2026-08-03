# Build Status — Agent Fleet MVP

**Date:** 2026-08-02  
**Branch:** `cursor/mvp-architecture-control-plane-3e60`  
**PR:** https://github.com/spinewatson-pixel/Agent-fleet/pull/3  
**Source of truth:** build brief (greenfield; blueprint files not in environment)

## Enhancement pass (learned from branch)

Follow-up polish on `cursor/mvp-architecture-control-plane-3e60` without scope creep:
- Shared remediation helper (`src/core/engines/remediation.ts`) for gate/review/validation
- Import UI: demo + eligible fixtures; seed both
- Eligibility panel on Candidates & Review; claim-chain list on Review
- Validation UI separates current-state observation vs projected simulation vs assumptions
- Intent form resyncs on workspace change; owner gap categorized under governance
- Docs updated for fixture guidance

## Release-blocking repair (eligibility gate)

A **single eligibility gate** (`src/core/engines/eligibility.ts`) is now used by recommendation, review surfacing, approval, and export.

A candidate is eligible only when:
1. Validation has **zero failed checks** (`overallPass`)
2. **No unresolved critical** gap findings remain for that candidate
3. Independent review is not `BLOCKED`

If none are eligible → `selectionStatus=BLOCKED_NO_ELIGIBLE_CANDIDATE`, `chosenCandidateId=null`, explicit reasons; **no fallback** to an invalid candidate. Approve/export of a recommendation throws / HTTP 400.

Also fixed:
- Validation separates **current-state observations** from **candidate assumptions**
- Owner assertions are **medium** confidence (not high) without corroborating observation

## Exact verified commands

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
pnpm start                # or pnpm dev:api
pnpm smoke                # demo blocked + eligible fixture export
```

### Results recorded this delivery

| Command | Result |
| --- | --- |
| `pnpm test` | **25 passed** (8 files; eligibility + remediation + HTTP e2e) |
| `pnpm test:e2e` | **1 passed** — demo blocked; eligible fixture exported |
| `pnpm typecheck` | passed |
| `pnpm lint` | passed |
| `pnpm build` | passed (tsc + vite) |
| `pnpm seed` | seeds demo org (intentionally ineligible until remediated) |
| `pnpm start` + `pnpm smoke` | **SMOKE_OK** (demo blocked; eligible org exported) |

## Regression coverage (release-blocking)

| # | Case | Test |
| --- | --- | --- |
| 1 | Demo failing candidates cannot be approved/exported | `tests/eligibility.regression.test.ts` |
| 2 | Eligible validated candidate can be approved/exported | same + `fixtures/eligible-org.yaml` |
| 3 | No-candidate condition blocks cleanly with reasons | same |
| — | Owner assertion ≠ high confidence without corroboration | same |
| — | Current-state vs candidate assumptions separated | same + validation engine |

## Product path

`import → inspect canonical → intent/evidence → gaps → candidates → validation → baseline/proposal → review → **eligibility gate** → recommendation → approval/export (only if eligible)`

## Honest limitations

1. **Not a full simulator** — declared-fidelity static/scenario checks only.
2. **Candidate projected pass** may credit explicit template remediations as assumptions; those are labeled and are not current-state evidence.
3. **Demo org is intentionally ineligible** after analysis (seeded defects remain unresolved under projected validation). Use `fixtures/eligible-org.yaml` for a selectable path.
4. **No browser automation** — HTTP e2e + `pnpm smoke` cover the product path.
5. **Single-user JSON store** — not concurrent-safe; `AGENT_FLEET_DATA_DIR` override supported.
6. No live adapters / auth / multi-tenancy / deployment.

## Operating posture

**Advisory-only. Read-only discovery. Deterministic engines. Eligibility-gated recommendation/export. No deployment.**
