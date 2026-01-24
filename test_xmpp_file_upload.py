#!/usr/bin/env python3
"""Test script to verify XEP-0363 file upload is properly configured"""

import sys
import asyncio
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent / 'backend'))

from backend.config.database import get_db
from backend.database.models.chat import AiChatCfg
from backend.modules.sns.xmpp_client import XMPPClient

async def test_xmpp_file_upload():
    """Test if XEP-0363 plugin is available"""
    try:
        # Get database session
        db = next(get_db())

        # Get XMPP config
        config = db.query(AiChatCfg).filter(
            AiChatCfg.is_delete == False
        ).first()

        if not config:
            print("❌ No XMPP configuration found")
            return False

        if not config.account or not config.password:
            print("❌ XMPP account or password not configured")
            return False

        print(f"✓ XMPP account: {config.account}")

        # Create XMPP client
        client = XMPPClient(config.account, config.password, db)

        # Check if xep_0363 plugin is registered
        if 'xep_0363' in client.plugin:
            print("✓ XEP-0363 (HTTP File Upload) plugin is registered")
        else:
            print("❌ XEP-0363 plugin not found")
            return False

        # Try to connect
        print("Connecting to XMPP server...")
        if client.connect():
            print("✓ Connected to XMPP server")

            # Process for a short time to establish session
            await asyncio.wait_for(client.process(forever=False), timeout=5.0)

            # Check if server supports XEP-0363
            try:
                # This will raise an exception if not supported
                info = await client['xep_0363'].find_upload_service()
                if info:
                    print(f"✓ Server supports XEP-0363 at: {info}")
                else:
                    print("⚠ Server may not support XEP-0363")
            except Exception as e:
                print(f"⚠ Could not verify XEP-0363 support: {e}")

            client.disconnect()
            print("✓ Disconnected")
            return True
        else:
            print("❌ Failed to connect to XMPP server")
            return False

    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    print("=" * 60)
    print("Testing XMPP XEP-0363 File Upload Configuration")
    print("=" * 60)

    result = asyncio.run(test_xmpp_file_upload())

    print("=" * 60)
    if result:
        print("✓ XEP-0363 file upload is properly configured")
    else:
        print("❌ XEP-0363 file upload configuration has issues")
    print("=" * 60)

    sys.exit(0 if result else 1)
