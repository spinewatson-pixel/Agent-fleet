"""REG-1 regime label service for discretionary admission."""

from __future__ import annotations

from dataclasses import dataclass, field

from agent_fleet.schemas.enums import MarketRegime


@dataclass
class RegimeService:
    """Simple paper regime labeler owned by REG-1 / HEAD-TRADE."""

    current: MarketRegime = MarketRegime.TRENDING_BULL
    history: list[MarketRegime] = field(default_factory=list)
    owner_agent_id: str = "REG-1"

    def set_regime(self, regime: MarketRegime) -> MarketRegime:
        self.history.append(self.current)
        self.current = regime
        return self.current

    def label(self) -> MarketRegime:
        return self.current

    def admits(self, valid: list[MarketRegime], invalid: list[MarketRegime] | None = None) -> bool:
        if invalid and self.current in invalid:
            return False
        if not valid:
            return True
        return self.current in valid
