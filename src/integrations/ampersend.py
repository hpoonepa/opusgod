"""ampersend x402 HTTP payment protocol client.

Implements the x402 payment flow:
1. Make HTTP request to a paid endpoint
2. Receive 402 Payment Required with payment details in headers
3. Create EIP-712 structured-data signed payment authorization
4. Retry request with payment proof in X-PAYMENT header
"""
from __future__ import annotations

import json
import logging
import time
import uuid

import httpx
from eth_account import Account

logger = logging.getLogger(__name__)


class PaymentError(Exception):
    """Raised when x402 payment flow fails."""


class AmpersendClient:
    """x402 payment client for HTTP-native micropayments (EIP-712 signed)."""

    DEFAULT_MAX_PAYMENT = 1.0  # Max single payment in token units

    def __init__(self, api_key: str, private_key: str = "", chain_id: int = 8453,
                 max_payment: float | None = None):
        self.api_key = api_key
        self._private_key = private_key
        self._account = Account.from_key(private_key) if private_key else None
        self.chain_id = chain_id
        self.max_payment = max_payment if max_payment is not None else self.DEFAULT_MAX_PAYMENT
        self._client = httpx.AsyncClient(timeout=30.0)
        self._payments: dict[str, dict] = {}
        self._total_spent: float = 0.0

    async def request_with_payment(self, method: str, url: str, **kwargs) -> httpx.Response:
        """Make an HTTP request, automatically handling 402 payment flows."""
        headers = kwargs.pop("headers", {})
        headers["X-API-Key"] = self.api_key

        resp = await self._client.request(method, url, headers=headers, **kwargs)

        if resp.status_code == 402:
            payment_details = self._parse_402(resp)

            # Enforce payment cap
            amount = float(payment_details.get("amount", 0))
            if amount > self.max_payment:
                raise PaymentError(
                    f"Payment amount {amount} exceeds cap {self.max_payment}. "
                    f"Increase max_payment or set OPUS_AMPERSEND_MAX_PAYMENT."
                )

            payment_proof = self._sign_payment(payment_details)
            headers["X-PAYMENT"] = json.dumps(payment_proof)
            resp = await self._client.request(method, url, headers=headers, **kwargs)

            if resp.status_code == 200:
                self._record_payment(payment_details, payment_proof)
            else:
                logger.warning(
                    f"x402 payment retry failed with status {resp.status_code} "
                    f"for {method} {url} — payment may have been lost"
                )

        return resp

    def _parse_402(self, resp: httpx.Response) -> dict:
        """Parse payment requirements from 402 response."""
        return {
            "amount": resp.headers.get("X-PAYMENT-AMOUNT", "0"),
            "token": resp.headers.get("X-PAYMENT-TOKEN", "0x0000000000000000000000000000000000000000"),
            "recipient": resp.headers.get("X-PAYMENT-RECIPIENT", ""),
            "network": resp.headers.get("X-PAYMENT-NETWORK", str(self.chain_id)),
            "facilitator": resp.headers.get("X-PAYMENT-FACILITATOR", ""),
            "nonce": str(uuid.uuid4()),
        }

    def _sign_payment(self, details: dict) -> dict:
        """Create EIP-712 structured-data signed payment authorization."""
        if not self._account:
            raise PaymentError("No private key configured for signing")

        # EIP-712 domain and types for x402 payments
        domain_data = {
            "name": "x402",
            "version": "1",
            "chainId": int(details.get("network", self.chain_id)),
        }
        message_types = {
            "Payment": [
                {"name": "amount", "type": "uint256"},
                {"name": "token", "type": "address"},
                {"name": "recipient", "type": "address"},
                {"name": "nonce", "type": "string"},
            ],
        }
        message_data = {
            "amount": int(details["amount"]),
            "token": details["token"],
            "recipient": details["recipient"],
            "nonce": details["nonce"],
        }

        signed = Account.sign_typed_data(
            self._private_key,
            domain_data=domain_data,
            message_types=message_types,
            message_data=message_data,
        )

        return {
            "signature": signed.signature.hex(),
            "sender": self._account.address,
            "amount": details["amount"],
            "token": details["token"],
            "recipient": details["recipient"],
            "nonce": details["nonce"],
            "chainId": int(details.get("network", self.chain_id)),
            "scheme": "eip712",
        }

    def _record_payment(self, details: dict, proof: dict) -> None:
        """Record a completed payment."""
        payment_id = proof["nonce"]
        amount = float(details["amount"])
        self._payments[payment_id] = {
            "id": payment_id,
            "amount": amount,
            "token": details["token"],
            "recipient": details["recipient"],
            "sender": proof["sender"],
            "timestamp": int(time.time()),
            "status": "completed",
            "scheme": "eip712",
        }
        self._total_spent += amount
        logger.info(f"x402 payment completed: {amount} {details['token']} to {details['recipient']}")

    def create_payment_intent(self, amount_usd: float, description: str) -> dict:
        """Create a payment intent (for compatibility)."""
        if amount_usd <= 0:
            raise PaymentError(f"Invalid payment amount: {amount_usd}")
        intent_id = str(uuid.uuid4())
        intent = {
            "id": intent_id, "amount": amount_usd, "currency": "USD",
            "description": description, "status": "pending",
            "timestamp": int(time.time()),
        }
        self._payments[intent_id] = intent
        return intent

    def complete_payment(self, payment_id: str) -> bool:
        """Mark a payment as completed. Only adds to total_spent if not already completed."""
        if payment_id in self._payments:
            payment = self._payments[payment_id]
            if payment["status"] != "completed":
                payment["status"] = "completed"
                self._total_spent += payment.get("amount", 0)
            return True
        return False

    def get_treasury_status(self) -> dict:
        """Get treasury/payment summary."""
        completed = [p for p in self._payments.values() if p["status"] == "completed"]
        return {
            "total_spent": self._total_spent,
            "total_payments": len(completed),
            "pending": sum(1 for p in self._payments.values() if p["status"] == "pending"),
            "address": self._account.address if self._account else None,
            "max_payment": self.max_payment,
            "scheme": "eip712",
        }

    async def close(self) -> None:
        await self._client.aclose()
