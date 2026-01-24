"""SNS Module - Business Logic Service - 异步版本"""
import logging
import os
import uuid
import base64
from pathlib import Path
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, or_
from sqlalchemy.orm import Session
from typing import List
from fastapi import HTTPException
from backend.database.models.chat import AIFriend, AIChatMessages, AiChatCfg
from backend.database.models.system import Prompt
from backend.modules.sns.xmpp_client import XMPPClientManager
from backend.config.database import get_db_sync

logger = logging.getLogger(__name__)

UPLOAD_DIR = Path("uploads/sns_files")
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

AVATAR_DIR = Path("uploads/avatars")
AVATAR_DIR.mkdir(parents=True, exist_ok=True)

_social_engine_instance = None
_social_engine_running = False


class SNSService:
    """SNS service for handling social network operations - 异步版本"""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_user_stats(self) -> dict:
        """异步获取用户统计"""
        try:
            stmt = select(AiChatCfg).where(AiChatCfg.is_delete == False)
            result = await self.db.execute(stmt)
            config = result.scalar_one_or_none()

            if not config:
                return {
                    "level":3,
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
            return {
                "level":3,
                "credit": 100,
                "money": 10996.61,
                "life": 125,
                "iq": 70,
                "energy": 150,
                "move": 187.5,
                "exp": 30
            }

    async def get_contacts(self) -> List[AIFriend]:
        """异步获取联系人列表"""
        try:
            stmt_config = select(AiChatCfg).where(AiChatCfg.is_delete == False)
            result_config = await self.db.execute(stmt_config)
            config = result_config.scalar_one_or_none()

            if not config:
                return []

            owner_account = config.account

            stmt_contacts = select(AIFriend).where(
                AIFriend.is_delete == False,
                AIFriend.owner_sns_account == owner_account
            ).order_by(AIFriend.nick_name)
            result_contacts = await self.db.execute(stmt_contacts)
            contacts = result_contacts.scalars().all()

            return contacts
        except Exception as e:
            logger.error(f"Error getting contacts: {e}")
            return []

    async def get_chat_history(self, friend_account: str, limit: int = 50) -> List[AIChatMessages]:
        """异步获取聊天历史"""
        try:
            stmt_config = select(AiChatCfg).where(AiChatCfg.is_delete == False)
            result_config = await self.db.execute(stmt_config)
            config = result_config.scalar_one_or_none()

            if not config:
                return []

            owner_account = config.account

            stmt_messages = select(AIChatMessages).where(
                AIChatMessages.is_delete == False,
                or_(
                    (AIChatMessages.owner_account == owner_account) &
                    (AIChatMessages.friend_account == friend_account),
                    (AIChatMessages.owner_account == friend_account) &
                    (AIChatMessages.friend_account == owner_account)
                )
            ).order_by(AIChatMessages.create_time.desc()).limit(limit)

            result_messages = await self.db.execute(stmt_messages)
            messages = result_messages.scalars().all()
            messages.reverse()

            return messages
        except Exception as e:
            logger.error(f"Error getting chat history: {e}")
            return []

    async def send_message(self, to_account: str, content: str) -> dict:
        """Send a message via XMPP"""
        try:
            xmpp_manager = XMPPClientManager.get_instance()
            client = xmpp_manager.get_client()

            if not client or not client.is_client_connected():
                return {
                    "success": False,
                    "message": "XMPP client not connected"
                }

            client.send_message_to_jid(to_account, content)

            stmt = select(AiChatCfg).where(AiChatCfg.is_delete == False)
            result = await self.db.execute(stmt)
            config = result.scalar_one_or_none()

            if config:
                message = AIChatMessages(
                    conversation_id=f"{config.account}_{to_account}",
                    flag=0,
                    content=content,
                    owner_account=config.account,
                    friend_account=to_account,
                    owner_name=config.nickname or config.account,
                    friend_name=to_account
                )
                self.db.add(message)
                await self.db.commit()

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
            xmpp_manager = XMPPClientManager.get_instance()
            client = xmpp_manager.get_client()

            if not client or not client.is_client_connected():
                return {
                    "success": False,
                    "message": "XMPP client not connected"
                }

            file_id = str(uuid.uuid4())
            file_ext = Path(file.filename).suffix
            temp_filename = f"{file_id}{file_ext}"
            temp_path = UPLOAD_DIR / temp_filename

            content = await file.read()
            with open(temp_path, "wb") as f:
                f.write(content)

            try:
                url = await client.upload_and_send_file(
                    to_account,
                    str(temp_path),
                    file.filename
                )

                stmt = select(AiChatCfg).where(AiChatCfg.is_delete == False)
                result = await self.db.execute(stmt)
                config = result.scalar_one_or_none()

                if config:
                    file_message = f"📎 File: {file.filename}\n{url}"
                    message = AIChatMessages(
                        conversation_id=f"{config.account}_{to_account}",
                        flag=0,
                        content=file_message,
                        attachment_list=file.filename,
                        owner_account=config.account,
                        friend_account=to_account,
                        owner_name=config.nickname or config.account,
                        friend_name=to_account
                    )
                    self.db.add(message)
                    await self.db.commit()

                return {
                    "success": True,
                    "message": "File sent successfully via XMPP",
                    "file_url": url
                }
            finally:
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

            from backend.modules.sns.ai_social_engine_adapter import AISocialEngine

            if _social_engine_instance is None:
                # 为 AISocialEngine 创建同步的 Session
                db_sync = get_db_sync()
                _social_engine_instance = AISocialEngine(db_sync)
                await _social_engine_instance.async_init()

            await _social_engine_instance.start()
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

    async def stop_social_engine(self) -> dict:
        """Stop the AI social engine"""
        global _social_engine_instance, _social_engine_running

        try:
            if not _social_engine_running:
                return {
                    "success": True,
                    "message": "AI Social Engine is not running",
                    "running": False
                }

            if _social_engine_instance is not None:
                await _social_engine_instance.stop()

            _social_engine_running = False

            logger.info("AI Social Engine stopped successfully")
            return {
                "success": True,
                "message": "AI Social Engine stopped successfully",
                "running": False
            }
        except Exception as e:
            logger.error(f"Error stopping AI social engine: {e}")
            return {
                "success": False,
                "message": f"Failed to stop AI Social Engine: {str(e)}",
                "running": _social_engine_running
            }

    def get_engine_status(self) -> dict:
        """Get the current status of the AI social engine"""
        global _social_engine_running
        return {
            "success": True,
            "running": _social_engine_running,
            "message": "AI Social Engine is " + ("running" if _social_engine_running else "stopped")
        }

    async def get_ai_chat_config(self, user_id: str = None):
        """Get AI chat configuration"""
        try:
            stmt = select(AiChatCfg).where(AiChatCfg.is_delete == False)
            if user_id:
                stmt = stmt.where(AiChatCfg.user_id == user_id)

            result = await self.db.execute(stmt)
            config = result.scalar_one_or_none()
            if not config:
                raise HTTPException(status_code=404, detail="Configuration not found")

            return config
        except Exception as e:
            logger.error(f"Error getting AI chat config: {e}")
            raise

    async def update_ai_chat_config(self, user_id: str = None, data: dict = None):
        """Update AI chat configuration"""
        try:
            stmt = select(AiChatCfg).where(AiChatCfg.is_delete == False)
            if user_id:
                stmt = stmt.where(AiChatCfg.user_id == user_id)

            result = await self.db.execute(stmt)
            config = result.scalar_one_or_none()
            if not config:
                config = AiChatCfg(user_id=user_id)
                self.db.add(config)

            for key, value in data.items():
                if hasattr(config, key) and value is not None:
                    setattr(config, key, value)

            await self.db.commit()
            await self.db.refresh(config)

            return {"success": True, "message": "Configuration updated successfully", "data": config}
        except Exception as e:
            logger.error(f"Error updating AI chat config: {e}")
            await self.db.rollback()
            return {"success": False, "message": str(e)}

    async def upload_avatar(self, user_id: str = None, file=None):
        """Upload avatar image"""
        try:
            file_ext = Path(file.filename).suffix
            file_id = str(uuid.uuid4())
            filename = f"{file_id}{file_ext}"
            file_path = AVATAR_DIR / filename

            content = await file.read()
            with open(file_path, "wb") as f:
                f.write(content)

            avatar_data = f"data:image/{file_ext[1:]};base64,{base64.b64encode(content).decode()}"

            stmt = select(AiChatCfg).where(AiChatCfg.is_delete == False)
            if user_id:
                stmt = stmt.where(AiChatCfg.user_id == user_id)

            result = await self.db.execute(stmt)
            config = result.scalar_one_or_none()
            if config:
                config.avatar = avatar_data
                await self.db.commit()

            return {
                "success": True,
                "message": "Avatar uploaded successfully",
                "avatar_url": f"/uploads/avatars/{filename}",
                "avatar_data": avatar_data
            }
        except Exception as e:
            logger.error(f"Error uploading avatar: {e}")
            return {"success": False, "message": str(e)}

    async def get_social_roles(self):
        """Get social roles (prompts with SNS tag)"""
        try:
            stmt = select(Prompt).where(Prompt.tags.like('%SNS%'))
            result = await self.db.execute(stmt)
            prompts = result.scalars().all()
            return prompts
        except Exception as e:
            logger.error(f"Error getting social roles: {e}")
            return []

    async def get_user_info(self):
        """Get user information from aichat_cfg"""
        try:
            stmt = select(AiChatCfg).where(AiChatCfg.is_delete == False)
            result = await self.db.execute(stmt)
            config = result.scalar_one_or_none()

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

    async def update_user_info(self, data: dict):
        """Update user information in aichat_cfg"""
        try:
            stmt = select(AiChatCfg).where(AiChatCfg.is_delete == False)
            result = await self.db.execute(stmt)
            config = result.scalar_one_or_none()

            if not config:
                return {"success": False, "message": "No user config found"}

            if 'nickname' in data:
                config.nickname = data['nickname']
            if 'sign' in data:
                config.sign = data['sign']
            if 'sns_url' in data:
                config.sns_url = data['sns_url']
            if 'agent_id' in data:
                if hasattr(config, 'agent_id'):
                    config.agent_id = data['agent_id']

            await self.db.commit()
            return {"success": True, "message": "User info updated successfully"}
        except Exception as e:
            logger.error(f"Error updating user info: {e}")
            await self.db.rollback()
            return {"success": False, "message": str(e)}

    async def get_map_config(self):
        """Get map configuration from aichat_cfg"""
        try:
            stmt = select(AiChatCfg).where(AiChatCfg.is_delete == False)
            result = await self.db.execute(stmt)
            config = result.scalar_one_or_none()

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

    async def update_map_config(self, data: dict):
        """Update map configuration in aichat_cfg and replace in files"""
        import re
        import json

        try:
            stmt = select(AiChatCfg).where(AiChatCfg.is_delete == False)
            result = await self.db.execute(stmt)
            config = result.scalar_one_or_none()

            if not config:
                return {"success": False, "message": "No config found"}

            old_api_keys = config.map_api_key.split(',') if config.map_api_key else ['', '']
            old_map_ids = config.map_id.split(',') if config.map_id else ['', '']
            old_map_type = config.map_type

            google_api_key = data.get('google_api_key', 'N/A')
            google_map_id = data.get('google_map_id', 'N/A')
            baidu_api_key = data.get('baidu_api_key', 'N/A')
            baidu_map_id = data.get('baidu_map_id', 'N/A')
            map_type = data.get('map_type', '0')

            map_api_key = f"{google_api_key},{baidu_api_key}"
            map_id = f"{google_map_id},{baidu_map_id}"

            map_type_changing = (old_map_type != map_type)

            config.map_type = map_type
            config.map_api_key = map_api_key
            config.map_id = map_id

            if map_type_changing:
                memo_data = {}
                if config.memo:
                    try:
                        memo_data = json.loads(config.memo)
                    except json.JSONDecodeError:
                        memo_data = {}

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

                config.route_start = ""
                config.route_end = ""
                config.route_current_position = ""
                config.route = ""
                config.route_status = "stopped"

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

            await self.db.commit()

            self._replace_map_config_in_files(
                old_api_keys, old_map_ids,
                [google_api_key, baidu_api_key],
                [google_map_id, baidu_map_id]
            )

            return {"success": True, "message": "Map config updated successfully"}
        except Exception as e:
            logger.error(f"Error updating map config: {e}")
            await self.db.rollback()
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

        if new_api_keys[0] != 'N/A' or new_map_ids[0] != 'N/A':
            google_replacements = {
                old_api_keys[0]: new_api_keys[0],
                old_map_ids[0]: new_map_ids[0],
            }
            replace_in_file("scripts/googlemap3d.html", google_replacements)
            replace_in_file("scripts/js/google/map_common.js", google_replacements)

        if new_api_keys[1] != 'N/A':
            baidu_replacements = {
                old_api_keys[1]: new_api_keys[1],
            }
            replace_in_file("scripts/map.html", baidu_replacements)
