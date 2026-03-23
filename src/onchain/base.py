"""Base chain client with POA middleware, gas estimation, receipt waiting."""
from __future__ import annotations

import asyncio
import logging

from eth_account import Account
from web3 import AsyncWeb3, AsyncHTTPProvider
from web3.middleware import ExtraDataToPOAMiddleware

logger = logging.getLogger(__name__)


class BaseClient:
    """Web3 client for Base Chain (chain ID 8453) with POA support."""

    def __init__(self, rpc_url: str, private_key: str):
        self.w3 = AsyncWeb3(AsyncHTTPProvider(rpc_url))
        self.w3.middleware_onion.inject(ExtraDataToPOAMiddleware, layer=0)
        self._account = Account.from_key(private_key)
        self.address = self._account.address
        self.chain_id = 8453
        self._nonce_lock = asyncio.Lock()

    async def get_balance(self) -> int:
        """Get native token (ETH) balance in wei."""
        return await self.w3.eth.get_balance(self.address)

    async def send_transaction(self, to: str, data: bytes = b"", value: int = 0) -> str:
        """Build, sign, send a transaction with gas estimation."""
        if not self.w3.is_address(to):
            raise ValueError(f"Invalid address: {to}")

        async with self._nonce_lock:
            nonce = await self.w3.eth.get_transaction_count(self.address)
            gas_price = await self.w3.eth.gas_price

            tx: dict = {
                "to": self.w3.to_checksum_address(to),
                "value": value,
                "gasPrice": gas_price,
                "nonce": nonce,
                "chainId": self.chain_id,
                "data": data,
                "from": self.address,
            }

            try:
                estimated = await self.w3.eth.estimate_gas(tx)
                tx["gas"] = int(estimated * 1.2)
            except Exception as e:
                logger.warning(f"Gas estimation failed, using default 300k: {e}")
                tx["gas"] = 300_000

            signed = self._account.sign_transaction(tx)
            tx_hash = await self.w3.eth.send_raw_transaction(signed.raw_transaction)
            logger.info(f"Base tx sent: {tx_hash.hex()}")
            return tx_hash.hex()

    async def wait_for_receipt(self, tx_hash: str, timeout: int = 120) -> dict:
        """Wait for transaction receipt and check status."""
        receipt = await self.w3.eth.wait_for_transaction_receipt(tx_hash, timeout=timeout)
        result = dict(receipt)
        if result.get("status") == 0:
            logger.error(f"Base tx reverted: {tx_hash} (gas used: {result.get('gasUsed')})")
        return result
