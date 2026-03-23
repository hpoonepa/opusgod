from __future__ import annotations
import logging

logger = logging.getLogger(__name__)

class ZyfaiClient:
    def __init__(self, safe_address: str):
        self.safe_address = safe_address
        self.total_earned: float = 0.0
        self.total_spent: float = 0.0
        self._deployed: float = 0.0

    def record_yield(self, amount: float) -> None:
        self.total_earned += amount
        logger.info(f"Zyfai yield: +${amount:.4f} (total: ${self.total_earned:.4f})")

    def record_spend(self, amount: float) -> None:
        self.total_spent += amount

    def can_fund(self, amount: float) -> bool:
        return (self.total_earned - self.total_spent) >= amount

    def get_yield_status(self) -> dict:
        return {"safe_address": self.safe_address, "earned": self.total_earned,
                "spent": self.total_spent, "available": self.total_earned - self.total_spent,
                "deployed": self._deployed, "self_sustaining": self.total_earned > self.total_spent}
