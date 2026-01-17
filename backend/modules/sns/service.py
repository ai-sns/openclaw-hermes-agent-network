"""SNS Module - Business Logic Service"""
import logging
import os
import uuid
from pathlib import Path
from sqlalchemy.orm import Session
from typing import List
from backend.database.models.chat import AIFriend, AIChatMessages, AiChatCfg
from backend.modules.sns.xmpp_client import XMPPClientManager

logger = logging.getLogger(__name__)

# File upload directory
UPLOAD_DIR = Path("uploads/sns_files")
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)


class SNSService:
    """SNS service for handling social network operations"""

    def __init__(self, db: Session):
        self.db = db

    def get_user_stats(self) -> dict:
        """Get user statistics from aichat_cfg table"""
        try:
            # Get first record from aichat_cfg
            config = self.db.query(AiChatCfg).filter(
                AiChatCfg.is_delete == False
            ).first()

            if not config:
                # Return default values
                return {
                    "level": 3,
                    "credit": 100,
                    "money": 10996.61,
                    "life": 125,
                    "iq": 70,
                    "energy": 150,
                    "move": 187.5,
                    "exp": 30
                }

            return {
                "level": config.level or 3,
                "credit": config.credit or 100,
                "money": config.money or 10996.61,
                "life": config.life_point or 125,
                "iq": config.iq_point or 70,
                "energy": config.energy_point or 150,
                "move": config.move_point or 187.5,
                "exp": config.exp_point or 30
            }
        except Exception as e:
            logger.error(f"Error getting user stats: {e}")
            # Return default values on error
            return {
                "level": 3,
                "credit": 100,
                "money": 10996.61,
                "life": 125,
                "iq": 70,
                "energy": 150,
                "move": 187.5,
                "exp": 30
            }

    def get_contacts(self) -> List[AIFriend]:
        """Get contact list from ai_friend table"""
        try:
            # Get owner account from first aichat_cfg record
            config = self.db.query(AiChatCfg).filter(
                AiChatCfg.is_delete == False
            ).first()

            if not config:
                return []

            owner_account = config.account

            # Query ai_friend table
            contacts = self.db.query(AIFriend).filter(
                AIFriend.is_delete == False,
                AIFriend.owner_sns_account == owner_account
            ).order_by(AIFriend.nick_name).all()

            return contacts
        except Exception as e:
            logger.error(f"Error getting contacts: {e}")
            return []

    def get_chat_history(self, friend_account: str, limit: int = 50) -> List[AIChatMessages]:
        """Get chat history with a specific contact"""
        try:
            # Get owner account
            config = self.db.query(AiChatCfg).filter(
                AiChatCfg.is_delete == False
            ).first()

            if not config:
                return []

            owner_account = config.account

            # Query chat messages
            messages = self.db.query(AIChatMessages).filter(
                AIChatMessages.is_delete == False,
                (
                    (AIChatMessages.owner_account == owner_account) &
                    (AIChatMessages.friend_account == friend_account)
                ) | (
                    (AIChatMessages.owner_account == friend_account) &
                    (AIChatMessages.friend_account == owner_account)
                )
            ).order_by(AIChatMessages.create_time.desc()).limit(limit).all()

            # Reverse to show oldest first
            messages.reverse()
            return messages
        except Exception as e:
            logger.error(f"Error getting chat history: {e}")
            return []

    async def send_message(self, to_account: str, content: str) -> dict:
        """Send a message via XMPP"""
        try:
            # Get XMPP client
            xmpp_manager = XMPPClientManager.get_instance()
            client = xmpp_manager.get_client()

            if not client or not client.is_client_connected():
                return {
                    "success": False,
                    "message": "XMPP client not connected"
                }

            # Send message via XMPP
            client.send_message_to_jid(to_account, content)

            # Save to database
            config = self.db.query(AiChatCfg).filter(
                AiChatCfg.is_delete == False
            ).first()

            if config:
                message = AIChatMessages(
                    conversation_id=f"{config.account}_{to_account}",
                    flag=0,  # 0=send
                    content=content,
                    owner_account=config.account,
                    friend_account=to_account,
                    owner_name=config.nickname or config.account,
                    friend_name=to_account
                )
                self.db.add(message)
                self.db.commit()

            return {
                "success": True,
                "message": "Message sent successfully"
            }
        except Exception as e:
            logger.error(f"Error sending message: {e}")
            return {
                "success": False,
                "message": str(e)
            }

    async def send_file(self, to_account: str, file) -> dict:
        """Send a file via XMPP using XEP-0363"""
        try:
            # Get XMPP client
            xmpp_manager = XMPPClientManager.get_instance()
            client = xmpp_manager.get_client()

            if not client or not client.is_client_connected():
                return {
                    "success": False,
                    "message": "XMPP client not connected"
                }

            # Save file temporarily
            file_id = str(uuid.uuid4())
            file_ext = Path(file.filename).suffix
            temp_filename = f"{file_id}{file_ext}"
            temp_path = UPLOAD_DIR / temp_filename

            # Read and save file content temporarily
            content = await file.read()
            with open(temp_path, "wb") as f:
                f.write(content)

            try:
                # Upload file via XEP-0363 and send to recipient
                url = await client.upload_and_send_file(
                    to_account,
                    str(temp_path),
                    file.filename
                )

                # Save to database
                config = self.db.query(AiChatCfg).filter(
                    AiChatCfg.is_delete == False
                ).first()

                if config:
                    file_message = f"📎 File: {file.filename}\n{url}"
                    message = AIChatMessages(
                        conversation_id=f"{config.account}_{to_account}",
                        flag=0,  # 0=send
                        content=file_message,
                        attachment_list=file.filename,
                        owner_account=config.account,
                        friend_account=to_account,
                        owner_name=config.nickname or config.account,
                        friend_name=to_account
                    )
                    self.db.add(message)
                    self.db.commit()

                return {
                    "success": True,
                    "message": "File sent successfully via XMPP",
                    "file_url": url
                }
            finally:
                # Clean up temporary file
                if temp_path.exists():
                    os.remove(temp_path)

        except Exception as e:
            logger.error(f"Error sending file: {e}")
            return {
                "success": False,
                "message": str(e)
            }
