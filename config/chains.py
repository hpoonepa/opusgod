from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ChainConfig:
    chain_id: int
    rpc_url: str
    name: str
    explorer: str


GNOSIS = ChainConfig(chain_id=100, rpc_url="https://rpc.gnosischain.com", name="Gnosis", explorer="https://gnosisscan.io")
BASE = ChainConfig(chain_id=8453, rpc_url="https://mainnet.base.org", name="Base", explorer="https://basescan.org")
CHAINS: dict[str, ChainConfig] = {"gnosis": GNOSIS, "base": BASE}
