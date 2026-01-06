"""
Signature Verification

Verifies Ethereum signatures for authentication and authorization.
"""

import os
from typing import Optional, Dict, Any
from datetime import datetime, timedelta
from dataclasses import dataclass
import logging
import hashlib
import hmac

try:
    from eth_account import Account
    from eth_account.messages import encode_defunct
    from web3 import Web3
    HAS_WEB3 = True
except ImportError:
    HAS_WEB3 = False
    Account = None
    Web3 = None

import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))


logger = logging.getLogger(__name__)


@dataclass
class SignedMessage:
    """Signed message structure"""
    message: str
    signature: str
    signer: str
    timestamp: datetime
    nonce: Optional[str] = None


@dataclass
class VerificationResult:
    """Signature verification result"""
    valid: bool
    signer: Optional[str] = None
    error: Optional[str] = None
    timestamp: datetime = None

    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now()


class SignatureVerifier:
    """
    Signature Verifier

    Verifies Ethereum signatures for:
    - Message authentication
    - Login/authorization
    - Transaction verification
    """

    def __init__(self, nonce_expiry_seconds: int = 300):
        """
        Initialize verifier.

        Args:
            nonce_expiry_seconds: Nonce expiry time in seconds
        """
        self.nonce_expiry_seconds = nonce_expiry_seconds
        self._used_nonces: Dict[str, datetime] = {}

        if HAS_WEB3:
            self._web3 = Web3()
        else:
            self._web3 = None

    def generate_nonce(self) -> str:
        """Generate a random nonce"""
        import secrets
        return secrets.token_hex(16)

    def create_signing_message(
        self,
        action: str,
        address: str,
        nonce: Optional[str] = None,
        extra_data: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Create a message for signing.

        Args:
            action: Action being performed
            address: Signer's address
            nonce: Optional nonce (generated if not provided)
            extra_data: Additional data to include

        Returns:
            Message to sign
        """
        nonce = nonce or self.generate_nonce()
        timestamp = datetime.now().isoformat()

        message_parts = [
            f"Action: {action}",
            f"Address: {address}",
            f"Timestamp: {timestamp}",
            f"Nonce: {nonce}"
        ]

        if extra_data:
            for key, value in extra_data.items():
                message_parts.append(f"{key}: {value}")

        return "\n".join(message_parts)

    def verify_signature(
        self,
        message: str,
        signature: str,
        expected_signer: Optional[str] = None
    ) -> VerificationResult:
        """
        Verify a signature.

        Args:
            message: Original message
            signature: Signature to verify
            expected_signer: Expected signer address (optional)

        Returns:
            VerificationResult
        """
        if not HAS_WEB3:
            return VerificationResult(
                valid=False,
                error="web3 package not installed"
            )

        try:
            # Recover signer from signature
            message_encoded = encode_defunct(text=message)
            recovered_address = Account.recover_message(
                message_encoded,
                signature=signature
            )

            # Check if matches expected signer
            if expected_signer:
                if recovered_address.lower() != expected_signer.lower():
                    return VerificationResult(
                        valid=False,
                        signer=recovered_address,
                        error="Signer does not match expected address"
                    )

            return VerificationResult(
                valid=True,
                signer=recovered_address
            )

        except Exception as e:
            logger.error(f"Signature verification failed: {e}")
            return VerificationResult(
                valid=False,
                error=str(e)
            )

    def verify_with_nonce(
        self,
        message: str,
        signature: str,
        nonce: str,
        expected_signer: Optional[str] = None
    ) -> VerificationResult:
        """
        Verify signature with nonce validation.

        Args:
            message: Original message
            signature: Signature to verify
            nonce: Nonce from the message
            expected_signer: Expected signer address

        Returns:
            VerificationResult
        """
        # Check if nonce was already used
        if nonce in self._used_nonces:
            nonce_time = self._used_nonces[nonce]
            if datetime.now() - nonce_time < timedelta(seconds=self.nonce_expiry_seconds):
                return VerificationResult(
                    valid=False,
                    error="Nonce already used"
                )

        # Verify signature
        result = self.verify_signature(message, signature, expected_signer)

        if result.valid:
            # Mark nonce as used
            self._used_nonces[nonce] = datetime.now()
            self._cleanup_expired_nonces()

        return result

    def verify_typed_data(
        self,
        domain: Dict[str, Any],
        types: Dict[str, Any],
        message: Dict[str, Any],
        signature: str,
        expected_signer: Optional[str] = None
    ) -> VerificationResult:
        """
        Verify EIP-712 typed data signature.

        Args:
            domain: EIP-712 domain
            types: Type definitions
            message: Message data
            signature: Signature to verify
            expected_signer: Expected signer address

        Returns:
            VerificationResult
        """
        if not HAS_WEB3:
            return VerificationResult(
                valid=False,
                error="web3 package not installed"
            )

        try:
            from eth_account.messages import encode_structured_data

            # Encode typed data
            structured_data = {
                "types": types,
                "primaryType": list(types.keys())[0],
                "domain": domain,
                "message": message
            }

            encoded = encode_structured_data(structured_data)
            recovered_address = Account.recover_message(encoded, signature=signature)

            if expected_signer:
                if recovered_address.lower() != expected_signer.lower():
                    return VerificationResult(
                        valid=False,
                        signer=recovered_address,
                        error="Signer does not match expected address"
                    )

            return VerificationResult(
                valid=True,
                signer=recovered_address
            )

        except Exception as e:
            logger.error(f"Typed data verification failed: {e}")
            return VerificationResult(
                valid=False,
                error=str(e)
            )

    def _cleanup_expired_nonces(self):
        """Remove expired nonces"""
        current_time = datetime.now()
        expired = [
            nonce for nonce, time in self._used_nonces.items()
            if current_time - time > timedelta(seconds=self.nonce_expiry_seconds * 2)
        ]
        for nonce in expired:
            del self._used_nonces[nonce]

    def create_hmac_signature(
        self,
        message: str,
        secret: str
    ) -> str:
        """
        Create HMAC signature (for webhook verification).

        Args:
            message: Message to sign
            secret: Signing secret

        Returns:
            HMAC signature
        """
        return hmac.new(
            secret.encode(),
            message.encode(),
            hashlib.sha256
        ).hexdigest()

    def verify_hmac_signature(
        self,
        message: str,
        signature: str,
        secret: str
    ) -> bool:
        """
        Verify HMAC signature.

        Args:
            message: Original message
            signature: HMAC signature
            secret: Signing secret

        Returns:
            True if valid
        """
        expected = self.create_hmac_signature(message, secret)
        return hmac.compare_digest(signature, expected)


# Singleton instance
_signature_verifier: Optional[SignatureVerifier] = None


def get_signature_verifier() -> SignatureVerifier:
    """Get the signature verifier instance"""
    global _signature_verifier
    if _signature_verifier is None:
        _signature_verifier = SignatureVerifier()
    return _signature_verifier
