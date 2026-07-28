"""CLI entrypoints for Agent Fleet paper organization."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from agent_fleet.contracts.registry import build_all_contracts
from agent_fleet.messaging.schemas import OrderType, Side, TradeProposalPayload
from agent_fleet.pipeline.organization import OperatingOrganization


def cmd_org_map(_: argparse.Namespace) -> None:
    org = OperatingOrganization()
    print(json.dumps(org.org_map(), indent=2))


def cmd_export_contracts(args: argparse.Namespace) -> None:
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    contracts = build_all_contracts()
    index = []
    for agent_id, contract in contracts.items():
        path = out / f"{agent_id}.json"
        path.write_text(contract.model_dump_json(indent=2))
        index.append({"agent_id": agent_id, "name": contract.agent_name, "role": contract.role.value})
    (out / "index.json").write_text(json.dumps(index, indent=2))
    print(f"Exported {len(contracts)} contracts to {out}")


def cmd_demo_paper(_: argparse.Namespace) -> None:
    org = OperatingOrganization(nav=100_000.0)
    org.ingest_market_data("AAPL", 190.0)
    org.set_price("AAPL", 190.0, sector="Technology")
    proposal = TradeProposalPayload(
        proposal_id="demo-001",
        strategy_agent_id="STRAT-MOM-001",
        strategy_version=org.contracts["STRAT-MOM-001"].strategy_version,
        symbol="AAPL",
        side=Side.BUY,
        order_type=OrderType.LIMIT,
        limit_price=190.0,
        stop_price=180.0,
        thesis="Trend continuation after SMA50/SMA200 cross with volume confirmation",
        setup_rules_fired=["MOM-SETUP-1", "MOM-ENTRY-1"],
        invalidation_rules=["MOM-INV-1"],
        expected_holding_period="swing_weeks",
        risk_per_trade_pct_nav_request=0.004,
    )
    result = org.run_proposal_chain(proposal)
    print(
        json.dumps(
            {
                "approved": result.approved,
                "rejected_by": result.rejected_by,
                "stages": result.stages,
                "reasons": result.reasons,
                "fill": result.fill,
                "audit_messages": len(result.envelopes),
            },
            indent=2,
        )
    )


def main() -> None:
    parser = argparse.ArgumentParser(prog="agent-fleet")
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_map = sub.add_parser("org-map", help="Print organizational map")
    p_map.set_defaults(func=cmd_org_map)

    p_exp = sub.add_parser("export-contracts", help="Export agent operating contracts")
    p_exp.add_argument("--out", default="config/contracts")
    p_exp.set_defaults(func=cmd_export_contracts)

    p_demo = sub.add_parser("demo-paper", help="Run one paper proposal through the chain")
    p_demo.set_defaults(func=cmd_demo_paper)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
