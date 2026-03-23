from __future__ import annotations
import logging
from web3 import AsyncWeb3, AsyncHTTPProvider
from eth_account import Account

logger = logging.getLogger(__name__)


class GnosisClient:
    def __init__(self, rpc_url: str, private_key: str):
        self.w3 = AsyncWeb3(AsyncHTTPProvider(rpc_url))
        self._account = Account.from_key(private_key)
        self.address = self._account.address
        self.chain_id = 100

    async def get_balance(self) -> int:
        return await self.w3.eth.get_balance(self.address)

    async def send_transaction(self, to: str, data: bytes, value: int = 0) -> str:
        nonce = await self.w3.eth.get_transaction_count(self.address)
        tx = {"to": to, "value": value, "gas": 200_000, "gasPrice": await self.w3.eth.gas_price,
              "nonce": nonce, "chainId": self.chain_id, "data": data}
        signed = self._account.sign_transaction(tx)
        tx_hash = await self.w3.eth.send_raw_transaction(signed.raw_transaction)
        logger.info(f"Gnosis tx sent: {tx_hash.hex()}")
        return tx_hash.hex()
