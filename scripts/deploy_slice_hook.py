"""Deploy the Slice pricing hook contract on Base."""
import logging

logger = logging.getLogger(__name__)


def deploy():
    logger.info("To deploy SlicePricingHook:")
    logger.info("  1. Install Foundry: curl -L https://foundry.paradigm.xyz | bash")
    logger.info("  2. forge create contracts/SlicePricingHook.sol:OpusGodPricingHook --constructor-args 1000000000000000")
    logger.info("  3. Verify on BaseScan")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    deploy()
