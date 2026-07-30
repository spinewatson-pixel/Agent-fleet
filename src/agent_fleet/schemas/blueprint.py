"""Complete Agent Blueprint — structural + operating + control layers.

Structural:
  Identity · Goal · Responsibilities · Functions · Tools · Capabilities · Memory · Knowledge Base

Operating:
  Skills · Workflows · Decision Rules · Communication · Inputs · Outputs · Learning · Evaluation · Permissions

Control / runtime:
  Constraints · Triggers · Scheduling · Logging · Self-Reflection · Escalation · Versioning · Health Monitoring
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class ToolAccess(BaseModel):
    name: str
    access: str  # CONNECTED | WRITE | READ-ONLY | ARMED | ENFORCED | LIMITED | REQUIRED | SANDBOX
    purpose: str = ""


class AgentBlueprint(BaseModel):
    """Complete operating identity for one agent — not a theatrical persona."""

    agent_id: str
    nick: str
    division: str
    department: str
    kind: str
    status: str = "RUNNING"

    # --- Structural ---
    identity: str = Field(description="Who the agent is")
    goal: str = Field(description="What success looks like")
    responsibilities: list[str] = Field(description="What it owns")
    functions: list[str] = Field(description="What it can do")
    tools: list[ToolAccess] = Field(description="What systems it can use")
    capabilities: list[str] = Field(description="What it is intellectually able to perform")
    memory: list[str] = Field(description="What it remembers")
    knowledge_base: list[str] = Field(description="Information it knows")

    # --- Operating ---
    skills: list[str] = Field(description="Specialized expertise")
    workflows: list[str] = Field(description="Step-by-step procedures")
    decision_rules: list[str] = Field(description="When it acts")
    communication: list[str] = Field(description="How it talks with other agents")
    inputs: list[str] = Field(description="What information it receives")
    outputs: list[str] = Field(description="What it produces")
    learning: list[str] = Field(description="How it improves")
    evaluation: list[str] = Field(description="How performance is measured")
    permissions: list[str] = Field(description="What it is allowed to access")

    # --- Control / runtime ---
    constraints: list[str] = Field(description="What it cannot do")
    triggers: list[str] = Field(description="What causes it to wake up")
    scheduling: list[str] = Field(description="How often it runs")
    logging: list[str] = Field(description="Records everything it does")
    self_reflection: list[str] = Field(description="Reviews mistakes")
    escalation: list[str] = Field(description="Knows when to ask for help")
    versioning: list[str] = Field(description="Tracks improvements")
    health_monitoring: list[str] = Field(description="Detects failures")

    # Machine flags
    may_propose_trades: bool = False
    may_place_orders: bool = False
    paper_only: bool = True
    live_enabled: bool = False
    supervisor_id: str = "GOV-CHAIR"
    success_metrics: list[str] = Field(default_factory=list)
    escalation_path: list[str] = Field(default_factory=list)
    hard_limits: list[str] = Field(default_factory=list)
    version: str = "3.0.0"

    def to_dict(self) -> dict[str, Any]:
        return self.model_dump(mode="json")

    def layer_table(self) -> list[tuple[str, str]]:
        def join(xs: list[Any]) -> str:
            if not xs:
                return ""
            if isinstance(xs[0], ToolAccess):
                return "; ".join(f"{t.name} [{t.access}]" for t in xs)  # type: ignore[misc]
            return "; ".join(str(x) for x in xs)

        return [
            ("Identity", self.identity),
            ("Goal", self.goal),
            ("Responsibilities", join(self.responsibilities)),
            ("Functions", join(self.functions)),
            ("Tools", join(self.tools)),
            ("Capabilities", join(self.capabilities)),
            ("Memory", join(self.memory)),
            ("Knowledge Base", join(self.knowledge_base)),
            ("Skills", join(self.skills)),
            ("Workflows", join(self.workflows)),
            ("Decision Rules", join(self.decision_rules)),
            ("Communication", join(self.communication)),
            ("Inputs", join(self.inputs)),
            ("Outputs", join(self.outputs)),
            ("Learning", join(self.learning)),
            ("Evaluation", join(self.evaluation)),
            ("Permissions", join(self.permissions)),
            ("Constraints", join(self.constraints)),
            ("Triggers", join(self.triggers)),
            ("Scheduling", join(self.scheduling)),
            ("Logging", join(self.logging)),
            ("Self-Reflection", join(self.self_reflection)),
            ("Escalation", join(self.escalation)),
            ("Versioning", join(self.versioning)),
            ("Health Monitoring", join(self.health_monitoring)),
        ]


STRUCTURAL_LAYERS = [
    "identity",
    "goal",
    "responsibilities",
    "functions",
    "tools",
    "capabilities",
    "memory",
    "knowledge_base",
]

OPERATING_LAYERS = [
    "skills",
    "workflows",
    "decision_rules",
    "communication",
    "inputs",
    "outputs",
    "learning",
    "evaluation",
    "permissions",
]

CONTROL_LAYERS = [
    "constraints",
    "triggers",
    "scheduling",
    "logging",
    "self_reflection",
    "escalation",
    "versioning",
    "health_monitoring",
]

ALL_BLUEPRINT_LAYERS = STRUCTURAL_LAYERS + OPERATING_LAYERS + CONTROL_LAYERS
