# 08 — Duplicate or Unnecessary Agents (Combine / Avoid)

## Combinations decided by ARCH-CHIEF-001

| Proposal | Decision | Reasoning | Dissent | Priority |
|----------|----------|-----------|---------|----------|
| Separate Portfolio vs Risk agents | **Combine** into `PORT-RISK-001` with two verdict objects | Small org; same veto owner; still emits distinct `PortfolioVerdict` + `RiskVerdict` | Citadel-ops preferred split OMS risk | P0 done |
| Separate News vs Filings agents | **Defer**; keep under `MKT-INFO-001` | Avoid duplicated normalization | Bloomberg-team wanted split desks | P2 |
| Per-strategy validators | **Reject**; single `VAL-IND-001` | Independence fails if validator sits inside strategy pod | Quant wanted specialist validators later | P0 done |
| Stewardship as “just another strategy” | **Reject** | Stewardship is a veto control, not an alpha book (though it supervises STRAT-VALUE-001) | — | P0 done |
| LLM “CEO persona” agents for each firm brand | **Reject** | Theatrical; no operational artifact | — | P0 done |

## Unnecessary anti-patterns banned

1. Strategy agent that also runs OMS  
2. Strategy agent that scores its own attribution as authoritative  
3. Experimental agent with write access to production rules  
4. Duplicate “risk chatbot” without limit math  
5. Brand-imitation agents that only role-play executives  

## If user later supplies overlapping skeletons

Merge rule: keep the contract with **stricter permissions + clearer measurable setup rules**; retire the looser duplicate to `RETIRED` deployment status.
