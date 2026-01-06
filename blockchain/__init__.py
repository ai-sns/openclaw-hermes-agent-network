"""
Blockchain Integration Module

Provides:
- DID (Decentralized Identity) with Ethereum wallet
- Smart Contract Escrow for task staking and settlement
- Payment system (pay-per-request, streaming)
- Audit logging with on-chain hash verification

Network: Ethereum Sepolia Testnet
"""

__version__ = "1.0.0"

from .config import BlockchainConfig
from .did import DIDWallet
from .escrow import EscrowContract
from .payment import PayPerRequest, StreamingPayment
from .audit import HashLogger

__all__ = [
    "BlockchainConfig",
    "DIDWallet",
    "EscrowContract",
    "PayPerRequest",
    "StreamingPayment",
    "HashLogger",
]
