from __future__ import annotations

import asyncio
import logging
import signal

from src.agent.state import AgentContext, AgentState
from src.agent.scheduler import AgentScheduler
from src.integrations.bankr import BankrClient
from src.integrations.lido import LidoMonitor
from src.integrations.telegram import TelegramNotifier
from src.integrations.zyfai import ZyfaiClient
from src.integrations.ampersend import AmpersendClient
from src.integrations.erc8128 import ERC8128Signer
from src.mech.server import MechServer
from src.mech.client import MechClient
from src.analysis.defi_analyzer import DeFiAnalyzer
from src.analysis.vault_scorer import VaultScorer
from src.analysis.market_signal import SignalAggregator
from src.pearl.compat import create_pearl_app
from config.settings import get_settings

from aiohttp import web

logger = logging.getLogger(__name__)


class OpusGodAgent:
    """OpusGod -- Autonomous DeFi Intelligence Agent. The only agent that earns its own living."""

    def __init__(self):
        self.settings = get_settings()
        self.ctx = AgentContext()
        self.scheduler = AgentScheduler()

        self.bankr = BankrClient(api_key=self.settings.bankr_api_key,
            endpoint=self.settings.bankr_endpoint, model=self.settings.bankr_model)
        self.lido = LidoMonitor()
        self.telegram = TelegramNotifier(bot_token=self.settings.telegram_bot_token, chat_id=self.settings.telegram_chat_id)
        self.zyfai = ZyfaiClient(safe_address=self.settings.zyfai_safe_address)
        self.ampersend = AmpersendClient(api_key=self.settings.ampersend_api_key)
        self.signer = ERC8128Signer(private_key=self.settings.private_key)

        self.mech_server = MechServer(bankr=self.bankr, port=self.settings.mech_server_port)
        self.mech_client = MechClient(private_key=self.settings.private_key, target_mech=self.settings.mech_target_address)

        self.analyzer = DeFiAnalyzer(bankr=self.bankr)
        self.signals = SignalAggregator()

        self.pearl_app = create_pearl_app(agent_status_fn=self.status, port=self.settings.pearl_port)

    async def startup(self) -> None:
        logger.info("OpusGod starting up...")
        self.ctx.transition(AgentState.IDLE)
        logger.info(f"Agent ready. Signer: {self.signer.address}")

    async def handle_mech_request(self, tool_name: str, query: str) -> str:
        result = await self.mech_server.handle_request(tool_name, query)
        self.ctx.requests_served = self.mech_server.requests_served
        return result

    async def check_vaults(self) -> None:
        try:
            stats = await self.lido.get_steth_stats()
            self.ctx.vaults_monitored += 1
            logger.info(f"Vault check #{self.ctx.vaults_monitored}: {stats}")
        except Exception as e:
            logger.error(f"Vault check failed: {e}")
            self.ctx.last_error = str(e)

    async def hire_agent(self, tool: str, query: str) -> str:
        tx_hash = await self.mech_client.send_request(tool, query)
        self.ctx.requests_hired = self.mech_client.requests_sent
        return tx_hash

    def status(self) -> dict:
        return self.ctx.to_dict()

    async def run(self) -> None:
        await self.startup()
        self.scheduler.register("vault_check", self.check_vaults,
            interval_seconds=self.settings.vault_check_interval_seconds)

        mech_runner = await self.mech_server.start()

        pearl_runner = web.AppRunner(self.pearl_app)
        await pearl_runner.setup()
        pearl_site = web.TCPSite(pearl_runner, "0.0.0.0", self.settings.pearl_port)
        await pearl_site.start()
        logger.info(f"Pearl server on port {self.settings.pearl_port}")

        await self.scheduler.start()

        logger.info("OpusGod is live. Earning its own living.")
        logger.info(f"  Mech server: port {self.settings.mech_server_port}")
        logger.info(f"  Pearl: port {self.settings.pearl_port}")
        logger.info(f"  Identity: {self.signer.address}")

        try:
            while self.ctx.state != AgentState.SHUTDOWN:
                await asyncio.sleep(1)
        except asyncio.CancelledError:
            pass
        finally:
            await self.shutdown()

    async def shutdown(self) -> None:
        logger.info("Shutting down...")
        await self.scheduler.stop()
        await self.bankr.close()
        await self.lido.close()
        await self.telegram.close()
        if self.ctx.state != AgentState.SHUTDOWN:
            if self.ctx.can_transition(AgentState.IDLE):
                self.ctx.transition(AgentState.IDLE)
            self.ctx.transition(AgentState.SHUTDOWN)
        logger.info(f"Final stats: {self.status()}")


def main():
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(name)s] %(levelname)s: %(message)s")
    agent = OpusGodAgent()
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    def _signal_handler():
        logger.info("Signal received, shutting down...")
        loop.create_task(agent.shutdown())

    for sig in (signal.SIGINT, signal.SIGTERM):
        loop.add_signal_handler(sig, _signal_handler)

    try:
        loop.run_until_complete(agent.run())
    finally:
        loop.close()


if __name__ == "__main__":
    main()
