"""ERC-8128 HTTP Message Signatures — spec-compliant Python implementation.

Signs HTTP requests per RFC 9421 with Ethereum secp256k1 keys, linking
every API call to an on-chain identity.

Signature flow:
1. Build RFC 9421 signature base from HTTP components
2. Keccak-256 hash the signature base
3. Sign with secp256k1 ECDSA (raw, NOT personal_sign)
4. Output Signature-Input + Signature headers per RFC 9421
"""
from __future__ import annotations

import base64
import hashlib
import re
import time
import uuid
from urllib.parse import urlparse

from eth_account import Account
from eth_account.messages import encode_defunct

ALGORITHM = "ecdsa-secp256k1-sha256"
DEFAULT_TTL_SECONDS = 300
SIGNATURE_LABEL = "sig1"

_COVERED = ('"@method"', '"@target-uri"', '"@authority"')
_COVERED_BODY = ('"@method"', '"@target-uri"', '"@authority"', '"content-digest"')


def _content_digest(body: str) -> str:
    """SHA-256 Content-Digest in RFC 9530 structured-field format."""
    raw = hashlib.sha256(body.encode("utf-8")).digest()
    return f"sha-256=:{base64.b64encode(raw).decode()}:"


def _build_signature_base(
    method: str, url: str, body: str | None,
    created: int, nonce: str, keyid: str,
) -> str:
    """Build the RFC 9421 signature base string."""
    parsed = urlparse(url)
    lines = [
        f'"@method": {method.upper()}',
        f'"@target-uri": {url}',
        f'"@authority": {parsed.netloc}',
    ]
    if body:
        lines.append(f'"content-digest": {_content_digest(body)}')

    components = _COVERED_BODY if body else _COVERED
    sig_params = (
        f"({' '.join(components)});created={created}"
        f';nonce="{nonce}";keyid="{keyid}";alg="{ALGORITHM}"'
    )
    lines.append(f'"@signature-params": {sig_params}')
    return "\n".join(lines)


class ERC8128Signer:
    """Sign HTTP requests with an Ethereum private key per ERC-8128 + RFC 9421."""

    def __init__(self, private_key: str, chain_id: int = 1):
        self._private_key = private_key
        self._account = Account.from_key(private_key)
        self.address: str = self._account.address
        self.chain_id = chain_id

    @property
    def keyid(self) -> str:
        return f"erc8128:{self.chain_id}:{self.address}"

    def sign_request(
        self, method: str, url: str, body: str | None = None,
        *, created: int | None = None, nonce: str | None = None,
    ) -> dict[str, str]:
        """Sign an HTTP request, returning RFC 9421 headers."""
        if created is None:
            created = int(time.time())
        if nonce is None:
            nonce = str(uuid.uuid4())

        sig_base = _build_signature_base(method, url, body, created, nonce, self.keyid)

        # Hash the signature base, then sign with secp256k1
        msg_hash = hashlib.sha256(sig_base.encode("utf-8")).digest()
        signable = encode_defunct(primitive=msg_hash)
        signed = self._account.sign_message(signable)
        sig_b64 = base64.b64encode(signed.signature).decode()

        components = _COVERED_BODY if body else _COVERED
        sig_input = (
            f"{SIGNATURE_LABEL}=({' '.join(components)});created={created}"
            f';nonce="{nonce}";keyid="{self.keyid}";alg="{ALGORITHM}"'
        )

        headers: dict[str, str] = {
            "Signature-Input": sig_input,
            "Signature": f"{SIGNATURE_LABEL}=:{sig_b64}:",
        }
        if body:
            headers["Content-Digest"] = _content_digest(body)
        return headers


def verify_signature(
    method: str, url: str, body: str | None,
    headers: dict[str, str], expected_address: str,
    *, ttl_seconds: int = DEFAULT_TTL_SECONDS,
) -> bool:
    """Verify an ERC-8128 signed request."""
    sig_input_raw = headers.get("Signature-Input")
    sig_raw = headers.get("Signature")
    if not sig_input_raw or not sig_raw:
        raise ValueError("Missing Signature-Input or Signature header")

    created_m = re.search(r";created=(\d+)", sig_input_raw)
    nonce_m = re.search(r';nonce="([^"]+)"', sig_input_raw)
    keyid_m = re.search(r';keyid="([^"]+)"', sig_input_raw)
    if not created_m or not nonce_m or not keyid_m:
        raise ValueError("Malformed Signature-Input")

    created = int(created_m.group(1))
    nonce = nonce_m.group(1)
    keyid = keyid_m.group(1)

    # Check freshness
    age = int(time.time()) - created
    if age > ttl_seconds or age < 0:
        return False

    # Extract signature bytes
    sig_b64_m = re.search(r"sig1=:([A-Za-z0-9+/=]+):", sig_raw)
    if not sig_b64_m:
        raise ValueError("Malformed Signature header")
    sig_bytes = base64.b64decode(sig_b64_m.group(1))

    # Rebuild signature base and verify
    sig_base = _build_signature_base(method, url, body, created, nonce, keyid)
    msg_hash = hashlib.sha256(sig_base.encode("utf-8")).digest()
    signable = encode_defunct(primitive=msg_hash)

    try:
        recovered = Account.recover_message(signable, signature=sig_bytes)
        return recovered.lower() == expected_address.lower()
    except Exception:
        return False
