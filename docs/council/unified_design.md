# Institutional Design Council — Unified Design Decision

**Chair:** ARCH-CHIEF-001 (Chief Architecture Agent)  
**Veto seats:** PORT-RISK-001, GOV-OPS-001, CAP-STEW-001  
**Status:** Adopted for Phase 0/1 paper organization

## Process executed

1. Each institutional team audited the empty repository (see `docs/00_audit.md`).  
2. Each submitted missing capabilities / weaknesses / unsafe permissions.  
3. Teams cross-critiqued (portfolio-vs-risk split, signal schema wars, stewardship vs short-horizon).  
4. Chair unified into one design.  
5. Risk, governance, and stewardship vetoed any path where strategies self-approve, self-execute, self-limit, or self-grade.  

## Concrete decisions (each with artifact)

| Decision | Artifact | Priority |
|----------|----------|----------|
| MessageEnvelope + typed payloads | `schemas/messages.py` | P0 |
| AuthorityResolver + veto chain | `core/authority.py` | P0 |
| AgentOperatingContract schema | `schemas/contracts.py` | P0 |
| Eight strategy contracts | `agents/strategy/` | P0 |
| Institutional supervisors | `agents/institutional.py` | P0 |
| Paper operating pipeline | `workflow/pipeline.py` | P0 |
| Memory env separation | `core/memory.py` | P0 |
| Live execution hard-disable | package + broker + org init | P0 |
| Controlled improvement sequence | contracts + LEARN-001 | P0 |
| Phased rollout + acceptance gates | `docs/12_*`, `docs/13_*` | P0 |

## Dissenting views retained

- **Trading Ops:** wanted earlier live microstructure hooks → deferred to Phase 5; paper OMS only.  
- **Quant:** wanted per-strategy validators → rejected for independence; revisit at scale.  
- **Market Info:** wanted immediate vendor split desks → deferred; single MKT-INFO supervisor.  
- **Stewardship:** preferred retiring MR entirely → retained with veto on low edge/conviction.

## Supporting evidence

- Repo audit: no prior agents to preserve beyond name.  
- User mandate: propose ≠ approve ≠ execute ≠ review.  
- Operating chain explicitly specified by user.  
- Paper-first objective with live disabled.

## Implementation priority order

P0 (this change) → Phase 1 hardening → data adapters → backtest factory → human review → limited live only with explicit authorization.
