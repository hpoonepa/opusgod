from __future__ import annotations

MECH_ABI = [
    {"inputs": [{"name": "data", "type": "bytes"}], "name": "request",
     "outputs": [{"name": "requestId", "type": "uint256"}], "stateMutability": "payable", "type": "function"},
    {"inputs": [{"name": "requestId", "type": "uint256"}], "name": "getResponse",
     "outputs": [{"name": "", "type": "bytes"}], "stateMutability": "view", "type": "function"},
]

ERC20_ABI = [
    {"inputs": [{"name": "account", "type": "address"}], "name": "balanceOf",
     "outputs": [{"name": "", "type": "uint256"}], "stateMutability": "view", "type": "function"},
    {"inputs": [{"name": "to", "type": "address"}, {"name": "amount", "type": "uint256"}],
     "name": "transfer", "outputs": [{"name": "", "type": "bool"}], "stateMutability": "nonpayable", "type": "function"},
]

ADDRESSES = {
    "gnosis": {"mech": "0x77af31De935740567Cf4fF1986D04B2c964A786a", "olas_token": "0xcE11e14225575945b8E6Dc0D4d255cB05d982BbB"},
    "base": {"slice_factory": "0x0000000000000000000000000000000000000000"},
}
