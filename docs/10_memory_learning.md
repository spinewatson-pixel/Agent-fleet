# 10 — Memory and Learning Architecture

## Separated environments

| Bucket | Purpose | May alter production rules? |
|--------|---------|-----------------------------|
| `paper` | Paper org observations | No |
| `experimental` | Research sandboxes | No |
| `production` | Live-promoted artifacts only | Only via approved improvement sequence |

Enforced in `MemoryStore` (`src/agent_fleet/core/memory.py`).

## What the organization learns from

research conclusions · predictions · approved trades · rejected trades · missed trades · execution quality · profits · losses

## Controlled improvement sequence (mandatory)

```
documented
  → statistical_test
  → out_of_sample
  → paper_trade
  → risk_review
  → versioned
  → approved
  → gradual_deploy
```

`ImprovementProposal.production_mutation_allowed` defaults **false**.  
`LEARN-001` records attribution and emits propose-only artifacts.

## Experimental agents

- No unrestricted capital  
- No write path to production rules / live limits  
- Must run under `Environment.EXPERIMENTAL` or `PAPER`

## Versioning

Each strategy contract carries `strategy_version`. Promoted changes bump version; old version remains addressable for attribution.
