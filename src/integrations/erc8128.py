"""ERC-8128 HTTP Message Signatures — first Python implementation.

Signs HTTP requests per RFC 9421 with Ethereum keys, linking
every API call to an on-chain identity (ERC-8004).
"""
from __future__ import annotations

import hashlib
import time
from urllib.parse import urlparse

from eth_account import Account
from eth_account.messages import encode_defunct


class ERC8128Signer:
    """Sign HTTP requests with an Ethereum private key per ERC-8128."""

    def __init__(self, private_key: str):
        self._account = Account.from_key(private_key)
        self.address = self._account.address

    @staticmethod
    def build_signature_base(
        method: str, url: str, body: str | None, timestamp: int
    ) -> str:
        """Build the canonical signature base string from HTTP parameters."""
        parsed = urlparse(url)
        components = [
            f'"@method": {method.upper()}',
            f'"@target-uri": {url}',
            f'"@authority": {parsed.netloc}',
            f'"@path": {parsed.path}',
            f'"created": {timestamp}',
        ]
        if body:
            digest = hashlib.sha256(body.encode()).hexdigest()
            components.append(f'"content-digest": sha-256={digest}')
        return "\n".join(components)

    def sign_request(
        self, method: str, url: str, body: str | None
    ) -> dict[str, str]:
        """Sign an HTTP request, returning headers to attach."""
        timestamp = int(time.time())
        sig_base = self.build_signature_base(method, url, body, timestamp)

        message = encode_defunct(text=sig_base)
        signed = self._account.sign_message(message)

        headers: dict[str, str] = {
            "Authorization": (
                f'Signature keyId="{self.address}",'
                f'algorithm="eth-personal-sign",'
                f"created={timestamp},"
                f'signature="{signed.signature.hex()}"'
            ),
            "X-ERC8128-Address": self.address,
        }

        if body:
            digest = hashlib.sha256(body.encode()).hexdigest()
            headers["Digest"] = f"sha-256={digest}"

        return headers


def verify_signature(
    method: str,
    url: str,
    body: str | None,
    headers: dict[str, str],
    expected_address: str,
) -> bool:
    """Verify an ERC-8128 signed request by rebuilding the signature base.

    Rebuilds the signature base from the HTTP parameters (method, url, body,
    timestamp) rather than trusting any internal header -- this is the
    production-correct approach.
    """
    try:
        auth = headers.get("Authorization", "")
        sig_hex = auth.split('signature="')[1].rstrip('"')
        timestamp_str = auth.split("created=")[1].split(",")[0]
        timestamp = int(timestamp_str)

        # Rebuild signature base from HTTP parameters (not from headers)
        sig_base = ERC8128Signer.build_signature_base(method, url, body, timestamp)
        message = encode_defunct(text=sig_base)

        recovered = Account.recover_message(message, signature=bytes.fromhex(sig_hex))
        return recovered.lower() == expected_address.lower()
    except Exception:
        return False
