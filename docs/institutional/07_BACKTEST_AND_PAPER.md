# Backtesting and Paper-Trading Framework

## Backtest (Renaissance controls)
1. Hypothesis registered with features and predicted edge.  
2. In-sample fit with pre-declared parameters.  
3. Out-of-sample holdout.  
4. Walk-forward windows.  
5. Multiple-testing deflation / haircut on Sharpe.  
6. Cost model: fees + slippage bps.  
7. No peeking: calendar alignment enforced.  
8. Artifact store: code hash + data vintage + metrics.

Promotion from backtest never skips paper.

## Paper trading (initial objective)
- `OperatingOrganization.run_proposal_chain` is the unit of live-like decisioning.
- `PaperBroker` applies slippage/fees; `paper=True` required.
- `LIVE_EXECUTION_ENABLED = False` in package root.
- Full audit lineage via `correlation_id`.

## Acceptance before strategy goes `paper_active`
- Contract complete and exported.
- Unit tests for setup rule evaluation hooks.
- Risk path rejects oversized proposals.
- No execution permissions on strategy contract.
- Demo chain produces fill only after Risk+Steward.

## Missed / rejected trade logging
Every rejection stores `rejected_by` + reasons on the chain result and bus — input to learning (false positives/negatives) without self-approval.
