"""Zyfai self-funding yield client.

Manages yield-bearing smart accounts (ERC-4337/ERC-7579 Safe-based).
Agents deposit funds, earn yield, and withdraw to fund operations.
"""
from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field

import httpx

logger = logging.getLogger(__name__)


class ZyfaiAPIError(Exception):
    """Raised when Zyfai SDK returns an error."""
    def __init__(self, status_code: int, detail: str):
        self.status_code = status_code
        self.detail = detail
        super().__init__(f"Zyfai API error {status_code}: {detail}")


@dataclass
class Operation:
    op_type: str  # "yield", "spend", "deposit", "withdraw"
    amount: float
    timestamp: int = field(default_factory=lambda: int(time.time()))
    tx_hash: str = ""


class ZyfaiClient:
    """Client for Zyfai yield-bearing smart accounts."""

    BASE_URL = "https://sdk.zyf.ai"

    def __init__(self, api_key: str = "", safe_address: str = "",
                 chain_id: int = 8453, base_url: str = ""):
        self.api_key = api_key
        self.safe_address = safe_address
        self.chain_id = chain_id
        self._base_url = base_url or self.BASE_URL
        self._client = httpx.AsyncClient(
            timeout=30.0,
            headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
        )
        self._operations: list[Operation] = []
        self.total_earned: float = 0.0
        self.total_spent: float = 0.0

    async def _request(self, method: str, path: str, **kwargs) -> dict:
        resp = await self._client.request(method, f"{self._base_url}{path}", **kwargs)
        if resp.status_code >= 400:
            raise ZyfaiAPIError(resp.status_code, resp.text)
        return resp.json() if resp.content else {}

    async def deploy_safe(self, owner_address: str) -> dict:
        """Deploy a new yield-bearing Safe smart account."""
        result = await self._request("POST", "/v1/safes", json={
            "owner": owner_address, "chainId": self.chain_id,
        })
        if "address" in result:
            self.safe_address = result["address"]
        return result

    async def deposit_funds(self, token: str, amount: float) -> dict:
        """Deposit funds into the yield account."""
        result = await self._request("POST", f"/v1/safes/{self.safe_address}/deposit", json={
            "token": token, "amount": str(amount),
        })
        self._operations.append(Operation("deposit", amount))
        return result

    async def withdraw_funds(self, token: str, amount: float, to: str = "") -> dict:
        """Withdraw funds from yield account."""
        result = await self._request("POST", f"/v1/safes/{self.safe_address}/withdraw", json={
            "token": token, "amount": str(amount), "to": to or self.safe_address,
        })
        self._operations.append(Operation("withdraw", amount))
        return result

    async def get_positions(self) -> list[dict]:
        """Get current yield positions."""
        result = await self._request("GET", f"/v1/safes/{self.safe_address}/positions")
        return result.get("positions", []) if isinstance(result, dict) else result

    async def get_yield_status(self) -> dict:
        """Get current yield status with P&L."""
        try:
            positions = await self.get_positions()
            position_value = sum(float(p.get("value", 0)) for p in positions)
            earned = sum(float(p.get("earned", 0)) for p in positions)
            self.total_earned = max(self.total_earned, earned)
        except (ZyfaiAPIError, httpx.HTTPError):
            position_value = 0.0

        available = self.total_earned - self.total_spent
        return {
            "safe_address": self.safe_address,
            "earned": self.total_earned,
            "spent": self.total_spent,
            "available": available,
            "self_sustaining": self.total_earned > self.total_spent,
        }

    def record_yield(self, amount: float) -> None:
        """Record yield earned."""
        self.total_earned += amount
        self._operations.append(Operation("yield", amount))
        logger.info(f"Zyfai yield: +${amount:.4f} (total: ${self.total_earned:.4f})")

    def record_spend(self, amount: float) -> None:
        """Record operational spend."""
        self.total_spent += amount
        self._operations.append(Operation("spend", amount))

    def can_fund(self, amount: float) -> bool:
        """Check if yield covers the operation cost."""
        return (self.total_earned - self.total_spent) >= amount

    def get_pnl(self) -> dict:
        """Get profit & loss summary."""
        return {
            "revenue": self.total_earned,
            "expenses": self.total_spent,
            "net": self.total_earned - self.total_spent,
            "operations": len(self._operations),
        }

    async def close(self) -> None:
        await self._client.aclose()
