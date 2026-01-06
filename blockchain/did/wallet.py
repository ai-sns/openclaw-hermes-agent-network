"""
DID Wallet Manager

Manages Ethereum wallets for decentralized identity.
"""

import os
import secrets
import hashlib
from typing import Optional, Dict, Any, List
from dataclasses import dataclass, field
from datetime import datetime
import logging
import json

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
class WalletInfo:
    """Wallet information"""
    address: str
    public_key: str
    created_at: datetime = field(default_factory=datetime.now)
    label: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)


class DIDWallet:
    """
    DID Wallet

    Manages an Ethereum wallet for:
    - Message signing
    - Transaction signing
    - Identity verification
    """

    def __init__(self, private_key: Optional[str] = None):
        """
        Initialize wallet.

        Args:
            private_key: Private key (hex string). If None, generates new wallet.
        """
        if not HAS_WEB3:
            raise ImportError(
                "web3 and eth-account packages required. "
                "Install with: pip install web3 eth-account"
            )

        if private_key:
            # Remove 0x prefix if present
            if private_key.startswith("0x"):
                private_key = private_key[2:]
            self._private_key = private_key
            self._account = Account.from_key(f"0x{private_key}")
        else:
            # Generate new wallet
            self._account = Account.create()
            # key.hex() returns 64-char hex without 0x prefix
            self._private_key = self._account.key.hex()

        self._web3 = Web3()

    @property
    def address(self) -> str:
        """Get wallet address"""
        return self._account.address

    @property
    def private_key(self) -> str:
        """Get private key (hex without 0x prefix)"""
        return self._private_key

    @property
    def private_key_hex(self) -> str:
        """Get private key with 0x prefix"""
        return f"0x{self._private_key}"

    @property
    def public_key(self) -> str:
        """Get public key"""
        # Derive public key from private key
        return self._account.address  # Simplified - address is derived from public key

    def sign_message(self, message: str) -> str:
        """
        Sign a message.

        Args:
            message: Message to sign

        Returns:
            Signature (hex string)
        """
        message_encoded = encode_defunct(text=message)
        signed = self._account.sign_message(message_encoded)
        return signed.signature.hex()

    def sign_hash(self, message_hash: bytes) -> str:
        """
        Sign a message hash.

        Args:
            message_hash: Hash to sign (32 bytes)

        Returns:
            Signature (hex string)
        """
        signed = self._account.signHash(message_hash)
        return signed.signature.hex()

    def sign_transaction(self, transaction: Dict[str, Any]) -> bytes:
        """
        Sign a transaction.

        Args:
            transaction: Transaction dictionary

        Returns:
            Signed transaction bytes
        """
        signed = self._account.sign_transaction(transaction)
        return signed.rawTransaction

    def get_did(self) -> str:
        """Get DID identifier"""
        return f"did:ethr:{self.address}"

    def export_keystore(self, password: str) -> Dict[str, Any]:
        """
        Export wallet as encrypted keystore.

        Args:
            password: Encryption password

        Returns:
            Keystore JSON
        """
        return Account.encrypt(self.private_key_hex, password)

    @classmethod
    def from_keystore(cls, keystore: Dict[str, Any], password: str) -> "DIDWallet":
        """
        Import wallet from encrypted keystore.

        Args:
            keystore: Keystore JSON
            password: Decryption password

        Returns:
            DIDWallet instance
        """
        private_key = Account.decrypt(keystore, password)
        return cls(private_key.hex())

    def get_info(self) -> WalletInfo:
        """Get wallet information"""
        return WalletInfo(
            address=self.address,
            public_key=self.public_key
        )


class WalletManager:
    """
    Wallet Manager

    Manages multiple wallets for the platform.
    """

    def __init__(self, storage_path: str = "wallets"):
        """
        Initialize wallet manager.

        Args:
            storage_path: Path for storing encrypted wallets
        """
        self.storage_path = storage_path
        os.makedirs(storage_path, exist_ok=True)

        self._wallets: Dict[str, DIDWallet] = {}
        self._default_wallet: Optional[str] = None

    def create_wallet(self, label: str = "") -> DIDWallet:
        """
        Create a new wallet.

        Args:
            label: Optional label for the wallet

        Returns:
            Created DIDWallet
        """
        wallet = DIDWallet()
        self._wallets[wallet.address] = wallet

        if not self._default_wallet:
            self._default_wallet = wallet.address

        logger.info(f"Created wallet: {wallet.address}")
        return wallet

    def import_wallet(
        self,
        private_key: str,
        label: str = ""
    ) -> DIDWallet:
        """
        Import an existing wallet.

        Args:
            private_key: Private key (hex string)
            label: Optional label

        Returns:
            Imported DIDWallet
        """
        wallet = DIDWallet(private_key)
        self._wallets[wallet.address] = wallet

        if not self._default_wallet:
            self._default_wallet = wallet.address

        logger.info(f"Imported wallet: {wallet.address}")
        return wallet

    def get_wallet(self, address: str) -> Optional[DIDWallet]:
        """Get wallet by address"""
        return self._wallets.get(address)

    def get_default_wallet(self) -> Optional[DIDWallet]:
        """Get default wallet"""
        if self._default_wallet:
            return self._wallets.get(self._default_wallet)
        return None

    def set_default_wallet(self, address: str) -> bool:
        """Set default wallet"""
        if address in self._wallets:
            self._default_wallet = address
            return True
        return False

    def list_wallets(self) -> List[WalletInfo]:
        """List all wallets"""
        return [w.get_info() for w in self._wallets.values()]

    def remove_wallet(self, address: str) -> bool:
        """Remove a wallet"""
        if address in self._wallets:
            del self._wallets[address]
            if self._default_wallet == address:
                self._default_wallet = next(iter(self._wallets), None)
            return True
        return False

    def save_wallet(
        self,
        address: str,
        password: str,
        filename: Optional[str] = None
    ) -> str:
        """
        Save wallet to encrypted file.

        Args:
            address: Wallet address
            password: Encryption password
            filename: Optional filename

        Returns:
            Path to saved file
        """
        wallet = self._wallets.get(address)
        if not wallet:
            raise ValueError(f"Wallet not found: {address}")

        keystore = wallet.export_keystore(password)
        filename = filename or f"{address}.json"
        filepath = os.path.join(self.storage_path, filename)

        with open(filepath, 'w') as f:
            json.dump(keystore, f)

        return filepath

    def load_wallet(
        self,
        filepath: str,
        password: str
    ) -> DIDWallet:
        """
        Load wallet from encrypted file.

        Args:
            filepath: Path to keystore file
            password: Decryption password

        Returns:
            Loaded DIDWallet
        """
        with open(filepath, 'r') as f:
            keystore = json.load(f)

        wallet = DIDWallet.from_keystore(keystore, password)
        self._wallets[wallet.address] = wallet

        return wallet


# Singleton instance
_wallet_manager: Optional[WalletManager] = None


def get_wallet_manager() -> WalletManager:
    """Get the wallet manager instance"""
    global _wallet_manager
    if _wallet_manager is None:
        _wallet_manager = WalletManager()
    return _wallet_manager
