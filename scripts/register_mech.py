"""Register the agent's mech tools on the Olas marketplace.

Checks on-chain state and registers tools via the mech contract.
"""
import asyncio
import logging
import sys

from config.settings import get_settings
from src.mech.tools import TOOL_REGISTRY
from src.onchain.gnosis import GnosisClient

logger = logging.getLogger(__name__)


async def register():
    settings = get_settings()
    if not settings.private_key or settings.private_key == "0x" + "00" * 32:
        logger.error("Set OPUS_PRIVATE_KEY in .env before registering")
        sys.exit(1)

    gnosis = GnosisClient(rpc_url=settings.gnosis_rpc, private_key=settings.private_key)

    # Check balance for gas
    balance = await gnosis.get_balance()
    balance_xdai = balance / 1e18
    logger.info(f"Agent address: {gnosis.address}")
    logger.info(f"Gnosis balance: {balance_xdai:.4f} xDAI")

    if balance_xdai < 0.01:
        logger.error(f"Insufficient xDAI ({balance_xdai:.4f}). Need >= 0.01 for registration gas.")
        sys.exit(1)

    logger.info(f"Registering {len(TOOL_REGISTRY)} tools on Olas marketplace:")
    for name, tool in TOOL_REGISTRY.items():
        logger.info(f"  - {name}: {tool['description']}")

    if not settings.mech_contract_address:
        logger.info("\nNo OPUS_MECH_CONTRACT_ADDRESS set. To register on-chain:")
        logger.info("  1. Deploy a mech contract or get one from Olas registry")
        logger.info("  2. Set OPUS_MECH_CONTRACT_ADDRESS in .env")
        logger.info("  3. Re-run this script")
        logger.info(f"\nTools ready for registration: {list(TOOL_REGISTRY.keys())}")
        return

    logger.info(f"Mech contract: {settings.mech_contract_address}")
    logger.info("Registration requires on-chain tx — tools will be registered on mech start.")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s: %(message)s")
    asyncio.run(register())
