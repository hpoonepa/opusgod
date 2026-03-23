"""Deploy the Slice pricing hook contract on Base.

Uses web3 to deploy the contract bytecode. Requires a funded Base wallet.
"""
import asyncio
import logging
import sys

from config.settings import get_settings
from src.onchain.base import BaseClient

logger = logging.getLogger(__name__)

# Minimal bytecode for a pricing hook (constructor takes basePrice uint256)
# In production, compile from contracts/SlicePricingHook.sol via forge/solc
HOOK_BYTECODE = None  # Set from compiled artifact


async def deploy():
    settings = get_settings()
    if not settings.private_key or settings.private_key == "0x" + "00" * 32:
        logger.error("Set OPUS_PRIVATE_KEY in .env before deploying")
        sys.exit(1)

    client = BaseClient(rpc_url=settings.base_rpc, private_key=settings.private_key)

    # Check balance
    balance = await client.get_balance()
    balance_eth = balance / 1e18
    logger.info(f"Deployer: {client.address}")
    logger.info(f"Base balance: {balance_eth:.6f} ETH")

    if balance_eth < 0.001:
        logger.error(f"Insufficient balance ({balance_eth:.6f} ETH). Need >= 0.001 ETH for deployment gas.")
        sys.exit(1)

    if HOOK_BYTECODE is None:
        logger.info("No compiled bytecode found. To deploy:")
        logger.info("  1. Install Foundry: curl -L https://foundry.paradigm.xyz | bash && foundryup")
        logger.info("  2. Compile: forge build")
        logger.info("  3. Set HOOK_BYTECODE in this script from the build artifact")
        logger.info("  4. Or deploy directly: forge create contracts/SlicePricingHook.sol:OpusGodPricingHook "
                     "--constructor-args 1000000000000000 --rpc-url $OPUS_BASE_RPC --private-key $OPUS_PRIVATE_KEY")
        sys.exit(0)

    logger.info("Deploying SlicePricingHook to Base...")
    tx_hash = await client.send_transaction(to="", data=HOOK_BYTECODE)
    receipt = await client.wait_for_receipt(tx_hash)
    contract_address = receipt.get("contractAddress", "unknown")
    logger.info(f"Deployed at: {contract_address}")
    logger.info(f"Set OPUS_SLICE_CONTRACT_ADDRESS={contract_address} in .env")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s: %(message)s")
    asyncio.run(deploy())
