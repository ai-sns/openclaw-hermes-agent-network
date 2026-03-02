"""SNS Module - Business Logic Service - Async version."""
import asyncio
import logging
import os
import uuid
import base64
import requests
import httpx
from datetime import datetime
from pathlib import Path
import json
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, or_
from sqlalchemy.orm import Session
from typing import List, Optional
from fastapi import HTTPException
from backend.database.models.chat import AIFriend, AIChatMessages, AiChatCfg
from backend.database.models.system import Prompt
from backend.database.models.system import SystemCfg
from backend.apps.sns.xmpp_client import XMPPClientManager
from backend.config.database import get_db_sync
from backend.shared.websocket_manager import manager as websocket_manager

logger = logging.getLogger(__name__)

UPLOAD_DIR = Path("uploads/sns_files")
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

AVATAR_DIR = Path("uploads/avatars")
AVATAR_DIR.mkdir(parents=True, exist_ok=True)

_social_engine_instance = None
_social_engine_running = False
_social_engine_op_lock = asyncio.Lock()


def apply_runtime_system_config(payload: dict) -> bool:
    global _social_engine_instance

    if not isinstance(payload, dict) or _social_engine_instance is None:
        return False

    changed = False
    for k in ("conversation_timeout_seconds", "contact_cooldown_seconds", "contact_recent_limit"):
        if k in payload and payload[k] is not None:
            try:
                v = int(payload[k])
            except (TypeError, ValueError):
                continue
            try:
                setattr(_social_engine_instance, k, v)
                changed = True
            except Exception:
                continue

    try:
        if changed and hasattr(_social_engine_instance, "_ensure_conversation_timeout_task"):
            active = getattr(_social_engine_instance, "active_conversation", None) or {}
            if (active.get("account") or "").strip():
                _social_engine_instance._ensure_conversation_timeout_task()
    except Exception:
        pass

    return changed


class SNSService:
    """SNS service for handling social network operations - async version."""

    def __init__(self, db: AsyncSession):
        self.db = db

    @staticmethod
    def _normalize_attachment_content(filename: str, content: bytes) -> bytes:
        """Normalize text attachments to UTF-8 to avoid mojibake on receiver side."""
        suffix = Path(filename or "").suffix.lower()
        if suffix != '.txt':
            return content

        # Try common encodings for Chinese text files, then store as UTF-8.
        for encoding in ('utf-8-sig', 'utf-8', 'gb18030', 'gbk', 'big5'):
            try:
                text = content.decode(encoding)
                return text.encode('utf-8-sig')
            except UnicodeDecodeError:
                continue

        # Fallback to loss-tolerant decode/encode to keep file readable as much as possible.
        return content.decode('utf-8', errors='replace').encode('utf-8-sig')

    async def _get_latest_user_config(self) -> Optional[AiChatCfg]:
        stmt = (
            select(AiChatCfg)
            .where(AiChatCfg.is_delete == False)
            .order_by(AiChatCfg.id.desc())
            .limit(1)
        )
        result = await self.db.execute(stmt)
        return result.scalars().first()

    @staticmethod
    def _parse_position(raw_value):
        if not raw_value:
            return None, None

        if isinstance(raw_value, (list, tuple)) and len(raw_value) >= 2:
            try:
                return float(raw_value[0]), float(raw_value[1])
            except (TypeError, ValueError):
                return raw_value[0], raw_value[1]

        if isinstance(raw_value, dict):
            return raw_value.get('lng'), raw_value.get('lat')

        if isinstance(raw_value, str):
            v = raw_value.strip()
            try:
                import json

                parsed = json.loads(v)
                if isinstance(parsed, (list, tuple)) and len(parsed) >= 2:
                    return float(parsed[0]), float(parsed[1])
                if isinstance(parsed, dict):
                    return parsed.get('lng'), parsed.get('lat')
            except Exception:
                pass

            try:
                import ast

                parsed = ast.literal_eval(v)
                if isinstance(parsed, (list, tuple)) and len(parsed) >= 2:
                    return float(parsed[0]), float(parsed[1])
            except Exception:
                pass

            import re

            nums = re.findall(r"[-+]?\d*\.?\d+", v)
            if len(nums) >= 2:
                try:
                    return float(nums[0]), float(nums[1])
                except (TypeError, ValueError):
                    return nums[0], nums[1]

        return None, None

    async def get_user_stats(self) -> dict:
        """Get user stats asynchronously."""
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

            config = await self._get_latest_user_config()

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
                "life": _to_int(config.life_point, 125),
                "iq": config.iq_point or 70,
                "energy": _to_int(config.energy_point, 150),
                "move": _to_float(config.move_point, 187.5),
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
        """Get contact list asynchronously."""
        try:
            config = await self._get_latest_user_config()

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
        """Get chat history asynchronously."""
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
                stmt_friend = select(AIFriend).where(
                    AIFriend.is_delete == False,
                    AIFriend.owner_sns_account == config.account,
                    AIFriend.account == to_account,
                )
                result_friend = await self.db.execute(stmt_friend)
                friend = result_friend.scalar_one_or_none()

                if friend:
                    if not friend.nick_name:
                        friend.nick_name = to_account
                else:
                    friend = AIFriend(
                        account=to_account,
                        nick_name=to_account,
                        groups="",
                        owner_sns_account=config.account,
                        subscription="none",
                        new_message_flag=False,
                        last_message_time=datetime.now(),
                    )
                    self.db.add(friend)

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

                friend.last_message_time = datetime.now()
                await self.db.commit()

                contact_payload = {
                    'account': friend.account,
                    'nick_name': friend.nick_name or friend.account,
                    'new_message_flag': bool(friend.new_message_flag),
                    'last_message_time': friend.last_message_time.isoformat() if friend.last_message_time else None,
                }

                await websocket_manager.broadcast({
                    'type': 'contact_upserted',
                    'data': contact_payload
                })

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
            content = self._normalize_attachment_content(file.filename, content)
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
                    stmt_friend = select(AIFriend).where(
                        AIFriend.is_delete == False,
                        AIFriend.owner_sns_account == config.account,
                        AIFriend.account == to_account,
                    )
                    result_friend = await self.db.execute(stmt_friend)
                    friend = result_friend.scalar_one_or_none()

                    if friend:
                        if not friend.nick_name:
                            friend.nick_name = to_account
                    else:
                        friend = AIFriend(
                            account=to_account,
                            nick_name=to_account,
                            groups="",
                            owner_sns_account=config.account,
                            subscription="none",
                            new_message_flag=False,
                            last_message_time=datetime.now(),
                        )
                        self.db.add(friend)

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

                    friend.last_message_time = datetime.now()
                    await self.db.commit()

                    contact_payload = {
                        'account': friend.account,
                        'nick_name': friend.nick_name or friend.account,
                        'new_message_flag': bool(friend.new_message_flag),
                        'last_message_time': friend.last_message_time.isoformat() if friend.last_message_time else None,
                    }

                    await websocket_manager.broadcast({
                        'type': 'contact_upserted',
                        'data': contact_payload
                    })

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

        async with _social_engine_op_lock:
            try:
                if _social_engine_running:
                    return {
                        "success": True,
                        "message": "AI Social Engine is already running",
                        "running": True
                    }

                from backend.apps.sns.ai_social_engine import AISocialEngine

                if _social_engine_instance is None:
                    # Create a sync Session for AISocialEngine
                    db_sync = get_db_sync()
                    _social_engine_instance = AISocialEngine(db_sync)
                    await _social_engine_instance.async_init()

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


    async def stop_social_engine(self) -> dict:
        """Stop the AI social engine"""
        global _social_engine_instance, _social_engine_running

        async with _social_engine_op_lock:
            try:
                if _social_engine_instance is None:
                    _social_engine_running = False
                    return {
                        "success": True,
                        "message": "AI Social Engine is already stopped",
                        "running": False
                    }

                result = await _social_engine_instance.stop_engine()
                _social_engine_running = False

                payload = {
                    "success": bool(result.get("success", True)) if isinstance(result, dict) else True,
                    "message": result.get("message") if isinstance(result, dict) else "AI Social Engine stopped",
                    "running": False,
                }
                if isinstance(result, dict):
                    payload.update({k: v for k, v in result.items() if k not in payload})
                return payload

            except Exception as e:
                logger.error(f"Error stopping AI social engine: {e}")
                _social_engine_running = False
                return {
                    "success": False,
                    "message": f"Failed to stop AI Social Engine: {str(e)}",
                    "running": False
                }


    async def restart_social_engine(self) -> dict:
        """Restart the AI social engine"""
        global _social_engine_instance, _social_engine_running

        async with _social_engine_op_lock:
            try:
                from backend.apps.sns.ai_social_engine import AISocialEngine

                if _social_engine_instance is None:
                    db_sync = get_db_sync()
                    _social_engine_instance = AISocialEngine(db_sync)
                    await _social_engine_instance.async_init()

                result = await _social_engine_instance.restart_engine()
                _social_engine_running = True

                payload = {
                    "success": bool(result.get("success", True)) if isinstance(result, dict) else True,
                    "message": result.get("message") if isinstance(result, dict) else "AI Social Engine restarted",
                    "running": True,
                }
                if isinstance(result, dict):
                    payload.update({k: v for k, v in result.items() if k not in payload})
                return payload

            except Exception as e:
                logger.error(f"Error restarting AI social engine: {e}")
                _social_engine_running = False
                return {
                    "success": False,
                    "message": f"Failed to restart AI Social Engine: {str(e)}",
                    "running": False
                }


    async def pause_social_engine(self) -> dict:
        """Pause the AI social engine"""
        global _social_engine_instance, _social_engine_running

        try:
            if not _social_engine_running or _social_engine_instance is None:
                return {
                    "success": False,
                    "message": "AI Social Engine is not running",
                    "status": "not_running"
                }

            result = await _social_engine_instance.pause_engine()
            return result

        except Exception as e:
            logger.error(f"Error pausing AI social engine: {e}")
            return {
                "success": False,
                "message": f"Failed to pause AI Social Engine: {str(e)}",
                "status": "error"
            }

    async def resume_social_engine(self) -> dict:
        """Resume the AI social engine"""
        global _social_engine_instance, _social_engine_running

        try:
            if not _social_engine_running or _social_engine_instance is None:
                return {
                    "success": False,
                    "message": "AI Social Engine is not running",
                    "status": "not_running"
                }

            result = await _social_engine_instance.resume_engine()
            return result

        except Exception as e:
            logger.error(f"Error resuming AI social engine: {e}")
            return {
                "success": False,
                "message": f"Failed to resume AI Social Engine: {str(e)}",
                "status": "error"
            }


    async def get_social_engine_status(self) -> dict:
        global _social_engine_instance, _social_engine_running

        started_flag = False
        task_status = None
        try:
            if _social_engine_instance is not None:
                started_flag = bool(getattr(_social_engine_instance, "started_flag", False))
                task_status = getattr(_social_engine_instance, "map_task_status", None)
        except Exception:
            started_flag = False
            task_status = None

        return {
            "success": True,
            "running": bool(_social_engine_running),
            "started": started_flag,
            "task_status": task_status,
        }


    async def set_human_control_state(self, human_take_over: bool, human_talk_type: int = None) -> dict:
        global _social_engine_instance

        if _social_engine_instance is None:
            return {
                "success": False,
                "message": "AI Social Engine is not initialized"
            }

        prev_take_over = bool(getattr(_social_engine_instance, "human_take_over", False))
        _social_engine_instance.human_take_over = bool(human_take_over)
        if human_talk_type is not None:
            _social_engine_instance.human_talk_type = int(human_talk_type)

        # If we are exiting control mode, resume normal task processing.
        if prev_take_over and not _social_engine_instance.human_take_over:
            try:
                started_flag = bool(getattr(_social_engine_instance, "started_flag", False))
                map_task_status = getattr(_social_engine_instance, "map_task_status", None)
                taskmng = getattr(_social_engine_instance, "taskmng", None)

                if started_flag and map_task_status == "started" and taskmng is not None:
                    ask_content = getattr(taskmng, "current_situation", "") or getattr(taskmng, "current_objective", "")
                    logger.info("Exiting human control mode: resuming task processing")
                    asyncio.create_task(taskmng.process_task(action="process_activity", ask_content=ask_content))
            except Exception as e:
                logger.error(f"Failed to resume task processing after exiting human control mode: {e}")

        return {
            "success": True,
            "message": "Human control state updated",
            "data": {
                "human_take_over": _social_engine_instance.human_take_over,
                "human_talk_type": _social_engine_instance.human_talk_type
            }
        }

    async def send_human_message(self, message: str) -> dict:
        global _social_engine_instance

        if _social_engine_instance is None:
            return {
                "success": False,
                "message": "AI Social Engine is not initialized"
            }

        _social_engine_instance.human_message_received(message)
        return {
            "success": True,
            "message": "Human message received"
        }

    async def get_ai_chat_config(self, user_id: str = None):
        """Get AI chat configuration"""
        try:
            stmt = (
                select(AiChatCfg)
                .where(AiChatCfg.is_delete == False)
                .order_by(AiChatCfg.id.desc())
                .limit(1)
            )
            if user_id:
                stmt = stmt.where(AiChatCfg.user_id == user_id)

            result = await self.db.execute(stmt)
            config = result.scalars().first()
            if not config:
                raise HTTPException(status_code=404, detail="Configuration not found")

            return config
        except Exception as e:
            logger.error(f"Error getting AI chat config: {e}")
            raise

    async def update_ai_chat_config(self, user_id: str = None, data: dict = None):
        """Update AI chat configuration"""
        try:
            stmt = (
                select(AiChatCfg)
                .where(AiChatCfg.is_delete == False)
                .order_by(AiChatCfg.id.desc())
                .limit(1)
            )
            if user_id:
                stmt = stmt.where(AiChatCfg.user_id == user_id)

            result = await self.db.execute(stmt)
            config = result.scalars().first()
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

            stmt = (
                select(AiChatCfg)
                .where(AiChatCfg.is_delete == False)
                .order_by(AiChatCfg.id.desc())
                .limit(1)
            )
            if user_id:
                stmt = stmt.where(AiChatCfg.user_id == user_id)

            result = await self.db.execute(stmt)
            config = result.scalars().first()
            if not config:
                config = AiChatCfg(user_id=user_id)
                self.db.add(config)

            config.avatar = avatar_data

            memo_raw = getattr(config, 'memo', None)
            memo_obj = {}
            if isinstance(memo_raw, str) and memo_raw.strip():
                try:
                    memo_obj = json.loads(memo_raw)
                except Exception:
                    memo_obj = {}
            if not isinstance(memo_obj, dict):
                memo_obj = {}
            memo_obj['avatar_file'] = filename
            memo_obj['avatar_map'] = avatar_map_filename
            try:
                config.memo = json.dumps(memo_obj, ensure_ascii=False)
            except Exception:
                # Keep avatar update even if memo serialization fails.
                pass

            await self.db.commit()
            await self.db.refresh(config)

            return {
                "success": True,
                "message": "Avatar uploaded successfully",
                "avatar_url": f"/uploads/avatars/{filename}",
                "avatar_data": avatar_data
            }
        except Exception as e:
            logger.error(f"Error uploading avatar: {e}")
            return {"success": False, "message": str(e)}

    async def upload_avatar_dialog(self, file) -> dict:
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

            avatar_data = f"data:image/{file_ext[1:]};base64,{base64.b64encode(content).decode()}"

            stmt = (
                select(AiChatCfg)
                .where(AiChatCfg.is_delete == False)
                .order_by(AiChatCfg.id.desc())
                .limit(1)
            )
            result = await self.db.execute(stmt)
            config = result.scalars().first()
            if not config:
                config = AiChatCfg(user_id=None)
                self.db.add(config)

            config.avatar = avatar_data
            await self.db.commit()
            await self.db.refresh(config)

            return {
                'success': True,
                'data': {
                    'avatar': filename,
                    'avatar_map': avatar_map_filename,
                    'avatar_data': avatar_data,
                }
            }
        except Exception as e:
            logger.error("Avatar dialog upload failed: %s", e)
            try:
                await self.db.rollback()
            except Exception:
                pass
            return {'success': False, 'message': str(e)}

    async def submit_avatar_dialog(self, payload: dict) -> dict:
        try:
            avatar_map = (payload.get('avatar_map') or '').strip()
            avatar3d = (payload.get('avatar3d') or payload.get('avatar_3d') or '').strip()
            nickname = (payload.get('nickname') or payload.get('nick_name') or '').strip()
            profile = (payload.get('profile') or '').strip()
            sns_url = (payload.get('sns_url') or '').strip()

            if not avatar3d:
                return {'success': False, 'message': 'avatar3d is required'}

            stmt = (
                select(AiChatCfg)
                .where(AiChatCfg.is_delete == False)
                .order_by(AiChatCfg.id.desc())
                .limit(1)
            )
            result = await self.db.execute(stmt)
            config = result.scalars().first()
            if not config:
                return {'success': False, 'message': 'No user config found'}

            if not avatar_map:
                memo_raw = getattr(config, 'memo', None)
                if isinstance(memo_raw, str) and memo_raw.strip():
                    try:
                        memo_obj = json.loads(memo_raw)
                        if isinstance(memo_obj, dict) and memo_obj.get('avatar_map'):
                            avatar_map = str(memo_obj.get('avatar_map')).strip()
                    except Exception:
                        pass

            if not avatar_map:
                return {'success': False, 'message': 'avatar_map is required'}

            nationid = (getattr(config, 'nationid', None) or '').strip()
            nationpassword = (getattr(config, 'nationpassword', None) or '').strip()
            if not nationid:
                return {'success': False, 'message': 'nationid is not configured'}
            if not nationpassword:
                return {'success': False, 'message': 'nationpassword is not configured'}

            nickname = nickname or (getattr(config, 'nickname', None) or '')
            profile = profile or (getattr(config, 'sign', None) or '')
            sns_url = sns_url or (getattr(config, 'sns_url', None) or '')

            config.avatar3d = avatar3d
            if nickname:
                config.nickname = nickname
            if profile:
                config.sign = profile
            config.sns_url = sns_url
            await self.db.commit()

            cfg_stmt = (
                select(SystemCfg)
                .where(SystemCfg.is_delete == False)
                .order_by(SystemCfg.id.asc())
                .limit(1)
            )
            cfg_result = await self.db.execute(cfg_stmt)
            system_cfg = cfg_result.scalars().first()
            base = (getattr(system_cfg, 'ai_sns_server', None) or '').strip().rstrip('/') if system_cfg else ''
            if not base:
                return {'success': False, 'message': 'ai_sns_server is not configured'}

            avatar_map_path = Path('images') / 'avatars' / avatar_map
            if not avatar_map_path.exists():
                return {'success': False, 'message': f'avatar_map file not found: {avatar_map}'}

            async with httpx.AsyncClient(timeout=60.0) as client:
                files = {
                    'avatar_file': (avatar_map_path.name, avatar_map_path.read_bytes(), 'image/png')
                }
                upload_resp = await client.post(
                    f"{base}/api/upload_avatar/",
                    data={'nation_id': nationid},
                    files=files,
                )
                if upload_resp.status_code not in (200, 201):
                    return {
                        'success': False,
                        'message': f"Remote avatar upload failed: {upload_resp.status_code} - {upload_resp.text}",
                    }

                update_resp = await client.post(
                    f"{base}/api/update-user/",
                    data={
                        'nation_id': nationid,
                        'password': nationpassword,
                        'nick_name': nickname,
                        'avatar_3d': avatar3d,
                        'profile': profile,
                        'sns_url': sns_url,
                    },
                )
                if update_resp.status_code not in (200, 201):
                    return {
                        'success': False,
                        'message': f"Remote profile update failed: {update_resp.status_code} - {update_resp.text}",
                    }

            return {
                'success': True,
                'data': {
                    'nationid': nationid,
                }
            }
        except Exception as e:
            logger.error("Avatar dialog submit failed: %s", e)
            try:
                await self.db.rollback()
            except Exception:
                pass
            return {'success': False, 'message': str(e)}

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

    async def get_social_role_by_id(self, role_id: int):
        """Get a specific social role by ID"""
        try:
            stmt = select(Prompt).where(Prompt.id == role_id)
            result = await self.db.execute(stmt)
            prompt = result.scalar_one_or_none()
            return prompt
        except Exception as e:
            logger.error(f"Error getting social role by ID: {e}")
            return None

    async def update_social_role(self, role_id: int, data: dict):
        """Update a social role"""
        try:
            stmt = select(Prompt).where(Prompt.id == role_id)
            result = await self.db.execute(stmt)
            prompt = result.scalar_one_or_none()

            if not prompt:
                return {"success": False, "message": "Social role not found"}

            # Update fields
            if "caption" in data:
                prompt.caption = data["caption"]
            if "content" in data:
                prompt.content = data["content"]
            if "question" in data:
                prompt.question = data["question"]
            if "tags" in data:
                prompt.tags = data["tags"]

            await self.db.commit()
            await self.db.refresh(prompt)

            return {
                "success": True,
                "message": "Social role updated successfully",
                "data": {
                    "id": prompt.id,
                    "caption": getattr(prompt, "caption", None),
                    "content": getattr(prompt, "content", None),
                    "question": getattr(prompt, "question", None),
                    "tags": getattr(prompt, "tags", None),
                }
            }
        except Exception as e:
            await self.db.rollback()
            logger.error(f"Error updating social role: {e}")
            return {"success": False, "message": str(e)}

    async def delete_social_role(self, role_id: int):
        """Delete a social role"""
        try:
            stmt = select(Prompt).where(Prompt.id == role_id)
            result = await self.db.execute(stmt)
            prompt = result.scalar_one_or_none()

            if not prompt:
                return {"success": False, "message": "Social role not found"}

            await self.db.delete(prompt)
            await self.db.commit()

            return {"success": True, "message": "Social role deleted successfully"}
        except Exception as e:
            await self.db.rollback()
            logger.error(f"Error deleting social role: {e}")
            return {"success": False, "message": str(e)}

    async def get_user_info(self):
        """Get user information from aichat_cfg"""
        try:
            config = await self._get_latest_user_config()

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
                    "handle_after_trade": getattr(config, 'handle_after_trade', None),
                    "handle_content": getattr(config, 'handle_content', None),
                    "goods_or_service_description": getattr(config, 'goods_or_service_description', None),
                    "goods_or_service_price": getattr(config, 'goods_or_service_price', None),
                    "money": getattr(config, 'money', None),
                    "current_position": getattr(config, 'current_position', None),
                    "current_place": getattr(config, 'current_place', None),
                }
            }
        except Exception as e:
            logger.error(f"Error getting user info: {e}")
            return {"success": False, "message": str(e)}

    async def get_resource_overview(self):
        """Build Resource tab overview content without starting the social engine."""
        try:
            config = await self._get_latest_user_config()

            if not config:
                return {"success": False, "message": "No user config found", "content": ""}

            base = ''
            try:
                stmt_cfg = (
                    select(SystemCfg)
                    .where(SystemCfg.is_delete == False)
                    .order_by(SystemCfg.id.asc())
                    .limit(1)
                )
                cfg_result = await self.db.execute(stmt_cfg)
                cfg = cfg_result.scalars().first()
                base = (getattr(cfg, 'ai_sns_server', None) or '').strip().rstrip('/') if cfg else ''
            except Exception:
                base = ''

            if not base:
                return {"success": False, "message": "ai_sns_server is not configured", "content": ""}

            lng, lat = self._parse_position(getattr(config, 'current_position', None))
            if lng is None or lat is None:
                return {"success": False, "message": "current_position is not set", "content": ""}

            try:
                lng = float(lng)
                lat = float(lat)
            except (TypeError, ValueError):
                return {"success": False, "message": "current_position is invalid", "content": ""}

            try:
                from backend.apps.sns.mixin.tools_mixin import ToolsMixin
                from backend.apps.sns.mixin.data_query_mixin import DataQueryMixin

                class _RemoteListAdapter(ToolsMixin, DataQueryMixin):
                    def __init__(self, *, base_url: str, position: list, nationid: str):
                        self._base_url = (base_url or '').strip().rstrip('/')
                        self.user_map_setting = {
                            "nationid": (nationid or '').strip(),
                            "nation_id": (nationid or '').strip(),
                        }

                        class _Cfg:
                            pass

                        self.aichatcfg_record = _Cfg()
                        self.aichatcfg_record.current_position = position

                    def _get_ai_sns_server_base(self):
                        return self._base_url

                adapter = _RemoteListAdapter(
                    base_url=base,
                    position=[lng, lat],
                    nationid=(getattr(config, 'nationid', None) or ''),
                )

                service_list = adapter.get_service_list() or []
                people_list = adapter.get_people_list() or []
                place_list = adapter.get_place_list() or []
            except Exception as e:
                logger.warning("Resource overview list fetch failed: %s", e)
                service_list, people_list, place_list = [], [], []

            from backend.apps.sns.mixin.ui_display_mixin import UIDisplayMixin

            class _Formatter(UIDisplayMixin):
                pass

            formatted = _Formatter()._format_resource_content(service_list, people_list, place_list)
            return {"success": True, "content": (formatted or '').strip()}
        except Exception as e:
            logger.error(f"Error building resource overview: {e}")
            return {"success": False, "message": str(e), "content": ""}

    async def get_current_status_overview(self):
        """Build Current Status content without starting the social engine."""
        try:
            config = await self._get_latest_user_config()
            if not config:
                return {"success": False, "message": "No user config found", "content": ""}

            profession = getattr(config, 'profession', None) or 'N/A'
            lng, lat = self._parse_position(getattr(config, 'current_position', None))
            if lng is None or lat is None:
                lng, lat = 'N/A', 'N/A'

            money = getattr(config, 'money', None)
            try:
                money_value = float(money) if money is not None else None
            except (TypeError, ValueError):
                money_value = None

            lines = []
            if money_value is not None:
                lines.append(f"💰 Money      : {money_value:,.2f}")
            else:
                lines.append("💰 Money      : N/A")

            lines.append(f"❤️ Life           : {getattr(config, 'life_point', None) if getattr(config, 'life_point', None) is not None else 'N/A'}")
            lines.append(f"⚡ Energy      : {getattr(config, 'energy_point', None) if getattr(config, 'energy_point', None) is not None else 'N/A'}")
            lines.append(f"🧑‍️ Profession: {profession}")
            lines.append("📍 Location")
            lines.append(f"   ├─ lng : {lng}")
            lines.append(f"   └─ lat : {lat}")

            return {"success": True, "content": "\n".join(lines)}
        except Exception as e:
            logger.error(f"Error building current status overview: {e}")
            return {"success": False, "message": str(e), "content": ""}

    async def _sync_profession_to_remote(self, nationid: str, nationpassword: str, profession: str) -> Optional[str]:
        try:
            cfg_stmt = (
                select(SystemCfg)
                .where(SystemCfg.is_delete == False)
                .order_by(SystemCfg.id.asc())
                .limit(1)
            )
            cfg_result = await self.db.execute(cfg_stmt)
            system_cfg = cfg_result.scalars().first()
            base = (getattr(system_cfg, 'ai_sns_server', None) or '').strip().rstrip('/') if system_cfg else ''
            if not base:
                return 'ai_sns_server is not configured'

            async with httpx.AsyncClient(timeout=60.0) as client:
                resp = await client.post(
                    f"{base}/api/update-profession/",
                    data={
                        'nation_id': nationid,
                        'password': nationpassword,
                        'profession': profession,
                    },
                )
                if resp.status_code not in (200, 201):
                    return f"Remote profession update failed: {resp.status_code} - {resp.text}"
            return None
        except Exception as e:
            return str(e)

    async def change_nationpassword(self, data: dict) -> dict:
        try:
            new_password = (data.get('new_password') if isinstance(data, dict) else None) or ''
            new_password = str(new_password).strip()
            if not new_password:
                return {"success": False, "message": "new_password is required"}

            config = await self._get_latest_user_config()
            if not config:
                return {"success": False, "message": "No user config found"}

            nationid = (getattr(config, 'nationid', None) or '').strip()
            old_password = (getattr(config, 'nationpassword', None) or '').strip()
            if not nationid:
                return {"success": False, "message": "nationid is not configured"}
            if not old_password:
                return {"success": False, "message": "nationpassword is not configured"}

            cfg_stmt = (
                select(SystemCfg)
                .where(SystemCfg.is_delete == False)
                .order_by(SystemCfg.id.asc())
                .limit(1)
            )
            cfg_result = await self.db.execute(cfg_stmt)
            system_cfg = cfg_result.scalars().first()
            base = (getattr(system_cfg, 'ai_sns_server', None) or '').strip().rstrip('/') if system_cfg else ''
            if not base:
                return {"success": False, "message": "ai_sns_server is not configured"}

            async with httpx.AsyncClient(timeout=60.0) as client:
                resp = await client.post(
                    f"{base}/api/change-password/",
                    data={
                        'nation_id': nationid,
                        'old_password': old_password,
                        'new_password': new_password,
                    },
                )
                if resp.status_code not in (200, 201):
                    await self.db.rollback()
                    return {
                        "success": False,
                        "message": f"Remote password change failed: {resp.status_code} - {resp.text}",
                    }

                try:
                    body = resp.json()
                    if isinstance(body, dict) and body.get('success') is False:
                        await self.db.rollback()
                        return {"success": False, "message": str(body.get('message') or 'Remote password change failed')}
                except Exception:
                    pass

            config.nationpassword = new_password
            await self.db.commit()
            return {"success": True, "message": "Nation password updated successfully"}
        except Exception as e:
            logger.error(f"Error changing nation password: {e}")
            await self.db.rollback()
            return {"success": False, "message": str(e)}

    async def update_user_info(self, data: dict):
        """Update user information in aichat_cfg"""
        try:
            config = await self._get_latest_user_config()

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

            profession_costs = {
                "Doctor": 800,
                "Restaurateur": 800
            }

            deducted = 0.0
            profession_changed = False
            new_profession = None
            if 'profession' in data:
                new_profession = data.get('profession')
                old_profession = getattr(config, 'profession', None)

                if new_profession != old_profession:
                    profession_changed = True
                    cost = float(profession_costs.get(new_profession, 0) or 0)
                    if cost > 0:
                        current_money = float(getattr(config, 'money', 0) or 0)
                        if current_money < cost:
                            return {
                                "success": False,
                                "message": f"Insufficient balance. Selecting this profession requires {int(cost)}."
                            }

                        config.money = current_money - cost
                        deducted = cost

                config.profession = new_profession

            if 'handle_after_trade' in data and hasattr(config, 'handle_after_trade'):
                config.handle_after_trade = data.get('handle_after_trade')
            if 'handle_content' in data and hasattr(config, 'handle_content'):
                config.handle_content = data.get('handle_content')

            if 'goods_or_service_description' in data and hasattr(config, 'goods_or_service_description'):
                config.goods_or_service_description = data.get('goods_or_service_description')
            if 'goods_or_service_price' in data and hasattr(config, 'goods_or_service_price'):
                config.goods_or_service_price = data.get('goods_or_service_price')

            if profession_changed and new_profession:
                nationid = (getattr(config, 'nationid', None) or '').strip()
                nationpassword = (getattr(config, 'nationpassword', None) or '').strip()
                if not nationid:
                    return {"success": False, "message": "nationid is not configured"}
                if not nationpassword:
                    return {"success": False, "message": "nationpassword is not configured"}

                remote_error = await self._sync_profession_to_remote(nationid, nationpassword, str(new_profession))
                if remote_error:
                    await self.db.rollback()
                    return {"success": False, "message": remote_error}

            await self.db.commit()
            return {
                "success": True,
                "message": "User info updated successfully",
                "data": {
                    "deducted": deducted,
                    "money": getattr(config, 'money', None)
                }
            }
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

    async def get_model_info(self):
        """
        Get AI model information from aichat_cfg, agent_cfg, and llm_config

        Returns:
            Dictionary containing provider, model, and agent information
        """
        try:
            import json
            from backend.database.models.agent import AgentCfg
            from backend.database.models.system import LlmConfig

            # 1. Get first record from aichat_cfg
            result = await self.db.execute(
                select(AiChatCfg).where(AiChatCfg.is_delete == False).limit(1)
            )
            aichat_cfg = result.scalar_one_or_none()

            if not aichat_cfg or not aichat_cfg.agent_id:
                return {
                    "success": True,
                    "data": {
                        "provider": "N/A",
                        "model": "N/A",
                        "agent": "N/A"
                    }
                }

            # 2. Get agent_cfg by agent_id
            result = await self.db.execute(
                select(AgentCfg).where(AgentCfg.id == aichat_cfg.agent_id)
            )
            agent_cfg = result.scalar_one_or_none()

            if not agent_cfg:
                return {
                    "success": True,
                    "data": {
                        "provider": "N/A",
                        "model": "N/A",
                        "agent": "N/A"
                    }
                }

            agent_name = agent_cfg.name or "N/A"
            memo = agent_cfg.memo

            if not memo:
                return {
                    "success": True,
                    "data": {
                        "provider": "N/A",
                        "model": "N/A",
                        "agent": agent_name
                    }
                }

            # 3. Parse memo JSON to get model_config_id
            try:
                memo_data = json.loads(memo)
                model_config_id = memo_data.get('model_config_id')

                if not model_config_id:
                    return {
                        "success": True,
                        "data": {
                            "provider": "N/A",
                            "model": "N/A",
                            "agent": agent_name
                        }
                    }

                # 4. Get llm_config by model_config_id
                result = await self.db.execute(
                    select(LlmConfig).where(LlmConfig.config_id == model_config_id)
                )
                llm_config = result.scalar_one_or_none()

                if not llm_config:
                    return {
                        "success": True,
                        "data": {
                            "provider": "N/A",
                            "model": "N/A",
                            "agent": agent_name
                        }
                    }

                provider_name = llm_config.name or "N/A"
                model_name = llm_config.model_name or "N/A"

                return {
                    "success": True,
                    "data": {
                        "provider": provider_name,
                        "model": model_name,
                        "agent": agent_name
                    }
                }

            except json.JSONDecodeError as e:
                logger.error(f"Error parsing memo JSON: {e}")
                return {
                    "success": True,
                    "data": {
                        "provider": "N/A",
                        "model": "N/A",
                        "agent": agent_name
                    }
                }

        except Exception as e:
            logger.error(f"Error getting model info: {e}")
            raise HTTPException(status_code=500, detail=str(e))
