"""Eight-layer Agent Blueprint — the structural schema for every Watchfloor agent.

Layers (user mandate):
  Identity · Goal · Responsibilities · Functions · Tools · Capabilities · Memory · Knowledge Base
"""

from __future__ import annotations

from typing import Any, Optional

from pydantic import BaseModel, Field


class ToolAccess(BaseModel):
    name: str
    access: str  # CONNECTED | WRITE | READ-ONLY | ARMED | ENFORCED | LIMITED | REQUIRED
    purpose: str = ""


class AgentBlueprint(BaseModel):
    """Complete operating identity for one agent — not a theatrical persona."""

    agent_id: str
    nick: str
    division: str
    department: str
    kind: str
    status: str = "RUNNING"

    identity: str = Field(description="Who the agent is")
    goal: str = Field(description="What success looks like")
    responsibilities: list[str] = Field(description="What it owns")
    functions: list[str] = Field(description="What it can do")
    tools: list[ToolAccess] = Field(description="What systems it can use")
    capabilities: list[str] = Field(description="What it is intellectually able to perform")
    memory: list[str] = Field(description="What it remembers")
    knowledge_base: list[str] = Field(description="Information it knows")

    # Operating constraints (non-negotiables)
    may_propose_trades: bool = False
    may_place_orders: bool = False
    paper_only: bool = True
    live_enabled: bool = False
    supervisor_id: str = "GOV-CHAIR"
    success_metrics: list[str] = Field(default_factory=list)
    escalation_path: list[str] = Field(default_factory=list)
    hard_limits: list[str] = Field(default_factory=list)
    version: str = "1.0.0"

    def to_dict(self) -> dict[str, Any]:
        return self.model_dump(mode="json")

    def layer_table(self) -> list[tuple[str, str]]:
        return [
            ("Identity", self.identity),
            ("Goal", self.goal),
            ("Responsibilities", "; ".join(self.responsibilities)),
            ("Functions", "; ".join(self.functions)),
            ("Tools", "; ".join(f"{t.name} [{t.access}]" for t in self.tools)),
            ("Capabilities", "; ".join(self.capabilities)),
            ("Memory", "; ".join(self.memory)),
            ("Knowledge Base", "; ".join(self.knowledge_base)),
        ]
