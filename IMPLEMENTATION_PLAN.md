# Implementation Plan — AI Enterprise Architecture Engineer (Builder) MVP

## Repository inspection

The repository is greenfield (`README.md` placeholder only; no established stack, package manager, or test harness). Blueprint paths cited in the brief (`/tasklet/agent/home/...`) are not present in this environment. **The build brief is the sole source of truth for MVP scope.**

## Chosen stack

| Layer | Choice | Rationale |
| --- | --- | --- |
| Language | TypeScript (strict) | Typed API + shared schemas between server and engines |
| Package manager | pnpm | Available in environment; workspace-friendly |
| Runtime / API | Node.js + Express | Simple typed HTTP API; local-only |
| Schemas | Zod | Versioned runtime validation for import + canonical model |
| Persistence | Local JSON file store under `data/` | Single-user workspace; no DB infra required |
| Engines | Pure deterministic TypeScript modules | Fixture/rule driven; no LLM in the path |
| LLM boundary | `LlmProvider` interface, `DisabledLlmProvider` default | Satisfies “behind an interface and disabled by default” |
| UI | React 18 + Vite + React Router | Browser journey across 7 screens |
| Tests | Vitest | Unit tests for schemas, normalization, engines, export |
| Lint / types | ESLint + `tsc --noEmit` | Acceptance: lint/type checks |

**Out of scope (explicit):** live framework adapters, auth, multi-tenancy, deployment/`apply`, secret storage, LLM-backed autonomous decisions, universal simulation.

## Product assumptions (non-blocking)

Documented so implementation does not invent unstated product behavior:

1. **Demo organization** ships as YAML under `fixtures/` with seeded defects: missing approval gate, broken/missing contract, incomplete intent fields, orphaned/unreachable topology elements.
2. **Optimization objective** defaults to `reliability_capability_coverage`; cost and latency appear only as recorded trade-offs.
3. **Approval** is local and advisory: storing `approved` / `rejected` / `draft` on a `ChangeSet` never triggers mutation or deployment.
4. **Weights** for candidate comparison are fixed constants in config (not user-tunable in MVP UI).
5. **Timestamps** use ISO-8601 UTC; IDs are `ulid`-style or prefixed UUIDs generated at import/normalize time.
6. **Export** writes Markdown + JSON into the local workspace store and returns downloadable content via API; no external publish.
7. **Knowledge objects** are a static fixture of six versioned rules used by gap/validation/review engines for citations only.

## Canonical module map

```
src/
  schemas/          Organization … IntentProfile (+ shared metadata)
  adapters/         ReadOnlyDiscoveryAdapter + MutationGuard (apply rejected)
  services/         evidence, intent completeness, workspace store
  engines/          gapAnalysis, candidateSynthesis, validation, review, export
  knowledge/        knowledgeObjects fixture loader
  llm/              disabled provider
  api/              Express routes (import → decision → history)
  web/              7 screens + evidence-type styling
fixtures/           demo org + optional traces/metrics
tests/              unit coverage per acceptance criteria
```

## Milestone map (brief → delivery)

### M1 — Plan & scaffold
- [x] Inspect repo; write this plan
- [x] Root tooling: pnpm, tsconfig, vitest, eslint, scripts
- [x] README skeleton (filled in M6)

### M2 — Schemas, persistence, demo fixtures, tests
- [x] Zod schemas for all 11 minimum entities + shared `EntityMeta`
- [x] Local JSON workspace store (orgs, evidence, intent, change history)
- [x] Demo org YAML with seeded defects + sample traces/metrics
- [x] Knowledge objects fixture (6 rules)
- [x] Schema/fixture unit tests

### M3 — Adapter + evidence/intent + organization map API
- [x] `discover` / `normalize` / `validate` on `ReadOnlyDiscoveryAdapter`
- [x] `apply` interface only; guard rejects mutation
- [x] Evidence store + provenance; intent completeness → unresolved questions
- [x] API: import, get org map, evidence inventory, intent upsert
- [x] Tests: normalization, intent completeness

### M4 — Deterministic engines + tests
- [x] Gap analysis (coverage, topology, contracts, governance, observability, recovery)
- [x] Candidate synthesis (≥2 templates: strengthen-single-workflow; planner–worker–verifier)
- [x] Declared-fidelity static + scenario validation
- [x] Independent architecture review with non-averaging critical blockers → `BLOCKED`
- [x] Recommendation + migration export (Markdown + JSON, claim chain)
- [x] Tests: gap, validation (seeded broken contract + absent approval), blocking review, export

### M5 — UI screens
- [x] Workspace / Import
- [x] Organization Map
- [x] Intent & Evidence Review
- [x] Gap Analysis
- [x] Candidates & Validation
- [x] Architecture Review & Decision (approve/export)
- [x] Change History
- [x] Visible distinction: fact / assertion / inference / simulation / recommendation

### M6 — Verification & status
- [x] Full test suite, lint, typecheck
- [x] Seeded acceptance walkthrough via API/tests
- [x] README (run, architecture diagram, security boundaries, limits, adapter roadmap)
- [x] `BUILD_STATUS.md`

## Traceability claim chain (enforced in export)

`Mission → Intent → Evidence → Knowledge → Simulation/Validation → Architecture Review → Recommendation → Approval/Outcome`

## Security / governance boundaries

- No live system credentials accepted or stored.
- Adapter `apply` always throws / returns rejected.
- Advisory-only operating mode hardcoded; export does not execute plans.
- Human approval recorded locally; absence of approval means no deployment path exists.

## Success criteria checklist

Mapped 1:1 to brief acceptance criteria; verified in M6 and reported in `BUILD_STATUS.md`.
