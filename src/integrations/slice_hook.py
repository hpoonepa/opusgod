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

# ABI matching contracts/SlicePricingHook.sol (OpusGodPricingHook)
SLICE_HOOK_ABI = [
    {"inputs": [
        {"name": "", "type": "uint256"}, {"name": "", "type": "uint256"},
        {"name": "", "type": "address"}, {"name": "quantity", "type": "uint256"},
        {"name": "", "type": "address"}, {"name": "", "type": "bytes"},
    ], "name": "productPrice",
     "outputs": [{"name": "ethPrice", "type": "uint256"}, {"name": "currencyPrice", "type": "uint256"}],
     "stateMutability": "view", "type": "function"},
    {"inputs": [{"name": "_basePriceWei", "type": "uint256"}, {"name": "_demandMultiplier", "type": "uint256"}],
     "name": "updatePricing", "outputs": [], "stateMutability": "nonpayable", "type": "function"},
    {"inputs": [], "name": "basePriceWei",
     "outputs": [{"name": "", "type": "uint256"}], "stateMutability": "view", "type": "function"},
    {"inputs": [], "name": "demandMultiplier",
     "outputs": [{"name": "", "type": "uint256"}], "stateMutability": "view", "type": "function"},
    {"inputs": [], "name": "owner",
     "outputs": [{"name": "", "type": "address"}], "stateMutability": "view", "type": "function"},
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

    async def get_on_chain_price(self, slicer_id: int = 0, product_id: int = 0,
                                    quantity: int = 1) -> int:
        """Read price from deployed OpusGodPricingHook contract."""
        if not self._contract:
            raise ValueError("No contract configured — set hook_address")
        zero = "0x0000000000000000000000000000000000000000"
        eth_price, _ = await self._contract.functions.productPrice(
            slicer_id, product_id, zero, quantity, zero, b""
        ).call()
        return eth_price

    async def get_on_chain_stats(self) -> dict:
        """Read pricing parameters from contract."""
        if not self._contract:
            raise ValueError("No contract configured")
        base = await self._contract.functions.basePriceWei().call()
        demand = await self._contract.functions.demandMultiplier().call()
        return {"base_price_wei": base, "demand_multiplier": demand}

    async def update_pricing_params(self, base_price_wei: int, demand_multiplier: int,
                                     account) -> str:
        """Write new pricing params to contract (requires signer)."""
        if not self._contract or not self._w3:
            raise ValueError("No contract configured")

        nonce = await self._w3.eth.get_transaction_count(account.address)
        tx = self._contract.functions.updatePricing(base_price_wei, demand_multiplier).build_transaction({
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
