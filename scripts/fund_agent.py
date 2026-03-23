"""Fund the agent wallet on Gnosis and Base.

Checks balances and reports funding status with minimum thresholds.
"""
import asyncio
import logging
import sys

from config.settings import get_settings
from src.onchain.gnosis import GnosisClient
from src.onchain.base import BaseClient

logger = logging.getLogger(__name__)

MIN_GNOSIS_XDAI = 0.1   # Minimum xDAI for mech operations
MIN_BASE_ETH = 0.001     # Minimum ETH for Slice/Base operations


async def check_funds():
    settings = get_settings()
    if not settings.private_key or settings.private_key == "0x" + "00" * 32:
        logger.error("Set OPUS_PRIVATE_KEY in .env first")
        sys.exit(1)

    gnosis = GnosisClient(rpc_url=settings.gnosis_rpc, private_key=settings.private_key)
    base = BaseClient(rpc_url=settings.base_rpc, private_key=settings.private_key)
    logger.info(f"Agent address: {gnosis.address}")

    issues = []

    # Check Gnosis
    try:
        gnosis_bal = await gnosis.get_balance()
        gnosis_xdai = gnosis_bal / 1e18
        status = "OK" if gnosis_xdai >= MIN_GNOSIS_XDAI else "LOW"
        logger.info(f"Gnosis balance: {gnosis_xdai:.4f} xDAI [{status}]")
        if gnosis_xdai < MIN_GNOSIS_XDAI:
            issues.append(f"Gnosis: need >= {MIN_GNOSIS_XDAI} xDAI, have {gnosis_xdai:.4f}")
    except Exception as e:
        logger.warning(f"Gnosis balance check failed: {e}")
        issues.append("Gnosis: could not check balance")

    # Check Base
    try:
        base_bal = await base.get_balance()
        base_eth = base_bal / 1e18
        status = "OK" if base_eth >= MIN_BASE_ETH else "LOW"
        logger.info(f"Base balance: {base_eth:.6f} ETH [{status}]")
        if base_eth < MIN_BASE_ETH:
            issues.append(f"Base: need >= {MIN_BASE_ETH} ETH, have {base_eth:.6f}")
    except Exception as e:
        logger.warning(f"Base balance check failed: {e}")
        issues.append("Base: could not check balance")

    if issues:
        logger.warning("Funding issues detected:")
        for issue in issues:
            logger.warning(f"  - {issue}")
        logger.info(f"\nFund address: {gnosis.address}")
        logger.info("  Gnosis faucet: https://gnosisfaucet.com")
        logger.info("  Base bridge: https://bridge.base.org")
    else:
        logger.info("All balances OK — agent is funded and ready to operate.")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s: %(message)s")
    asyncio.run(check_funds())
