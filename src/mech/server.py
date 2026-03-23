"""Olas mech-server: serves DeFi analysis tools on the marketplace.

HTTP endpoints + on-chain event listener for mech requests.
Target: serve 50+ requests to qualify for Olas Monetize track.
"""
from __future__ import annotations

import asyncio
import json
import logging
from typing import Any

from aiohttp import web

from src.mech.tools import TOOL_REGISTRY
from src.onchain.contracts import MECH_ABI

logger = logging.getLogger(__name__)


class MechServer:
    """Olas-compatible mech server with HTTP + on-chain event handling."""

    def __init__(self, bankr, port: int = 8080,
                 web3_provider=None, mech_address: str = "",
                 private_key: str = ""):
        self.bankr = bankr
        self.port = port
        self.requests_served: int = 0
        self._w3 = web3_provider
        self._mech_address = mech_address
        self._private_key = private_key
        self._contract = None
        self._event_task: asyncio.Task | None = None
        self._lock = asyncio.Lock()

        self._app = web.Application()
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
        """Process an on-chain Request event."""
        try:
            data = bytes.fromhex(log["data"][2:]) if isinstance(log["data"], str) else log["data"]
            payload = json.loads(data)
            tool_name = payload.get("tool", "")
            query = payload.get("query", "")
            result = await self.handle_request(tool_name, query)
            logger.info(f"Processed on-chain request: {tool_name}")
        except Exception as e:
            logger.error(f"Failed to process on-chain request: {e}")

    async def _handle_http(self, request: web.Request) -> web.Response:
        data = await request.json()
        try:
            result = await self.handle_request(data.get("tool", ""), data.get("query", ""))
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
        site = web.TCPSite(runner, "0.0.0.0", self.port)
        await site.start()
        logger.info(f"Mech server listening on port {self.port}")
        await self.start_event_listener()
        return runner
