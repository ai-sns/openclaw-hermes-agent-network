"""SNS Module - Business Logic Service - Async version."""
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
from backend.database.models.system import SystemCfg
from backend.apps.sns.xmpp_client import XMPPClientManager
from backend.apps.sns.message_formatter import format_internal_xmpp_message_for_storage

from backend.modules.map.file_replace import (
    GOOGLE_KEY_PLACEHOLDER,
    BAIDU_KEY_PLACEHOLDER,
    GOOGLE_MAP_ID_PLACEHOLDER,
    BAIDU_MAP_ID_SENTINEL,
    replace_map_config_in_files,
)

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
    """SNS service for handling social network operations - async version."""

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

            def _to_float(value, default: float, decimals: int = 1) -> float:
                if value is None:
                    return default
                try:
                    return round(float(value), decimals)
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
                    "credit": 0,
                    "money": 0.0,
                    "life": 100,
                    "iq": 100,
                    "energy": 100,
                    "move": 100,
                    "exp": 0
                }

            return {
                "level": _to_int(config.level, 3),
                "credit": _to_int(config.credit, 0),
                "money": _to_float(config.money, 0.0, 2),
                "life": _to_int(config.life_point, 100),
                "iq": _to_int(config.iq_point, 100),
                "energy": _to_int(config.energy_point, 100),
                "move": _to_float(config.move_point, 100.0),
                "exp": _to_int(config.exp_point, 0)
            }
        except Exception as e:
            logger.error(f"Error getting user stats: {e}")
            # Return default values on error
            return {
                "level": 3,
                "credit": 0,
                "money": 0.0,
                "life": 100,
                "iq": 100,
                "energy": 100,
                "move": 100,
                "exp": 0
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
            to_account = (to_account or "").strip()
            if (not to_account) or ("@" not in to_account):
                return {
                    "success": False,
                    "message": "Invalid XMPP account. Expected a full JID like user@domain.",
                }

            # Get XMPP client
            xmpp_manager = XMPPClientManager.get_instance()
            client = xmpp_manager.get_client()

            if not client or not client.is_client_connected():
                return {
                    "success": False,
                    "message": "XMPP client not connected"
                }

            # Send message via XMPP (async: includes subscription check)
            await client.send_message_to_jid(to_account, content)

            stored_content = format_internal_xmpp_message_for_storage(content)

            # Save to database
            config = self.db.query(AiChatCfg).filter(
                AiChatCfg.is_delete == False
            ).first()

            if config:
                from db.write_queue import db_write
                _config_account = config.account
                _config_nickname = config.nickname or config.account
                _to_account = to_account
                _stored_content = stored_content

                def _save_sent_msg(session):
                    msg = AIChatMessages(
                        conversation_id=f"{_config_account}_{_to_account}",
                        flag=0,  # 0=send
                        content=_stored_content,
                        owner_account=_config_account,
                        friend_account=_to_account,
                        owner_name=_config_nickname,
                        friend_name=_to_account
                    )
                    session.add(msg)
                db_write(_save_sent_msg, description="service_sync_send_message")

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
            to_account = (to_account or "").strip()
            if (not to_account) or ("@" not in to_account):
                return {
                    "success": False,
                    "message": "Invalid XMPP account. Expected a full JID like user@domain.",
                }

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
                    from db.write_queue import db_write
                    file_message = f"📎 File: {file.filename}\n{url}"
                    stored_file_message = format_internal_xmpp_message_for_storage(file_message)
                    _ca = config.account
                    _cn = config.nickname or config.account
                    _ta = to_account
                    _sfm = stored_file_message
                    _fn = file.filename
                    def _save_file_msg(session):
                        msg = AIChatMessages(
                            conversation_id=f"{_ca}_{_ta}",
                            flag=0,
                            content=_sfm,
                            attachment_list=_fn,
                            owner_account=_ca,
                            friend_account=_ta,
                            owner_name=_cn,
                            friend_name=_ta
                        )
                        session.add(msg)
                    db_write(_save_file_msg, description="service_sync_send_file")

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

            # Import the AI social engine
            from backend.apps.sns.ai_social_engine import AISocialEngine

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

            # Update fields via write queue
            from db.write_queue import db_write
            _config_id = config.id
            _data = {k: v for k, v in data.items() if v is not None}
            def _update_cfg(session):
                rec = session.query(AiChatCfg).filter_by(id=_config_id).first()
                if rec:
                    for key, value in _data.items():
                        if hasattr(rec, key):
                            setattr(rec, key, value)
            db_write(_update_cfg, description="service_sync_update_ai_chat_config")
            self.db.expire_all()
            config = query.first()

            return {"success": True, "message": "Configuration updated successfully", "data": config}
        except Exception as e:
            logger.error(f"Error updating AI chat config: {e}")
            return {"success": False, "message": str(e)}

    async def upload_avatar(self, user_id: str = None, file=None):
        """Upload avatar image"""
        try:
            from backend.modules.system.service import SystemInitWizardService

            file_ext = Path(file.filename or '').suffix.lower()
            if file_ext not in ('.png', '.jpg', '.jpeg', '.bmp', '.webp'):
                file_ext = '.png'

            file_id = str(uuid.uuid4())
            filename = f"{file_id}{file_ext}"

            content = await file.read()
            SystemInitWizardService._save_uploaded_avatar(content, filename)
            avatar_map_filename = SystemInitWizardService._generate_avatar_map(filename)

            # Update config
            query = self.db.query(AiChatCfg).filter(AiChatCfg.is_delete == False)
            if user_id:
                query = query.filter(AiChatCfg.user_id == user_id)

            config = query.first()
            if config:
                from db.write_queue import db_write
                _config_id = config.id
                _filename = filename
                def _set_avatar(session):
                    rec = session.query(AiChatCfg).filter_by(id=_config_id).first()
                    if rec:
                        rec.avatar = _filename
                db_write(_set_avatar, description="service_sync_upload_avatar")

            return {
                "success": True,
                "message": "Avatar uploaded successfully",
                "avatar_url": f"/images/avatars/{filename}",
                "avatar": filename,
                "avatar_map": avatar_map_filename,
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
                    "nationid": getattr(config, 'nationid', None),
                    "nickname": config.nickname,
                    "sign": config.sign,
                    "sns_url": config.sns_url,
                    "agent_id": getattr(config, 'agent_id', None),
                    "profession": getattr(config, 'profession', None),
                    "money": getattr(config, 'money', None),
                    "current_position": getattr(config, 'current_position', None),
                    "current_place": getattr(config, 'current_place', None),
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
                if hasattr(config, 'agent_id'):
                    config.agent_id = data['agent_id']

            from db.write_queue import db_write
            _config_id = config.id
            _updates = {}
            if 'nickname' in data:
                _updates['nickname'] = data['nickname']
            if 'sign' in data:
                _updates['sign'] = data['sign']
            if 'sns_url' in data:
                _updates['sns_url'] = data['sns_url']
            if 'agent_id' in data and hasattr(config, 'agent_id'):
                _updates['agent_id'] = data['agent_id']
            def _update_info(session):
                rec = session.query(AiChatCfg).filter_by(id=_config_id).first()
                if rec:
                    for k, v in _updates.items():
                        setattr(rec, k, v)
            db_write(_update_info, description="service_sync_update_user_info")
            return {"success": True, "message": "User info updated successfully"}
        except Exception as e:
            logger.error(f"Error updating user info: {e}")
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

            map_type = str(data.get('map_type', '0')).strip() or '0'
            google_api_key = str(data.get('google_api_key', '') or '').strip()
            google_map_id = str(data.get('google_map_id', '') or '').strip()
            baidu_api_key = str(data.get('baidu_api_key', '') or '').strip()

            if map_type == '0':
                if (not google_api_key) or google_api_key == GOOGLE_KEY_PLACEHOLDER:
                    return {"success": False, "message": "Google Maps API key is required."}
                if (not google_map_id) or google_map_id == GOOGLE_MAP_ID_PLACEHOLDER:
                    return {"success": False, "message": "Google map ID is required."}

                map_api_key = f"{google_api_key},{BAIDU_KEY_PLACEHOLDER}"
                map_id = f"{google_map_id},{BAIDU_MAP_ID_SENTINEL}"
            else:
                if (not baidu_api_key) or baidu_api_key == BAIDU_KEY_PLACEHOLDER:
                    return {"success": False, "message": "Baidu Maps API key is required."}

                map_api_key = f"{GOOGLE_KEY_PLACEHOLDER},{baidu_api_key}"
                map_id = f"{GOOGLE_MAP_ID_PLACEHOLDER},{BAIDU_MAP_ID_SENTINEL}"

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

            from db.write_queue import db_write
            import copy
            _config_id = config.id
            _updates = {
                'map_type': config.map_type,
                'map_api_key': config.map_api_key,
                'map_id': config.map_id,
            }
            if hasattr(config, 'memo'):
                _updates['memo'] = config.memo
            if map_type_changing:
                _updates['route_start'] = config.route_start
                _updates['route_end'] = config.route_end
                _updates['route_current_position'] = config.route_current_position
                _updates['route'] = config.route
                _updates['route_status'] = config.route_status
                _updates['home_position'] = config.home_position
                _updates['positionx'] = config.positionx
                _updates['positiony'] = config.positiony
                _updates['positionz'] = config.positionz

            def _update_map(session):
                rec = session.query(AiChatCfg).filter_by(id=_config_id).first()
                if rec:
                    for k, v in _updates.items():
                        setattr(rec, k, v)
            db_write(_update_map, description="service_sync_update_map_config")

            # Replace in files (best-effort)
            try:
                replace_map_config_in_files(
                    old_api_keys,
                    old_map_ids,
                    map_api_key.split(',') if map_api_key else ['', ''],
                    map_id.split(',') if map_id else ['', ''],
                    logger,
                )
            except Exception as e:
                logger.error("Failed to update local map files: %s", e)

            return {"success": True, "message": "Map config updated successfully"}
        except Exception as e:
            logger.error(f"Error updating map config: {e}")
            return {"success": False, "message": str(e)}

    def _replace_map_config_in_files(self, old_api_keys, old_map_ids, new_api_keys, new_map_ids):
        """Backward compatible wrapper."""
        replace_map_config_in_files(old_api_keys, old_map_ids, new_api_keys, new_map_ids, logger)
