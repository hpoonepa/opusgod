"""On-chain contract ABIs and addresses."""
from __future__ import annotations

MECH_ABI = [
    {"inputs": [{"name": "data", "type": "bytes"}], "name": "request",
     "outputs": [{"name": "requestId", "type": "uint256"}], "stateMutability": "payable", "type": "function"},
    {"inputs": [{"name": "requestId", "type": "uint256"}], "name": "getResponse",
     "outputs": [{"name": "", "type": "bytes"}], "stateMutability": "view", "type": "function"},
    # deliver() — mech operator calls this to fulfill a request on-chain
    {"inputs": [
        {"name": "requestId", "type": "uint256"},
        {"name": "data", "type": "bytes"},
    ], "name": "deliver",
     "outputs": [], "stateMutability": "nonpayable", "type": "function"},
    # Deliver event — emitted when a mech fulfills a request
    {"anonymous": False, "inputs": [
        {"indexed": True, "name": "requestId", "type": "uint256"},
        {"indexed": False, "name": "data", "type": "bytes"},
    ], "name": "Deliver", "type": "event"},
    # Request event — emitted when a request is made
    {"anonymous": False, "inputs": [
        {"indexed": True, "name": "sender", "type": "address"},
        {"indexed": True, "name": "requestId", "type": "uint256"},
        {"indexed": False, "name": "data", "type": "bytes"},
    ], "name": "Request", "type": "event"},
]

ERC20_ABI = [
    {"inputs": [{"name": "account", "type": "address"}], "name": "balanceOf",
     "outputs": [{"name": "", "type": "uint256"}], "stateMutability": "view", "type": "function"},
    {"inputs": [{"name": "to", "type": "address"}, {"name": "amount", "type": "uint256"}],
     "name": "transfer", "outputs": [{"name": "", "type": "bool"}], "stateMutability": "nonpayable", "type": "function"},
    {"inputs": [{"name": "spender", "type": "address"}, {"name": "amount", "type": "uint256"}],
     "name": "approve", "outputs": [{"name": "", "type": "bool"}], "stateMutability": "nonpayable", "type": "function"},
    {"inputs": [{"name": "owner", "type": "address"}, {"name": "spender", "type": "address"}],
     "name": "allowance", "outputs": [{"name": "", "type": "uint256"}], "stateMutability": "view", "type": "function"},
]

ADDRESSES = {
    "gnosis": {
        "mech": "0x77af31De935740567Cf4fF1986D04B2c964A786a",
        "olas_token": "0xcE11e14225575945b8E6Dc0D4d255cB05d982BbB",
    },
    "base": {
        "slice_factory": "0x3bC0C5F89b10e45F74e7b87bFd1203Ed43422EFa",
    },
}
