"""
Pay-Per-Request Payment System

Handles per-request payment processing for AI agent services.
"""

import os
from typing import Optional, Dict, Any, List
from decimal import Decimal
from datetime import datetime
from dataclasses import dataclass, field
from enum import Enum
import logging
import hashlib

import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from blockchain.escrow.contract import get_escrow_contract

logger = logging.getLogger(__name__)


class PaymentStatus(str, Enum):
    """Payment status"""
    PENDING = "pending"
    AUTHORIZED = "authorized"
    CAPTURED = "captured"
    REFUNDED = "refunded"
    FAILED = "failed"


class PaymentType(str, Enum):
    """Payment types"""
    CHAT_REQUEST = "chat_request"
    TASK_EXECUTION = "task_execution"
    FILE_PROCESSING = "file_processing"
    API_CALL = "api_call"


@dataclass
class PricingTier:
    """Pricing tier definition"""
    name: str
    base_price_wei: int
    price_per_token_wei: int = 0
    price_per_second_wei: int = 0
    max_tokens: int = 0
    max_seconds: int = 0


@dataclass
class PaymentRequest:
    """Payment request record"""
    payment_id: str
    request_id: str
    payer_address: str
    recipient_address: str
    payment_type: PaymentType
    amount_wei: int
    status: PaymentStatus = PaymentStatus.PENDING
    input_tokens: int = 0
    output_tokens: int = 0
    execution_time_ms: int = 0
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.now)
    processed_at: Optional[datetime] = None
    tx_hash: Optional[str] = None

    @property
    def amount_eth(self) -> Decimal:
        """Get amount in ETH"""
        return Decimal(self.amount_wei) / Decimal(10**18)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "payment_id": self.payment_id,
            "request_id": self.request_id,
            "payer_address": self.payer_address,
            "recipient_address": self.recipient_address,
            "payment_type": self.payment_type.value,
            "amount_wei": str(self.amount_wei),
            "amount_eth": str(self.amount_eth),
            "status": self.status.value,
            "input_tokens": self.input_tokens,
            "output_tokens": self.output_tokens,
            "execution_time_ms": self.execution_time_ms,
            "created_at": self.created_at.isoformat(),
            "processed_at": self.processed_at.isoformat() if self.processed_at else None,
            "tx_hash": self.tx_hash
        }


# Default pricing (in wei per unit)
DEFAULT_PRICING = {
    PaymentType.CHAT_REQUEST: PricingTier(
        name="Chat Request",
        base_price_wei=1000000000000000,  # 0.001 ETH base
        price_per_token_wei=100000000000,  # 0.0001 ETH per 1000 tokens
        max_tokens=100000
    ),
    PaymentType.TASK_EXECUTION: PricingTier(
        name="Task Execution",
        base_price_wei=5000000000000000,  # 0.005 ETH base
        price_per_second_wei=1000000000000,  # 0.000001 ETH per second
        max_seconds=3600
    ),
    PaymentType.FILE_PROCESSING: PricingTier(
        name="File Processing",
        base_price_wei=2000000000000000,  # 0.002 ETH base
    ),
    PaymentType.API_CALL: PricingTier(
        name="API Call",
        base_price_wei=500000000000000,  # 0.0005 ETH per call
    )
}


class PayPerRequest:
    """
    Pay-Per-Request Payment System

    Handles:
    - Dynamic pricing based on usage
    - Payment authorization
    - Payment capture
    - Refunds
    """

    def __init__(
        self,
        pricing: Optional[Dict[PaymentType, PricingTier]] = None,
        platform_fee_percent: float = 5.0
    ):
        """
        Initialize pay-per-request system.

        Args:
            pricing: Custom pricing tiers
            platform_fee_percent: Platform fee percentage
        """
        self.pricing = pricing or DEFAULT_PRICING
        self.platform_fee_percent = platform_fee_percent

        self._payments: Dict[str, PaymentRequest] = {}
        self._escrow = get_escrow_contract()

    def _generate_payment_id(self, request_id: str) -> str:
        """Generate unique payment ID"""
        hash_input = f"{request_id}_{datetime.now().isoformat()}"
        return f"pay_{hashlib.sha256(hash_input.encode()).hexdigest()[:16]}"

    def calculate_price(
        self,
        payment_type: PaymentType,
        input_tokens: int = 0,
        output_tokens: int = 0,
        execution_time_seconds: int = 0
    ) -> int:
        """
        Calculate payment amount.

        Args:
            payment_type: Type of payment
            input_tokens: Number of input tokens
            output_tokens: Number of output tokens
            execution_time_seconds: Execution time

        Returns:
            Amount in wei
        """
        tier = self.pricing.get(payment_type)
        if not tier:
            return 0

        amount = tier.base_price_wei

        # Token-based pricing
        total_tokens = input_tokens + output_tokens
        if tier.price_per_token_wei > 0 and total_tokens > 0:
            token_cost = (total_tokens * tier.price_per_token_wei) // 1000
            amount += token_cost

        # Time-based pricing
        if tier.price_per_second_wei > 0 and execution_time_seconds > 0:
            time_cost = execution_time_seconds * tier.price_per_second_wei
            amount += time_cost

        return amount

    async def create_payment(
        self,
        request_id: str,
        payer_address: str,
        recipient_address: str,
        payment_type: PaymentType,
        input_tokens: int = 0,
        output_tokens: int = 0,
        execution_time_ms: int = 0,
        custom_amount_wei: Optional[int] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> PaymentRequest:
        """
        Create a payment request.

        Args:
            request_id: Original request ID
            payer_address: Payer's address
            recipient_address: Recipient's address
            payment_type: Type of payment
            input_tokens: Input token count
            output_tokens: Output token count
            execution_time_ms: Execution time in milliseconds
            custom_amount_wei: Override calculated amount
            metadata: Additional metadata

        Returns:
            PaymentRequest
        """
        # Calculate amount
        if custom_amount_wei:
            amount_wei = custom_amount_wei
        else:
            amount_wei = self.calculate_price(
                payment_type,
                input_tokens,
                output_tokens,
                execution_time_ms // 1000
            )

        payment = PaymentRequest(
            payment_id=self._generate_payment_id(request_id),
            request_id=request_id,
            payer_address=payer_address,
            recipient_address=recipient_address,
            payment_type=payment_type,
            amount_wei=amount_wei,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            execution_time_ms=execution_time_ms,
            metadata=metadata or {}
        )

        self._payments[payment.payment_id] = payment

        logger.info(f"Payment created: {payment.payment_id}, amount: {payment.amount_eth} ETH")
        return payment

    async def authorize_payment(
        self,
        payment_id: str,
        wallet = None
    ) -> Dict[str, Any]:
        """
        Authorize a payment (stake funds in escrow).

        Args:
            payment_id: Payment ID
            wallet: Payer's wallet

        Returns:
            Authorization result
        """
        payment = self._payments.get(payment_id)
        if not payment:
            return {"success": False, "error": "Payment not found"}

        if payment.status != PaymentStatus.PENDING:
            return {"success": False, "error": "Payment already processed"}

        # Deposit to escrow
        result = await self._escrow.deposit(
            task_id=payment.request_id,
            beneficiary=payment.recipient_address,
            amount_wei=payment.amount_wei,
            from_wallet=wallet
        )

        if result.get("success"):
            payment.status = PaymentStatus.AUTHORIZED
            payment.tx_hash = result.get("tx_hash")
            logger.info(f"Payment authorized: {payment_id}")

        return {
            "success": result.get("success"),
            "payment": payment.to_dict(),
            "tx_hash": result.get("tx_hash")
        }

    async def capture_payment(self, payment_id: str) -> Dict[str, Any]:
        """
        Capture an authorized payment (release escrow).

        Args:
            payment_id: Payment ID

        Returns:
            Capture result
        """
        payment = self._payments.get(payment_id)
        if not payment:
            return {"success": False, "error": "Payment not found"}

        if payment.status != PaymentStatus.AUTHORIZED:
            return {"success": False, "error": "Payment not authorized"}

        # Release escrow
        result = await self._escrow.release(payment.request_id)

        if result.get("success"):
            payment.status = PaymentStatus.CAPTURED
            payment.processed_at = datetime.now()
            logger.info(f"Payment captured: {payment_id}")

        return {
            "success": result.get("success"),
            "payment": payment.to_dict(),
            "tx_hash": result.get("tx_hash")
        }

    async def refund_payment(self, payment_id: str) -> Dict[str, Any]:
        """
        Refund a payment.

        Args:
            payment_id: Payment ID

        Returns:
            Refund result
        """
        payment = self._payments.get(payment_id)
        if not payment:
            return {"success": False, "error": "Payment not found"}

        if payment.status == PaymentStatus.CAPTURED:
            return {"success": False, "error": "Cannot refund captured payment"}

        # Refund escrow
        result = await self._escrow.refund(payment.request_id)

        if result.get("success"):
            payment.status = PaymentStatus.REFUNDED
            payment.processed_at = datetime.now()
            logger.info(f"Payment refunded: {payment_id}")

        return {
            "success": result.get("success"),
            "payment": payment.to_dict(),
            "tx_hash": result.get("tx_hash")
        }

    async def get_payment(self, payment_id: str) -> Optional[PaymentRequest]:
        """Get payment by ID"""
        return self._payments.get(payment_id)

    async def get_payments_for_request(self, request_id: str) -> List[PaymentRequest]:
        """Get all payments for a request"""
        return [p for p in self._payments.values() if p.request_id == request_id]

    def get_pricing(self) -> Dict[str, Dict[str, Any]]:
        """Get current pricing"""
        return {
            k.value: {
                "name": v.name,
                "base_price_wei": str(v.base_price_wei),
                "base_price_eth": str(Decimal(v.base_price_wei) / Decimal(10**18)),
                "price_per_token_wei": str(v.price_per_token_wei),
                "price_per_second_wei": str(v.price_per_second_wei)
            }
            for k, v in self.pricing.items()
        }

    def get_stats(self) -> Dict[str, Any]:
        """Get payment statistics"""
        total_captured = sum(
            p.amount_wei for p in self._payments.values()
            if p.status == PaymentStatus.CAPTURED
        )
        total_refunded = sum(
            p.amount_wei for p in self._payments.values()
            if p.status == PaymentStatus.REFUNDED
        )

        return {
            "total_payments": len(self._payments),
            "captured_payments": len([p for p in self._payments.values() if p.status == PaymentStatus.CAPTURED]),
            "total_captured_wei": str(total_captured),
            "total_refunded_wei": str(total_refunded),
            "platform_fee_percent": self.platform_fee_percent
        }


# Singleton instance
_pay_per_request: Optional[PayPerRequest] = None


def get_pay_per_request() -> PayPerRequest:
    """Get the pay-per-request instance"""
    global _pay_per_request
    if _pay_per_request is None:
        _pay_per_request = PayPerRequest()
    return _pay_per_request
