import pytest
from eth_account import Account
from src.integrations.erc8128 import ERC8128Signer, verify_signature


@pytest.fixture
def account():
    return Account.create()


@pytest.fixture
def signer(account):
    return ERC8128Signer(private_key=account.key.hex())


class TestERC8128:
    def test_sign_request(self, signer):
        headers = signer.sign_request(method="GET", url="https://api.example.com/vaults", body=None)
        assert "Authorization" in headers
        assert "Signature" in headers["Authorization"]

    def test_sign_request_with_body(self, signer):
        headers = signer.sign_request(method="POST", url="https://api.example.com/analyze", body='{"vault": "0x123"}')
        assert "Digest" in headers
        assert "Authorization" in headers

    def test_verify_valid_signature(self, signer, account):
        headers = signer.sign_request("GET", "https://api.example.com/test", None)
        is_valid = verify_signature(
            method="GET", url="https://api.example.com/test", body=None,
            headers=headers, expected_address=account.address,
        )
        assert is_valid

    def test_verify_rejects_tampered(self, signer, account):
        headers = signer.sign_request("GET", "https://api.example.com/test", None)
        is_valid = verify_signature(
            method="GET", url="https://api.example.com/TAMPERED", body=None,
            headers=headers, expected_address=account.address,
        )
        assert not is_valid
