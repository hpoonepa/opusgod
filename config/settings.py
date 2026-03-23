from __future__ import annotations

import re

from pydantic_settings import BaseSettings
from pydantic import Field, field_validator


class Settings(BaseSettings):
    """All configuration loaded from environment / .env file."""

    # --- Demo mode: skip integrations that need API keys ---
    demo_mode: bool = Field(default=False, description="Run in demo mode with mock integrations")

    # --- Required: Agent identity ---
    private_key: str = Field(
        default="0x" + "00" * 32,
        description="Agent Ethereum private key (hex)",
    )

    # --- Chain RPCs ---
    gnosis_rpc: str = Field(default="https://rpc.gnosischain.com")
    base_rpc: str = Field(default="https://mainnet.base.org")

    # --- Bankr LLM Gateway ---
    bankr_api_key: str = Field(default="", description="Bankr LLM Gateway API key")
    bankr_endpoint: str = Field(default="https://llm.bankr.bot/v1/chat/completions")
    bankr_model: str = Field(default="gpt-4o")

    # --- Telegram notifications ---
    telegram_bot_token: str = Field(default="", description="Telegram bot token")
    telegram_chat_id: str = Field(default="", description="Telegram chat ID for alerts")

    # --- Zyfai yield SDK ---
    zyfai_api_key: str = Field(default="", description="Zyfai SDK API key")
    zyfai_safe_address: str = Field(default="")

    # --- Mech server / client ---
    mech_server_port: int = Field(default=8080)
    mech_target_address: str = Field(
        default="0x77af31De935740567Cf4fF1986D04B2c964A786a",
        description="Target mech contract address for hiring",
    )
    mech_contract_address: str = Field(default="", description="Mech contract address")

    # --- Lido monitoring ---
    lido_api_base: str = Field(default="https://eth-api.lido.fi", alias="lido_api_url")

    # --- Slice commerce ---
    slice_contract_address: str = Field(default="", description="Slice hook contract address on Base")

    # --- Ampersend payments ---
    ampersend_api_key: str = Field(default="", description="Ampersend API key")

    # --- Ampersend payment cap ---
    ampersend_max_payment: float = Field(default=1.0, description="Max single x402 payment in token units")

    # --- Pearl dashboard ---
    pearl_port: int = Field(default=8716)

    # --- Scheduling ---
    poll_interval_seconds: int = Field(default=30)
    vault_check_interval_seconds: int = Field(default=300)

    model_config = {
        "env_file": ".env",
        "env_prefix": "OPUS_",
        "populate_by_name": True,
    }

    @field_validator("private_key")
    @classmethod
    def validate_private_key(cls, v: str) -> str:
        if not v:
            raise ValueError(
                "OPUS_PRIVATE_KEY is required. Set it in your .env file:\n"
                "  OPUS_PRIVATE_KEY=0x<your-64-char-hex-key>\n"
                "Or run with OPUS_DEMO_MODE=true to skip key validation."
            )
        if not re.match(r"^0x[0-9a-fA-F]{64}$", v):
            raise ValueError(
                "OPUS_PRIVATE_KEY must be a 0x-prefixed 64-char hex string.\n"
                "Example: OPUS_PRIVATE_KEY=0xac0974bec39a17e36ba4a6b4d238ff944bacb478cbed5efcae784d7bf4f2ff80"
            )
        if v == "0x" + "00" * 32:
            raise ValueError(
                "Default zero key is insecure — set OPUS_PRIVATE_KEY in .env.\n"
                "Or run with OPUS_DEMO_MODE=true for a demo without real keys."
            )
        return v


def get_settings() -> Settings:
    """Load settings. In demo mode, relax private key validation."""
    import os
    if os.environ.get("OPUS_DEMO_MODE", "").lower() in ("true", "1", "yes"):
        os.environ.setdefault("OPUS_PRIVATE_KEY", "0x" + "ab" * 32)
        os.environ["OPUS_DEMO_MODE"] = "true"
    return Settings()
