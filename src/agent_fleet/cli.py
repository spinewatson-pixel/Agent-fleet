"""CLI entrypoint for paper-trading organization demos and contract export."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from agent_fleet.registry.watchfloor import load_watchfloor_registry
from agent_fleet.workflow.pipeline import Organization
from agent_fleet.workflow.watchfloor_org import WatchfloorOrganization


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Agent Fleet institutional paper org")
    sub = parser.add_subparsers(dest="cmd", required=True)

    run = sub.add_parser("paper-run", help="Run a Watchfloor paper trade through the full chain")
    run.add_argument("--symbol", default="AAPL")
    run.add_argument("--price", type=float, default=190.0)
    run.add_argument("--agent", default="AAPL-L", help="Watchfloor proposer agent id")
    run.add_argument("--legacy-strategy", default="", help="Optional legacy STRAT-* path")
    run.add_argument("--conviction", type=float, default=0.75)

    exp = sub.add_parser("export-contracts", help="Export legacy agent operating contracts")
    exp.add_argument("--out", default="docs/agent_contracts/contracts.json")

    auth = sub.add_parser("authority-map", help="Print Watchfloor authority map JSON")
    reg = sub.add_parser("registry", help="Print Watchfloor registry summary")

    args = parser.parse_args(argv)

    if args.cmd == "paper-run":
        if args.legacy_strategy:
            org = Organization()
            result = org.ingest_market_event(
                symbol=args.symbol,
                price=args.price,
                conviction=args.conviction,
                strategy_hint=args.legacy_strategy,
            )
        else:
            org = WatchfloorOrganization()
            result = org.ingest_market_event(
                symbol=args.symbol,
                price=args.price,
                agent_id=args.agent,
            )
        print(json.dumps(result, indent=2, default=str))
        return 0
    if args.cmd == "export-contracts":
        org = Organization()
        path = Path(args.out)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(org.contracts(), indent=2), encoding="utf-8")
        print(f"Wrote {path}")
        return 0
    if args.cmd == "authority-map":
        registry = load_watchfloor_registry()
        print(
            json.dumps(
                {
                    "veto_agents": registry["veto_agents"],
                    "approval_chain": registry["approval_chain"],
                    "hard_rules": registry["hard_rules"],
                    "institutional_council_map": registry["institutional_council_map"],
                    "counts": registry["counts"],
                },
                indent=2,
            )
        )
        return 0
    if args.cmd == "registry":
        registry = load_watchfloor_registry()
        print(json.dumps(registry["counts"], indent=2))
        return 0
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
