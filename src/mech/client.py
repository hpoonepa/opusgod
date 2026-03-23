"""Olas mech-client: hires other agents via on-chain requests.

Target: fire 10+ requests to qualify for Olas Hire track.
Uses real web3 transactions to interact with the mech contract.
"""
from __future__ import annotations

import asyncio
import json
import logging

from eth_account import Account
from web3 import AsyncWeb3, AsyncHTTPProvider

from src.onchain.contracts import MECH_ABI

logger = logging.getLogger(__name__)


class MechClientError(Exception):
    """Raised when mech client operations fail."""


class MechClient:
    """Olas mech-client: hires agents via on-chain contract calls."""

    def __init__(self, private_key: str, target_mech: str,
                 rpc_url: str = "https://rpc.gnosischain.com",
                 chain_id: int = 100, mech_price: int = 1_000_000_000_000_000):
        self._account = Account.from_key(private_key)
        self.target_mech = target_mech
        self.address = self._account.address
        self.rpc_url = rpc_url
        self.chain_id = chain_id
        self.mech_price = mech_price
        self.requests_sent: int = 0
        self._total_gas: int = 0
        self._nonce_lock = asyncio.Lock()

        self.w3 = AsyncWeb3(AsyncHTTPProvider(rpc_url))
        self.contract = self.w3.eth.contract(
            address=self.w3.to_checksum_address(target_mech),
            abi=MECH_ABI,
        )

    def build_request_payload(self, tool: str, query: str) -> bytes:
        """ABI-encode the tool request as JSON bytes."""
        payload = json.dumps({"tool": tool, "query": query, "sender": self.address})
        return payload.encode("utf-8")

    async def _send_onchain(self, data: bytes) -> str:
        """Build, sign, and send a real on-chain transaction."""
        async with self._nonce_lock:
            nonce = await self.w3.eth.get_transaction_count(self.address)
            gas_price = await self.w3.eth.gas_price

            tx = self.contract.functions.request(data).build_transaction({
                "from": self.address,
                "value": self.mech_price,
                "gas": 300_000,
                "gasPrice": gas_price,
                "nonce": nonce,
                "chainId": self.chain_id,
            })

            # Estimate gas with 20% buffer
            try:
                estimated = await self.w3.eth.estimate_gas(tx)
                tx["gas"] = int(estimated * 1.2)
            except Exception:
                pass  # Use default 300k

            signed = self._account.sign_transaction(tx)
            tx_hash = await self.w3.eth.send_raw_transaction(signed.raw_transaction)
            receipt = await self.w3.eth.wait_for_transaction_receipt(tx_hash, timeout=120)

            self._total_gas += receipt.get("gasUsed", 0)
            return tx_hash.hex()

    async def send_request(self, tool: str, query: str) -> str:
        """Send a mech hire request on-chain."""
        data = self.build_request_payload(tool, query)
        tx_hash = await self._send_onchain(data)
        self.requests_sent += 1
        logger.info(f"Hired agent #{self.requests_sent}: {tool} (tx: {tx_hash[:10]}...)")
        return tx_hash

    async def get_response(self, request_id: int) -> bytes:
        """Poll for a mech response on-chain."""
        return await self.contract.functions.getResponse(request_id).call()

    async def wait_for_response(self, request_id: int, timeout: int = 300, poll_interval: int = 5) -> bytes:
        """Wait for a mech delivery response with timeout."""
        deadline = asyncio.get_event_loop().time() + timeout
        while asyncio.get_event_loop().time() < deadline:
            response = await self.get_response(request_id)
            if response and response != b"":
                return response
            await asyncio.sleep(poll_interval)
        raise MechClientError(f"Timeout waiting for response to request {request_id}")

    def get_stats(self) -> dict:
        """Get client statistics."""
        return {
            "requests_sent": self.requests_sent,
            "total_gas_used": self._total_gas,
            "average_gas": self._total_gas // max(self.requests_sent, 1),
            "target_mech": self.target_mech,
        }
