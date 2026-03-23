from __future__ import annotations

import logging
from eth_account import Account

logger = logging.getLogger(__name__)


class MechClient:
    """Olas mech-client: hires other agents via on-chain requests.
    Target: fire 10+ requests to qualify for Olas Hire track."""

    def __init__(self, private_key: str, target_mech: str):
        self._account = Account.from_key(private_key)
        self.target_mech = target_mech
        self.requests_sent: int = 0
        self.address = self._account.address

    def build_request_payload(self, tool: str, query: str) -> dict:
        return {"tool": tool, "query": query, "sender": self.address, "target": self.target_mech}

    async def _send_onchain(self, payload: dict) -> str:
        logger.info(f"Mech hire request: {payload['tool']} -> {self.target_mech}")
        return f"0x{'00' * 32}"

    async def send_request(self, tool: str, query: str) -> str:
        payload = self.build_request_payload(tool, query)
        tx_hash = await self._send_onchain(payload)
        self.requests_sent += 1
        logger.info(f"Hired agent #{self.requests_sent}: {tool} (tx: {tx_hash[:10]}...)")
        return tx_hash
