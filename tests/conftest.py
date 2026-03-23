import pytest
import os

os.environ.setdefault("OPUS_PRIVATE_KEY", "0x" + "ab" * 32)
os.environ.setdefault("OPUS_BANKR_API_KEY", "test-key")
os.environ.setdefault("OPUS_TELEGRAM_BOT_TOKEN", "test-token")
os.environ.setdefault("OPUS_TELEGRAM_CHAT_ID", "123456")

pytest_plugins = ["pytest_asyncio"]
