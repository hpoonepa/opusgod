from __future__ import annotations
import uuid
import logging

logger = logging.getLogger(__name__)

class AmpersendClient:
    def __init__(self, api_key: str):
        self.api_key = api_key
        self._payments: list[dict] = []

    def create_payment_intent(self, amount_usd: float, description: str) -> dict:
        intent = {"id": str(uuid.uuid4()), "amount": amount_usd, "currency": "USD",
                  "description": description, "status": "pending"}
        self._payments.append(intent)
        logger.info(f"Payment intent created: ${amount_usd} for {description}")
        return intent

    def get_treasury_status(self) -> dict:
        total_earned = sum(p["amount"] for p in self._payments if p["status"] == "completed")
        return {"balance": total_earned, "total_payments": len(self._payments),
                "pending": sum(1 for p in self._payments if p["status"] == "pending")}

    def complete_payment(self, payment_id: str) -> bool:
        for p in self._payments:
            if p["id"] == payment_id:
                p["status"] = "completed"
                return True
        return False
