"""Pearl-compatible HTTP server for Olas zero-knowledge deployment.

Endpoints:
- GET / → HTML dashboard with agent status
- GET /healthcheck → Health check
- GET /funds-status → Treasury and revenue info
"""
from __future__ import annotations

import json
import logging
import os
import time
from typing import Callable

from aiohttp import web

logger = logging.getLogger(__name__)

_START_TIME = time.time()

HTML_TEMPLATE = """<!DOCTYPE html>
<html>
<head><title>OpusGod Agent</title>
<style>
body {{ font-family: monospace; background: #0d1117; color: #c9d1d9; padding: 2em; }}
h1 {{ color: #58a6ff; }}
.metric {{ display: inline-block; background: #161b22; border: 1px solid #30363d;
           border-radius: 6px; padding: 1em; margin: 0.5em; min-width: 150px; }}
.value {{ font-size: 1.5em; color: #7ee787; }}
.label {{ color: #8b949e; font-size: 0.9em; }}
.status {{ padding: 4px 8px; border-radius: 4px; }}
.running {{ background: #238636; }}
.stopped {{ background: #da3633; }}
</style></head>
<body>
<h1>OpusGod — Autonomous DeFi Intelligence Agent</h1>
<p>The only agent that earns its own living.</p>
<div>
<div class="metric"><div class="label">State</div>
<div class="value"><span class="status {status_class}">{state}</span></div></div>
<div class="metric"><div class="label">Requests Served</div>
<div class="value">{requests_served}</div></div>
<div class="metric"><div class="label">Agents Hired</div>
<div class="value">{requests_hired}</div></div>
<div class="metric"><div class="label">Vaults Monitored</div>
<div class="value">{vaults_monitored}</div></div>
<div class="metric"><div class="label">Revenue</div>
<div class="value">${total_revenue_usd:.2f}</div></div>
<div class="metric"><div class="label">Uptime</div>
<div class="value">{uptime}</div></div>
</div>
<p style="color:#8b949e;margin-top:2em;">Identity: {address} | Chains: Gnosis + Base | Pearl v0.1</p>
</body></html>"""


def _format_uptime() -> str:
    elapsed = int(time.time() - _START_TIME)
    hours, remainder = divmod(elapsed, 3600)
    minutes, seconds = divmod(remainder, 60)
    return f"{hours}h {minutes}m {seconds}s"


def format_performance(status: dict) -> dict:
    return {
        "status": "running" if status.get("state") != "SHUTDOWN" else "stopped",
        "agent_state": status.get("state", "UNKNOWN"),
        "requests_served": status.get("requests_served", 0),
        "requests_hired": status.get("requests_hired", 0),
        "vaults_monitored": status.get("vaults_monitored", 0),
        "total_revenue_usd": status.get("total_revenue_usd", 0.0),
        "uptime_seconds": int(time.time() - _START_TIME),
    }


def write_performance_file(status: dict, path: str | None = None) -> None:
    """Write agent performance to JSON file for Pearl monitoring."""
    if path is None:
        path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "agent_performance.json")
    perf = format_performance(status)
    with open(path, "w") as f:
        json.dump(perf, f, indent=2)


def create_pearl_app(agent_status_fn: Callable[[], dict], port: int = 8716) -> web.Application:
    app = web.Application()

    async def healthcheck(request: web.Request) -> web.Response:
        uptime = int(time.time() - _START_TIME)
        return web.json_response({"status": "ok", "uptime_seconds": uptime})

    async def index(request: web.Request) -> web.Response:
        status = agent_status_fn()
        state = status.get("state", "UNKNOWN")
        html = HTML_TEMPLATE.format(
            state=state,
            status_class="running" if state != "SHUTDOWN" else "stopped",
            requests_served=status.get("requests_served", 0),
            requests_hired=status.get("requests_hired", 0),
            vaults_monitored=status.get("vaults_monitored", 0),
            total_revenue_usd=status.get("total_revenue_usd", 0.0),
            uptime=_format_uptime(),
            address=status.get("address", "Not configured"),
        )
        return web.Response(text=html, content_type="text/html")

    async def funds_status(request: web.Request) -> web.Response:
        status = agent_status_fn()
        revenue = status.get("total_revenue_usd", 0.0)
        return web.json_response({
            "total_revenue": revenue,
            "mech_fees": status.get("mech_revenue", 0.0),
            "yield_earned": status.get("yield_earned", 0.0),
            "total_spent": status.get("total_spent", 0.0),
            "self_sustaining": revenue > status.get("total_spent", 0.0),
        })

    async def metrics(request: web.Request) -> web.Response:
        status = agent_status_fn()
        perf = format_performance(status)
        # Prometheus-style text metrics
        lines = [
            f"# HELP opusgod_requests_served Total mech requests served",
            f"# TYPE opusgod_requests_served counter",
            f"opusgod_requests_served {perf['requests_served']}",
            f"# HELP opusgod_requests_hired Total agents hired",
            f"# TYPE opusgod_requests_hired counter",
            f"opusgod_requests_hired {perf['requests_hired']}",
            f"# HELP opusgod_vaults_monitored Total vault checks",
            f"# TYPE opusgod_vaults_monitored counter",
            f"opusgod_vaults_monitored {perf['vaults_monitored']}",
            f"# HELP opusgod_revenue_usd Total revenue in USD",
            f"# TYPE opusgod_revenue_usd gauge",
            f"opusgod_revenue_usd {perf['total_revenue_usd']}",
            f"# HELP opusgod_uptime_seconds Agent uptime",
            f"# TYPE opusgod_uptime_seconds gauge",
            f"opusgod_uptime_seconds {perf['uptime_seconds']}",
        ]
        return web.Response(text="\n".join(lines) + "\n", content_type="text/plain")

    app.router.add_get("/healthcheck", healthcheck)
    app.router.add_get("/", index)
    app.router.add_get("/funds-status", funds_status)
    app.router.add_get("/metrics", metrics)
    return app
