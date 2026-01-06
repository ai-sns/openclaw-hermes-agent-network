"""
A2A Payment Integration Module

Integrates blockchain payment verification and settlement with A2A task execution.
"""

import os
import sys
import logging
from typing import Dict, Any, Optional, List, Tuple
from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from enum import Enum

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))))

from blockchain.escrow.contract import get_escrow_contract, EscrowStatus
from blockchain.payment.pay_per_request import (
    get_pay_per_request,
    PaymentType,
    PaymentStatus,
    PaymentRequest
)

logger = logging.getLogger(__name__)


class PaymentVerificationStatus(str, Enum):
    """Payment verification status"""
    VERIFIED = "verified"
    PENDING = "pending"
    FAILED = "failed"
    NOT_FOUND = "not_found"
    INSUFFICIENT = "insufficient"


@dataclass
class PaymentVerification:
    """Payment verification result"""
    status: PaymentVerificationStatus
    tx_hash: Optional[str] = None
    amount_wei: int = 0
    payer_address: str = ""
    verified_at: Optional[datetime] = None
    message: str = ""

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "status": self.status.value,
            "tx_hash": self.tx_hash,
            "amount_wei": str(self.amount_wei),
            "amount_eth": str(Decimal(self.amount_wei) / Decimal(10**18)) if self.amount_wei else "0",
            "payer_address": self.payer_address,
            "verified_at": self.verified_at.isoformat() if self.verified_at else None,
            "message": self.message
        }


@dataclass
class SettlementResult:
    """Settlement result"""
    success: bool
    settlement_type: str  # "release" or "refund"
    tx_hash: Optional[str] = None
    amount_wei: int = 0
    settled_at: Optional[datetime] = None
    message: str = ""

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "success": self.success,
            "settlement_type": self.settlement_type,
            "tx_hash": self.tx_hash,
            "amount_wei": str(self.amount_wei),
            "amount_eth": str(Decimal(self.amount_wei) / Decimal(10**18)) if self.amount_wei else "0",
            "settled_at": self.settled_at.isoformat() if self.settled_at else None,
            "message": self.message
        }


class A2APaymentIntegration:
    """
    A2A Payment Integration

    Handles:
    1. Payment verification before task execution
    2. Automatic settlement after task completion
    3. Refunds on task failure/cancellation
    4. Audit trail for blockchain transactions
    """

    def __init__(self):
        """Initialize payment integration"""
        self.escrow = get_escrow_contract()
        self.payment_system = get_pay_per_request()

        # Track task payments
        self._task_payments: Dict[str, PaymentRequest] = {}

        # Pricing per skill (in wei)
        self._skill_pricing = {
            "chat": 1000000000000000,       # 0.001 ETH
            "code-execution": 5000000000000000,  # 0.005 ETH
            "web-search": 500000000000000,   # 0.0005 ETH
            "file-analysis": 2000000000000000,  # 0.002 ETH
            "weather": 500000000000000       # 0.0005 ETH
        }

    def get_skill_price(self, skill_id: str) -> int:
        """Get price for a skill in wei"""
        return self._skill_pricing.get(skill_id, 1000000000000000)  # Default 0.001 ETH

    def get_pricing_info(self) -> Dict[str, Dict[str, Any]]:
        """Get pricing information for all skills"""
        result = {}
        for skill_id, price_wei in self._skill_pricing.items():
            result[skill_id] = {
                "price_wei": str(price_wei),
                "price_eth": str(Decimal(price_wei) / Decimal(10**18)),
                "per_request": True
            }
        return result

    async def verify_payment(
        self,
        task_id: str,
        tx_hash: Optional[str] = None,
        payer_address: Optional[str] = None,
        skill_id: Optional[str] = None
    ) -> PaymentVerification:
        """
        Verify payment before task execution.

        Args:
            task_id: Task identifier
            tx_hash: Payment transaction hash
            payer_address: Payer's wallet address
            skill_id: Skill being invoked

        Returns:
            PaymentVerification result
        """
        # Check if payment exists in escrow
        escrow_record = await self.escrow.get_escrow(task_id)

        if not escrow_record:
            # No escrow found - check if tx_hash provided
            if not tx_hash:
                return PaymentVerification(
                    status=PaymentVerificationStatus.NOT_FOUND,
                    message="No payment found for this task. Please deposit to escrow first."
                )

            # For simulation mode, create a mock verification
            required_amount = self.get_skill_price(skill_id) if skill_id else 1000000000000000

            return PaymentVerification(
                status=PaymentVerificationStatus.VERIFIED,
                tx_hash=tx_hash,
                amount_wei=required_amount,
                payer_address=payer_address or "",
                verified_at=datetime.now(),
                message="Payment verified (simulation mode)"
            )

        # Verify escrow is active
        if escrow_record.status != EscrowStatus.ACTIVE:
            return PaymentVerification(
                status=PaymentVerificationStatus.FAILED,
                tx_hash=escrow_record.tx_hash,
                message=f"Escrow is not active. Current status: {escrow_record.status.value}"
            )

        # Verify amount is sufficient
        required_amount = self.get_skill_price(skill_id) if skill_id else 1000000000000000
        if escrow_record.amount_wei < required_amount:
            return PaymentVerification(
                status=PaymentVerificationStatus.INSUFFICIENT,
                tx_hash=escrow_record.tx_hash,
                amount_wei=escrow_record.amount_wei,
                payer_address=escrow_record.depositor,
                message=f"Insufficient payment. Required: {required_amount} wei, Found: {escrow_record.amount_wei} wei"
            )

        return PaymentVerification(
            status=PaymentVerificationStatus.VERIFIED,
            tx_hash=escrow_record.tx_hash,
            amount_wei=escrow_record.amount_wei,
            payer_address=escrow_record.depositor,
            verified_at=datetime.now(),
            message="Payment verified successfully"
        )

    async def settle_task(
        self,
        task_id: str,
        success: bool,
        tokens_used: int = 0,
        execution_time_ms: int = 0
    ) -> SettlementResult:
        """
        Settle payment after task execution.

        Args:
            task_id: Task identifier
            success: Whether task succeeded
            tokens_used: Number of tokens used
            execution_time_ms: Execution time in milliseconds

        Returns:
            SettlementResult
        """
        escrow_record = await self.escrow.get_escrow(task_id)

        if not escrow_record:
            # No escrow to settle - might be in simulation mode
            return SettlementResult(
                success=True,
                settlement_type="release" if success else "refund",
                settled_at=datetime.now(),
                message="No escrow to settle (simulation mode)"
            )

        if escrow_record.status != EscrowStatus.ACTIVE:
            return SettlementResult(
                success=False,
                settlement_type="none",
                message=f"Cannot settle: escrow status is {escrow_record.status.value}"
            )

        try:
            if success:
                # Release funds to beneficiary
                result = await self.escrow.release(task_id)

                return SettlementResult(
                    success=result.get("success", False),
                    settlement_type="release",
                    tx_hash=result.get("tx_hash"),
                    amount_wei=escrow_record.amount_wei,
                    settled_at=datetime.now(),
                    message="Funds released to agent"
                )
            else:
                # Refund to payer
                result = await self.escrow.refund(task_id)

                return SettlementResult(
                    success=result.get("success", False),
                    settlement_type="refund",
                    tx_hash=result.get("tx_hash"),
                    amount_wei=escrow_record.amount_wei,
                    settled_at=datetime.now(),
                    message="Funds refunded to payer"
                )

        except Exception as e:
            logger.error(f"Settlement failed: {e}")
            return SettlementResult(
                success=False,
                settlement_type="error",
                message=str(e)
            )

    async def create_payment_for_task(
        self,
        task_id: str,
        skill_id: str,
        payer_address: str,
        recipient_address: str
    ) -> Tuple[PaymentRequest, Dict[str, Any]]:
        """
        Create and authorize payment for a task.

        Args:
            task_id: Task identifier
            skill_id: Skill to invoke
            payer_address: Payer's wallet address
            recipient_address: Recipient's wallet address

        Returns:
            Tuple of (PaymentRequest, authorization result)
        """
        # Map skill to payment type
        skill_to_type = {
            "chat": PaymentType.CHAT_REQUEST,
            "code-execution": PaymentType.TASK_EXECUTION,
            "web-search": PaymentType.API_CALL,
            "file-analysis": PaymentType.FILE_PROCESSING,
            "weather": PaymentType.API_CALL
        }
        payment_type = skill_to_type.get(skill_id, PaymentType.CHAT_REQUEST)

        # Create payment request
        payment = await self.payment_system.create_payment(
            request_id=task_id,
            payer_address=payer_address,
            recipient_address=recipient_address,
            payment_type=payment_type,
            custom_amount_wei=self.get_skill_price(skill_id)
        )

        # Store reference
        self._task_payments[task_id] = payment

        # Authorize payment (deposit to escrow)
        auth_result = await self.payment_system.authorize_payment(payment.payment_id)

        return payment, auth_result

    async def get_task_payment(self, task_id: str) -> Optional[PaymentRequest]:
        """Get payment for a task"""
        return self._task_payments.get(task_id)

    def get_audit_info(self, task_id: str) -> Dict[str, Any]:
        """Get audit information for a task"""
        payment = self._task_payments.get(task_id)

        audit_info = {
            "task_id": task_id,
            "payment": payment.to_dict() if payment else None,
            "timestamp": datetime.now().isoformat()
        }

        return audit_info


# Singleton instance
_payment_integration: Optional[A2APaymentIntegration] = None


def get_payment_integration() -> A2APaymentIntegration:
    """Get the payment integration instance"""
    global _payment_integration
    if _payment_integration is None:
        _payment_integration = A2APaymentIntegration()
    return _payment_integration


class PaymentMiddleware:
    """
    Middleware for A2A requests to verify and process payments.
    """

    def __init__(self):
        """Initialize middleware"""
        self.integration = get_payment_integration()

    async def before_task_execution(
        self,
        task_id: str,
        skill_id: str,
        metadata: Dict[str, Any]
    ) -> Tuple[bool, Optional[PaymentVerification]]:
        """
        Called before task execution to verify payment.

        Args:
            task_id: Task identifier
            skill_id: Skill being invoked
            metadata: Request metadata (may contain payment info)

        Returns:
            Tuple of (can_proceed, verification_result)
        """
        # Extract payment info from metadata
        payment_info = metadata.get("payment", {})
        tx_hash = payment_info.get("tx_hash")
        payer_address = payment_info.get("payer_address")

        # Skip payment verification if not required (for development)
        if metadata.get("skip_payment"):
            return True, None

        # Verify payment
        verification = await self.integration.verify_payment(
            task_id=task_id,
            tx_hash=tx_hash,
            payer_address=payer_address,
            skill_id=skill_id
        )

        can_proceed = verification.status == PaymentVerificationStatus.VERIFIED

        return can_proceed, verification

    async def after_task_execution(
        self,
        task_id: str,
        success: bool,
        tokens_used: int = 0,
        execution_time_ms: int = 0
    ) -> SettlementResult:
        """
        Called after task execution to settle payment.

        Args:
            task_id: Task identifier
            success: Whether task succeeded
            tokens_used: Number of tokens used
            execution_time_ms: Execution time

        Returns:
            SettlementResult
        """
        return await self.integration.settle_task(
            task_id=task_id,
            success=success,
            tokens_used=tokens_used,
            execution_time_ms=execution_time_ms
        )


# Convenience functions
async def verify_task_payment(
    task_id: str,
    metadata: Dict[str, Any],
    skill_id: str
) -> Tuple[bool, Dict[str, Any]]:
    """
    Verify payment for a task.

    Returns:
        Tuple of (is_verified, verification_info)
    """
    middleware = PaymentMiddleware()
    can_proceed, verification = await middleware.before_task_execution(
        task_id=task_id,
        skill_id=skill_id,
        metadata=metadata
    )

    return can_proceed, verification.to_dict() if verification else {}


async def settle_task_payment(
    task_id: str,
    success: bool,
    tokens_used: int = 0,
    execution_time_ms: int = 0
) -> Dict[str, Any]:
    """
    Settle payment for a completed task.

    Returns:
        Settlement info
    """
    middleware = PaymentMiddleware()
    result = await middleware.after_task_execution(
        task_id=task_id,
        success=success,
        tokens_used=tokens_used,
        execution_time_ms=execution_time_ms
    )

    return result.to_dict()
