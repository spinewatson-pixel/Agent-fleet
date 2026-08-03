"""CLI entrypoint for paper-trading organization demos and contract export."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from agent_fleet.agents.blueprints import blueprints_as_dicts, incomplete_blueprint_ids
from agent_fleet.agents.watchfloor_contracts import contracts_as_dicts
from agent_fleet.council import InstitutionalDesignCouncil, plan_to_markdown
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

    exp = sub.add_parser("export-contracts", help="Export agent operating contracts")
    exp.add_argument("--out", default="docs/agent_contracts/contracts.json")
    exp.add_argument(
        "--watchfloor",
        action="store_true",
        help="Export Watchfloor proposer contract stubs instead of legacy STRAT-*",
    )

    auth = sub.add_parser("authority-map", help="Print Watchfloor authority map JSON")
    reg = sub.add_parser("registry", help="Print Watchfloor registry summary")

    enhance = sub.add_parser(
        "enhance",
        help="Run Institutional Design Council audits and write enhancement plan",
    )
    enhance.add_argument(
        "--out-dir",
        default="docs/council",
        help="Directory for enhancement_plan.json and enhancement_plan.md",
    )
    enhance.add_argument(
        "--stdout",
        action="store_true",
        help="Also print a short task summary to stdout",
    )

    bp = sub.add_parser(
        "blueprints",
        help="Export 8-layer expert blueprints for every Watchfloor agent",
    )
    bp.add_argument("--out", default="docs/agent_blueprints/blueprints.json")

    builder = sub.add_parser(
        "builder",
        help="AI Enterprise Architecture Engineer — advisory control plane",
    )
    builder_sub = builder.add_subparsers(dest="builder_cmd", required=True)
    b_run = builder_sub.add_parser("run", help="Full discover→analyze→recommend loop (export only)")
    b_run.add_argument("--out-dir", default="docs/builder")
    b_run.add_argument(
        "--objective",
        default="governance_and_reliability",
        help="Optimization objective for candidate ranking",
    )
    builder_sub.add_parser("discover", help="Read-only Watchfloor discovery → snapshot JSON")
    builder_sub.add_parser("analyze", help="Intent + gap analysis + AKB consultation")
    builder_sub.add_parser("decisions", help="Print settled MVP product decisions")
    b_rec = builder_sub.add_parser("recommend", help="Emit recommendation contract JSON")
    b_rec.add_argument("--objective", default="governance_and_reliability")

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
        path = Path(args.out)
        path.parent.mkdir(parents=True, exist_ok=True)
        if args.watchfloor:
            if path.name == "contracts.json":
                path = Path("docs/agent_contracts/watchfloor_contracts.json")
                path.parent.mkdir(parents=True, exist_ok=True)
            payload = contracts_as_dicts()
            path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
            print(
                json.dumps(
                    {
                        "wrote": str(path),
                        "agents": len(payload),
                        "proposers": sum(
                            1
                            for c in payload.values()
                            if c.get("execution", {}).get("may_propose_trades")
                        ),
                    },
                    indent=2,
                )
            )
        else:
            org = Organization()
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
    if args.cmd == "enhance":
        council = InstitutionalDesignCouncil()
        plan = council.run()
        out_dir = Path(args.out_dir)
        out_dir.mkdir(parents=True, exist_ok=True)
        json_path = out_dir / "enhancement_plan.json"
        md_path = out_dir / "enhancement_plan.md"
        json_path.write_text(json.dumps(plan.to_dict(), indent=2), encoding="utf-8")
        md_path.write_text(plan_to_markdown(plan), encoding="utf-8")
        summary = {
            "wrote": [str(json_path), str(md_path)],
            "teams": [t.team_id for t in council.teams],
            "finding_count": len(plan.findings),
            "veto_count": len(plan.vetoes),
            "task_counts": {k: len(v) for k, v in plan.tasks_by_priority.items()},
            "p0_titles": [t["title"] for t in plan.tasks_by_priority.get("P0", [])],
        }
        print(json.dumps(summary, indent=2))
        if args.stdout:
            print(plan_to_markdown(plan))
        return 0
    if args.cmd == "blueprints":
        path = Path(args.out)
        path.parent.mkdir(parents=True, exist_ok=True)
        payload = blueprints_as_dicts()
        path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        print(
            json.dumps(
                {
                    "wrote": str(path),
                    "agents": len(payload),
                    "incomplete": incomplete_blueprint_ids(),
                    "layers": [
                        "Identity",
                        "Goal",
                        "Responsibilities",
                        "Functions",
                        "Tools",
                        "Capabilities",
                        "Memory",
                        "Knowledge Base",
                        "Skills",
                        "Workflows",
                        "Decision Rules",
                        "Communication",
                        "Inputs",
                        "Outputs",
                        "Learning",
                        "Evaluation",
                        "Permissions",
                        "Constraints",
                        "Triggers",
                        "Scheduling",
                        "Logging",
                        "Self-Reflection",
                        "Escalation",
                        "Versioning",
                        "Health Monitoring",
                    ],
                },
                indent=2,
            )
        )
        return 0
    if args.cmd == "builder":
        from agent_fleet.builder import BuilderControlPlane, decisions_as_dict

        plane = BuilderControlPlane()
        if args.builder_cmd == "decisions":
            print(json.dumps(decisions_as_dict(), indent=2))
            return 0
        if args.builder_cmd == "discover":
            snap = plane.discover()
            print(json.dumps(snap.to_dict(), indent=2, default=str))
            return 0
        if args.builder_cmd == "analyze":
            print(json.dumps(plane.analyze(), indent=2, default=str))
            return 0
        if args.builder_cmd == "recommend":
            rec = plane.recommend(objective=args.objective)
            print(json.dumps(rec.to_dict(), indent=2, default=str))
            return 0
        if args.builder_cmd == "run":
            summary = plane.run(objective=args.objective, out_dir=args.out_dir)
            print(json.dumps(summary, indent=2))
            return 0
        return 1
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
