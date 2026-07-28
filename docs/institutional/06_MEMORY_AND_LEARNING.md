# Memory and Learning Architecture

## Memory classes
| Memory | Owner | Contents | Retention |
|---|---|---|---|
| Audit log | MessageBus | All envelopes | Hot deque; persist in Phase 1 |
| Contract versions | GOV / SYS-ORCH | Operating contracts | Immutable versions |
| Feature/signal store | RSH-QUANT | Features, signals | Research DB |
| Proposal/outcome | REV-ATTR | Proposals, rejects, fills, PnL | Trade ledger |
| Incident memory | GOV-COMP | Halts, violations | Permanent |
| Experimental artifacts | LEARN-CTRL | Change requests, metrics | Isolated env |

## What the organization learns from
Research notes, predictions/signals, approved trades, rejected trades, missed trades (logged no-bid), execution quality, profits, losses.

## Controlled improvement state machine
`documented → statistical_test → out_of_sample_test → paper_trade → risk_review → version → approve → gradual_deploy`

Implemented in `src/agent_fleet/memory/learning.py`.

### Hard constraints
- Agents may **propose** changes; may **not** alter production rules directly.
- Experimental agents never access unrestricted capital.
- Production rule deploy requires RISK-APPR-001 + GOV-COMP-001 in approvals.
- Transitions must be sequential; skipping stages raises errors.

## Separation
| Environment | May trade | May change prod rules |
|---|---|---|
| backtest | simulated | no |
| experimental | paper sandbox | no |
| paper | paper org capital | no |
| production | only when live enabled | only via approved change |
