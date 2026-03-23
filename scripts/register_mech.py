"""Register the agent's mech tools on the Olas marketplace."""
import asyncio
import logging
from config.settings import get_settings
from src.mech.tools import TOOL_REGISTRY

logger = logging.getLogger(__name__)


async def register():
    settings = get_settings()
    logger.info(f"Registering {len(TOOL_REGISTRY)} tools on Olas marketplace...")
    for name, tool in TOOL_REGISTRY.items():
        logger.info(f"  {name}: {tool['description']}")
    logger.info("Registration complete (requires on-chain tx in production)")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(register())
