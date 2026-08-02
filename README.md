# Agent Fleet — AI Enterprise Architecture Engineer (Builder) MVP

Read-only, advisory-first architecture control plane for AI organizations. Import a workflow description, reconstruct intent with explicit uncertainty, identify gaps, compare candidate improvements, run declared-fidelity checks, and export a traceable recommendation. **It does not deploy, mutate connected systems, or act as an autonomous worker.**

## Quick start

```bash
pnpm install
pnpm dev          # API :8787 + UI :5173
# or separately:
pnpm dev:api
pnpm dev:web
```

Checks:

```bash
pnpm test
pnpm typecheck
pnpm lint
pnpm check        # typecheck + lint + test
```

Production-ish local serve (build UI, then API serves `dist/web`):

```bash
pnpm build
pnpm start
```

Open `http://localhost:5173` in dev (proxies `/api` → `:8787`). Load **demo organization** from the Import screen.

## Architecture

```text
┌─────────────┐   YAML/JSON    ┌──────────────────────────┐
│  Browser UI │ ─────────────► │ Express API (advisory)   │
│  7 screens  │ ◄───────────── │  /api/workspaces/*       │
└─────────────┘   snapshots    └────────────┬─────────────┘
                                            │
                               ┌────────────▼─────────────┐
                               │ BuilderPipeline          │
                               │  adapter → intent → gap  │
                               │  → candidates → validate │
                               │  → review → export       │
                               └────────────┬─────────────┘
                                            │
                    ┌───────────────────────┼───────────────────────┐
                    ▼                       ▼                       ▼
           ReadOnlyDiscoveryAdapter   Deterministic engines   JSON workspace store
           (discover/normalize/       (gap, candidates,       (data/workspaces)
            validate; apply REJECT)    validation, review)
```

**Claim chain (exported):**  
`Mission → Intent → Evidence → Knowledge → Simulation/Validation → Architecture Review → Recommendation → Approval/Outcome`

## Security boundaries

| Boundary | MVP behavior |
| --- | --- |
| Discovery | Read-only local JSON/YAML only |
| `apply` / mutation | Interface defined; always rejected (`MutationRejectedError` / `POST /api/apply` → 405) |
| Secrets | Not accepted or stored |
| LLM | `LlmProvider` interface present; `DisabledLlmProvider` default; engines do not call it |
| Approval | Local draft/approved/rejected/exported record only — **no deployment path** |
| Tenancy | Single local workspace (`data/`) |

## Current limits

- Declared-fidelity static/scenario validation — **not** full behavioral simulation
- Template-backed candidates (two templates), not open-ended synthesis
- Optimization objective fixed to reliability / capability coverage; cost & latency are trade-offs
- No live LangGraph / custom-Python / cloud discovery
- Knowledge base is a small cited fixture (6 rules), not the full research corpus

## Adapter roadmap

1. **Now:** `ReadOnlyDiscoveryAdapter` (generic local JSON/YAML)
2. **Next:** LangGraph inventory adapter implementing the same `discover/normalize/validate` interface
3. **Later:** Custom Python / service adapters
4. **Not in MVP:** any `apply` implementation — mutation remains guarded until a future governed release

## Project layout

```text
fixtures/demo-org.yaml     Seeded demo with intentional defects
src/core/schemas           Zod canonical model
src/core/adapters          Read-only adapter + mutation guard
src/core/engines           Gap, candidates, validation, review, export
src/core/services          Intent completeness + workspace store
src/api                    Express API
src/web                    React UI (7 screens)
tests/                     Vitest unit + acceptance slice
IMPLEMENTATION_PLAN.md     Stack + milestone map
BUILD_STATUS.md            Delivery status
```

## License

Private / as designated by repository owners.
