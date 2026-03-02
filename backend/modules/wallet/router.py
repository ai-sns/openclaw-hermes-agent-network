# -*- coding: utf-8 -*-
"""
Wallet module - API router for blockchain wallet management
"""
import logging
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional

logger = logging.getLogger(__name__)

router = APIRouter()


class WalletCreateRequest(BaseModel):
    """Wallet creation request"""
    label: Optional[str] = ""


class WalletResponse(BaseModel):
    """Wallet response model"""
    address: str
    public_key: str
    private_key: Optional[str] = None  # Only returned on creation
    created_at: Optional[str] = None
    label: Optional[str] = ""


@router.post("/create", response_model=dict)
async def create_wallet(request: WalletCreateRequest):
    """
    Create a new blockchain wallet

    Returns:
        Wallet address, public key, and private key (IMPORTANT: save private key securely!)
    """
    try:
        # Import wallet manager
        import sys
        import os
        sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../../'))

        from blockchain.did.wallet import get_wallet_manager

        manager = get_wallet_manager()
        wallet = manager.create_wallet(label=request.label or "")

        return {
            "success": True,
            "data": {
                "address": wallet.address,
                "public_key": wallet.public_key,
                "private_key": wallet.private_key,  # IMPORTANT: Save this securely!
                "label": request.label or "",
                "warning": "Please store your private key securely! If you lose it, the wallet cannot be recovered!"
            }
        }
    except ImportError as e:
        logger.error(f"Wallet dependencies not installed: {e}")
        raise HTTPException(
            status_code=500,
            detail="Blockchain wallet features require web3 and eth-account. Please run: pip install web3 eth-account"
        )
    except Exception as e:
        logger.error(f"Error creating wallet: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/import", response_model=dict)
async def import_wallet(private_key: str, label: Optional[str] = ""):
    """
    Import an existing wallet using private key

    Args:
        private_key: Private key (with or without 0x prefix)
        label: Optional wallet label

    Returns:
        Wallet information
    """
    try:
        import sys
        import os
        sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../../'))

        from blockchain.did.wallet import get_wallet_manager

        manager = get_wallet_manager()
        wallet = manager.import_wallet(private_key=private_key, label=label or "")

        return {
            "success": True,
            "data": {
                "address": wallet.address,
                "public_key": wallet.public_key,
                "label": label or ""
            }
        }
    except ImportError as e:
        logger.error(f"Wallet dependencies not installed: {e}")
        raise HTTPException(
            status_code=500,
            detail="Blockchain wallet features require web3 and eth-account. Please run: pip install web3 eth-account"
        )
    except Exception as e:
        logger.error(f"Error importing wallet: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/list", response_model=dict)
async def list_wallets():
    """
    List all wallets

    Returns:
        List of wallet addresses and labels
    """
    try:
        import sys
        import os
        sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../../'))

        from blockchain.did.wallet import get_wallet_manager

        manager = get_wallet_manager()
        wallets = manager.list_wallets()

        return {
            "success": True,
            "data": [
                {
                    "address": w.address,
                    "public_key": w.public_key,
                    "label": w.label or "",
                    "created_at": w.created_at.isoformat() if w.created_at else None
                }
                for w in wallets
            ]
        }
    except ImportError as e:
        logger.error(f"Wallet dependencies not installed: {e}")
        raise HTTPException(
            status_code=500,
            detail="Blockchain wallet features require web3 and eth-account. Please run: pip install web3 eth-account"
        )
    except Exception as e:
        logger.error(f"Error listing wallets: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{address}", response_model=dict)
async def get_wallet(address: str):
    """
    Get wallet information by address

    Args:
        address: Wallet address

    Returns:
        Wallet information (without private key)
    """
    try:
        import sys
        import os
        sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../../'))

        from blockchain.did.wallet import get_wallet_manager

        manager = get_wallet_manager()
        wallet = manager.get_wallet(address)

        if not wallet:
            raise HTTPException(status_code=404, detail="Wallet not found")

        info = wallet.get_info()
        return {
            "success": True,
            "data": {
                "address": info.address,
                "public_key": info.public_key,
                "label": info.label or "",
                "created_at": info.created_at.isoformat() if info.created_at else None
            }
        }
    except HTTPException:
        raise
    except ImportError as e:
        logger.error(f"Wallet dependencies not installed: {e}")
        raise HTTPException(
            status_code=500,
            detail="Blockchain wallet features require web3 and eth-account. Please run: pip install web3 eth-account"
        )
    except Exception as e:
        logger.error(f"Error getting wallet: {e}")
        raise HTTPException(status_code=500, detail=str(e))
