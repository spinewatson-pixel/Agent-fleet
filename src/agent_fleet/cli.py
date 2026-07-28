"""CLI entrypoint for paper-trading organization demos and contract export."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from agent_fleet.workflow.pipeline import Organization


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Agent Fleet institutional paper org")
    sub = parser.add_subparsers(dest="cmd", required=True)

    run = sub.add_parser("paper-run", help="Run a paper trade through the full chain")
    run.add_argument("--symbol", default="AAPL")
    run.add_argument("--price", type=float, default=190.0)
    run.add_argument("--strategy", default="STRAT-MOM-001")
    run.add_argument("--conviction", type=float, default=0.75)

    exp = sub.add_parser("export-contracts", help="Export all agent operating contracts")
    exp.add_argument("--out", default="docs/agent_contracts/contracts.json")

    auth = sub.add_parser("authority-map", help="Print authority map JSON")

    args = parser.parse_args(argv)
    org = Organization()

    if args.cmd == "paper-run":
        result = org.ingest_market_event(
            symbol=args.symbol,
            price=args.price,
            conviction=args.conviction,
            strategy_hint=args.strategy,
        )
        print(json.dumps(result, indent=2, default=str))
        return 0
    if args.cmd == "export-contracts":
        path = Path(args.out)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(org.contracts(), indent=2), encoding="utf-8")
        print(f"Wrote {path}")
        return 0
    if args.cmd == "authority-map":
        print(json.dumps(org.authority_map(), indent=2))
        return 0
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
