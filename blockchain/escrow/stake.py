"""
Stake Manager

Manages staking operations for task escrow.
"""

import os
from typing import Optional, Dict, Any, List
from decimal import Decimal
from datetime import datetime
from dataclasses import dataclass, field
from enum import Enum
import logging

import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from blockchain.escrow.contract import EscrowContract, EscrowStatus, get_escrow_contract

logger = logging.getLogger(__name__)


class StakeType(str, Enum):
    """Types of stakes"""
    TASK_PAYMENT = "task_payment"
    QUALITY_BOND = "quality_bond"
    SECURITY_DEPOSIT = "security_deposit"


@dataclass
class StakeRecord:
    """Stake record"""
    stake_id: str
    task_id: str
    stake_type: StakeType
    staker_address: str
    amount_wei: int
    status: str = "active"
    created_at: datetime = field(default_factory=datetime.now)
    released_at: Optional[datetime] = None
    tx_hash: Optional[str] = None

    @property
    def amount_eth(self) -> Decimal:
        """Get amount in ETH"""
        return Decimal(self.amount_wei) / Decimal(10**18)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "stake_id": self.stake_id,
            "task_id": self.task_id,
            "stake_type": self.stake_type.value,
            "staker_address": self.staker_address,
            "amount_wei": str(self.amount_wei),
            "amount_eth": str(self.amount_eth),
            "status": self.status,
            "created_at": self.created_at.isoformat(),
            "released_at": self.released_at.isoformat() if self.released_at else None,
            "tx_hash": self.tx_hash
        }


class StakeManager:
    """
    Stake Manager

    Manages staking operations:
    - Task payment staking
    - Quality bonds
    - Automatic stake release
    """

    def __init__(self, escrow_contract: Optional[EscrowContract] = None):
        """
        Initialize stake manager.

        Args:
            escrow_contract: Escrow contract instance
        """
        self.escrow = escrow_contract or get_escrow_contract()
        self._stakes: Dict[str, StakeRecord] = {}

    def _generate_stake_id(self, task_id: str, stake_type: StakeType) -> str:
        """Generate unique stake ID"""
        import hashlib
        hash_input = f"{task_id}_{stake_type.value}_{datetime.now().isoformat()}"
        return f"stake_{hashlib.sha256(hash_input.encode()).hexdigest()[:16]}"

    async def stake_for_task(
        self,
        task_id: str,
        beneficiary: str,
        amount_eth: Decimal,
        stake_type: StakeType = StakeType.TASK_PAYMENT,
        wallet = None
    ) -> StakeRecord:
        """
        Create a stake for a task.

        Args:
            task_id: Task ID
            beneficiary: Address to receive funds on completion
            amount_eth: Amount in ETH
            stake_type: Type of stake
            wallet: Wallet to use for staking

        Returns:
            StakeRecord
        """
        # Convert to wei
        amount_wei = int(amount_eth * Decimal(10**18))

        # Deposit to escrow
        result = await self.escrow.deposit(
            task_id=task_id,
            beneficiary=beneficiary,
            amount_wei=amount_wei,
            from_wallet=wallet
        )

        # Create stake record
        stake = StakeRecord(
            stake_id=self._generate_stake_id(task_id, stake_type),
            task_id=task_id,
            stake_type=stake_type,
            staker_address=wallet.address if wallet else "unknown",
            amount_wei=amount_wei,
            status="active",
            tx_hash=result.get("tx_hash")
        )

        self._stakes[stake.stake_id] = stake

        logger.info(f"Stake created: {stake.stake_id} for task {task_id}")
        return stake

    async def release_stake(self, task_id: str) -> Dict[str, Any]:
        """
        Release stake for a completed task.

        Args:
            task_id: Task ID

        Returns:
            Release result
        """
        # Find stake for task
        stake = None
        for s in self._stakes.values():
            if s.task_id == task_id and s.status == "active":
                stake = s
                break

        if not stake:
            return {"success": False, "error": "No active stake found for task"}

        # Release from escrow
        result = await self.escrow.release(task_id)

        if result.get("success"):
            stake.status = "released"
            stake.released_at = datetime.now()
            logger.info(f"Stake released: {stake.stake_id}")

        return {
            "success": result.get("success"),
            "stake": stake.to_dict(),
            "tx_hash": result.get("tx_hash")
        }

    async def refund_stake(self, task_id: str) -> Dict[str, Any]:
        """
        Refund stake for a cancelled task.

        Args:
            task_id: Task ID

        Returns:
            Refund result
        """
        # Find stake for task
        stake = None
        for s in self._stakes.values():
            if s.task_id == task_id and s.status == "active":
                stake = s
                break

        if not stake:
            return {"success": False, "error": "No active stake found for task"}

        # Refund from escrow
        result = await self.escrow.refund(task_id)

        if result.get("success"):
            stake.status = "refunded"
            stake.released_at = datetime.now()
            logger.info(f"Stake refunded: {stake.stake_id}")

        return {
            "success": result.get("success"),
            "stake": stake.to_dict(),
            "tx_hash": result.get("tx_hash")
        }

    async def get_stake(self, stake_id: str) -> Optional[StakeRecord]:
        """Get stake by ID"""
        return self._stakes.get(stake_id)

    async def get_stakes_for_task(self, task_id: str) -> List[StakeRecord]:
        """Get all stakes for a task"""
        return [s for s in self._stakes.values() if s.task_id == task_id]

    async def get_stake_balance(self, task_id: str) -> int:
        """Get current stake balance for a task"""
        return await self.escrow.get_balance(task_id)

    def get_stats(self) -> Dict[str, Any]:
        """Get staking statistics"""
        total_staked = sum(
            s.amount_wei for s in self._stakes.values()
            if s.status == "active"
        )
        total_released = sum(
            s.amount_wei for s in self._stakes.values()
            if s.status == "released"
        )
        total_refunded = sum(
            s.amount_wei for s in self._stakes.values()
            if s.status == "refunded"
        )

        return {
            "total_stakes": len(self._stakes),
            "active_stakes": len([s for s in self._stakes.values() if s.status == "active"]),
            "total_staked_wei": str(total_staked),
            "total_released_wei": str(total_released),
            "total_refunded_wei": str(total_refunded)
        }


# Singleton instance
_stake_manager: Optional[StakeManager] = None


def get_stake_manager() -> StakeManager:
    """Get the stake manager instance"""
    global _stake_manager
    if _stake_manager is None:
        _stake_manager = StakeManager()
    return _stake_manager
