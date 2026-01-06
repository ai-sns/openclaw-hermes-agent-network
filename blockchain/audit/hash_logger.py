"""
Hash Logger

Logs interaction hashes to blockchain for audit trails.
"""

import os
import hashlib
import json
from typing import Optional, Dict, Any, List
from datetime import datetime
from dataclasses import dataclass, field
from enum import Enum
import logging

try:
    from web3 import Web3
    HAS_WEB3 = True
except ImportError:
    HAS_WEB3 = False
    Web3 = None

import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from blockchain.config import get_blockchain_config

logger = logging.getLogger(__name__)


class AuditType(str, Enum):
    """Types of auditable events"""
    TASK_CREATED = "task_created"
    TASK_COMPLETED = "task_completed"
    TASK_FAILED = "task_failed"
    PAYMENT_COMPLETED = "payment_completed"
    FILE_UPLOADED = "file_uploaded"
    API_CALL = "api_call"
    AGENT_INTERACTION = "agent_interaction"


@dataclass
class AuditEntry:
    """Audit log entry"""
    audit_id: str
    audit_type: AuditType
    task_id: Optional[str]
    data_hash: str
    timestamp: datetime = field(default_factory=datetime.now)
    tx_hash: Optional[str] = None
    block_number: Optional[int] = None
    data_summary: Dict[str, Any] = field(default_factory=dict)
    verified: bool = False

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "audit_id": self.audit_id,
            "audit_type": self.audit_type.value,
            "task_id": self.task_id,
            "data_hash": self.data_hash,
            "timestamp": self.timestamp.isoformat(),
            "tx_hash": self.tx_hash,
            "block_number": self.block_number,
            "data_summary": self.data_summary,
            "verified": self.verified
        }


# Simple audit storage contract ABI
AUDIT_ABI = [
    {
        "inputs": [
            {"name": "auditId", "type": "bytes32"},
            {"name": "dataHash", "type": "bytes32"}
        ],
        "name": "logAudit",
        "outputs": [],
        "stateMutability": "nonpayable",
        "type": "function"
    },
    {
        "inputs": [{"name": "auditId", "type": "bytes32"}],
        "name": "getAuditHash",
        "outputs": [{"name": "", "type": "bytes32"}],
        "stateMutability": "view",
        "type": "function"
    },
    {
        "inputs": [
            {"name": "auditId", "type": "bytes32"},
            {"name": "dataHash", "type": "bytes32"}
        ],
        "name": "verifyAudit",
        "outputs": [{"name": "", "type": "bool"}],
        "stateMutability": "view",
        "type": "function"
    }
]


class HashLogger:
    """
    Hash Logger

    Logs data hashes to blockchain for:
    - Audit trails
    - Data integrity verification
    - Non-repudiation
    """

    def __init__(
        self,
        contract_address: Optional[str] = None,
        enable_blockchain: bool = True
    ):
        """
        Initialize hash logger.

        Args:
            contract_address: Audit contract address
            enable_blockchain: Enable blockchain logging
        """
        self.enable_blockchain = enable_blockchain and HAS_WEB3
        self._entries: Dict[str, AuditEntry] = {}

        if self.enable_blockchain:
            config = get_blockchain_config()
            self._config = config
            self._web3 = Web3(Web3.HTTPProvider(config.rpc_url))

            if contract_address:
                self._contract = self._web3.eth.contract(
                    address=Web3.to_checksum_address(contract_address),
                    abi=AUDIT_ABI
                )
            else:
                self._contract = None
        else:
            self._web3 = None
            self._contract = None

    def _generate_audit_id(self, audit_type: AuditType, task_id: str = "") -> str:
        """Generate unique audit ID"""
        hash_input = f"{audit_type.value}_{task_id}_{datetime.now().isoformat()}"
        return f"audit_{hashlib.sha256(hash_input.encode()).hexdigest()[:16]}"

    def compute_hash(self, data: Any) -> str:
        """
        Compute SHA-256 hash of data.

        Args:
            data: Data to hash

        Returns:
            Hex-encoded hash
        """
        if isinstance(data, dict) or isinstance(data, list):
            data_str = json.dumps(data, sort_keys=True)
        elif isinstance(data, str):
            data_str = data
        else:
            data_str = str(data)

        return hashlib.sha256(data_str.encode()).hexdigest()

    async def log(
        self,
        audit_type: AuditType,
        data: Any,
        task_id: Optional[str] = None,
        data_summary: Optional[Dict[str, Any]] = None,
        store_on_chain: bool = True
    ) -> AuditEntry:
        """
        Log an audit entry.

        Args:
            audit_type: Type of audit event
            data: Data to hash
            task_id: Associated task ID
            data_summary: Summary of data (stored off-chain)
            store_on_chain: Store hash on blockchain

        Returns:
            AuditEntry
        """
        data_hash = self.compute_hash(data)

        entry = AuditEntry(
            audit_id=self._generate_audit_id(audit_type, task_id or ""),
            audit_type=audit_type,
            task_id=task_id,
            data_hash=data_hash,
            data_summary=data_summary or {}
        )

        self._entries[entry.audit_id] = entry

        # Store on blockchain if enabled
        if store_on_chain and self._contract and self.enable_blockchain:
            try:
                result = await self._store_on_chain(entry)
                entry.tx_hash = result.get("tx_hash")
                entry.block_number = result.get("block_number")
                entry.verified = True
            except Exception as e:
                logger.error(f"Failed to store audit on chain: {e}")

        logger.info(f"Audit logged: {entry.audit_id}, type: {audit_type.value}")
        return entry

    async def _store_on_chain(self, entry: AuditEntry) -> Dict[str, Any]:
        """Store audit hash on blockchain"""
        if not self._contract:
            return {"success": False, "error": "No contract configured"}

        from eth_account import Account

        config = get_blockchain_config()
        if not config.private_key:
            return {"success": False, "error": "No private key configured"}

        account = Account.from_key(config.private_key)

        # Convert IDs to bytes32
        audit_id_bytes = bytes.fromhex(entry.audit_id.replace("audit_", "").ljust(64, "0"))
        data_hash_bytes = bytes.fromhex(entry.data_hash)

        # Build transaction
        tx = self._contract.functions.logAudit(
            audit_id_bytes,
            data_hash_bytes
        ).build_transaction({
            "from": account.address,
            "gas": 100000,
            "gasPrice": self._web3.eth.gas_price,
            "nonce": self._web3.eth.get_transaction_count(account.address)
        })

        # Sign and send
        signed = account.sign_transaction(tx)
        tx_hash = self._web3.eth.send_raw_transaction(signed.rawTransaction)

        # Wait for confirmation
        receipt = self._web3.eth.wait_for_transaction_receipt(tx_hash)

        return {
            "success": receipt.status == 1,
            "tx_hash": tx_hash.hex(),
            "block_number": receipt.blockNumber
        }

    async def verify(
        self,
        audit_id: str,
        data: Optional[Any] = None
    ) -> Dict[str, Any]:
        """
        Verify an audit entry.

        Args:
            audit_id: Audit ID to verify
            data: Original data to verify against (optional)

        Returns:
            Verification result
        """
        entry = self._entries.get(audit_id)
        if not entry:
            return {"valid": False, "error": "Audit entry not found"}

        # Verify data hash if provided
        if data is not None:
            computed_hash = self.compute_hash(data)
            if computed_hash != entry.data_hash:
                return {
                    "valid": False,
                    "error": "Data hash mismatch",
                    "expected": entry.data_hash,
                    "computed": computed_hash
                }

        # Verify on blockchain if available
        if self._contract and entry.tx_hash:
            try:
                on_chain_valid = await self._verify_on_chain(entry)
                return {
                    "valid": on_chain_valid,
                    "entry": entry.to_dict(),
                    "on_chain": True
                }
            except Exception as e:
                logger.error(f"On-chain verification failed: {e}")
                return {
                    "valid": True,
                    "entry": entry.to_dict(),
                    "on_chain": False,
                    "warning": "Could not verify on chain"
                }

        return {
            "valid": True,
            "entry": entry.to_dict(),
            "on_chain": False
        }

    async def _verify_on_chain(self, entry: AuditEntry) -> bool:
        """Verify audit on blockchain"""
        if not self._contract:
            return False

        audit_id_bytes = bytes.fromhex(entry.audit_id.replace("audit_", "").ljust(64, "0"))
        data_hash_bytes = bytes.fromhex(entry.data_hash)

        return self._contract.functions.verifyAudit(
            audit_id_bytes,
            data_hash_bytes
        ).call()

    async def get_entry(self, audit_id: str) -> Optional[AuditEntry]:
        """Get audit entry by ID"""
        return self._entries.get(audit_id)

    async def get_entries_for_task(self, task_id: str) -> List[AuditEntry]:
        """Get all audit entries for a task"""
        return [e for e in self._entries.values() if e.task_id == task_id]

    async def get_entries_by_type(
        self,
        audit_type: AuditType,
        limit: int = 100
    ) -> List[AuditEntry]:
        """Get audit entries by type"""
        entries = [e for e in self._entries.values() if e.audit_type == audit_type]
        return sorted(entries, key=lambda e: e.timestamp, reverse=True)[:limit]

    def get_stats(self) -> Dict[str, Any]:
        """Get audit statistics"""
        type_counts = {}
        verified_count = 0

        for entry in self._entries.values():
            type_counts[entry.audit_type.value] = type_counts.get(
                entry.audit_type.value, 0
            ) + 1
            if entry.verified:
                verified_count += 1

        return {
            "total_entries": len(self._entries),
            "verified_entries": verified_count,
            "type_counts": type_counts,
            "blockchain_enabled": self.enable_blockchain
        }


# Singleton instance
_hash_logger: Optional[HashLogger] = None


def get_hash_logger() -> HashLogger:
    """Get the hash logger instance"""
    global _hash_logger
    if _hash_logger is None:
        _hash_logger = HashLogger()
    return _hash_logger
