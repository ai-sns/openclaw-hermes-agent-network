"""
Escrow Smart Contract Interface

Interacts with the Escrow smart contract for task staking.
"""

import os
from typing import Optional, Dict, Any, List
from decimal import Decimal
from datetime import datetime
from dataclasses import dataclass, field
from enum import Enum
import logging
import json

try:
    from web3 import Web3
    from web3.contract import Contract
    from eth_account import Account
    HAS_WEB3 = True
except ImportError:
    HAS_WEB3 = False
    Web3 = None
    Contract = None

import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from blockchain.config import get_blockchain_config

logger = logging.getLogger(__name__)


class EscrowStatus(str, Enum):
    """Escrow status"""
    PENDING = "pending"
    ACTIVE = "active"
    COMPLETED = "completed"
    REFUNDED = "refunded"
    DISPUTED = "disputed"


@dataclass
class EscrowRecord:
    """Escrow record"""
    escrow_id: str
    task_id: str
    depositor: str
    beneficiary: str
    amount_wei: int
    status: EscrowStatus = EscrowStatus.PENDING
    created_at: datetime = field(default_factory=datetime.now)
    completed_at: Optional[datetime] = None
    tx_hash: Optional[str] = None
    release_tx_hash: Optional[str] = None

    @property
    def amount_eth(self) -> Decimal:
        """Get amount in ETH"""
        return Decimal(self.amount_wei) / Decimal(10**18)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "escrow_id": self.escrow_id,
            "task_id": self.task_id,
            "depositor": self.depositor,
            "beneficiary": self.beneficiary,
            "amount_wei": str(self.amount_wei),
            "amount_eth": str(self.amount_eth),
            "status": self.status.value,
            "created_at": self.created_at.isoformat(),
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "tx_hash": self.tx_hash,
            "release_tx_hash": self.release_tx_hash
        }


# Escrow contract ABI (simplified)
ESCROW_ABI = [
    {
        "inputs": [
            {"name": "taskId", "type": "bytes32"},
            {"name": "beneficiary", "type": "address"}
        ],
        "name": "deposit",
        "outputs": [],
        "stateMutability": "payable",
        "type": "function"
    },
    {
        "inputs": [{"name": "taskId", "type": "bytes32"}],
        "name": "release",
        "outputs": [],
        "stateMutability": "nonpayable",
        "type": "function"
    },
    {
        "inputs": [{"name": "taskId", "type": "bytes32"}],
        "name": "refund",
        "outputs": [],
        "stateMutability": "nonpayable",
        "type": "function"
    },
    {
        "inputs": [{"name": "taskId", "type": "bytes32"}],
        "name": "getEscrow",
        "outputs": [
            {"name": "depositor", "type": "address"},
            {"name": "beneficiary", "type": "address"},
            {"name": "amount", "type": "uint256"},
            {"name": "status", "type": "uint8"}
        ],
        "stateMutability": "view",
        "type": "function"
    },
    {
        "inputs": [{"name": "taskId", "type": "bytes32"}],
        "name": "getBalance",
        "outputs": [{"name": "", "type": "uint256"}],
        "stateMutability": "view",
        "type": "function"
    },
    {
        "anonymous": False,
        "inputs": [
            {"indexed": True, "name": "taskId", "type": "bytes32"},
            {"indexed": True, "name": "depositor", "type": "address"},
            {"indexed": False, "name": "amount", "type": "uint256"}
        ],
        "name": "Deposited",
        "type": "event"
    },
    {
        "anonymous": False,
        "inputs": [
            {"indexed": True, "name": "taskId", "type": "bytes32"},
            {"indexed": True, "name": "beneficiary", "type": "address"},
            {"indexed": False, "name": "amount", "type": "uint256"}
        ],
        "name": "Released",
        "type": "event"
    }
]


class EscrowContract:
    """
    Escrow Smart Contract

    Interacts with the on-chain escrow contract for:
    - Depositing funds for tasks
    - Releasing funds upon completion
    - Refunding on cancellation
    """

    def __init__(
        self,
        contract_address: Optional[str] = None,
        private_key: Optional[str] = None
    ):
        """
        Initialize escrow contract.

        Args:
            contract_address: Contract address
            private_key: Private key for signing transactions
        """
        # Local escrow records (for simulation when web3 not available)
        self._local_records: Dict[str, EscrowRecord] = {}

        if not HAS_WEB3:
            logger.warning("web3 package not installed")
            self._web3 = None
            self._contract = None
            self._account = None
            self._config = None
            self._contract_address = None
            return

        config = get_blockchain_config()
        self._config = config

        # Initialize Web3
        self._web3 = Web3(Web3.HTTPProvider(config.rpc_url))

        # Contract address
        self._contract_address = contract_address or config.escrow_contract_address

        # Initialize contract (if address provided)
        if self._contract_address:
            self._contract = self._web3.eth.contract(
                address=Web3.to_checksum_address(self._contract_address),
                abi=ESCROW_ABI
            )
        else:
            self._contract = None

        # Account for signing
        pk = private_key or config.private_key
        if pk:
            self._account = Account.from_key(pk)
        else:
            self._account = None

    @property
    def is_connected(self) -> bool:
        """Check if connected to blockchain"""
        if not self._web3:
            return False
        try:
            return self._web3.is_connected()
        except:
            return False

    @property
    def contract_address(self) -> Optional[str]:
        """Get contract address"""
        return self._contract_address

    def _task_id_to_bytes32(self, task_id: str) -> bytes:
        """Convert task ID to bytes32"""
        if task_id.startswith("0x"):
            return bytes.fromhex(task_id[2:].zfill(64))
        return Web3.keccak(text=task_id)

    async def deposit(
        self,
        task_id: str,
        beneficiary: str,
        amount_wei: int,
        from_wallet = None
    ) -> Dict[str, Any]:
        """
        Deposit funds into escrow.

        Args:
            task_id: Task ID
            beneficiary: Beneficiary address
            amount_wei: Amount in wei
            from_wallet: Wallet to use (optional)

        Returns:
            Transaction result
        """
        if not self._contract:
            # Simulate locally
            return await self._simulate_deposit(
                task_id, beneficiary, amount_wei
            )

        account = from_wallet._account if from_wallet else self._account
        if not account:
            raise ValueError("No wallet available for signing")

        task_id_bytes = self._task_id_to_bytes32(task_id)

        # Build transaction
        tx = self._contract.functions.deposit(
            task_id_bytes,
            Web3.to_checksum_address(beneficiary)
        ).build_transaction({
            "from": account.address,
            "value": amount_wei,
            "gas": 200000,
            "gasPrice": self._web3.eth.gas_price,
            "nonce": self._web3.eth.get_transaction_count(account.address)
        })

        # Sign and send
        signed = account.sign_transaction(tx)
        tx_hash = self._web3.eth.send_raw_transaction(signed.rawTransaction)

        # Wait for confirmation
        receipt = self._web3.eth.wait_for_transaction_receipt(
            tx_hash,
            timeout=self._config.timeout_seconds
        )

        # Create local record
        record = EscrowRecord(
            escrow_id=f"esc_{task_id}",
            task_id=task_id,
            depositor=account.address,
            beneficiary=beneficiary,
            amount_wei=amount_wei,
            status=EscrowStatus.ACTIVE,
            tx_hash=tx_hash.hex()
        )
        self._local_records[task_id] = record

        return {
            "success": receipt.status == 1,
            "tx_hash": tx_hash.hex(),
            "block_number": receipt.blockNumber,
            "gas_used": receipt.gasUsed,
            "escrow": record.to_dict()
        }

    async def release(self, task_id: str) -> Dict[str, Any]:
        """
        Release escrow funds to beneficiary.

        Args:
            task_id: Task ID

        Returns:
            Transaction result
        """
        if not self._contract:
            return await self._simulate_release(task_id)

        if not self._account:
            raise ValueError("No wallet available for signing")

        task_id_bytes = self._task_id_to_bytes32(task_id)

        # Build transaction
        tx = self._contract.functions.release(task_id_bytes).build_transaction({
            "from": self._account.address,
            "gas": 100000,
            "gasPrice": self._web3.eth.gas_price,
            "nonce": self._web3.eth.get_transaction_count(self._account.address)
        })

        # Sign and send
        signed = self._account.sign_transaction(tx)
        tx_hash = self._web3.eth.send_raw_transaction(signed.rawTransaction)

        # Wait for confirmation
        receipt = self._web3.eth.wait_for_transaction_receipt(tx_hash)

        # Update local record
        if task_id in self._local_records:
            record = self._local_records[task_id]
            record.status = EscrowStatus.COMPLETED
            record.completed_at = datetime.now()
            record.release_tx_hash = tx_hash.hex()

        return {
            "success": receipt.status == 1,
            "tx_hash": tx_hash.hex(),
            "block_number": receipt.blockNumber
        }

    async def refund(self, task_id: str) -> Dict[str, Any]:
        """
        Refund escrow to depositor.

        Args:
            task_id: Task ID

        Returns:
            Transaction result
        """
        if not self._contract:
            return await self._simulate_refund(task_id)

        if not self._account:
            raise ValueError("No wallet available for signing")

        task_id_bytes = self._task_id_to_bytes32(task_id)

        # Build transaction
        tx = self._contract.functions.refund(task_id_bytes).build_transaction({
            "from": self._account.address,
            "gas": 100000,
            "gasPrice": self._web3.eth.gas_price,
            "nonce": self._web3.eth.get_transaction_count(self._account.address)
        })

        # Sign and send
        signed = self._account.sign_transaction(tx)
        tx_hash = self._web3.eth.send_raw_transaction(signed.rawTransaction)

        # Wait for confirmation
        receipt = self._web3.eth.wait_for_transaction_receipt(tx_hash)

        # Update local record
        if task_id in self._local_records:
            record = self._local_records[task_id]
            record.status = EscrowStatus.REFUNDED
            record.completed_at = datetime.now()

        return {
            "success": receipt.status == 1,
            "tx_hash": tx_hash.hex(),
            "block_number": receipt.blockNumber
        }

    async def get_balance(self, task_id: str) -> int:
        """Get escrow balance for a task"""
        if not self._contract:
            record = self._local_records.get(task_id)
            if record and record.status == EscrowStatus.ACTIVE:
                return record.amount_wei
            return 0

        task_id_bytes = self._task_id_to_bytes32(task_id)
        return self._contract.functions.getBalance(task_id_bytes).call()

    async def get_escrow(self, task_id: str) -> Optional[EscrowRecord]:
        """Get escrow details for a task"""
        return self._local_records.get(task_id)

    # Simulation methods for testing without blockchain
    async def _simulate_deposit(
        self,
        task_id: str,
        beneficiary: str,
        amount_wei: int
    ) -> Dict[str, Any]:
        """Simulate deposit locally"""
        import hashlib
        import secrets

        tx_hash = f"0x{secrets.token_hex(32)}"

        record = EscrowRecord(
            escrow_id=f"esc_{task_id}",
            task_id=task_id,
            depositor="0x" + "0" * 40,  # Simulated
            beneficiary=beneficiary,
            amount_wei=amount_wei,
            status=EscrowStatus.ACTIVE,
            tx_hash=tx_hash
        )
        self._local_records[task_id] = record

        return {
            "success": True,
            "tx_hash": tx_hash,
            "block_number": 0,
            "gas_used": 0,
            "escrow": record.to_dict(),
            "simulated": True
        }

    async def _simulate_release(self, task_id: str) -> Dict[str, Any]:
        """Simulate release locally"""
        import secrets

        record = self._local_records.get(task_id)
        if not record:
            return {"success": False, "error": "Escrow not found"}

        tx_hash = f"0x{secrets.token_hex(32)}"
        record.status = EscrowStatus.COMPLETED
        record.completed_at = datetime.now()
        record.release_tx_hash = tx_hash

        return {
            "success": True,
            "tx_hash": tx_hash,
            "block_number": 0,
            "simulated": True
        }

    async def _simulate_refund(self, task_id: str) -> Dict[str, Any]:
        """Simulate refund locally"""
        import secrets

        record = self._local_records.get(task_id)
        if not record:
            return {"success": False, "error": "Escrow not found"}

        tx_hash = f"0x{secrets.token_hex(32)}"
        record.status = EscrowStatus.REFUNDED
        record.completed_at = datetime.now()

        return {
            "success": True,
            "tx_hash": tx_hash,
            "block_number": 0,
            "simulated": True
        }


# Singleton instance
_escrow_contract: Optional[EscrowContract] = None


def get_escrow_contract() -> EscrowContract:
    """Get the escrow contract instance"""
    global _escrow_contract
    if _escrow_contract is None:
        _escrow_contract = EscrowContract()
    return _escrow_contract
