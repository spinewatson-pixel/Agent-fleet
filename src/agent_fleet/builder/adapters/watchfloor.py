"""Read-only Watchfloor discovery adapter.

Framework/substrate objects (registry, contracts, blueprints, council plan)
are normalized into the canonical Organization Model. Watchfloor IDs remain
canonical; this adapter never mutates the trading org.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from agent_fleet.builder.adapters.base import Adapter
from agent_fleet.registry.watchfloor import load_watchfloor_registry
from agent_fleet.schemas.organization import (
    Capability,
    EvidenceKind,
    EvidenceRef,
    GovernancePolicy,
    Interface,
    KnowledgeAsset,
    MetricDef,
    Organization,
    OrganizationSnapshot,
    TopologyEdge,
    Worker,
    WorkerKind,
)


def _root() -> Path:
    return Path(__file__).resolve().parents[4]


class WatchfloorReadOnlyAdapter(Adapter):
    adapter_id = "watchfloor_readonly"
    substrate = "custom_python_watchfloor"
    mutation_supported = False
    capability_coverage = [
        "registry_inventory",
        "authority_map",
        "hard_rules",
        "contracts",
        "blueprints",
        "council_plan",
        "topology_approval_chain",
    ]
    mapping_fidelity = "high_for_static_design_partial_for_runtime"

    def discover(self) -> dict[str, Any]:
        root = _root()
        registry = load_watchfloor_registry()
        evidence_paths = {
            "registry": root / "config" / "watchfloor_registry.json",
            "contracts": root / "docs" / "agent_contracts" / "watchfloor_contracts.json",
            "blueprints": root / "docs" / "agent_blueprints" / "blueprints.json",
            "council": root / "docs" / "council" / "enhancement_plan.json",
            "ui": root / "ui" / "watchfloor.html",
        }
        loaded: dict[str, Any] = {"registry": registry, "paths": {}}
        for key, path in evidence_paths.items():
            loaded["paths"][key] = str(path)
            if key == "registry":
                continue
            if path.exists() and path.suffix == ".json":
                loaded[key] = json.loads(path.read_text(encoding="utf-8"))
            elif path.exists():
                loaded[key] = {"exists": True, "bytes": path.stat().st_size}
            else:
                loaded[key] = None
        return loaded

    def normalize(self, discovered: dict[str, Any]) -> OrganizationSnapshot:
        registry = discovered["registry"]
        rules = registry.get("hard_rules") or {}
        counts = registry.get("counts") or {}
        evidence: list[EvidenceRef] = [
            EvidenceRef(
                evidence_id="EV-REG-001",
                kind=EvidenceKind.OBSERVED,
                source=discovered["paths"].get("registry", "config/watchfloor_registry.json"),
                integrity="file_hash_not_computed",
                confidence=0.95,
                summary=f"Registry v{registry.get('version')} · {counts.get('total_agents')} agents",
            ),
            EvidenceRef(
                evidence_id="EV-RULES-001",
                kind=EvidenceKind.OBSERVED,
                source="hard_rules",
                confidence=0.99,
                summary="paper_only=true; live_execution_enabled=false; SoD enforced",
            ),
        ]
        if discovered.get("contracts"):
            evidence.append(
                EvidenceRef(
                    evidence_id="EV-CONTRACTS-001",
                    kind=EvidenceKind.OBSERVED,
                    source=discovered["paths"].get("contracts", ""),
                    confidence=0.85,
                    summary=f"{len(discovered['contracts'])} operating contracts",
                )
            )
        if discovered.get("blueprints"):
            evidence.append(
                EvidenceRef(
                    evidence_id="EV-BP-001",
                    kind=EvidenceKind.OBSERVED,
                    source=discovered["paths"].get("blueprints", ""),
                    confidence=0.85,
                    summary=f"{len(discovered['blueprints'])} agent blueprints (25 layers)",
                )
            )
        if discovered.get("council"):
            evidence.append(
                EvidenceRef(
                    evidence_id="EV-IDC-001",
                    kind=EvidenceKind.INFERENCE,
                    source=discovered["paths"].get("council", ""),
                    confidence=0.7,
                    summary="Institutional Design Council enhancement plan present",
                )
            )

        org = Organization(
            org_id="org-watchfloor-quant-lab",
            name=registry.get("organization") or "watchfloor quant lab",
            mission=(
                "Operate a paper-only multi-agent trading laboratory with "
                "institutional separation of duties, measurable mandates, and "
                "human Mode-B governance — never silent live execution."
            ),
            scope="Paper trading organization; research, risk, governance, learning loops",
            owners=["HUMAN-1", "GOV-CHAIR"],
            stakeholders=["HUMAN-1", "GOV-CHAIR", "HEAD-TRADE", "RISK-1", "COMP-1"],
            lifecycle="operating_paper",
            criticality="high",
            environment="paper" if rules.get("paper_only") else "unknown",
            version=str(registry.get("version") or "0.0.0"),
            substrate=self.substrate,
            evidence_ids=[e.evidence_id for e in evidence],
            unresolved_intent_fields=[
                "external_capital_mandate",
                "regulatory_jurisdiction",
                "production_broker_boundary",
                "success_metric_targets_numeric",
            ],
        )

        workers = [self._worker(a, org.org_id) for a in registry.get("agents") or []]
        policies = [
            GovernancePolicy(
                policy_id="POL-HARD-RULES",
                org_id=org.org_id,
                name="Watchfloor Hard Rules",
                approval_rules=list(registry.get("approval_chain") or []),
                risk_class="trading_lab",
                data_rules=["paper_only", "no_look_ahead", "dual_source_macro"],
                budgets=[
                    f"agent_ceiling={rules.get('agent_ceiling')}",
                    f"default_sizing_usd={rules.get('default_sizing_usd')}",
                    f"compute_ceiling={rules.get('compute_ceiling')}",
                ],
                escalation=["COMP-1", "GOV-CHAIR", "SEC-HALT", "HUMAN-1"],
                audit_requirements=["MEM-1 lineage", "data/audit/events.jsonl"],
                evidence_ids=["EV-RULES-001"],
            )
        ]
        topology = self._topology(org.org_id, registry)
        interfaces = [
            Interface(
                interface_id="IF-UI-WATCHFLOOR",
                org_id=org.org_id,
                kind="ui",
                name="Watchfloor Quant Lab UI",
                schema_ref="ui/watchfloor.html",
                authentication="local_session",
                evidence_ids=["EV-REG-001"],
            ),
            Interface(
                interface_id="IF-PAPER-BROKER",
                org_id=org.org_id,
                kind="service",
                name="Paper Broker (EXEC-1 only)",
                schema_ref="agent_fleet.paper.broker",
                authentication="in_process",
                evidence_ids=["EV-RULES-001"],
            ),
            Interface(
                interface_id="IF-MSG-BUS",
                org_id=org.org_id,
                kind="event",
                name="Internal message bus",
                schema_ref="agent_fleet.schemas.messages",
                evidence_ids=["EV-REG-001"],
            ),
        ]
        knowledge = [
            KnowledgeAsset(
                knowledge_id="KN-REGISTRY",
                org_id=org.org_id,
                source="config/watchfloor_registry.json",
                ownership="GOV-CHAIR",
                freshness="rebuild_on_ui_sync",
                access_policy="repo_read",
                provenance="ui/watchfloor.html baseDivisions()",
                retrieval_behavior="load_watchfloor_registry()",
                evidence_ids=["EV-REG-001"],
            ),
            KnowledgeAsset(
                knowledge_id="KN-BLUEPRINTS",
                org_id=org.org_id,
                source="docs/agent_blueprints/blueprints.json",
                ownership="ARCH-1",
                freshness="generated",
                access_policy="repo_read",
                provenance="agent_fleet.agents.blueprints",
                retrieval_behavior="blueprints_as_dicts()",
                evidence_ids=["EV-BP-001"] if discovered.get("blueprints") else [],
            ),
            KnowledgeAsset(
                knowledge_id="KN-MEM1",
                org_id=org.org_id,
                source="MEM-1 org memory",
                ownership="MEM-1",
                freshness="runtime",
                access_policy="namespaced_writes",
                provenance="agent outputs with lineage",
                retrieval_behavior="division namespaces",
            ),
        ]
        capabilities = self._ideal_and_present_capabilities(org.org_id, registry, discovered)
        metrics = [
            MetricDef(
                metric_id="M-CEILING",
                org_id=org.org_id,
                name="Agent ceiling utilization",
                definition="total_agents / agent_ceiling",
                baseline=str(counts.get("total_agents")),
                target=f"<= {rules.get('agent_ceiling')}",
                dimensions=["governance", "capacity"],
                evidence_ids=["EV-REG-001"],
            ),
            MetricDef(
                metric_id="M-SOD",
                org_id=org.org_id,
                name="Separation of duties integrity",
                definition="proposers cannot approve/execute; only EXEC-1 places orders",
                baseline="enforced_in_registry_loader",
                target="zero_violations",
                dimensions=["safety", "governance"],
                evidence_ids=["EV-RULES-001"],
            ),
            MetricDef(
                metric_id="M-PAPER-ONLY",
                org_id=org.org_id,
                name="Live execution disabled",
                definition="live_execution_enabled == false",
                baseline=str(rules.get("live_execution_enabled")),
                target="false",
                dimensions=["safety"],
                evidence_ids=["EV-RULES-001"],
            ),
        ]

        preserve = [
            "Paper-only hard gate with live execution locked",
            "Single executor EXEC-1 after authority chain",
            "Proposers cannot self-approve or self-execute",
            "Institutional Design Council as designer/supervisor layer (no trades)",
            "25-layer blueprints for every seat",
            "Watchfloor IDs as canonical naming",
            "Mode-B human seat HUMAN-1 with veto",
            "Risk / compliance / stewardship / security veto paths",
        ]
        spof = [
            "EXEC-1 sole paper executor",
            "HUMAN-1 Mode-B overrides",
            "MEM-1 org memory write path",
            "ui/watchfloor.html as roster source of truth",
        ]
        fidelity = [
            "Static design fidelity high (registry/contracts/blueprints)",
            "Runtime behavior fidelity partial (no full production telemetry ingest in MVP)",
            "Does not model market microstructure or broker latency",
            "Simulation outputs are predictions with intervals — not facts",
        ]

        return OrganizationSnapshot(
            organization=org,
            capabilities=capabilities,
            workers=workers,
            interfaces=interfaces,
            knowledge=knowledge,
            policies=policies,
            topology=topology,
            metrics=metrics,
            evidence=evidence,
            preserve_list=preserve,
            single_points_of_failure=spof,
            adapter_id=self.adapter_id,
            fidelity_notes=fidelity,
        )

    def _worker(self, agent: dict[str, Any], org_id: str) -> Worker:
        kind = WorkerKind.HUMAN if agent.get("id") == "HUMAN-1" else WorkerKind.AGENT
        authority: list[str] = []
        if agent.get("may_propose_trades"):
            authority.append("propose_trades")
        if agent.get("may_place_orders") or agent.get("execution_role"):
            authority.append("place_paper_orders")
        perms = ["paper_only"]
        if agent.get("can_self_approve"):
            perms.append("self_approve")  # should never appear for proposers
        return Worker(
            worker_id=agent["id"],
            org_id=org_id,
            kind=kind,
            name=agent.get("nick") or agent["id"],
            responsibilities=[agent.get("role") or ""],
            authority=authority,
            model_runtime="watchfloor_python",
            permissions=perms,
            cost_profile="lab_seat",
            division=agent.get("division") or "",
            department=agent.get("department") or "",
            supervisor_id=agent.get("supervisor_id") or "",
            may_propose_trades=bool(agent.get("may_propose_trades")),
            may_place_orders=bool(agent.get("may_place_orders") or agent.get("execution_role")),
            evidence_ids=["EV-REG-001"],
        )

    def _topology(self, org_id: str, registry: dict[str, Any]) -> list[TopologyEdge]:
        edges: list[TopologyEdge] = []
        chain = registry.get("approval_chain") or []
        prev = "PROPOSER"
        for i, node in enumerate(chain):
            edges.append(
                TopologyEdge(
                    edge_id=f"E-APPROVAL-{i}",
                    org_id=org_id,
                    source_id=prev,
                    target_id=node,
                    kind="orchestration",
                    notes="authority_chain",
                    evidence_ids=["EV-RULES-001"],
                )
            )
            prev = node
        edges.append(
            TopologyEdge(
                edge_id="E-EXEC",
                org_id=org_id,
                source_id=prev,
                target_id="EXEC-1",
                kind="orchestration",
                notes="authorized paper fill only",
                evidence_ids=["EV-RULES-001"],
            )
        )
        for vid in registry.get("veto_agents") or []:
            edges.append(
                TopologyEdge(
                    edge_id=f"E-VETO-{vid}",
                    org_id=org_id,
                    source_id=vid,
                    target_id="PROPOSER",
                    kind="veto",
                    notes="can halt or reject",
                    evidence_ids=["EV-RULES-001"],
                )
            )
        return edges

    def _ideal_and_present_capabilities(
        self, org_id: str, registry: dict[str, Any], discovered: dict[str, Any]
    ) -> list[Capability]:
        ids = {a["id"] for a in registry.get("agents") or []}
        catalog = [
            ("CAP-DISCOVER", "Organization discovery & inventory", True, "strong"),
            ("CAP-INTENT", "Intent reconstruction with field confidence", False, "nascent"),
            ("CAP-AUTHORITY", "Authority / approval / veto chain", True, "strong"),
            ("CAP-SOD", "Separation of duties (propose ≠ execute)", True, "strong"),
            ("CAP-PAPER", "Paper execution with audit lineage", True, "working"),
            ("CAP-RISK", "Portfolio risk & halt", "RISK-1" in ids, "working"),
            ("CAP-RECON", "Book reconciliation", "RECON-1" in ids, "working"),
            ("CAP-EVIDENCE", "Evidence packages for quant promotion", "EVID-1" in ids, "working"),
            ("CAP-REGIME", "Regime detection", "REG-1" in ids, "working"),
            ("CAP-LEARN", "Controlled learning without auto mutation", True, "working"),
            ("CAP-BLUEPRINT", "Complete agent blueprints", bool(discovered.get("blueprints")), "strong"),
            ("CAP-CONTRACT", "Measurable operating contracts", bool(discovered.get("contracts")), "working"),
            ("CAP-SIM", "Digital twin / architecture simulation", False, "missing"),
            ("CAP-OBS", "Live architecture observability & drift", False, "nascent"),
            ("CAP-CHANGE", "Formal change-request lifecycle", False, "nascent"),
            ("CAP-AKB", "Consult Architecture Knowledge Base", "BLD-CHIEF" in ids, "working"),
            ("CAP-BUILDER", "Builder control plane + agent engineering", "BLD-ENHANCE" in ids, "working"),
            ("CAP-CEIL-GATE", "UI hard gate on agent ceiling", False, "missing"),
        ]
        out: list[Capability] = []
        for cid, purpose, present, maturity in catalog:
            if isinstance(present, str):
                present_b = present in ids
            else:
                present_b = bool(present)
            out.append(
                Capability(
                    capability_id=cid,
                    org_id=org_id,
                    purpose=purpose,
                    present=present_b,
                    maturity=maturity if present_b else "missing",
                    evaluation_criteria=["evidence_linked", "owner_assigned"],
                    evidence_ids=["EV-REG-001"],
                )
            )
        return out
