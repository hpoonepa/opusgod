"""Slice dynamic pricing hook — on-chain contract interaction on Base.

Manages a Solidity pricing hook contract that adjusts prices based on
demand, volatility, and market conditions. Interacts with the deployed
contract via web3.
"""
from __future__ import annotations

import json
import logging

from web3 import AsyncWeb3, AsyncHTTPProvider

logger = logging.getLogger(__name__)

# Minimal ABI for the SlicePricingHook contract
SLICE_HOOK_ABI = [
    {"inputs": [{"name": "productId", "type": "uint256"}], "name": "getPrice",
     "outputs": [{"name": "", "type": "uint256"}], "stateMutability": "view", "type": "function"},
    {"inputs": [{"name": "_basePrice", "type": "uint256"}, {"name": "_surgeMultiplier", "type": "uint256"}],
     "name": "updatePricing", "outputs": [], "stateMutability": "nonpayable", "type": "function"},
    {"inputs": [], "name": "basePrice",
     "outputs": [{"name": "", "type": "uint256"}], "stateMutability": "view", "type": "function"},
    {"inputs": [], "name": "surgeMultiplier",
     "outputs": [{"name": "", "type": "uint256"}], "stateMutability": "view", "type": "function"},
    {"inputs": [], "name": "totalPurchases",
     "outputs": [{"name": "", "type": "uint256"}], "stateMutability": "view", "type": "function"},
]


class SliceHookManager:
    """Manages Slice dynamic pricing hook with on-chain + off-chain pricing."""

    def __init__(self, hook_address: str = "", base_price: float = 1.0,
                 rpc_url: str = "https://mainnet.base.org", private_key: str = ""):
        self.hook_address = hook_address
        self.base_price = base_price
        self.rpc_url = rpc_url
        self._private_key = private_key
        self._contract = None
        self._w3 = None

        if hook_address and rpc_url:
            self._w3 = AsyncWeb3(AsyncHTTPProvider(rpc_url))
            self._contract = self._w3.eth.contract(
                address=self._w3.to_checksum_address(hook_address),
                abi=SLICE_HOOK_ABI,
            )

    def calculate_dynamic_price(self, base_price_usd: float, demand_factor: float,
                                 market_volatility: float) -> float:
        """Off-chain dynamic price preview."""
        volatility_premium = market_volatility * 0.5
        price = base_price_usd * demand_factor * (1.0 + volatility_premium)
        return round(price, 6)

    async def get_on_chain_price(self, product_id: int = 0) -> int:
        """Read price from deployed contract."""
        if not self._contract:
            raise ValueError("No contract configured — set hook_address")
        return await self._contract.functions.getPrice(product_id).call()

    async def get_on_chain_stats(self) -> dict:
        """Read pricing parameters from contract."""
        if not self._contract:
            raise ValueError("No contract configured")
        base = await self._contract.functions.basePrice().call()
        surge = await self._contract.functions.surgeMultiplier().call()
        purchases = await self._contract.functions.totalPurchases().call()
        return {"base_price": base, "surge_multiplier": surge, "total_purchases": purchases}

    async def update_pricing_params(self, base_price_wei: int, surge_multiplier: int,
                                     account) -> str:
        """Write new pricing params to contract (requires signer)."""
        if not self._contract or not self._w3:
            raise ValueError("No contract configured")

        nonce = await self._w3.eth.get_transaction_count(account.address)
        tx = self._contract.functions.updatePricing(base_price_wei, surge_multiplier).build_transaction({
            "from": account.address,
            "nonce": nonce,
            "gasPrice": await self._w3.eth.gas_price,
            "chainId": 8453,
        })
        signed = account.sign_transaction(tx)
        tx_hash = await self._w3.eth.send_raw_transaction(signed.raw_transaction)
        receipt = await self._w3.eth.wait_for_transaction_receipt(tx_hash)
        logger.info(f"Updated pricing params: tx={tx_hash.hex()}")
        return tx_hash.hex()

    def get_pricing_config(self) -> dict:
        """Get current pricing configuration."""
        return {
            "hook_address": self.hook_address,
            "base_price": self.base_price,
            "currency": "USD",
            "chain": "base",
            "chain_id": 8453,
            "has_contract": self._contract is not None,
        }
