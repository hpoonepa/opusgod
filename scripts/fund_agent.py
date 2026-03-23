"""Fund the agent wallet on Gnosis and Base."""
import asyncio
import logging
from config.settings import get_settings
from src.onchain.gnosis import GnosisClient
from src.onchain.base import BaseClient

logger = logging.getLogger(__name__)


async def check_funds():
    settings = get_settings()
    gnosis = GnosisClient(rpc_url=settings.gnosis_rpc, private_key=settings.private_key)
    base = BaseClient(rpc_url=settings.base_rpc, private_key=settings.private_key)
    logger.info(f"Agent address: {gnosis.address}")
    try:
        gnosis_bal = await gnosis.get_balance()
        logger.info(f"Gnosis balance: {gnosis_bal / 1e18:.4f} xDAI")
    except Exception as e:
        logger.warning(f"Gnosis balance check failed: {e}")
    try:
        base_bal = await base.get_balance()
        logger.info(f"Base balance: {base_bal / 1e18:.6f} ETH")
    except Exception as e:
        logger.warning(f"Base balance check failed: {e}")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(check_funds())
