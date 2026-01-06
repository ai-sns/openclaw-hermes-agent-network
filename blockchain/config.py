"""
Blockchain Configuration

Configuration for Ethereum Sepolia testnet connection.
"""

import os
from typing import Optional, Dict, Any
from dataclasses import dataclass, field
from enum import Enum
import logging

logger = logging.getLogger(__name__)


class NetworkType(str, Enum):
    """Supported blockchain networks"""
    MAINNET = "mainnet"
    SEPOLIA = "sepolia"
    GOERLI = "goerli"
    LOCALHOST = "localhost"


@dataclass
class NetworkConfig:
    """Network-specific configuration"""
    name: str
    chain_id: int
    rpc_url: str
    explorer_url: str
    currency_symbol: str = "ETH"
    is_testnet: bool = True


# Public RPC endpoints (no API key required)
PUBLIC_RPC_ENDPOINTS = {
    NetworkType.SEPOLIA: [
        "https://rpc.sepolia.org",
        "https://ethereum-sepolia.publicnode.com",
        "https://sepolia.gateway.tenderly.co",
        "https://1rpc.io/sepolia",
        "https://eth-sepolia.public.blastapi.io",
    ],
    NetworkType.MAINNET: [
        "https://eth.llamarpc.com",
        "https://ethereum.publicnode.com",
    ]
}

# Network configurations
NETWORK_CONFIGS: Dict[NetworkType, NetworkConfig] = {
    NetworkType.MAINNET: NetworkConfig(
        name="Ethereum Mainnet",
        chain_id=1,
        rpc_url="https://mainnet.infura.io/v3/",
        explorer_url="https://etherscan.io",
        is_testnet=False
    ),
    NetworkType.SEPOLIA: NetworkConfig(
        name="Sepolia Testnet",
        chain_id=11155111,
        rpc_url="https://rpc.sepolia.org",  # Default to public RPC
        explorer_url="https://sepolia.etherscan.io",
        is_testnet=True
    ),
    NetworkType.GOERLI: NetworkConfig(
        name="Goerli Testnet",
        chain_id=5,
        rpc_url="https://goerli.infura.io/v3/",
        explorer_url="https://goerli.etherscan.io",
        is_testnet=True
    ),
    NetworkType.LOCALHOST: NetworkConfig(
        name="Local Development",
        chain_id=31337,
        rpc_url="http://localhost:8545",
        explorer_url="",
        is_testnet=True
    )
}


@dataclass
class BlockchainConfig:
    """
    Blockchain Configuration

    Manages connection settings for Ethereum networks.
    """
    network: NetworkType = NetworkType.SEPOLIA
    infura_api_key: str = ""
    private_key: Optional[str] = None
    escrow_contract_address: Optional[str] = None
    gas_price_multiplier: float = 1.1
    max_gas_price_gwei: int = 100
    confirmation_blocks: int = 2
    timeout_seconds: int = 120

    # Contract addresses (Sepolia defaults)
    contracts: Dict[str, str] = field(default_factory=dict)

    def __post_init__(self):
        """Load configuration from environment"""
        self.infura_api_key = os.environ.get(
            "INFURA_API_KEY",
            self.infura_api_key
        )
        self.private_key = os.environ.get(
            "BLOCKCHAIN_PRIVATE_KEY",
            self.private_key
        )
        self.escrow_contract_address = os.environ.get(
            "ESCROW_CONTRACT_ADDRESS",
            self.escrow_contract_address
        )

    @property
    def network_config(self) -> NetworkConfig:
        """Get network configuration"""
        return NETWORK_CONFIGS[self.network]

    @property
    def rpc_url(self) -> str:
        """Get full RPC URL with API key or public endpoint"""
        base_url = self.network_config.rpc_url

        if self.network == NetworkType.LOCALHOST:
            return base_url

        # If we have an Infura API key and the URL expects one, use it
        if self.infura_api_key and "infura.io" in base_url:
            return f"{base_url}{self.infura_api_key}"

        # Otherwise, use public RPC endpoints
        if self.network in PUBLIC_RPC_ENDPOINTS:
            return PUBLIC_RPC_ENDPOINTS[self.network][0]  # Use first available

        return base_url

    @property
    def chain_id(self) -> int:
        """Get chain ID"""
        return self.network_config.chain_id

    @property
    def explorer_url(self) -> str:
        """Get block explorer URL"""
        return self.network_config.explorer_url

    def get_explorer_tx_url(self, tx_hash: str) -> str:
        """Get explorer URL for a transaction"""
        if not self.explorer_url:
            return ""
        return f"{self.explorer_url}/tx/{tx_hash}"

    def get_explorer_address_url(self, address: str) -> str:
        """Get explorer URL for an address"""
        if not self.explorer_url:
            return ""
        return f"{self.explorer_url}/address/{address}"

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary (excluding sensitive data)"""
        return {
            "network": self.network.value,
            "chain_id": self.chain_id,
            "rpc_url": self.rpc_url.replace(self.infura_api_key, "***") if self.infura_api_key else self.rpc_url,
            "explorer_url": self.explorer_url,
            "escrow_contract_address": self.escrow_contract_address,
            "gas_price_multiplier": self.gas_price_multiplier,
            "max_gas_price_gwei": self.max_gas_price_gwei,
            "is_testnet": self.network_config.is_testnet
        }

    def validate(self) -> bool:
        """Validate configuration"""
        if self.network != NetworkType.LOCALHOST:
            if not self.infura_api_key:
                logger.warning("Infura API key not set")
                return False

        return True


# Singleton instance
_blockchain_config: Optional[BlockchainConfig] = None


def get_blockchain_config() -> BlockchainConfig:
    """Get the blockchain configuration instance"""
    global _blockchain_config
    if _blockchain_config is None:
        _blockchain_config = BlockchainConfig()
    return _blockchain_config


def set_blockchain_config(config: BlockchainConfig):
    """Set the blockchain configuration"""
    global _blockchain_config
    _blockchain_config = config
