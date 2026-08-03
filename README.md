# Agent Fleet — AI Enterprise Architecture Engineer (Builder) MVP

One integrated, **read-only / advisory-only** architecture control plane. Import an AI organization, inspect the canonical model, reconstruct intent with explicit uncertainty, run deterministic gap/candidate/validation/review engines, compare baseline vs proposals, and export a cited recommendation. **No deployment or mutation of connected systems.**

## Clean clone → runnable product

```bash
git clone <repo-url> Agent-fleet
cd Agent-fleet
pnpm install
pnpm seed                 # import fixtures/demo-org.yaml into data/workspaces
pnpm dev                  # API :8787 + UI :5173
```

Open **http://localhost:5173** → Import (or open seeded workspace) → complete the journey via sidebar / step nav:

1. **Import** fixture  
2. **Organization Map** — canonical model + evidence  
3. **Intent & Evidence** — owner form; unresolved questions (no invented answers)  
4. **Gap Analysis** — run engines (also produces candidates, validation, review)  
5. **Candidates & Validation** — baseline vs proposals + declared-fidelity checks  
6. **Review & Decision** — non-averaging blockers; approve & export  
7. **Change History** — immutable local decision/export record  

Production-style single process (serves built UI from API if `dist/web` exists):

```bash
pnpm build
pnpm start                # http://localhost:8787
```

## Verified commands

```bash
pnpm install
pnpm seed
pnpm test                 # unit + HTTP e2e journey
pnpm test:e2e             # HTTP journey only
pnpm typecheck
pnpm lint
pnpm build
pnpm check                # typecheck + lint + test
pnpm verify               # full build verification for every registered ecosystem
```

## Build verification

`pnpm verify` runs the reusable verification framework across every registered
project. Each build produces build verification, dependency validation, end-to-end
simulation, contract verification, capability/governance validation, performance
metrics, a regression comparison against the last successful build, and a deployment
readiness score. A failing required gate exits non-zero with a report naming exactly
what failed, so any deployment step chained after it stops on its own. It runs in CI
on every push (`.github/workflows/verify.yml`).

Registered ecosystems: `agent-fleet` (this MVP) and `nursing-ecosystem`
(`ecosystem/`). See **[docs/VERIFICATION.md](docs/VERIFICATION.md)** for the gate
contract and how to onboard a new project.

Against a running API:

```bash
pnpm dev:api              # terminal A
pnpm smoke                # terminal B — full HTTP journey smoke
```

## Architecture

```text
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

**Claim chain:**  
`Mission → Intent → Evidence → Knowledge → Simulation/Validation → Architecture Review → Recommendation → Approval/Outcome`

## Security boundaries

| Boundary | Behavior |
| --- | --- |
| Discovery | Local JSON/YAML only |
| Mutation / `apply` | Always rejected (`POST /api/apply` → 405) |
| Secrets | Not accepted or stored |
| LLM | Interface present; disabled by default; engines do not call it |
| Approval | Local export record only — **no deployment path** |

## Current limits (honest)

- Declared-fidelity static/scenario validation — **not** full behavioral simulation
- Template-backed candidates (two), not open-ended synthesis
- Objective fixed to reliability / capability coverage; cost & latency are trade-offs
- No live LangGraph / cloud discovery; no browser automation suite (HTTP e2e covers the product path)
- JSON file store is single-process

## Adapter roadmap

1. **Now:** `ReadOnlyDiscoveryAdapter` (local JSON/YAML)  
2. **Next:** LangGraph inventory adapter (same interface)  
3. **Later:** Custom Python / service adapters  
4. **Not in MVP:** any `apply` implementation  

## Project layout

```text
fixtures/demo-org.yaml
scripts/seed.ts            Seed demo into local store
scripts/smoke.ts           Repeatable smoke against running API
src/core/                  Schemas, adapter, engines, pipeline
src/api/                   createApp + server
src/web/                   Integrated 7-screen UI
tests/e2e.http.journey.test.ts
IMPLEMENTATION_PLAN.md
BUILD_STATUS.md
```
