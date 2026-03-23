import pytest
from src.onchain.gnosis import GnosisClient
from src.onchain.base import BaseClient
from src.onchain.contracts import MECH_ABI, ADDRESSES


class TestOnchain:
    def test_gnosis_client_init(self):
        client = GnosisClient(rpc_url="https://rpc.gnosischain.com", private_key="0x" + "ab" * 32)
        assert client.chain_id == 100

    def test_base_client_init(self):
        client = BaseClient(rpc_url="https://mainnet.base.org", private_key="0x" + "ab" * 32)
        assert client.chain_id == 8453

    def test_addresses_have_gnosis_and_base(self):
        assert "gnosis" in ADDRESSES
        assert "base" in ADDRESSES

    def test_mech_abi_not_empty(self):
        assert len(MECH_ABI) > 0
