# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

Agent Fleet is a **read-only / advisory-only** AI enterprise architecture control plane (MVP). It imports a description of an AI organization (capabilities, workers, interfaces, governance policies, topology), reconstructs canonical + intent models, runs deterministic gap/candidate/validation/review engines, compares baseline vs proposed architectures, and produces a cited, human-approved export. **It never deploys or mutates any connected system** — `apply()` is permanently rejected everywhere it appears in the codebase.

## Commands

```bash
pnpm install
pnpm seed                 # import fixtures/demo-org.yaml into data/workspaces
pnpm dev                  # API :8787 + UI :5173 concurrently
pnpm dev:api              # API only (tsx watch)
pnpm dev:web              # UI only (vite)
pnpm build                # tsc -p tsconfig.build.json && vite build
pnpm start                # NODE_ENV=production tsx src/api/server.ts (serves dist/web if built)
pnpm test                 # vitest run — all unit + HTTP e2e tests
pnpm test:e2e             # vitest run tests/e2e.http.journey.test.ts only
pnpm test:watch           # vitest watch mode
pnpm typecheck             # tsc --noEmit for both tsconfig.json (node) and tsconfig.web.json (browser)
pnpm lint                 # eslint . --ext .ts,.tsx
pnpm check                # typecheck + lint + test — run before considering work done
pnpm smoke                # scripts/smoke.ts — full HTTP journey against a running API (needs `pnpm start`/`pnpm dev:api` in another terminal)
```

Run a single test file: `pnpm vitest run tests/engines.test.ts`. Run a single test by name: `pnpm vitest run -t "test name substring"`.

`AGENT_FLEET_DATA_DIR` overrides the JSON workspace store location (defaults to `data/workspaces`); tests and scripts use this to isolate fixtures.

## Architecture

```
Browser UI (7 screens + journey nav)
        │  /api/*
        ▼
Express createApp() ──► BuilderPipeline (single product path)
        │                      │
        │         discover → normalize → intent → gaps
        │         → candidates → validation → baseline compare
        │         → review → recommendation → export
        ▼
JSON workspace store (data/workspaces)   ReadOnlyDiscoveryAdapter
                                         apply() permanently rejected
```

Claim chain enforced end-to-end and asserted in exports/tests: `Mission → Intent → Evidence → Knowledge → Simulation/Validation → Architecture Review → Recommendation → Approval/Outcome`.

### `src/core` — the product path (framework-free TypeScript)

- **`schemas/`** — Zod schemas for the canonical model (`entities.ts`: Organization, Capability, Worker, Interface, KnowledgeMemory, GovernancePolicy, Topology, Metric, Evidence, ChangeSet, IntentProfile, CanonicalOrganization) plus shared metadata (`common.ts`: `EntityMetaSchema`, `EvidenceStatus` enum `observation|assertion|inference|simulation|recommendation`, `Confidence` enum, `MVP_CONFIG`). Every entity extends `EntityMetaSchema` (id, schemaVersion, timestamps, ownerIds, evidenceIds) so provenance is always traceable.
- **`adapters/`** — `ReadOnlyDiscoveryAdapter` (`discover` → `normalize` → `validate`) turns raw JSON/YAML input into a `CanonicalOrganization`, generating `Evidence` records with a `status`/`confidence` as it goes. `mutationGuard.ts` provides `rejectMutation()` — the adapter's `apply()` and the `/api/apply` route both call it and always throw/405. Never implement a working `apply()`.
- **`engines/`** — pure, deterministic functions, no LLM calls:
  - `gapAnalysis.ts` — coverage/topology/contract/governance/observability/recovery findings, each with a `severity` (`critical` is the one that matters for eligibility).
  - `candidateSynthesis.ts` — produces ≥2 template-backed `CandidateArchitecture`s (not open-ended synthesis) from gaps + intent.
  - `validation.ts` — declared-fidelity static/scenario checks per candidate (`ValidationResult.overallPass`, `checks[]`). Keeps current-state **observations** separate from candidate **assumptions** — do not blur this distinction when editing.
  - `review.ts` — independent architecture review per candidate; can set `status: "BLOCKED"` with non-averaging `blockers[]` that cannot be outweighed by a high `weightedScore`.
  - `eligibility.ts` — **the single gate** used everywhere a candidate is selected or approved. A candidate is eligible only if: validation `overallPass` with zero failed checks, no unresolved critical gap findings, and review not `BLOCKED`. No eligible candidate → `selectionStatus="BLOCKED_NO_ELIGIBLE_CANDIDATE"`, `chosenCandidateId=null`, and there is **no fallback to an invalid candidate**. `assertEligibleForApprovalExport` re-runs this gate at approval time so a stale/tampered `chosenCandidateId` can never be approved — `BuilderPipeline.approveAndExport` always re-checks rather than trusting a previously computed recommendation.
  - `baselineComparison.ts` — baseline vs proposal comparison.
  - `recommendAndExport.ts` — builds the `RecommendationResult` (embeds the eligibility gate) and renders Markdown + JSON export artifacts carrying the claim chain.
  - `index.ts` re-exports all of the above; import engines from `./engines/index.js` where convenient.
- **`services/`** — `workspaceStore.ts` (`JsonFileWorkspaceStore`: one JSON file per organization under `data/workspaces`, single-process, not concurrency-safe) and `intentCompleteness.ts` (turns partial owner-supplied intent into `unresolvedQuestions` rather than inventing answers).
- **`knowledge/knowledgeObjects.ts`** — static fixture of versioned rules cited by engines (served at `/api/knowledge`).
- **`pipeline.ts`** — `BuilderPipeline` is the single orchestrator (`importDemo`/`importFixture`/`importRaw` → `updateIntent` → `runAnalysis` → `approveAndExport`). This is the class to extend for new product steps; the API layer is a thin wrapper around it.

### `src/llm` — disabled by default

`LlmProvider` interface + `DisabledLlmProvider` (throws on `complete()`). Deterministic engines must never call this. If wiring in a real provider, it must stay behind this interface and off by default; nothing in `engines/` should depend on `llmEnabled` being true.

### `src/api`

`createApp.ts` builds the Express app: CORS, JSON + YAML body parsing, routes under `/api/workspaces/*` for import/intent/analyze/decision/exports, `/api/health`, `/api/config`, `/api/knowledge`, and `/api/apply` (always 405 via `rejectMutation`). Serves `dist/web` as static files when present (production single-process mode). `server.ts` is the thin entrypoint that calls `createApp()` and listens.

### `src/web`

React 18 + Vite + React Router, 7 screens under `screens/` matching the product journey (Import → Organization Map → Intent & Evidence → Gap Analysis → Candidates & Validation → Review & Decision → Change History). `App.tsx` holds workspace state in a context (`WorkspaceCtx`), persists the active workspace id to `localStorage`, and fetches via `api.ts`. UI must visibly distinguish evidence types (fact/assertion/inference/simulation/recommendation) — see `EvidenceBadge.tsx`.

### Path aliases

`@core/*` maps to `src/core/*` in `tsconfig.json`, `vite.config.ts`, and `vitest.config.ts` — use it from `src/web` instead of relative `../../core` paths.

## Conventions worth knowing before editing

- **Eligibility is centralized.** Any code path that selects, approves, or exports a candidate must go through `eligibility.ts`'s gate (`runEligibilityGate` / `assertEligibleForApprovalExport`), not reimplement the pass/fail logic locally.
- **Evidence provenance is mandatory.** New data entering the canonical model (owner form input, imported fields, engine outputs) should be recorded as an `Evidence` entry with an honest `status` and `confidence` — e.g. owner-submitted form fields are `status: "assertion"`, `confidence: "medium"` (not `"high"`) unless corroborated by an observation.
- **Two build targets, two tsconfigs.** `tsconfig.build.json` compiles only `src/core`, `src/api`, `src/llm` (server bundle, excludes `src/web` and `tests`). `tsconfig.web.json` type-checks only `src/web` against DOM/vite types. `pnpm typecheck` runs both. Keep server code out of `src/web` type scope and vice versa.
- **No `any`, unused vars are errors** (`.eslintrc.cjs`): `@typescript-eslint/no-explicit-any: error`, `no-unused-vars: error` (prefix intentionally-unused args with `_`).
- **Tests mirror the product path**, not files 1:1: `schemas.test.ts`, `adapter.test.ts`, `intent.test.ts`, `engines.test.ts`, `eligibility.regression.test.ts` (release-blocking regressions), `pipeline.test.ts`, `e2e.http.journey.test.ts`. When changing eligibility/validation/review behavior, check `eligibility.regression.test.ts` first — it encodes the release-blocking acceptance cases.
- **Fixtures encode two states on purpose**: `fixtures/demo-org.yaml` is intentionally ineligible (seeded defects: missing approval gate, broken/missing contract, incomplete intent) to exercise the blocked path; `fixtures/eligible-org.yaml` is the selectable/approvable path. Don't "fix" the demo fixture into eligibility — that would remove the regression coverage.
