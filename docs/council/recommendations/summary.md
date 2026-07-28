# Council Team Recommendations (Operational, Non-Theatrical)

Each entry is a concrete architecture decision — not role-play dialogue.

## SYS-INTEL-001 (Palantir-inspired)
- **Decision:** Every handoff is a `MessageEnvelope` with lineage + audit append.
- **Task:** Maintain decision graph in `SystemsIntelligenceAgent.graph`.

## MKT-INFO-001 (Bloomberg-inspired)
- **Decision:** `MarketEvent` with `source_verified` gate; unverified dropped.
- **Task:** Phase 2 vendor adapters implementing same schema.

## AI-INFRA-001 (NVIDIA-inspired)
- **Decision:** Phase 0/1 deterministic local execution; model router interface reserved.
- **Task:** Add latency/health metrics endpoint in Phase 1.

## PORT-RISK-001 (BlackRock-inspired)
- **Decision:** Binding exposure limits; strategies only suggest size.
- **Task:** Correlation cluster engine Phase 3; halt flags Phase 1.

## TRADE-OPS-001 (Citadel-inspired)
- **Decision:** Single paper OMS (`EXEC-OMS-001`); regime label owned by ops.
- **Task:** Slippage ledger & multi-strategy schedule Phase 1–2.

## QUANT-RES-001 (Renaissance-inspired)
- **Decision:** Promotion requires OOS + walk-forward; LEARN cannot auto-mutate.
- **Task:** Backtest factory Phase 3.

## FUND-RES-001 (Goldman-inspired)
- **Decision:** Only `ResearchSignal` crosses into strategies.
- **Task:** Sector/macro/earnings research playbooks Phase 2.

## GOV-OPS-001 (JPMorgan-inspired)
- **Decision:** Org shutdown switch; permission checks before approval finalize.
- **Task:** Incident runbooks + reconciliation Phase 2.

## CAP-STEW-001 (Berkshire-inspired)
- **Decision:** Veto short-horizon low-conviction and sub-hurdle edge.
- **Task:** Quality/valuation service feeding STRAT-VALUE-001 Phase 2.
