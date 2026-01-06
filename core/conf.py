"""
Core Configuration

Contains application settings used across modules.
"""

import os
from dataclasses import dataclass


@dataclass
class Settings:
    """Application settings"""

    # Database settings
    SQL_URL: str = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        "data"
    )

    # Application settings
    APP_NAME: str = "AI Agent Open Platform"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = os.environ.get("DEBUG", "false").lower() == "true"

    # Server settings
    HOST: str = os.environ.get("HOST", "0.0.0.0")
    PORT: int = int(os.environ.get("PORT", "8000"))

    # Security settings
    SECRET_KEY: str = os.environ.get("SECRET_KEY", "your-secret-key-change-in-production")
    API_KEY_EXPIRE_DAYS: int = int(os.environ.get("API_KEY_EXPIRE_DAYS", "365"))

    # Rate limiting
    RATE_LIMIT_DEFAULT: int = int(os.environ.get("RATE_LIMIT", "100"))
    RATE_LIMIT_WINDOW: int = int(os.environ.get("RATE_LIMIT_WINDOW", "60"))

    # Blockchain settings
    BLOCKCHAIN_NETWORK: str = os.environ.get("BLOCKCHAIN_NETWORK", "sepolia")
    INFURA_API_KEY: str = os.environ.get("INFURA_API_KEY", "")
    BLOCKCHAIN_PRIVATE_KEY: str = os.environ.get("BLOCKCHAIN_PRIVATE_KEY", "")
    ESCROW_CONTRACT_ADDRESS: str = os.environ.get("ESCROW_CONTRACT_ADDRESS", "")

    # File storage
    UPLOAD_DIR: str = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        "uploads"
    )
    MAX_UPLOAD_SIZE: int = int(os.environ.get("MAX_UPLOAD_SIZE", str(50 * 1024 * 1024)))  # 50MB


# Singleton settings instance
settings = Settings()

# Ensure directories exist
os.makedirs(settings.SQL_URL, exist_ok=True)
os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
