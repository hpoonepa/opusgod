import base64
import re
import time

import pytest
from eth_account import Account
from src.integrations.erc8128 import ERC8128Signer, verify_signature, _content_digest


@pytest.fixture
def account():
    return Account.create()


@pytest.fixture
def signer(account):
    return ERC8128Signer(private_key=account.key.hex(), chain_id=1)


class TestERC8128:
    def test_sign_request(self, signer):
        headers = signer.sign_request(method="GET", url="https://api.example.com/vaults")
        assert "Signature-Input" in headers
        assert "Signature" in headers
        assert "Authorization" not in headers

    def test_sign_request_with_body(self, signer):
        headers = signer.sign_request(method="POST", url="https://api.example.com/analyze", body='{"vault": "0x123"}')
        assert "Content-Digest" in headers
        assert "Signature-Input" in headers
        assert headers["Content-Digest"].startswith("sha-256=:")

    def test_signature_input_format(self, signer):
        headers = signer.sign_request("GET", "https://api.example.com/test")
        sig_input = headers["Signature-Input"]
        assert sig_input.startswith("sig1=(")
        assert ";created=" in sig_input
        assert ";nonce=" in sig_input
        assert f';keyid="{signer.keyid}"' in sig_input

    def test_signature_format(self, signer):
        headers = signer.sign_request("GET", "https://api.example.com/test")
        assert re.match(r"sig1=:[A-Za-z0-9+/=]+:", headers["Signature"])

    def test_keyid_format(self, signer, account):
        assert signer.keyid == f"erc8128:1:{account.address}"

    def test_nonce_unique(self, signer):
        h1 = signer.sign_request("GET", "https://example.com")
        h2 = signer.sign_request("GET", "https://example.com")
        n1 = re.search(r';nonce="([^"]+)"', h1["Signature-Input"]).group(1)
        n2 = re.search(r';nonce="([^"]+)"', h2["Signature-Input"]).group(1)
        assert n1 != n2

    def test_verify_valid_signature(self, signer, account):
        headers = signer.sign_request("GET", "https://api.example.com/test")
        assert verify_signature(
            method="GET", url="https://api.example.com/test", body=None,
            headers=headers, expected_address=account.address,
        )

    def test_verify_roundtrip_with_body(self, signer, account):
        body = '{"vault": "0xabc"}'
        headers = signer.sign_request("POST", "https://api.example.com/analyze", body=body)
        assert verify_signature(
            method="POST", url="https://api.example.com/analyze", body=body,
            headers=headers, expected_address=account.address,
        )

    def test_verify_rejects_tampered(self, signer, account):
        headers = signer.sign_request("GET", "https://api.example.com/test")
        assert not verify_signature(
            method="GET", url="https://api.example.com/TAMPERED", body=None,
            headers=headers, expected_address=account.address,
        )

    def test_verify_rejects_wrong_address(self, signer):
        other = Account.create()
        headers = signer.sign_request("GET", "https://api.example.com/test")
        assert not verify_signature(
            method="GET", url="https://api.example.com/test", body=None,
            headers=headers, expected_address=other.address,
        )

    def test_verify_rejects_expired(self, signer, account):
        headers = signer.sign_request("GET", "https://api.example.com/test",
                                       created=int(time.time()) - 600)
        assert not verify_signature(
            method="GET", url="https://api.example.com/test", body=None,
            headers=headers, expected_address=account.address,
        )

    def test_content_digest_deterministic(self):
        d1 = _content_digest("hello")
        d2 = _content_digest("hello")
        assert d1 == d2

    def test_content_digest_different(self):
        assert _content_digest("hello") != _content_digest("world")
