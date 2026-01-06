"""
DID (Decentralized Identity) Module

Provides Ethereum wallet generation and message signing.
"""

from .wallet import DIDWallet
from .signature import SignatureVerifier

__all__ = ["DIDWallet", "SignatureVerifier"]
