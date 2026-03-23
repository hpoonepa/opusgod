"""ampersend x402 HTTP payment protocol client.

Implements the x402 payment flow:
1. Make HTTP request to a paid endpoint
2. Receive 402 Payment Required with payment details in headers
3. Create EIP-712 signed payment authorization
4. Retry request with payment proof in X-PAYMENT header
"""
from __future__ import annotations

import json
import logging
import time
import uuid

import httpx
from eth_account import Account
from eth_account.messages import encode_defunct

logger = logging.getLogger(__name__)


class PaymentError(Exception):
    """Raised when x402 payment flow fails."""


class AmpersendClient:
    """x402 payment client for HTTP-native micropayments."""

    def __init__(self, api_key: str, private_key: str = "", chain_id: int = 8453):
        self.api_key = api_key
        self._private_key = private_key
        self._account = Account.from_key(private_key) if private_key else None
        self.chain_id = chain_id
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
            "token": resp.headers.get("X-PAYMENT-TOKEN", "ETH"),
            "recipient": resp.headers.get("X-PAYMENT-RECIPIENT", ""),
            "network": resp.headers.get("X-PAYMENT-NETWORK", str(self.chain_id)),
            "facilitator": resp.headers.get("X-PAYMENT-FACILITATOR", ""),
            "nonce": str(uuid.uuid4()),
        }

    def _sign_payment(self, details: dict) -> dict:
        """Create personal_sign payment authorization (EIP-191)."""
        if not self._account:
            raise PaymentError("No private key configured for signing")

        # Build EIP-191 personal_sign message
        message_data = (
            f"x402-payment:{details['amount']}:{details['token']}:"
            f"{details['recipient']}:{details['nonce']}"
        )
        signable = encode_defunct(text=message_data)
        signed = self._account.sign_message(signable)

        return {
            "signature": signed.signature.hex(),
            "sender": self._account.address,
            "amount": details["amount"],
            "token": details["token"],
            "recipient": details["recipient"],
            "nonce": details["nonce"],
            "chainId": int(details["network"]),
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
        }

    async def close(self) -> None:
        await self._client.aclose()
