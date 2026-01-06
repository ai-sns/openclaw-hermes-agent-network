"""
Escrow Module

Provides smart contract interaction for staking and settlement.
"""

from .contract import EscrowContract
from .stake import StakeManager
from .settlement import SettlementEngine

__all__ = ["EscrowContract", "StakeManager", "SettlementEngine"]
