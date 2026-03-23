from __future__ import annotations

import re

from pydantic_settings import BaseSettings
from pydantic import Field, field_validator


class Settings(BaseSettings):
    """All configuration loaded from environment / .env file."""

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
            raise ValueError("OPUS_PRIVATE_KEY is required")
        if not re.match(r"^0x[0-9a-fA-F]{64}$", v):
            raise ValueError(
                "OPUS_PRIVATE_KEY must be a 0x-prefixed 64-char hex string"
            )
        return v


def get_settings() -> Settings:
    return Settings()
