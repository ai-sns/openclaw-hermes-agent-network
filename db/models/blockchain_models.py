"""
Blockchain Database Models

SQLAlchemy models for blockchain features (DID, Escrow, Payment, Audit).
"""

from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, Boolean, Text, JSON, Index, Numeric
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from db.base_class import Base


class WalletRecord(Base):
    """Blockchain Wallet Record (DID)"""
    __tablename__ = 'blockchain_wallets'
    __table_args__ = {'extend_existing': True}

    id = Column(Integer, primary_key=True, autoincrement=True)
    wallet_id = Column(String(50), unique=True, index=True, nullable=False, comment="Wallet ID (UUID)")

    # Wallet info
    address = Column(String(42), unique=True, index=True, nullable=False, comment="Ethereum address (0x...)")
    # Note: Private key should be stored encrypted or in secure vault, not in DB
    encrypted_private_key = Column(Text, nullable=True, comment="Encrypted private key (for managed wallets)")

    # Ownership
    user_id = Column(String(100), nullable=True, index=True, comment="Associated user ID")
    agent_id = Column(String(100), nullable=True, index=True, comment="Associated agent ID")

    # Wallet type
    wallet_type = Column(String(20), default='managed', comment="Type: managed/imported/hardware")

    # ENS (Ethereum Name Service)
    ens_name = Column(String(100), nullable=True, comment="ENS name (e.g., agent.eth)")

    # Status
    is_active = Column(Boolean, default=True)

    # Timestamps
    created_at = Column(DateTime, default=datetime.now, nullable=False)
    last_used_at = Column(DateTime, nullable=True)

    # Wallet metadata (renamed from 'metadata' to avoid SQLAlchemy conflict)
    wallet_metadata = Column(JSON, nullable=True, comment="Additional wallet metadata")

    def __repr__(self):
        return f"<WalletRecord(address={self.address[:10]}...)>"


class BlockchainTx(Base):
    """Blockchain Transaction Record"""
    __tablename__ = 'blockchain_transactions'

    id = Column(Integer, primary_key=True, autoincrement=True)
    tx_id = Column(String(50), unique=True, index=True, nullable=False, comment="Internal TX ID (UUID)")
    tx_hash = Column(String(66), unique=True, nullable=True, index=True, comment="On-chain TX hash (0x...)")

    # Transaction type
    tx_type = Column(String(30), nullable=False, index=True,
                    comment="Type: stake/release/refund/payment/audit")

    # Addresses
    from_address = Column(String(42), nullable=False, index=True, comment="Sender address")
    to_address = Column(String(42), nullable=False, comment="Recipient address")
    contract_address = Column(String(42), nullable=True, comment="Contract address (if applicable)")

    # Value
    amount = Column(String(78), nullable=False, comment="Amount in wei (as string for precision)")
    amount_decimal = Column(Numeric(36, 18), nullable=True, comment="Amount in ETH")
    token_address = Column(String(42), nullable=True, comment="Token address (null for ETH)")

    # Related entities
    task_id = Column(String(50), nullable=True, index=True, comment="Related task ID")
    session_id = Column(String(50), nullable=True, comment="Related session ID")

    # Chain info
    chain_id = Column(Integer, default=11155111, comment="Chain ID (11155111 = Sepolia)")
    block_number = Column(Integer, nullable=True, comment="Block number when confirmed")
    gas_used = Column(Integer, nullable=True, comment="Gas used")
    gas_price = Column(String(78), nullable=True, comment="Gas price in wei")

    # Status
    status = Column(String(20), default='pending', nullable=False,
                   comment="Status: pending/submitted/confirmed/failed")
    confirmations = Column(Integer, default=0, comment="Number of confirmations")

    # Error handling
    error_message = Column(Text, nullable=True, comment="Error message if failed")
    retry_count = Column(Integer, default=0, comment="Number of retries")

    # Timestamps
    created_at = Column(DateTime, default=datetime.now, nullable=False)
    submitted_at = Column(DateTime, nullable=True, comment="When TX was submitted to network")
    confirmed_at = Column(DateTime, nullable=True, comment="When TX was confirmed")

    # Raw data
    raw_tx = Column(JSON, nullable=True, comment="Raw transaction data")
    receipt = Column(JSON, nullable=True, comment="Transaction receipt")

    __table_args__ = (
        Index('idx_blockchain_tx_type_status', 'tx_type', 'status'),
        Index('idx_blockchain_tx_task', 'task_id'),
        {'extend_existing': True}
    )

    def __repr__(self):
        return f"<BlockchainTx(type={self.tx_type}, status={self.status})>"


class EscrowRecord(Base):
    """Escrow Staking Record"""
    __tablename__ = 'escrow_records'
    __table_args__ = {'extend_existing': True}

    id = Column(Integer, primary_key=True, autoincrement=True)
    escrow_id = Column(String(50), unique=True, index=True, nullable=False, comment="Escrow ID (UUID)")

    # Task info
    task_id = Column(String(50), index=True, nullable=False, comment="Related task ID")
    agent_id = Column(String(100), nullable=False, comment="Agent providing service")

    # Parties
    client_address = Column(String(42), nullable=False, comment="Client (staker) address")
    provider_address = Column(String(42), nullable=False, comment="Provider (agent) address")

    # Amount
    staked_amount = Column(String(78), nullable=False, comment="Staked amount in wei")
    staked_amount_decimal = Column(Numeric(36, 18), nullable=True, comment="Staked amount in ETH")
    released_amount = Column(String(78), default='0', comment="Released amount in wei")
    refunded_amount = Column(String(78), default='0', comment="Refunded amount in wei")

    # Contract info
    contract_address = Column(String(42), nullable=True, comment="Escrow contract address")

    # Status
    status = Column(String(20), default='pending', nullable=False,
                   comment="Status: pending/staked/released/refunded/disputed")

    # Transaction references
    stake_tx_hash = Column(String(66), nullable=True, comment="Stake transaction hash")
    release_tx_hash = Column(String(66), nullable=True, comment="Release transaction hash")
    refund_tx_hash = Column(String(66), nullable=True, comment="Refund transaction hash")

    # SLA (Service Level Agreement)
    sla_conditions = Column(JSON, nullable=True, comment="SLA conditions")
    sla_met = Column(Boolean, nullable=True, comment="Whether SLA was met")

    # Timestamps
    created_at = Column(DateTime, default=datetime.now, nullable=False)
    staked_at = Column(DateTime, nullable=True)
    released_at = Column(DateTime, nullable=True)
    refunded_at = Column(DateTime, nullable=True)
    expires_at = Column(DateTime, nullable=True, comment="Escrow expiration time")

    def __repr__(self):
        return f"<EscrowRecord(id={self.escrow_id}, status={self.status})>"


class PaymentRecord(Base):
    """Payment Record (Pay-per-request, Streaming)"""
    __tablename__ = 'payment_records'
    __table_args__ = {'extend_existing': True}

    id = Column(Integer, primary_key=True, autoincrement=True)
    payment_id = Column(String(50), unique=True, index=True, nullable=False)

    # Payment type
    payment_type = Column(String(20), nullable=False, comment="Type: per_request/streaming")

    # Parties
    payer_address = Column(String(42), nullable=False, index=True)
    payee_address = Column(String(42), nullable=False)

    # Related entities
    task_id = Column(String(50), nullable=True, index=True)
    session_id = Column(String(50), nullable=True)

    # Amount
    amount = Column(String(78), nullable=False, comment="Total amount in wei")
    amount_decimal = Column(Numeric(36, 18), nullable=True)

    # For streaming payments
    rate_per_second = Column(String(78), nullable=True, comment="Rate per second in wei")
    stream_start = Column(DateTime, nullable=True)
    stream_end = Column(DateTime, nullable=True)
    streamed_amount = Column(String(78), default='0', comment="Amount streamed so far")

    # Status
    status = Column(String(20), default='pending',
                   comment="Status: pending/active/completed/cancelled")

    # Transaction
    tx_hash = Column(String(66), nullable=True)

    # Timestamps
    created_at = Column(DateTime, default=datetime.now, nullable=False)
    completed_at = Column(DateTime, nullable=True)

    def __repr__(self):
        return f"<PaymentRecord(id={self.payment_id}, type={self.payment_type})>"


class AuditLog(Base):
    """Audit Log with On-chain Hash"""
    __tablename__ = 'audit_logs'

    id = Column(Integer, primary_key=True, autoincrement=True)
    audit_id = Column(String(50), unique=True, index=True, nullable=False, comment="Audit ID (UUID)")

    # Related entities
    task_id = Column(String(50), index=True, nullable=True, comment="Related task ID")
    session_id = Column(String(50), nullable=True, comment="Related session ID")
    agent_id = Column(String(100), nullable=True, comment="Agent ID")

    # Audit type
    audit_type = Column(String(30), nullable=False, index=True,
                       comment="Type: task_complete/payment/error/security")

    # Hash
    data_hash = Column(String(66), nullable=False, comment="SHA256 hash of interaction data")
    merkle_root = Column(String(66), nullable=True, comment="Merkle root if batched")

    # On-chain proof
    tx_hash = Column(String(66), nullable=True, index=True, comment="On-chain TX hash")
    block_number = Column(Integer, nullable=True, comment="Block number")
    is_on_chain = Column(Boolean, default=False, comment="Whether logged on chain")

    # Data summary (not full data to save space)
    data_summary = Column(JSON, nullable=True, comment="Summary of audited data")

    # Timestamps
    created_at = Column(DateTime, default=datetime.now, nullable=False)
    submitted_at = Column(DateTime, nullable=True, comment="When submitted to chain")
    confirmed_at = Column(DateTime, nullable=True, comment="When confirmed on chain")

    # Verification
    verified = Column(Boolean, nullable=True, comment="Verification result")
    verified_at = Column(DateTime, nullable=True)

    __table_args__ = (
        Index('idx_audit_log_type', 'audit_type'),
        Index('idx_audit_log_hash', 'data_hash'),
        {'extend_existing': True}
    )

    def __repr__(self):
        return f"<AuditLog(id={self.audit_id}, type={self.audit_type})>"
