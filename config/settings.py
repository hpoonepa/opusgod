from __future__ import annotations

from pydantic_settings import BaseSettings
from pydantic import Field


class Settings(BaseSettings):
    """All configuration loaded from environment / .env file."""

    private_key: str = Field(default="")
    gnosis_rpc: str = Field(default="https://rpc.gnosischain.com")
    base_rpc: str = Field(default="https://mainnet.base.org")
    bankr_api_key: str = Field(default="")
    bankr_endpoint: str = Field(default="https://llm.bankr.bot/v1/chat/completions")
    bankr_model: str = Field(default="gpt-4o")
    telegram_bot_token: str = Field(default="")
    telegram_chat_id: str = Field(default="")
    mech_server_port: int = Field(default=8080)
    mech_target_address: str = Field(default="0x77af31De935740567Cf4fF1986D04B2c964A786a")
    lido_api_base: str = Field(default="https://eth-api.lido.fi/v1")
    zyfai_safe_address: str = Field(default="")
    ampersend_api_key: str = Field(default="")
    pearl_port: int = Field(default=8716)
    poll_interval_seconds: int = Field(default=30)
    vault_check_interval_seconds: int = Field(default=300)

    model_config = {"env_file": ".env", "env_prefix": "OPUS_"}


def get_settings() -> Settings:
    return Settings()
