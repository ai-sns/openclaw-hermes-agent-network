"""SNS Module - Business Logic Service - 异步版本"""
import logging
import os
import uuid
import base64
from pathlib import Path
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List
from fastapi import HTTPException
from backend.database.models.chat import AIFriend, AIChatMessages, AiChatCfg
from backend.database.models.system import Prompt
from backend.apps.sns.xmpp_client import XMPPClientManager

logger = logging.getLogger(__name__)

# File upload directory
UPLOAD_DIR = Path("uploads/sns_files")
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

AVATAR_DIR = Path("uploads/avatars")
AVATAR_DIR.mkdir(parents=True, exist_ok=True)

# Global instance for AI Social Engine
_social_engine_instance = None
_social_engine_running = False


class SNSService:
    """SNS service for handling social network operations - 异步版本"""

    def __init__(self, db: AsyncSession):
        self.db = db

    @staticmethod
    def _normalize_attachment_content(filename: str, content: bytes) -> bytes:
        """Normalize text attachments to UTF-8 with BOM to avoid Chinese mojibake."""
        suffix = Path(filename or "").suffix.lower()
        if suffix != '.txt':
            return content

        for encoding in ('utf-8-sig', 'utf-8', 'gb18030', 'gbk', 'big5'):
            try:
                text = content.decode(encoding)
                return text.encode('utf-8-sig')
            except UnicodeDecodeError:
                continue

        return content.decode('utf-8', errors='replace').encode('utf-8-sig')

    def get_user_stats(self) -> dict:
        """Get user statistics from aichat_cfg table"""
        try:
            def _to_int(value, default: int) -> int:
                if value is None:
                    return default
                try:
                    return int(value)
                except (TypeError, ValueError):
                    try:
                        return int(round(float(value)))
                    except (TypeError, ValueError):
                        return default

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
                "life": _to_int(config.life_point, 125),
                "iq": config.iq_point or 70,
                "energy": _to_int(config.energy_point, 150),
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
            content = self._normalize_attachment_content(file.filename, content)
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

    async def start_social_engine(self) -> dict:
        """Start the AI social engine"""
        global _social_engine_instance, _social_engine_running

        try:
            if _social_engine_running:
                return {
                    "success": True,
                    "message": "AI Social Engine is already running",
                    "running": True
                }

            # Import the AI social engine adapter
            from backend.apps.sns.ai_social_engine_adapter import AISocialEngine

            # Create engine instance if not exists
            if _social_engine_instance is None:
                _social_engine_instance = AISocialEngine(self.db)

            # Start the engine
            await _social_engine_instance.start_engine()
            _social_engine_running = True

            logger.info("AI Social Engine started successfully")
            return {
                "success": True,
                "message": "AI Social Engine started successfully",
                "running": True
            }
        except Exception as e:
            logger.error(f"Error starting AI social engine: {e}")
            _social_engine_running = False
            return {
                "success": False,
                "message": f"Failed to start AI Social Engine: {str(e)}",
                "running": False
            }


    def get_engine_status(self) -> dict:
        """Get the current status of the AI social engine"""
        global _social_engine_running
        return {
            "success": True,
            "running": _social_engine_running,
            "message": "AI Social Engine is " + ("running" if _social_engine_running else "stopped")
        }

    def get_ai_chat_config(self, user_id: str = None):
        """Get AI chat configuration"""
        try:
            query = self.db.query(AiChatCfg).filter(AiChatCfg.is_delete == False)
            if user_id:
                query = query.filter(AiChatCfg.user_id == user_id)

            config = query.first()
            if not config:
                raise HTTPException(status_code=404, detail="Configuration not found")

            return config
        except Exception as e:
            logger.error(f"Error getting AI chat config: {e}")
            raise

    def update_ai_chat_config(self, user_id: str = None, data: dict = None):
        """Update AI chat configuration"""
        try:
            query = self.db.query(AiChatCfg).filter(AiChatCfg.is_delete == False)
            if user_id:
                query = query.filter(AiChatCfg.user_id == user_id)

            config = query.first()
            if not config:
                # Create new config if not exists
                config = AiChatCfg(user_id=user_id)
                self.db.add(config)

            # Update fields
            for key, value in data.items():
                if hasattr(config, key) and value is not None:
                    setattr(config, key, value)

            self.db.commit()
            self.db.refresh(config)

            return {"success": True, "message": "Configuration updated successfully", "data": config}
        except Exception as e:
            logger.error(f"Error updating AI chat config: {e}")
            self.db.rollback()
            return {"success": False, "message": str(e)}

    async def upload_avatar(self, user_id: str = None, file=None):
        """Upload avatar image"""
        try:
            # Generate unique filename
            file_ext = Path(file.filename).suffix
            file_id = str(uuid.uuid4())
            filename = f"{file_id}{file_ext}"
            file_path = AVATAR_DIR / filename

            # Read and save file
            content = await file.read()
            with open(file_path, "wb") as f:
                f.write(content)

            # Convert to base64 for storage
            avatar_data = f"data:image/{file_ext[1:]};base64,{base64.b64encode(content).decode()}"

            # Update config
            query = self.db.query(AiChatCfg).filter(AiChatCfg.is_delete == False)
            if user_id:
                query = query.filter(AiChatCfg.user_id == user_id)

            config = query.first()
            if config:
                config.avatar = avatar_data
                self.db.commit()

            return {
                "success": True,
                "message": "Avatar uploaded successfully",
                "avatar_url": f"/uploads/avatars/{filename}",
                "avatar_data": avatar_data
            }
        except Exception as e:
            logger.error(f"Error uploading avatar: {e}")
            return {"success": False, "message": str(e)}

    def get_social_roles(self):
        """Get social roles (prompts with SNS tag)"""
        try:
            prompts = self.db.query(Prompt).filter(
                Prompt.tags.like('%SNS%')
            ).all()
            return prompts
        except Exception as e:
            logger.error(f"Error getting social roles: {e}")
            return []

    def get_user_info(self):
        """Get user information from aichat_cfg"""
        try:
            config = self.db.query(AiChatCfg).filter(
                AiChatCfg.is_delete == False
            ).first()

            if not config:
                return {"success": False, "message": "No user config found"}

            return {
                "success": True,
                "data": {
                    "nickname": config.nickname,
                    "sign": config.sign,
                    "sns_url": config.sns_url,
                    "agent_id": getattr(config, 'agent_id', None)
                }
            }
        except Exception as e:
            logger.error(f"Error getting user info: {e}")
            return {"success": False, "message": str(e)}

    def update_user_info(self, data: dict):
        """Update user information in aichat_cfg"""
        try:
            config = self.db.query(AiChatCfg).filter(
                AiChatCfg.is_delete == False
            ).first()

            if not config:
                return {"success": False, "message": "No user config found"}

            # Update fields
            if 'nickname' in data:
                config.nickname = data['nickname']
            if 'sign' in data:
                config.sign = data['sign']
            if 'sns_url' in data:
                config.sns_url = data['sns_url']
            if 'agent_id' in data:
                # Check if agent_id column exists
                if hasattr(config, 'agent_id'):
                    config.agent_id = data['agent_id']

            self.db.commit()
            return {"success": True, "message": "User info updated successfully"}
        except Exception as e:
            logger.error(f"Error updating user info: {e}")
            self.db.rollback()
            return {"success": False, "message": str(e)}

    def get_map_config(self):
        """Get map configuration from aichat_cfg"""
        try:
            config = self.db.query(AiChatCfg).filter(
                AiChatCfg.is_delete == False
            ).first()

            if not config:
                return {"success": False, "message": "No config found"}

            return {
                "success": True,
                "data": {
                    "map_api_key": config.map_api_key or "",
                    "map_id": config.map_id or "",
                    "map_type": config.map_type or "0"
                }
            }
        except Exception as e:
            logger.error(f"Error getting map config: {e}")
            return {"success": False, "message": str(e)}

    def update_map_config(self, data: dict):
        """Update map configuration in aichat_cfg and replace in files"""
        import re
        import json

        try:
            config = self.db.query(AiChatCfg).filter(
                AiChatCfg.is_delete == False
            ).first()

            if not config:
                return {"success": False, "message": "No config found"}

            # Get original values for file replacement
            old_api_keys = config.map_api_key.split(',') if config.map_api_key else ['', '']
            old_map_ids = config.map_id.split(',') if config.map_id else ['', '']
            old_map_type = config.map_type

            # Prepare new values
            google_api_key = data.get('google_api_key', 'N/A')
            google_map_id = data.get('google_map_id', 'N/A')
            baidu_api_key = data.get('baidu_api_key', 'N/A')
            baidu_map_id = data.get('baidu_map_id', 'N/A')
            map_type = data.get('map_type', '0')

            # Create comma-separated strings
            map_api_key = f"{google_api_key},{baidu_api_key}"
            map_id = f"{google_map_id},{baidu_map_id}"

            # Check if map type is changing
            map_type_changing = (old_map_type != map_type)

            # Update database
            config.map_type = map_type
            config.map_api_key = map_api_key
            config.map_id = map_id

            # Handle map position data if map type is changing
            if map_type_changing:
                memo_data = {}
                if config.memo:
                    try:
                        memo_data = json.loads(config.memo)
                    except json.JSONDecodeError:
                        memo_data = {}

                # Save current map position data
                current_map_data = {
                    "home_position": config.home_position or "",
                    "positionx": config.positionx if config.positionx is not None else 0,
                    "positiony": config.positiony if config.positiony is not None else 0,
                    "positionz": config.positionz if config.positionz is not None else 0
                }

                if old_map_type == "0":
                    memo_data["google"] = current_map_data
                elif old_map_type == "1":
                    memo_data["baidu"] = current_map_data

                config.memo = json.dumps(memo_data, ensure_ascii=False)

                # Reset route fields
                config.route_start = ""
                config.route_end = ""
                config.route_current_position = ""
                config.route = ""
                config.route_status = "stopped"

                # Load position data for new map type
                if map_type == "0" and "google" in memo_data:
                    google_data = memo_data["google"]
                    config.home_position = google_data.get("home_position", "")
                    config.positionx = google_data.get("positionx", 0)
                    config.positiony = google_data.get("positiony", 0)
                    config.positionz = google_data.get("positionz", 0)
                elif map_type == "1" and "baidu" in memo_data:
                    baidu_data = memo_data["baidu"]
                    config.home_position = baidu_data.get("home_position", "")
                    config.positionx = baidu_data.get("positionx", 0)
                    config.positiony = baidu_data.get("positiony", 0)
                    config.positionz = baidu_data.get("positionz", 0)

            self.db.commit()

            # Replace in files
            self._replace_map_config_in_files(
                old_api_keys, old_map_ids,
                [google_api_key, baidu_api_key],
                [google_map_id, baidu_map_id]
            )

            return {"success": True, "message": "Map config updated successfully"}
        except Exception as e:
            logger.error(f"Error updating map config: {e}")
            self.db.rollback()
            return {"success": False, "message": str(e)}

    def _replace_map_config_in_files(self, old_api_keys, old_map_ids, new_api_keys, new_map_ids):
        """Replace map configuration in HTML/JS files"""
        import re

        def replace_in_file(filepath, replacements):
            if not os.path.exists(filepath):
                logger.warning(f"File not found: {filepath}")
                return False

            try:
                with open(filepath, "r", encoding="utf-8") as f:
                    content = f.read()

                original_content = content

                for old_value, new_value in replacements.items():
                    if not old_value or old_value == new_value or old_value == "N/A" or not new_value or new_value == "N/A":
                        continue

                    patterns = []
                    if 'googlemap' in filepath or 'google' in filepath:
                        patterns.append((
                            r'(maps\.googleapis\.com/maps/api/js\?[^"\']*key=)' + re.escape(old_value),
                            r'\1' + new_value
                        ))
                        patterns.append((
                            r'(mapId:\s*["\'])' + re.escape(old_value) + r'(["\'])',
                            r'\1' + new_value + r'\2'
                        ))
                    elif 'map.html' in filepath or 'baidu' in filepath:
                        patterns.append((
                            r'(api\.map\.baidu\.com/api\?[^"\']*ak=)' + re.escape(old_value),
                            r'\1' + new_value
                        ))

                    for pattern, replacement in patterns:
                        content = re.sub(pattern, replacement, content)

                if content != original_content:
                    with open(filepath, "w", encoding="utf-8") as f:
                        f.write(content)
                    logger.info(f"Updated file: {filepath}")

                return True
            except Exception as e:
                logger.error(f"Error replacing in file {filepath}: {e}")
                return False

        # Google Map files
        if new_api_keys[0] != 'N/A' or new_map_ids[0] != 'N/A':
            google_replacements = {
                old_api_keys[0]: new_api_keys[0],
                old_map_ids[0]: new_map_ids[0],
            }
            replace_in_file("scripts/googlemap3d.html", google_replacements)
            replace_in_file("scripts/js/google/map_common.js", google_replacements)

        # Baidu Map files
        if new_api_keys[1] != 'N/A':
            baidu_replacements = {
                old_api_keys[1]: new_api_keys[1],
            }
            replace_in_file("scripts/map.html", baidu_replacements)
