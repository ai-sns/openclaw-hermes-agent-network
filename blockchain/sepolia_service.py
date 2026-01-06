"""
Sepolia Testnet Service

Provides real blockchain interaction with Sepolia testnet.
Uses public RPC endpoints, no API key required.
"""

import os
import asyncio
import logging
from typing import Optional, Dict, Any, List
from decimal import Decimal
from dataclasses import dataclass

logger = logging.getLogger(__name__)

# Try to import web3
try:
    from web3 import Web3
    # Try new-style import first (web3 v6+)
    try:
        from web3.middleware import ExtraDataToPOAMiddleware
        POA_MIDDLEWARE = ExtraDataToPOAMiddleware
    except ImportError:
        # Fall back to old-style import (web3 v5)
        try:
            from web3.middleware import geth_poa_middleware
            POA_MIDDLEWARE = geth_poa_middleware
        except ImportError:
            POA_MIDDLEWARE = None
    HAS_WEB3 = True
except ImportError:
    HAS_WEB3 = False
    POA_MIDDLEWARE = None
    logger.warning("web3 not available. Install with: pip install web3")

# Public Sepolia RPC endpoints (no API key required)
SEPOLIA_RPC_ENDPOINTS = [
    "https://rpc.sepolia.org",
    "https://ethereum-sepolia.publicnode.com",
    "https://sepolia.gateway.tenderly.co",
    "https://1rpc.io/sepolia",
    "https://eth-sepolia.public.blastapi.io",
]

SEPOLIA_CHAIN_ID = 11155111
SEPOLIA_EXPLORER = "https://sepolia.etherscan.io"

# Faucet URLs
SEPOLIA_FAUCETS = [
    {
        "name": "Alchemy Sepolia Faucet",
        "url": "https://sepoliafaucet.com",
        "description": "Get 0.5 ETH per day (requires Alchemy account)"
    },
    {
        "name": "Google Cloud Web3 Faucet",
        "url": "https://cloud.google.com/application/web3/faucet/ethereum/sepolia",
        "description": "Get 0.05 ETH per day (requires Google account)"
    },
    {
        "name": "Infura Sepolia Faucet",
        "url": "https://www.infura.io/faucet/sepolia",
        "description": "Get 0.5 ETH per day (requires Infura account)"
    },
    {
        "name": "QuickNode Sepolia Faucet",
        "url": "https://faucet.quicknode.com/ethereum/sepolia",
        "description": "Get test ETH (requires QuickNode account)"
    }
]


@dataclass
class SepoliaConnectionStatus:
    """Sepolia connection status"""
    connected: bool
    rpc_url: str
    chain_id: Optional[int]
    block_number: Optional[int]
    error: Optional[str] = None


class SepoliaService:
    """
    Service for interacting with Sepolia testnet.

    Provides:
    - Connection management with automatic failover
    - Balance checking
    - Transaction sending
    - Gas price estimation
    """

    def __init__(self, rpc_url: Optional[str] = None):
        """
        Initialize Sepolia service.

        Args:
            rpc_url: Optional specific RPC URL. If None, uses public endpoints.
        """
        self._web3: Optional[Web3] = None
        self._connected = False
        self._current_rpc = None
        self._rpc_url = rpc_url

        if HAS_WEB3:
            self._connect()

    def _connect(self, rpc_url: Optional[str] = None) -> bool:
        """
        Connect to Sepolia network.

        Args:
            rpc_url: Specific RPC URL to use

        Returns:
            True if connected successfully
        """
        if not HAS_WEB3:
            logger.error("web3 not available")
            return False

        # Determine which RPCs to try
        if rpc_url:
            endpoints_to_try = [rpc_url]
        elif self._rpc_url:
            endpoints_to_try = [self._rpc_url]
        else:
            endpoints_to_try = SEPOLIA_RPC_ENDPOINTS

        # Try each endpoint
        for endpoint in endpoints_to_try:
            try:
                logger.info(f"Trying to connect to: {endpoint}")
                web3 = Web3(Web3.HTTPProvider(endpoint, request_kwargs={'timeout': 10}))

                # Add POA middleware for Sepolia (if available)
                if POA_MIDDLEWARE:
                    try:
                        web3.middleware_onion.inject(POA_MIDDLEWARE, layer=0)
                    except Exception as e:
                        logger.warning(f"Could not inject POA middleware: {e}")

                # Check connection
                if web3.is_connected():
                    chain_id = web3.eth.chain_id
                    if chain_id == SEPOLIA_CHAIN_ID:
                        self._web3 = web3
                        self._connected = True
                        self._current_rpc = endpoint
                        logger.info(f"Connected to Sepolia via {endpoint}")
                        return True
                    else:
                        logger.warning(f"Wrong chain ID: {chain_id} (expected {SEPOLIA_CHAIN_ID})")

            except Exception as e:
                logger.warning(f"Failed to connect to {endpoint}: {e}")
                continue

        logger.error("Failed to connect to any Sepolia RPC")
        self._connected = False
        return False

    @property
    def is_connected(self) -> bool:
        """Check if connected to Sepolia"""
        if not self._web3:
            return False
        try:
            return self._web3.is_connected()
        except:
            return False

    @property
    def web3(self) -> Optional[Web3]:
        """Get Web3 instance"""
        return self._web3

    def get_connection_status(self) -> SepoliaConnectionStatus:
        """Get detailed connection status"""
        if not HAS_WEB3:
            return SepoliaConnectionStatus(
                connected=False,
                rpc_url="",
                chain_id=None,
                block_number=None,
                error="web3 library not installed"
            )

        if not self._connected or not self._web3:
            return SepoliaConnectionStatus(
                connected=False,
                rpc_url=self._current_rpc or "",
                chain_id=None,
                block_number=None,
                error="Not connected"
            )

        try:
            chain_id = self._web3.eth.chain_id
            block_number = self._web3.eth.block_number
            return SepoliaConnectionStatus(
                connected=True,
                rpc_url=self._current_rpc,
                chain_id=chain_id,
                block_number=block_number
            )
        except Exception as e:
            return SepoliaConnectionStatus(
                connected=False,
                rpc_url=self._current_rpc or "",
                chain_id=None,
                block_number=None,
                error=str(e)
            )

    def get_balance(self, address: str) -> Dict[str, Any]:
        """
        Get ETH balance for an address.

        Args:
            address: Ethereum address

        Returns:
            Dictionary with balance information
        """
        if not self._connected or not self._web3:
            return {
                "success": False,
                "error": "Not connected to Sepolia",
                "address": address
            }

        try:
            # Validate address
            if not Web3.is_address(address):
                return {
                    "success": False,
                    "error": "Invalid Ethereum address",
                    "address": address
                }

            # Get balance in wei
            balance_wei = self._web3.eth.get_balance(Web3.to_checksum_address(address))
            balance_eth = Decimal(balance_wei) / Decimal(10**18)

            return {
                "success": True,
                "address": address,
                "balance_wei": str(balance_wei),
                "balance_eth": str(balance_eth),
                "network": "sepolia",
                "explorer_url": f"{SEPOLIA_EXPLORER}/address/{address}"
            }

        except Exception as e:
            logger.error(f"Failed to get balance for {address}: {e}")
            return {
                "success": False,
                "error": str(e),
                "address": address
            }

    def get_gas_price(self) -> Dict[str, Any]:
        """Get current gas price"""
        if not self._connected or not self._web3:
            return {"success": False, "error": "Not connected"}

        try:
            gas_price_wei = self._web3.eth.gas_price
            gas_price_gwei = Decimal(gas_price_wei) / Decimal(10**9)

            return {
                "success": True,
                "gas_price_wei": str(gas_price_wei),
                "gas_price_gwei": str(gas_price_gwei),
                "network": "sepolia"
            }
        except Exception as e:
            return {"success": False, "error": str(e)}

    def get_transaction(self, tx_hash: str) -> Dict[str, Any]:
        """
        Get transaction details.

        Args:
            tx_hash: Transaction hash

        Returns:
            Transaction details
        """
        if not self._connected or not self._web3:
            return {"success": False, "error": "Not connected"}

        try:
            tx = self._web3.eth.get_transaction(tx_hash)
            receipt = self._web3.eth.get_transaction_receipt(tx_hash)

            return {
                "success": True,
                "tx_hash": tx_hash,
                "from": tx['from'],
                "to": tx['to'],
                "value_wei": str(tx['value']),
                "value_eth": str(Decimal(tx['value']) / Decimal(10**18)),
                "gas_used": receipt['gasUsed'] if receipt else None,
                "status": receipt['status'] if receipt else None,
                "block_number": tx['blockNumber'],
                "explorer_url": f"{SEPOLIA_EXPLORER}/tx/{tx_hash}"
            }
        except Exception as e:
            return {"success": False, "error": str(e), "tx_hash": tx_hash}

    def get_block_number(self) -> Dict[str, Any]:
        """Get current block number"""
        if not self._connected or not self._web3:
            return {"success": False, "error": "Not connected"}

        try:
            block_number = self._web3.eth.block_number
            return {
                "success": True,
                "block_number": block_number,
                "network": "sepolia"
            }
        except Exception as e:
            return {"success": False, "error": str(e)}

    @staticmethod
    def get_faucet_urls() -> List[Dict[str, str]]:
        """Get list of Sepolia faucet URLs"""
        return SEPOLIA_FAUCETS

    @staticmethod
    def get_explorer_url(address_or_tx: str, is_tx: bool = False) -> str:
        """
        Get Sepolia explorer URL.

        Args:
            address_or_tx: Address or transaction hash
            is_tx: True if it's a transaction hash

        Returns:
            Explorer URL
        """
        if is_tx:
            return f"{SEPOLIA_EXPLORER}/tx/{address_or_tx}"
        return f"{SEPOLIA_EXPLORER}/address/{address_or_tx}"


# Singleton instance
_sepolia_service: Optional[SepoliaService] = None


def get_sepolia_service() -> SepoliaService:
    """Get the Sepolia service instance"""
    global _sepolia_service
    if _sepolia_service is None:
        _sepolia_service = SepoliaService()
    return _sepolia_service


def reset_sepolia_service():
    """Reset the Sepolia service (for testing)"""
    global _sepolia_service
    _sepolia_service = None


# Quick test function
async def test_sepolia_connection():
    """Test Sepolia connection"""
    service = get_sepolia_service()
    status = service.get_connection_status()
    print(f"Connected: {status.connected}")
    print(f"RPC URL: {status.rpc_url}")
    print(f"Chain ID: {status.chain_id}")
    print(f"Block Number: {status.block_number}")
    if status.error:
        print(f"Error: {status.error}")
    return status


if __name__ == "__main__":
    import asyncio
    asyncio.run(test_sepolia_connection())
