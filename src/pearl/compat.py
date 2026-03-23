from __future__ import annotations
import logging
from typing import Callable
from aiohttp import web

logger = logging.getLogger(__name__)


def format_performance(status: dict) -> dict:
    return {"status": "running" if status.get("state") != "SHUTDOWN" else "stopped",
            "agent_state": status.get("state", "UNKNOWN"),
            "requests_served": status.get("requests_served", 0),
            "requests_hired": status.get("requests_hired", 0),
            "vaults_monitored": status.get("vaults_monitored", 0),
            "total_revenue_usd": status.get("total_revenue_usd", 0.0)}


def create_pearl_app(agent_status_fn: Callable[[], dict], port: int = 8716) -> web.Application:
    app = web.Application()

    async def healthcheck(request: web.Request) -> web.Response:
        return web.Response(text="OK", status=200)

    async def index(request: web.Request) -> web.Response:
        status = agent_status_fn()
        return web.json_response({"name": "OpusGod", "description": "Autonomous DeFi Intelligence Agent",
                                   "version": "0.1.0", **format_performance(status)})

    async def funds_status(request: web.Request) -> web.Response:
        status = agent_status_fn()
        return web.json_response({"total_revenue": status.get("total_revenue_usd", 0.0),
                                   "self_sustaining": status.get("total_revenue_usd", 0.0) > 0})

    app.router.add_get("/healthcheck", healthcheck)
    app.router.add_get("/", index)
    app.router.add_get("/funds-status", funds_status)
    return app
