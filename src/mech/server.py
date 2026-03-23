"""Olas mech-server: serves DeFi analysis tools on the marketplace.

HTTP endpoints + on-chain event listener for mech requests.
Target: serve 50+ requests to qualify for Olas Monetize track.
"""
from __future__ import annotations

import asyncio
import json
import logging
from typing import Any, TYPE_CHECKING

import os

from aiohttp import web
from eth_account import Account

from src.mech.tools import TOOL_REGISTRY
from src.onchain.contracts import MECH_ABI

if TYPE_CHECKING:
    from src.integrations.bankr import BankrClient

logger = logging.getLogger(__name__)

MAX_QUERY_LENGTH = 10_000


class MechServer:
    """Olas-compatible mech server with HTTP + on-chain event handling + deliver()."""

    def __init__(self, bankr: BankrClient, port: int = 8080,
                 web3_provider=None, mech_address: str = "",
                 private_key: str = ""):
        self.bankr = bankr
        self.port = port
        self.requests_served: int = 0
        self._w3 = web3_provider
        self._mech_address = mech_address
        self._private_key = private_key
        self._account = Account.from_key(private_key) if private_key else None
        self._contract = None
        self._event_task: asyncio.Task | None = None
        self._lock = asyncio.Lock()

        self._app = web.Application(client_max_size=1024 * 1024)
        self._app.router.add_post("/request", self._handle_http)
        self._app.router.add_get("/tools", self._list_tools_http)
        self._app.router.add_get("/health", self._health)

        if web3_provider and mech_address:
            self._contract = web3_provider.eth.contract(
                address=web3_provider.to_checksum_address(mech_address),
                abi=MECH_ABI,
            )

    async def handle_request(self, tool_name: str, query: str) -> tuple:
        """Dispatch a request to a tool handler. Returns Olas-compatible tuple."""
        if tool_name not in TOOL_REGISTRY:
            raise ValueError(f"Unknown tool: {tool_name}")
        handler = TOOL_REGISTRY[tool_name]["handler"]
        result = await handler(query, bankr=self.bankr)

        async with self._lock:
            self.requests_served += 1

        logger.info(f"Served request #{self.requests_served}: {tool_name}")
        return result

    async def deliver(self, request_id: int, data: bytes) -> str | None:
        """Deliver a response on-chain for a completed mech request.

        This is the missing piece that allows the mech to complete the
        on-chain request/response cycle required by the Olas protocol.
        """
        if not self._contract or not self._w3 or not self._account:
            logger.warning("Cannot deliver: no web3 provider, contract, or signing key")
            return None

        try:
            nonce = await self._w3.eth.get_transaction_count(self._account.address)
            gas_price = await self._w3.eth.gas_price

            tx = self._contract.functions.deliver(request_id, data).build_transaction({
                "from": self._account.address,
                "gas": 300_000,
                "gasPrice": gas_price,
                "nonce": nonce,
                "chainId": 100,  # Gnosis
            })

            # Estimate gas with 20% buffer
            try:
                estimated = await self._w3.eth.estimate_gas(tx)
                tx["gas"] = int(estimated * 1.2)
            except Exception as e:
                logger.warning(f"Gas estimation failed for deliver, using 300k: {e}")

            signed = self._account.sign_transaction(tx)
            tx_hash = await self._w3.eth.send_raw_transaction(signed.raw_transaction)
            receipt = await self._w3.eth.wait_for_transaction_receipt(tx_hash, timeout=120)

            if receipt.get("status") == 0:
                logger.error(f"Deliver tx reverted: {tx_hash.hex()}")
                return None

            logger.info(f"Delivered response for request {request_id}: tx={tx_hash.hex()}")
            return tx_hash.hex()
        except Exception as e:
            logger.error(f"Failed to deliver response for request {request_id}: {e}")
            return None

    def list_tools(self) -> list[dict]:
        return [{"name": name, "description": tool["description"]}
                for name, tool in TOOL_REGISTRY.items()]

    async def start_event_listener(self) -> None:
        """Start polling for on-chain Request events."""
        if not self._contract:
            logger.warning("No web3 provider — skipping on-chain event listener")
            return
        self._event_task = asyncio.create_task(self._poll_events())
        logger.info("On-chain event listener started")

    async def _poll_events(self) -> None:
        """Poll for Request events and process them."""
        last_block = await self._w3.eth.block_number
        while True:
            try:
                current = await self._w3.eth.block_number
                if current > last_block:
                    logs = await self._w3.eth.get_logs({
                        "address": self._mech_address,
                        "fromBlock": last_block + 1,
                        "toBlock": current,
                        "topics": [self._w3.keccak(text="Request(address,uint256,bytes)").hex()],
                    })
                    for log in logs:
                        await self._handle_onchain_request(log)
                    last_block = current
            except Exception as e:
                logger.error(f"Event poll error: {e}")
            await asyncio.sleep(5)

    async def _handle_onchain_request(self, log: dict) -> None:
        """Process an on-chain Request event and deliver the response."""
        try:
            data = bytes.fromhex(log["data"][2:]) if isinstance(log["data"], str) else log["data"]
            payload = json.loads(data)
            tool_name = payload.get("tool", "")
            query = payload.get("query", "")
            result = await self.handle_request(tool_name, query)

            # Deliver the response on-chain
            request_id = int(log["topics"][1], 16) if len(log.get("topics", [])) > 1 else 0
            if request_id > 0 and result:
                response_data = json.dumps(result[0] if isinstance(result, tuple) else result).encode()
                await self.deliver(request_id, response_data)

            logger.info(f"Processed on-chain request: {tool_name}")
        except Exception as e:
            logger.error(f"Failed to process on-chain request: {e}")

    async def _handle_http(self, request: web.Request) -> web.Response:
        # API key auth — reject if key is configured but not provided
        api_key = request.headers.get("X-API-Key", "")
        expected_key = os.environ.get("OPUS_MECH_API_KEY", "")
        if not expected_key:
            logger.warning("OPUS_MECH_API_KEY not set — mech server running without auth")
        if expected_key and api_key != expected_key:
            return web.json_response({"error": "Unauthorized"}, status=401)

        data = await request.json()
        tool_name = data.get("tool", "")
        query = data.get("query", "")
        if not tool_name or not query:
            return web.json_response({"error": "Missing tool or query"}, status=400)
        if len(query) > MAX_QUERY_LENGTH:
            return web.json_response({"error": "Query too long"}, status=413)

        try:
            result = await self.handle_request(tool_name, query)
            # result is a tuple (text, prompt, error, metadata, raw)
            if isinstance(result, tuple):
                return web.json_response({
                    "result": result[0], "prompt": result[1],
                    "error": result[2], "metadata": result[3],
                    "requests_served": self.requests_served,
                })
            return web.json_response({"result": result, "requests_served": self.requests_served})
        except ValueError as e:
            return web.json_response({"error": str(e)}, status=400)

    async def _list_tools_http(self, request: web.Request) -> web.Response:
        return web.json_response({"tools": self.list_tools()})

    async def _health(self, request: web.Request) -> web.Response:
        return web.json_response({"status": "ok", "requests_served": self.requests_served})

    async def start(self) -> web.AppRunner:
        runner = web.AppRunner(self._app)
        await runner.setup()
        bind_addr = os.environ.get("OPUS_MECH_BIND", "0.0.0.0")
        site = web.TCPSite(runner, bind_addr, self.port)
        await site.start()
        logger.info(f"Mech server listening on {bind_addr}:{self.port}")
        await self.start_event_listener()
        return runner
