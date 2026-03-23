from __future__ import annotations

import asyncio
import logging
import signal

from src.agent.state import AgentContext, AgentState
from src.agent.scheduler import AgentScheduler
from src.integrations.bankr import BankrClient
from src.integrations.lido import LidoMonitor, VaultAlert, AlertSeverity
from src.pearl.compat import create_pearl_app, write_performance_file
from src.integrations.telegram import TelegramNotifier
from src.integrations.zyfai import ZyfaiClient
from src.integrations.ampersend import AmpersendClient
from src.integrations.erc8128 import ERC8128Signer
from src.integrations.slice_hook import SliceHookManager
from src.mech.server import MechServer
from src.mech.client import MechClient
from src.analysis.defi_analyzer import DeFiAnalyzer
from src.analysis.vault_scorer import VaultScorer
from src.analysis.market_signal import SignalAggregator, Signal, SignalType
from config.settings import get_settings

from aiohttp import web

logger = logging.getLogger(__name__)

# Revenue milestone thresholds in USD for Telegram alerts
_REVENUE_MILESTONES = [1.0, 10.0, 50.0, 100.0, 500.0, 1000.0]


class OpusGodAgent:
    """OpusGod -- Autonomous DeFi Intelligence Agent. The only agent that earns its own living."""

    def __init__(self):
        self.settings = get_settings()
        self.ctx = AgentContext()
        self.scheduler = AgentScheduler()

        # --- Core integrations ---
        self.bankr = BankrClient(
            api_key=self.settings.bankr_api_key,
            endpoint=self.settings.bankr_endpoint,
            model=self.settings.bankr_model,
        )
        self.lido = LidoMonitor(api_base=self.settings.lido_api_base)
        self.telegram = TelegramNotifier(
            bot_token=self.settings.telegram_bot_token,
            chat_id=self.settings.telegram_chat_id,
        )
        self.zyfai = ZyfaiClient(
            api_key=self.settings.zyfai_api_key,
            safe_address=self.settings.zyfai_safe_address,
        )
        self.ampersend = AmpersendClient(
            api_key=self.settings.ampersend_api_key,
            private_key=self.settings.private_key,
        )
        self.signer = ERC8128Signer(private_key=self.settings.private_key, chain_id=100)
        self.slice_hook = SliceHookManager(
            hook_address=self.settings.slice_contract_address,
            rpc_url=self.settings.base_rpc,
            private_key=self.settings.private_key,
        )

        # --- Mech server + client ---
        self.mech_server = MechServer(bankr=self.bankr, port=self.settings.mech_server_port)
        self.mech_client = MechClient(
            private_key=self.settings.private_key,
            target_mech=self.settings.mech_target_address,
            rpc_url=self.settings.gnosis_rpc,
        )

        # --- Analysis ---
        self.analyzer = DeFiAnalyzer(bankr=self.bankr)
        self.signals = SignalAggregator()

        # --- Pearl dashboard ---
        self.pearl_app = create_pearl_app(agent_status_fn=self.status, port=self.settings.pearl_port)

        # --- Revenue tracking ---
        self._mech_revenue: float = 0.0
        self._slice_revenue: float = 0.0
        self._last_milestone_hit: float = 0.0

        # --- Monitoring state ---
        self._prev_apr: float = 0.0
        self._prev_tvl: float = 0.0

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    async def startup(self) -> None:
        """STARTUP -> IDLE: initialise clients, sign startup attestation."""
        logger.info("OpusGod starting up...")

        # Sign a startup attestation via ERC-8128
        startup_headers = self.signer.sign_request(
            "POST",
            "https://agent.opusgod.ai/startup",
            '{"event":"startup"}',
        )
        logger.info(f"Startup signed with ERC-8128: {list(startup_headers.keys())}")

        self.ctx.transition(AgentState.IDLE)
        logger.info(f"Agent ready. Signer: {self.signer.address}")

    async def shutdown(self) -> None:
        logger.info("Shutting down...")
        await self.scheduler.stop()
        await self.bankr.close()
        await self.lido.close()
        await self.telegram.close()
        await self.zyfai.close()
        await self.ampersend.close()
        await self.analyzer.close()
        if self.ctx.state != AgentState.SHUTDOWN:
            if self.ctx.can_transition(AgentState.IDLE):
                self.ctx.transition(AgentState.IDLE)
            self.ctx.transition(AgentState.SHUTDOWN)
        logger.info(f"Final stats: {self.status()}")

    # ------------------------------------------------------------------
    # ERC-8128 signing
    # ------------------------------------------------------------------

    def sign_request(self, method: str, url: str, body: str | None = None) -> dict[str, str]:
        """Sign an outbound HTTP request with ERC-8128."""
        return self.signer.sign_request(method, url, body)

    # ------------------------------------------------------------------
    # Monitoring  (IDLE -> MONITORING -> ANALYZING)
    # ------------------------------------------------------------------

    async def check_vaults(self) -> None:
        """Scheduled task: fetch Lido stats, detect anomalies, trigger analysis."""
        try:
            # Transition to MONITORING
            if self.ctx.state == AgentState.IDLE:
                self.ctx.transition(AgentState.MONITORING)

            stats = await self.lido.get_steth_stats()
            self.ctx.vaults_monitored += 1
            logger.info(f"Vault check #{self.ctx.vaults_monitored}: {stats}")

            current_apr = float(stats.get("apr", 0))
            tvl = float(stats.get("tvl", 0))

            # Detect anomalies
            alerts = self.lido.check_anomalies(
                current_apr=current_apr,
                historical_apr=self._prev_apr,
                tvl=tvl,
                prev_tvl=self._prev_tvl,
            )

            # Update stored values for next check
            if current_apr > 0:
                self._prev_apr = current_apr
            if tvl > 0:
                self._prev_tvl = tvl

            if alerts:
                await self._handle_anomalies(alerts, stats)
            else:
                # Return to IDLE if no anomalies
                if self.ctx.state == AgentState.MONITORING:
                    self.ctx.transition(AgentState.IDLE)
        except Exception as e:
            logger.error(f"Vault check failed: {e}")
            self.ctx.last_error = str(e)
            # Return to IDLE on error
            if self.ctx.state == AgentState.MONITORING and self.ctx.can_transition(AgentState.IDLE):
                self.ctx.transition(AgentState.IDLE)

    async def _handle_anomalies(self, alerts: list[VaultAlert], stats: dict) -> None:
        """MONITORING -> ANALYZING: process detected anomalies."""
        # Transition to ANALYZING
        if self.ctx.state == AgentState.MONITORING:
            self.ctx.transition(AgentState.ANALYZING)

        # Send Telegram alerts
        for alert in alerts:
            try:
                await self.telegram.send_alert(alert)
            except Exception as e:
                logger.error(f"Failed to send alert: {e}")

        # Run DeFi analysis via Bankr LLM
        try:
            analysis = await self.analyzer.analyze_protocol("lido")
            logger.info(f"Analysis result: {analysis}")

            # Add signals from the analysis
            for alert in alerts:
                signal_type = (
                    SignalType.APR_CHANGE if alert.metric == "apr" else SignalType.TVL_CHANGE
                )
                severity_weight = {
                    AlertSeverity.INFO: -0.2,
                    AlertSeverity.WARNING: -0.5,
                    AlertSeverity.CRITICAL: -1.0,
                }.get(alert.severity, -0.5)
                self.signals.add(Signal(
                    type=signal_type,
                    source="lido",
                    value=severity_weight,
                    confidence=0.9,
                ))

            market_summary = self.signals.aggregate()
            logger.info(f"Market signals: {market_summary}")
        except Exception as e:
            logger.error(f"Analysis failed: {e}")

        # Return to IDLE
        if self.ctx.state == AgentState.ANALYZING:
            self.ctx.transition(AgentState.IDLE)

    # ------------------------------------------------------------------
    # Serving  (IDLE -> SERVING)
    # ------------------------------------------------------------------

    async def handle_mech_request(self, tool_name: str, query: str) -> str:
        """Handle an inbound mech request and track revenue."""
        result = await self.mech_server.handle_request(tool_name, query)
        self.ctx.requests_served = self.mech_server.requests_served

        # Track mech fee revenue via SliceHook dynamic pricing
        fee = self.slice_hook.calculate_dynamic_price(
            base_price_usd=0.01,
            demand_factor=max(1.0, self.mech_server.requests_served / 10.0),
            market_volatility=0.1,
        )
        self._mech_revenue += fee
        self._update_total_revenue()

        # Create payment intent via Ampersend
        self.ampersend.create_payment_intent(fee, f"mech-request-{tool_name}")

        return result

    # ------------------------------------------------------------------
    # Hiring  (IDLE -> HIRING)
    # ------------------------------------------------------------------

    async def hire_agent(self, tool: str, query: str) -> str:
        """IDLE -> HIRING -> IDLE: hire another mech agent."""
        if self.ctx.state == AgentState.IDLE:
            self.ctx.transition(AgentState.HIRING)

        tx_hash = await self.mech_client.send_request(tool, query)
        self.ctx.requests_hired = self.mech_client.requests_sent

        # Return to IDLE
        if self.ctx.state == AgentState.HIRING:
            self.ctx.transition(AgentState.IDLE)

        return tx_hash

    # ------------------------------------------------------------------
    # Revenue tracking
    # ------------------------------------------------------------------

    def _update_total_revenue(self) -> None:
        """Recalculate total revenue from all sources."""
        zyfai_yield = self.zyfai.total_earned
        self.ctx.total_revenue_usd = self._mech_revenue + zyfai_yield + self._slice_revenue
        self._check_revenue_milestones()

    def _check_revenue_milestones(self) -> None:
        """Send Telegram alert when a revenue milestone is crossed."""
        for milestone in _REVENUE_MILESTONES:
            if (
                self.ctx.total_revenue_usd >= milestone
                and self._last_milestone_hit < milestone
            ):
                self._last_milestone_hit = milestone
                # Fire-and-forget the notification
                try:
                    loop = asyncio.get_running_loop()
                    loop.create_task(self._notify_revenue_milestone(milestone))
                except RuntimeError:
                    pass  # No running loop -- skip async notification

    async def _notify_revenue_milestone(self, milestone: float) -> None:
        try:
            await self.telegram.send_status({
                "state": self.ctx.state.name,
                "requests_served": self.ctx.requests_served,
                "total_revenue_usd": self.ctx.total_revenue_usd,
                "milestone": milestone,
            })
        except Exception as e:
            logger.error(f"Failed to send revenue milestone alert: {e}")

    def record_zyfai_yield(self, amount: float) -> None:
        """Record yield from Zyfai SDK and update total revenue."""
        self.zyfai.record_yield(amount)
        self._update_total_revenue()

    def record_slice_revenue(self, amount: float) -> None:
        """Record revenue from Slice commerce and update total revenue."""
        self._slice_revenue += amount
        self._update_total_revenue()

    def get_revenue_report(self) -> dict:
        """Return a breakdown of revenue across all sources."""
        self._update_total_revenue()
        return {
            "mech_fees": round(self._mech_revenue, 6),
            "zyfai_yield": round(self.zyfai.total_earned, 6),
            "slice_commerce": round(self._slice_revenue, 6),
            "total_usd": round(self.ctx.total_revenue_usd, 6),
            "ampersend_treasury": self.ampersend.get_treasury_status(),
            "zyfai_status": self.zyfai.get_yield_status(),
            "self_sustaining": self.ctx.total_revenue_usd > self.zyfai.total_spent,
        }

    # ------------------------------------------------------------------
    # Status
    # ------------------------------------------------------------------

    def status(self) -> dict:
        return self.ctx.to_dict()

    # ------------------------------------------------------------------
    # Main run loop
    # ------------------------------------------------------------------

    async def run(self) -> None:
        await self.startup()

        # Register scheduled vault monitoring
        self.scheduler.register(
            "vault_check",
            self.check_vaults,
            interval_seconds=self.settings.vault_check_interval_seconds,
        )

        # Start mech server (SERVING)
        mech_runner = await self.mech_server.start()

        # Start Pearl dashboard
        pearl_runner = web.AppRunner(self.pearl_app)
        await pearl_runner.setup()
        pearl_site = web.TCPSite(pearl_runner, "0.0.0.0", self.settings.pearl_port)
        await pearl_site.start()
        logger.info(f"Pearl server on port {self.settings.pearl_port}")

        # Start the scheduler (kicks off vault_check loop)
        await self.scheduler.start()

        logger.info("OpusGod is live. Earning its own living.")
        logger.info(f"  Mech server: port {self.settings.mech_server_port}")
        logger.info(f"  Pearl: port {self.settings.pearl_port}")
        logger.info(f"  Identity: {self.signer.address}")
        logger.info(f"  Slice pricing: {self.slice_hook.get_pricing_config()}")

        try:
            while self.ctx.state != AgentState.SHUTDOWN:
                write_performance_file(self.status())
                await asyncio.sleep(1)
        except asyncio.CancelledError:
            pass
        finally:
            await self.shutdown()


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
