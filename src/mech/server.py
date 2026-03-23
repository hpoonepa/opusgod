from __future__ import annotations
import logging
from aiohttp import web
from src.mech.tools import TOOL_REGISTRY

logger = logging.getLogger(__name__)


class MechServer:
    def __init__(self, bankr, port: int = 8080):
        self.bankr = bankr
        self.port = port
        self.requests_served: int = 0
        self._app = web.Application()
        self._app.router.add_post("/request", self._handle_http)
        self._app.router.add_get("/tools", self._list_tools_http)
        self._app.router.add_get("/health", self._health)

    async def handle_request(self, tool_name: str, query: str) -> str:
        if tool_name not in TOOL_REGISTRY:
            raise ValueError(f"Unknown tool: {tool_name}")
        handler = TOOL_REGISTRY[tool_name]["handler"]
        result = await handler(query, bankr=self.bankr)
        self.requests_served += 1
        logger.info(f"Served request #{self.requests_served}: {tool_name}")
        return result

    def list_tools(self) -> list[dict]:
        return [{"name": name, "description": tool["description"]} for name, tool in TOOL_REGISTRY.items()]

    async def _handle_http(self, request: web.Request) -> web.Response:
        data = await request.json()
        try:
            result = await self.handle_request(data.get("tool", ""), data.get("query", ""))
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
        return runner
