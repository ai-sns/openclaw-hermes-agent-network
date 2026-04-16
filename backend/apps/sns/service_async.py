"""SNS Module - Business Logic Service - Async version."""
import asyncio
import logging
import os
import uuid
import requests
import httpx
from datetime import datetime
from pathlib import Path
import json
import inspect
import re
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, or_, text
from sqlalchemy.orm import Session
from typing import List, Optional, Any, Dict
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


_ENGINE_INSPECT_PATH_RE = re.compile(r"^[a-zA-Z0-9_\.]+$")


def _engine_inspect_not_started_payload() -> dict:
    return {
        "success": False,
        "message": "Engine is not started. Please click Start in the SNS UI.",
    }


def _get_running_engine_or_error() -> tuple[Optional[object], Optional[dict]]:
    global _social_engine_instance

    if _social_engine_instance is None:
        return None, _engine_inspect_not_started_payload()
    try:
        started_flag = bool(getattr(_social_engine_instance, "started_flag", False))
    except Exception:
        started_flag = False
    if not started_flag:
        return None, _engine_inspect_not_started_payload()
    return _social_engine_instance, None


def _validate_engine_inspect_path(name: str, *, max_depth: int = 6) -> Optional[str]:
    raw = str(name or "").strip()
    if not raw:
        return None
    if len(raw) > 200:
        return None
    if not _ENGINE_INSPECT_PATH_RE.match(raw):
        return None

    parts = [p for p in raw.split(".") if p]
    if not parts or len(parts) > max_depth:
        return None

    for p in parts:
        if "__" in p:
            return None
        if not re.match(r"^[a-zA-Z_][a-zA-Z0-9_]*$", p):
            return None
    return ".".join(parts)


def _resolve_engine_inspect_path(root: object, path: str):
    cur = root
    for seg in path.split("."):
        cur = getattr(cur, seg)
    return cur


def _safe_json_value(value: Any, *, depth: int = 4, max_items: int = 200, max_chars: int = 8192):
    if depth <= 0:
        s = repr(value)
        return s[:max_chars]

    if value is None or isinstance(value, (bool, int, float, str)):
        if isinstance(value, str) and len(value) > max_chars:
            return value[:max_chars]
        return value

    if isinstance(value, dict):
        out: Dict[str, Any] = {}
        for idx, (k, v) in enumerate(value.items()):
            if idx >= max_items:
                break
            out[str(k)[:256]] = _safe_json_value(v, depth=depth - 1, max_items=max_items, max_chars=max_chars)
        return out

    if isinstance(value, (list, tuple, set)):
        out_list = []
        for idx, item in enumerate(list(value)):
            if idx >= max_items:
                break
            out_list.append(_safe_json_value(item, depth=depth - 1, max_items=max_items, max_chars=max_chars))
        return out_list

    s = repr(value)
    return s[:max_chars]


def apply_runtime_system_config(payload: dict) -> bool:
    global _social_engine_instance

    if not isinstance(payload, dict) or _social_engine_instance is None:
        return False

    changed = False
    if "memory_enabled" in payload and _social_engine_instance is not None:
        try:
            from backend.apps.sns.memory import MemoryConfig
            MemoryConfig.ENABLED = bool(payload.get("memory_enabled"))
            setattr(_social_engine_instance, "memory_enabled", MemoryConfig.ENABLED)
            changed = True
        except Exception:
            pass

    if "memory_embedding_enabled" in payload and _social_engine_instance is not None:
        try:
            from backend.apps.sns.memory import MemoryConfig
            emb = bool(payload.get("memory_embedding_enabled"))
            if not bool(getattr(MemoryConfig, "ENABLED", True)):
                emb = False
            MemoryConfig.EMBEDDING_ENABLED = emb
            setattr(_social_engine_instance, "memory_embedding_enabled", emb)
            changed = True
        except Exception:
            pass

    for k in (
        "contact_cooldown_seconds",
        "contact_recent_limit",
        "process_info_compact_every_n",
        "process_info_plan_summary_every_n",
        "tool_check_every_n",
    ):
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

    if "tool_check_before_review_enabled" in payload and _social_engine_instance is not None:
        try:
            setattr(_social_engine_instance, "tool_check_before_review_enabled", bool(payload["tool_check_before_review_enabled"]))
            changed = True
        except Exception:
            pass

    if "agent_card_before_review_enabled" in payload and _social_engine_instance is not None:
        try:
            setattr(_social_engine_instance, "agent_card_before_review_enabled", bool(payload["agent_card_before_review_enabled"]))
            changed = True
        except Exception:
            pass

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

    async def _broadcast_engine_status(self) -> None:
        try:
            status_payload = await self.get_social_engine_status()
            if isinstance(status_payload, dict):
                await websocket_manager.broadcast({
                    "type": "sns_engine_status",
                    **status_payload
                })
        except Exception as e:
            logger.warning("Failed to broadcast engine status: %s", e)

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

    async def _get_membership_by_nationid(self, nationid: Optional[str]) -> int:
        nid = (nationid or '').strip()
        if not nid:
            return 0

        for col in ("nation_id", "nationid"):
            try:
                result = await self.db.execute(
                    text(f"SELECT membership AS membership FROM users WHERE {col} = :nid LIMIT 1"),
                    {"nid": nid},
                )
                row = result.mappings().first()
                if row and row.get("membership") is not None:
                    return int(row.get("membership") or 0)
            except Exception:
                continue

        return 0

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

            # Read rebirth count from the running engine instance (in-memory only)
            rebirth = 0
            if _social_engine_instance is not None:
                rebirth = getattr(_social_engine_instance, '_rebirth_count', 0)

            config = await self._get_latest_user_config()

            if not config:
                return {
                    "rebirth": rebirth,
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
                "rebirth": rebirth,
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
            return {
                "rebirth": 0,
                "level": 3,
                "credit": 0,
                "money": 0.0,
                "life": 100,
                "iq": 100,
                "energy": 100,
                "move": 100,
                "exp": 0
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
            to_account = (to_account or "").strip()
            if (not to_account) or ("@" not in to_account):
                return {
                    "success": False,
                    "message": "Invalid XMPP account. Expected a full JID like user@domain.",
                }

            xmpp_manager = XMPPClientManager.get_instance()
            client = xmpp_manager.get_client()

            if not client or not client.is_client_connected():
                return {
                    "success": False,
                    "message": "XMPP client not connected"
                }

            await client.send_message_to_jid(to_account, content)
            stored_content = format_internal_xmpp_message_for_storage(content)

            stmt = select(AiChatCfg).where(AiChatCfg.is_delete == False)
            result = await self.db.execute(stmt)
            config = result.scalar_one_or_none()

            if config:
                from db.write_queue import db_write_async
                _config_account = config.account
                _config_nickname = config.nickname or config.account
                _to_account = to_account
                _stored_content = stored_content

                def _save_and_upsert(session):
                    friend = session.query(AIFriend).filter(
                        AIFriend.is_delete == False,
                        AIFriend.owner_sns_account == _config_account,
                        AIFriend.account == _to_account,
                    ).first()
                    if friend:
                        if not friend.nick_name:
                            friend.nick_name = _to_account
                        friend.new_message_flag = False
                    else:
                        friend = AIFriend(
                            account=_to_account,
                            nick_name=_to_account,
                            groups="",
                            owner_sns_account=_config_account,
                            subscription="none",
                            new_message_flag=False,
                            last_message_time=datetime.now(),
                        )
                        session.add(friend)

                    message = AIChatMessages(
                        conversation_id=f"{_config_account}_{_to_account}",
                        flag=0,
                        content=_stored_content,
                        owner_account=_config_account,
                        friend_account=_to_account,
                        owner_name=_config_nickname,
                        friend_name=_to_account
                    )
                    session.add(message)
                    friend.last_message_time = datetime.now()
                    return {
                        'account': friend.account,
                        'nick_name': friend.nick_name or friend.account,
                        'new_message_flag': bool(friend.new_message_flag),
                        'last_message_time': friend.last_message_time.isoformat() if friend.last_message_time else None,
                    }

                contact_payload = await db_write_async(_save_and_upsert, description="service_async_send_message")

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

    async def mark_contact_read(self, account: str) -> dict:
        """Mark a contact as read by clearing new_message_flag in DB."""
        try:
            account = (account or "").strip()
            if not account:
                return {"success": False, "message": "Account is required."}

            config = await self._get_latest_user_config()
            if not config:
                return {"success": False, "message": "No user config found."}

            from db.write_queue import db_write_async
            _owner = config.account
            _account = account

            def _clear_flag(session):
                friend = session.query(AIFriend).filter(
                    AIFriend.is_delete == False,
                    AIFriend.owner_sns_account == _owner,
                    AIFriend.account == _account,
                ).first()
                if not friend:
                    return None
                friend.new_message_flag = False
                return {
                    'account': friend.account,
                    'nick_name': friend.nick_name or friend.account,
                    'new_message_flag': False,
                    'last_message_time': friend.last_message_time.isoformat() if friend.last_message_time else None,
                }

            contact_payload = await db_write_async(_clear_flag, description="mark_contact_read")

            if contact_payload:
                await websocket_manager.broadcast({
                    'type': 'contact_upserted',
                    'data': contact_payload
                })

            return {"success": True, "message": "Contact marked as read."}
        except Exception as e:
            logger.error(f"Error marking contact as read: {e}")
            return {"success": False, "message": str(e)}

    async def send_file(self, to_account: str, file) -> dict:
        """Send a file via XMPP using XEP-0363"""
        try:
            to_account = (to_account or "").strip()
            if (not to_account) or ("@" not in to_account):
                return {
                    "success": False,
                    "message": "Invalid XMPP account. Expected a full JID like user@domain.",
                }

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
                    from db.write_queue import db_write_async
                    _ca = config.account
                    _cn = config.nickname or config.account
                    _ta = to_account
                    file_message = f"📎 File: {file.filename}\n{url}"
                    _sfm = format_internal_xmpp_message_for_storage(file_message)
                    _fn = file.filename

                    def _save_file_and_upsert(session):
                        friend = session.query(AIFriend).filter(
                            AIFriend.is_delete == False,
                            AIFriend.owner_sns_account == _ca,
                            AIFriend.account == _ta,
                        ).first()
                        if friend:
                            if not friend.nick_name:
                                friend.nick_name = _ta
                            friend.new_message_flag = False
                        else:
                            friend = AIFriend(
                                account=_ta,
                                nick_name=_ta,
                                groups="",
                                owner_sns_account=_ca,
                                subscription="none",
                                new_message_flag=False,
                                last_message_time=datetime.now(),
                            )
                            session.add(friend)
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
                        friend.last_message_time = datetime.now()
                        return {
                            'account': friend.account,
                            'nick_name': friend.nick_name or friend.account,
                            'new_message_flag': bool(friend.new_message_flag),
                            'last_message_time': friend.last_message_time.isoformat() if friend.last_message_time else None,
                        }

                    contact_payload = await db_write_async(_save_file_and_upsert, description="service_async_send_file")

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
                # _social_engine_running may become stale (e.g. instance not started or status not 'started').
                # Only treat as running if the instance exists and is actually started.
                if _social_engine_running and _social_engine_instance is not None:
                    try:
                        started_flag = bool(getattr(_social_engine_instance, "started_flag", False))
                        map_task_status = getattr(_social_engine_instance, "map_task_status", "")
                    except Exception:
                        started_flag = False
                        map_task_status = ""

                    if started_flag and map_task_status in ("started", "paused"):
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

                try:
                    started_flag = bool(getattr(_social_engine_instance, "started_flag", False))
                    map_task_status = getattr(_social_engine_instance, "map_task_status", "")
                except Exception:
                    started_flag = False
                    map_task_status = ""

                if not started_flag:
                    _social_engine_running = False
                    return {
                        "success": False,
                        "message": "AI Social Engine failed to start (started_flag is False)",
                        "running": False,
                        "task_status": map_task_status,
                    }

                _social_engine_running = True

                logger.info("AI Social Engine started successfully")
                await self._broadcast_engine_status()
                return {
                    "success": True,
                    "message": "AI Social Engine started successfully",
                    "running": True
                }
            except Exception as e:
                logger.error(f"Error starting AI social engine: {e}")
                _social_engine_running = False
                await self._broadcast_engine_status()
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
                await self._broadcast_engine_status()
                return payload

            except Exception as e:
                logger.error(f"Error stopping AI social engine: {e}")
                _social_engine_running = False
                await self._broadcast_engine_status()
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
                await self._broadcast_engine_status()
                return payload

            except Exception as e:
                logger.error(f"Error restarting AI social engine: {e}")
                _social_engine_running = False
                await self._broadcast_engine_status()
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
            await self._broadcast_engine_status()
            return result

        except Exception as e:
            logger.error(f"Error pausing AI social engine: {e}")
            await self._broadcast_engine_status()
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
            await self._broadcast_engine_status()
            return result

        except Exception as e:
            logger.error(f"Error resuming AI social engine: {e}")
            await self._broadcast_engine_status()
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


    async def engine_inspect_default(self) -> dict:
        engine, err = _get_running_engine_or_error()
        if err:
            return err

        snapshot = {
            "service_running": bool(_social_engine_running),
        }

        keys = [
            "started_flag",
            "map_task_status",
            "command_status",
            "human_take_over",
            "human_talk_type",
            "current_place",
            "current_position",
            "target_place",
            "target_position",
            "pause_flag",
            "agent_replying_flag",
            "_rebirth_count",
            "_instruction_total_count",
            "_instruction_invalid_count",
        ]

        for k in keys:
            try:
                snapshot[k] = _safe_json_value(getattr(engine, k, None))
            except Exception:
                snapshot[k] = None

        return {
            "success": True,
            "data": snapshot,
        }


    async def engine_inspect_var(self, name: str) -> dict:
        engine, err = _get_running_engine_or_error()
        if err:
            return err

        path = _validate_engine_inspect_path(name)
        if not path:
            return {
                "success": False,
                "message": "Invalid variable path",
            }

        try:
            value = _resolve_engine_inspect_path(engine, path)
        except Exception as e:
            return {
                "success": False,
                "message": f"Failed to read variable: {str(e)}",
            }

        try:
            value_type = type(value).__name__
        except Exception:
            value_type = "unknown"

        return {
            "success": True,
            "name": path,
            "value": _safe_json_value(value),
            "value_type": value_type,
        }


    async def engine_inspect_call(self, name: str, args: Any = None, kwargs: Any = None) -> dict:
        engine, err = _get_running_engine_or_error()
        if err:
            return err

        path = _validate_engine_inspect_path(name)
        if not path:
            return {
                "success": False,
                "message": "Invalid function path",
            }

        if args is None:
            args = []
        if kwargs is None:
            kwargs = {}
        if not isinstance(args, list):
            return {"success": False, "message": "args must be a list"}
        if not isinstance(kwargs, dict):
            return {"success": False, "message": "kwargs must be an object"}

        try:
            fn = _resolve_engine_inspect_path(engine, path)
        except Exception as e:
            return {
                "success": False,
                "message": f"Failed to resolve function: {str(e)}",
            }

        if not callable(fn):
            return {
                "success": False,
                "message": "Target is not callable",
            }

        timeout_seconds = 5.0
        try:
            result = fn(*args, **kwargs)
            if inspect.isawaitable(result):
                result = await asyncio.wait_for(result, timeout=timeout_seconds)
            return {
                "success": True,
                "name": path,
                "result": _safe_json_value(result),
            }
        except asyncio.TimeoutError:
            return {
                "success": False,
                "message": f"Function call timed out after {timeout_seconds:.0f}s",
            }
        except Exception as e:
            return {
                "success": False,
                "message": f"Function call failed: {str(e)}",
            }


    async def set_human_control_state(self, human_take_over: bool, human_talk_type: int = None) -> dict:
        global _social_engine_instance, _social_engine_running

        if _social_engine_instance is None:
            if human_take_over:
                start_result = await self.start_social_engine()
                if not isinstance(start_result, dict) or not start_result.get("success", False):
                    return {
                        "success": False,
                        "message": "Failed to initialize engine for human control",
                        "engine_start": start_result,
                    }
            else:
                return {
                    "success": True,
                    "message": "Human control state ignored because engine is not initialized",
                    "data": {
                        "human_take_over": False,
                        "human_talk_type": int(human_talk_type) if human_talk_type is not None else None,
                    }
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
                    try:
                        active = getattr(_social_engine_instance, "active_conversation", None)
                    except Exception:
                        active = None

                    if active:
                        last_line = ""
                        try:
                            hist = getattr(_social_engine_instance, "current_talk_history", None)
                            if isinstance(hist, list) and hist:
                                for item in reversed(hist):
                                    if isinstance(item, str) and item.strip():
                                        last_line = item.strip()
                                        break
                        except Exception:
                            last_line = ""

                        if last_line.startswith("Friend:"):
                            try:
                                logger.info("Exiting human control mode: triggering conversation review")
                                asyncio.create_task(taskmng.process_task(
                                    event="conversation_message_received",
                                    talk_history_str=json.dumps(
                                        getattr(_social_engine_instance, "current_talk_history", []) or [],
                                        ensure_ascii=False,
                                    ),
                                ))
                            except Exception as e:
                                logger.error("Failed to trigger conversation review after exiting human control mode: %s", e)
                        else:
                            logger.info("Exiting human control mode: keeping active conversation idle (waiting for peer reply)")
                        return {
                            "success": True,
                            "message": "Human control state updated",
                            "data": {
                                "human_take_over": _social_engine_instance.human_take_over,
                                "human_talk_type": _social_engine_instance.human_talk_type
                            }
                        }

                    try:
                        if hasattr(_social_engine_instance, "is_idle_for_auto_activity") and (not _social_engine_instance.is_idle_for_auto_activity()):
                            logger.info("Exiting human control mode: engine not idle, skipping process_activity resume")
                            return {
                                "success": True,
                                "message": "Human control state updated",
                                "data": {
                                    "human_take_over": _social_engine_instance.human_take_over,
                                    "human_talk_type": _social_engine_instance.human_talk_type
                                }
                            }
                    except Exception:
                        pass
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
        global _social_engine_instance, _social_engine_running

        # Auto-start engine if not initialized or not running
        if _social_engine_instance is None or not _social_engine_running:
            logger.info("Human message received but engine not running, auto-starting engine")
            await self.start_social_engine()

        if _social_engine_instance is None:
            return {
                "success": False,
                "message": "AI Social Engine is not initialized"
            }

        try:
            if hasattr(_social_engine_instance, "is_busy_for_human_command") and _social_engine_instance.is_busy_for_human_command():
                msg = "Previous command is still running. Please wait."
                try:
                    _social_engine_instance.taskmng_js.show_information(f"<b>{msg}</b>")
                except Exception:
                    pass
                try:
                    if hasattr(_social_engine_instance, "show_alert_on_map"):
                        _social_engine_instance.show_alert_on_map(msg, is_error=False)
                except Exception:
                    pass
                return {
                    "success": False,
                    "message": msg,
                }
        except Exception:
            pass

        # Ensure engine is in started state (handle paused/stopped)
        await self._ensure_engine_running_for_priority_action()

        engine = _social_engine_instance
        try:
            human_take_over = bool(getattr(engine, "human_take_over", False))
        except Exception:
            human_take_over = False

        try:
            human_talk_type = getattr(engine, "human_talk_type", 0)
            human_talk_type = int(human_talk_type) if human_talk_type is not None else 0
        except Exception:
            human_talk_type = 0

        if human_take_over and human_talk_type == 1:
            current_talk_people = None
            try:
                current_talk_people = getattr(engine, "current_talk_people", None)
            except Exception:
                current_talk_people = None

            account = ""
            if isinstance(current_talk_people, dict):
                try:
                    account = (current_talk_people.get("account") or "").strip()
                except Exception:
                    account = ""

            if not account:
                await self._broadcast_engine_status()
                return {
                    "success": False,
                    "message": "Message send failed: no active conversation.",
                }

            ok = False
            try:
                ok = bool(engine.sendMessage(message, by_click=True))
            except Exception as e:
                logger.error(f"Failed to send human message to target: {e}")
                ok = False

            await self._broadcast_engine_status()
            if not ok:
                return {
                    "success": False,
                    "message": "Failed to send message to the selected target.",
                }

            return {
                "success": True,
                "message": "Message sent",
            }

        engine.human_message_received(message)
        await self._broadcast_engine_status()
        return {
            "success": True,
            "message": "Human message received"
        }

    async def _ensure_engine_running_for_priority_action(self):
        """Ensure engine is in started state for priority actions.

        Handles paused/stopped/not-started states by resuming or starting
        the engine, then delegates to the engine's own method to cancel
        competing background tasks.
        """
        global _social_engine_instance, _social_engine_running

        if _social_engine_instance is None:
            return

        try:
            status = getattr(_social_engine_instance, "map_task_status", "")
            started = getattr(_social_engine_instance, "started_flag", False)

            if status == "paused":
                logger.info("Priority action: resuming paused engine via service")
                await self.resume_social_engine()
            elif status == "stopped" or not started:
                logger.info("Priority action: starting engine via service")
                _social_engine_running = False  # reset so start_social_engine proceeds
                await self.start_social_engine()

            # Delegate task interruption to the engine instance
            if hasattr(_social_engine_instance, "_ensure_engine_ready_for_priority_action"):
                await _social_engine_instance._ensure_engine_ready_for_priority_action()
        except Exception as e:
            logger.error(f"Failed to ensure engine running for priority action: {e}")

    async def submit_agent_instruction(self, instruction: str) -> dict:
        global _social_engine_instance, _social_engine_running

        raw_instruction = str(instruction or '').strip()
        if not raw_instruction:
            return {
                "success": False,
                "message": "Instruction is empty"
            }

        try:
            logger.info("submit_agent_instruction received: %s", raw_instruction[:200])
        except Exception:
            pass

        try:
            started_flag = bool(getattr(_social_engine_instance, "started_flag", False)) if _social_engine_instance is not None else False
        except Exception:
            started_flag = False

        if (not _social_engine_running) or (_social_engine_instance is None) or (not started_flag):
            start_result = await self.start_social_engine()
            if not isinstance(start_result, dict) or not start_result.get("success", False):
                return {
                    "success": False,
                    "message": f"Failed to start AI Social Engine for instruction: {start_result}",
                }

        if _social_engine_instance is None:
            return {
                "success": False,
                "message": "AI Social Engine is not initialized"
            }

        try:
            # Frontend chat button (talk_to_it) uses 【3_COMMUNICATE】 instruction.
            # In this mode we bypass contact cooldown/recent limits so the user can
            # immediately talk to the clicked person.
            if "【3_COMMUNICATE】" in raw_instruction:
                engine = _social_engine_instance
                setattr(engine, "_bypass_contact_limits", True)

                try:
                    if not bool(getattr(engine, "human_take_over", False)):
                        prev_task = getattr(engine, "_bypass_contact_limits_cleanup_task", None)
                        if isinstance(prev_task, asyncio.Task) and not prev_task.done():
                            prev_task.cancel()

                        async def _cleanup_bypass_flag(target_engine):
                            await asyncio.sleep(120)
                            try:
                                if bool(getattr(target_engine, "human_take_over", False)):
                                    return
                                if bool(getattr(target_engine, "_bypass_contact_limits", False)):
                                    setattr(target_engine, "_bypass_contact_limits", False)
                            except Exception:
                                pass

                        setattr(
                            engine,
                            "_bypass_contact_limits_cleanup_task",
                            asyncio.create_task(_cleanup_bypass_flag(engine)),
                        )
                except Exception:
                    pass
        except Exception:
            pass

        # Ensure engine is fully ready and interrupt current tasks for priority execution
        try:
            await self._ensure_engine_running_for_priority_action()
        except Exception:
            try:
                setattr(_social_engine_instance, "_human_command_inflight", False)
            except Exception:
                pass
            raise

        try:
            if hasattr(_social_engine_instance, "_terminate_active_conversation_for_priority_action"):
                _social_engine_instance._terminate_active_conversation_for_priority_action()
        except Exception:
            pass

        try:
            started_flag_after = bool(getattr(_social_engine_instance, "started_flag", False))
            map_task_status_after = getattr(_social_engine_instance, "map_task_status", "")
        except Exception:
            started_flag_after = False
            map_task_status_after = ""

        if not started_flag_after:
            return {
                "success": False,
                "message": "AI Social Engine is not started after ensure step",
                "task_status": map_task_status_after,
            }

        formatted_instruction = raw_instruction
        try:
            # Frontend talk_to_it sends instructions with 【3_COMMUNICATE】 embedded
            # (not at the start), so use 'in' instead of startswith.
            if "【3_COMMUNICATE】" in raw_instruction and "### Next Action" not in raw_instruction:
                formatted_instruction = f"### Current Task List\n\n### Next Action\n{raw_instruction}\n"
        except Exception:
            formatted_instruction = raw_instruction

        try:
            _social_engine_instance.handle_parse_agent_instruction_for_process_activity(formatted_instruction)
        except Exception as e:
            try:
                setattr(_social_engine_instance, "_human_command_inflight", False)
            except Exception:
                pass
            logger.error(f"Error submitting agent instruction: {e}")
            return {
                "success": False,
                "message": f"Failed to submit agent instruction: {str(e)}"
            }

        try:
            status_payload = await self.get_social_engine_status()
        except Exception:
            status_payload = {
                "success": True,
                "running": bool(_social_engine_running),
                "started": bool(getattr(_social_engine_instance, "started_flag", False)),
                "task_status": getattr(_social_engine_instance, "map_task_status", None),
            }

        await self._broadcast_engine_status()

        return {
            "success": True,
            "message": "Agent instruction submitted",
            "engine_status": status_payload
        }

    async def end_active_conversation(self, *, reason: str, message: str = "", resume_activity: bool = True) -> dict:
        global _social_engine_instance, _social_engine_running

        if _social_engine_instance is None:
            return {
                "success": False,
                "message": "AI Social Engine is not initialized",
            }

        try:
            await self._ensure_engine_running_for_priority_action()
        except Exception:
            pass

        active = {}
        try:
            active = getattr(_social_engine_instance, "active_conversation", None) or {}
        except Exception:
            active = {}

        try:
            active_account = (active.get("account") or "").strip() if isinstance(active, dict) else ""
        except Exception:
            active_account = ""

        if not active_account:
            return {
                "success": True,
                "message": "No active conversation.",
            }

        try:
            _social_engine_instance.end_active_conversation(
                reason=str(reason or "user_stop"),
                message=str(message or ""),
                resume_activity=bool(resume_activity),
            )
        except Exception as e:
            logger.error("Failed to end active conversation: %s", e, exc_info=True)
            return {
                "success": False,
                "message": f"Failed to end active conversation: {str(e)}",
            }

        try:
            await self._broadcast_engine_status()
        except Exception:
            pass

        return {
            "success": True,
            "message": "Active conversation ended",
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

            from db.write_queue import db_write_async
            _config_id = config.id
            _data = {k: v for k, v in data.items() if v is not None}
            def _update_cfg(session):
                rec = session.query(AiChatCfg).filter_by(id=_config_id).first()
                if rec:
                    for key, value in _data.items():
                        if hasattr(rec, key):
                            setattr(rec, key, value)
            await db_write_async(_update_cfg, description="service_async_update_ai_chat_config")
            self.db.expire_all()
            result2 = await self.db.execute(stmt)
            config = result2.scalars().first()

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

            from db.write_queue import db_write_async
            _config_id = config.id
            _filename = filename
            _avatar_map = avatar_map_filename

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
                _memo_str = json.dumps(memo_obj, ensure_ascii=False)
            except Exception:
                _memo_str = None

            def _set_avatar(session):
                rec = session.query(AiChatCfg).filter_by(id=_config_id).first()
                if rec:
                    rec.avatar = _filename
                    if _memo_str is not None:
                        rec.memo = _memo_str
            await db_write_async(_set_avatar, description="service_async_upload_avatar")

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

            from db.write_queue import db_write_async
            _config_id = config.id
            _filename = filename

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
                _memo_str = json.dumps(memo_obj, ensure_ascii=False)
            except Exception:
                _memo_str = None

            def _set_avatar_dialog(session):
                rec = session.query(AiChatCfg).filter_by(id=_config_id).first()
                if rec:
                    rec.avatar = _filename
                    if _memo_str is not None:
                        rec.memo = _memo_str
            await db_write_async(_set_avatar_dialog, description="service_async_upload_avatar_dialog")

            return {
                'success': True,
                'data': {
                    'avatar': filename,
                    'avatar_map': avatar_map_filename,
                    'avatar_url': f"/images/avatars/{filename}",
                }
            }
        except Exception as e:
            logger.error("Avatar dialog upload failed: %s", e)
            return {'success': False, 'message': str(e)}

    async def submit_avatar_dialog(self, payload: dict) -> dict:
        try:
            avatar_map = (payload.get('avatar_map') or '').strip()
            avatar3d = (payload.get('avatar3d') or payload.get('avatar_3d') or '').strip()
            nickname = (payload.get('nickname') or payload.get('nick_name') or '').strip()
            profile = (payload.get('profile') or '').strip()
            raw_sns_url = payload.get('sns_url', None)
            sns_url = '' if raw_sns_url is None else str(raw_sns_url).strip()
            xmpp_account = (payload.get('account') or payload.get('xmpp_account') or payload.get('sns_account') or '').strip()
            raw_agent_id = payload.get('agent_id', None)
            agent_id = None
            if raw_agent_id is not None and str(raw_agent_id).strip() != '':
                try:
                    agent_id = int(str(raw_agent_id).strip())
                except Exception:
                    return {'success': False, 'message': 'agent_id must be an integer'}

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

            # If avatar_map is still missing, treat it as "no avatar change" and
            # skip remote avatar upload. This allows saving other profile fields
            # without forcing users to re-upload an avatar.
            should_upload_avatar = bool(avatar_map)

            nationid = (getattr(config, 'nationid', None) or '').strip()
            nationpassword = (getattr(config, 'nationpassword', None) or '').strip()
            if not nationid:
                return {'success': False, 'message': 'nationid is not configured'}
            if not nationpassword:
                return {'success': False, 'message': 'nationpassword is not configured'}

            nickname = nickname or (getattr(config, 'nickname', None) or '')
            profile = profile or (getattr(config, 'sign', None) or '')
            if raw_sns_url is None:
                sns_url = (getattr(config, 'sns_url', None) or '')

            if not xmpp_account:
                xmpp_account = (getattr(config, 'account', None) or '').strip()

            from db.write_queue import db_write_async
            _config_id = config.id
            _avatar3d = avatar3d
            _nickname = nickname
            _profile = profile
            _sns_url = sns_url
            _xmpp_account = xmpp_account
            _agent_id = agent_id

            def _update_avatar_dialog(session):
                rec = session.query(AiChatCfg).filter_by(id=_config_id).first()
                if rec:
                    rec.avatar3d = _avatar3d
                    if _nickname:
                        rec.nickname = _nickname
                    if _profile:
                        rec.sign = _profile
                    rec.sns_url = _sns_url
                    if _xmpp_account and hasattr(rec, 'account'):
                        rec.account = _xmpp_account
                    if _agent_id is not None and hasattr(rec, 'agent_id'):
                        rec.agent_id = _agent_id
            await db_write_async(_update_avatar_dialog, description="service_async_submit_avatar_dialog")

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

            derived_framework: Optional[str] = None
            derived_model: Optional[str] = None
            if agent_id is not None:
                try:
                    from backend.database.models.agent import AgentCfg
                    from backend.database.models.system import LlmConfig

                    agent_result = await self.db.execute(select(AgentCfg).where(AgentCfg.id == agent_id))
                    agent_cfg = agent_result.scalar_one_or_none()

                    if agent_cfg:
                        memo_raw = getattr(agent_cfg, 'memo', None)
                        memo_data: Dict[str, Any] = {}
                        if isinstance(memo_raw, str) and memo_raw.strip():
                            try:
                                memo_data = json.loads(memo_raw)
                            except Exception:
                                memo_data = {}
                        if not isinstance(memo_data, dict):
                            memo_data = {}

                        agent_type_value = str(memo_data.get('agent_type') or 'local').strip().lower() or 'local'

                        if agent_type_value == 'local':
                            derived_framework = 'AI-SNS'
                        else:
                            fw = str(memo_data.get('framework') or '').strip()
                            fw_other = str(memo_data.get('framework_other') or '').strip()
                            if fw == 'Other' and fw_other:
                                derived_framework = fw_other
                            elif fw:
                                derived_framework = fw

                        if agent_type_value == 'remote':
                            md = str(memo_data.get('model_description') or '').strip()
                            derived_model = md or None
                        else:
                            model_config_id = str(memo_data.get('model_config_id') or '').strip()
                            if not model_config_id:
                                model_config_id = str(getattr(agent_cfg, 'defaultmodel', '') or '').strip()

                            if model_config_id:
                                llm_result = await self.db.execute(
                                    select(LlmConfig).where(LlmConfig.config_id == model_config_id)
                                )
                                llm_cfg = llm_result.scalar_one_or_none()
                                if llm_cfg:
                                    model_name = str(getattr(llm_cfg, 'model_name', '') or '').strip()
                                    if model_name:
                                        derived_model = model_name

                            if not derived_model:
                                fallback = str(getattr(agent_cfg, 'defaultmodel', '') or '').strip()
                                if fallback and not fallback.startswith('llm_'):
                                    derived_model = fallback
                except Exception as e:
                    logger.warning("Failed to derive framework/model from agent config: %s", e)

            a2a_endpoint = (payload.get('a2a_endpoint') or '').strip()

            async with httpx.AsyncClient(timeout=60.0) as client:
                if should_upload_avatar:
                    avatar_map_path = Path('images') / 'avatars' / avatar_map
                    if not avatar_map_path.exists():
                        return {'success': False, 'message': f'avatar_map file not found: {avatar_map}'}

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
                        'account': xmpp_account,
                        'avatar_3d': avatar3d,
                        'profile': profile,
                        'sns_url': sns_url,
                        **({'framework': derived_framework} if derived_framework else {}),
                        **({'model': derived_model} if derived_model else {}),
                        **({'a2a_endpoint': a2a_endpoint} if a2a_endpoint else {}),
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

    async def get_prompt_by_title(self, title: str):
        """Get a prompt record by its exact title."""
        try:
            title_value = (title or '').strip()
            if not title_value:
                return {"success": False, "message": "Title is required", "data": None}

            stmt = select(Prompt).where(Prompt.title == title_value)
            result = await self.db.execute(stmt)
            prompt = result.scalar_one_or_none()
            if not prompt:
                return {"success": False, "message": "Prompt not found", "data": None}

            return {
                "success": True,
                "data": {
                    "id": getattr(prompt, "id", None),
                    "title": getattr(prompt, "title", None),
                    "caption": getattr(prompt, "caption", None),
                    "content": getattr(prompt, "content", "") or "",
                    "question": getattr(prompt, "question", None),
                    "tags": getattr(prompt, "tags", None),
                },
            }
        except Exception as e:
            logger.error(f"Error getting prompt by title: {e}")
            return {"success": False, "message": str(e), "data": None}

    async def upsert_prompt_content_by_title(self, title: str, content: str):
        """Insert or update prompt content by its exact title."""
        try:
            title_value = (title or '').strip()
            if not title_value:
                return {"success": False, "message": "Title is required"}

            stmt = select(Prompt).where(Prompt.title == title_value)
            result = await self.db.execute(stmt)
            prompt = result.scalar_one_or_none()

            content_value = "" if content is None else str(content)

            from db.write_queue import db_write_async
            _title_value = title_value
            _content_value = content_value

            def _upsert_prompt(session):
                rec = session.query(Prompt).filter_by(title=_title_value).first()
                if not rec:
                    rec = Prompt(
                        title=_title_value,
                        caption=_title_value,
                        content=_content_value,
                        question="",
                        tags="",
                        model_name="",
                        position=9999,
                    )
                    session.add(rec)
                else:
                    rec.content = _content_value
                session.flush()
                return {
                    "id": rec.id,
                    "title": rec.title,
                    "caption": getattr(rec, "caption", None),
                    "content": rec.content or "",
                    "question": getattr(rec, "question", None),
                    "tags": getattr(rec, "tags", None),
                }

            prompt_data = await db_write_async(_upsert_prompt, description="service_async_upsert_prompt_by_title")

            return {
                "success": True,
                "message": "Prompt updated successfully",
                "data": prompt_data,
            }
        except Exception as e:
            logger.error(f"Error upserting prompt by title: {e}")
            return {"success": False, "message": str(e)}

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

            from db.write_queue import db_write_async
            _prompt_id = prompt.id
            _data = data
            def _update_role(session):
                rec = session.query(Prompt).filter_by(id=_prompt_id).first()
                if rec:
                    if "caption" in _data:
                        rec.caption = _data["caption"]
                    if "content" in _data:
                        rec.content = _data["content"]
                    if "question" in _data:
                        rec.question = _data["question"]
                    if "tags" in _data:
                        rec.tags = _data["tags"]
                    return {
                        "id": rec.id,
                        "caption": getattr(rec, "caption", None),
                        "content": getattr(rec, "content", None),
                        "question": getattr(rec, "question", None),
                        "tags": getattr(rec, "tags", None),
                    }
                return None
            result_data = await db_write_async(_update_role, description="service_async_update_social_role")

            return {
                "success": True,
                "message": "Social role updated successfully",
                "data": result_data
            }
        except Exception as e:
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

            from db.write_queue import db_write_async
            _prompt_id = prompt.id
            def _delete_role(session):
                rec = session.query(Prompt).filter_by(id=_prompt_id).first()
                if rec:
                    session.delete(rec)
            await db_write_async(_delete_role, description="service_async_delete_social_role")

            return {"success": True, "message": "Social role deleted successfully"}
        except Exception as e:
            logger.error(f"Error deleting social role: {e}")
            return {"success": False, "message": str(e)}

    async def get_user_info(self):
        """Get user information from aichat_cfg"""
        try:
            config = await self._get_latest_user_config()

            if not config:
                return {"success": False, "message": "No user config found"}

            membership_value = 0
            try:
                if hasattr(config, 'membership') and getattr(config, 'membership', None) is not None:
                    membership_value = int(getattr(config, 'membership') or 0)
                else:
                    membership_value = await self._get_membership_by_nationid(getattr(config, 'nationid', None))
            except Exception:
                membership_value = 0

            level_value = 0
            try:
                if hasattr(config, 'level') and getattr(config, 'level', None) is not None:
                    level_value = int(getattr(config, 'level') or 0)
            except Exception:
                level_value = 0

            return {
                "success": True,
                "data": {
                    "nationid": getattr(config, 'nationid', None),
                    "nickname": config.nickname,
                    "sign": config.sign,
                    "sns_url": config.sns_url,
                    "membership": membership_value,
                    "level": level_value,
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

            from db.write_queue import db_write_async
            _config_id = config.id
            _new_password = new_password
            def _set_password(session):
                rec = session.query(AiChatCfg).filter_by(id=_config_id).first()
                if rec:
                    rec.nationpassword = _new_password
            await db_write_async(_set_password, description="service_async_change_nation_password")
            return {"success": True, "message": "Nation password updated successfully"}
        except Exception as e:
            logger.error(f"Error changing nation password: {e}")
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

            if 'membership' in data and hasattr(config, 'membership'):
                try:
                    config.membership = int(data.get('membership') or 0)
                except Exception:
                    config.membership = 0

            if 'level' in data and hasattr(config, 'level'):
                try:
                    config.level = int(data.get('level') or 0)
                except Exception:
                    config.level = 0

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
                            try:
                                msg = (
                                    f"Insufficient balance to select profession {str(new_profession)}. "
                                    f"Required: ${float(cost):.2f}, available: ${float(current_money):.2f}."
                                )
                                if _social_engine_instance is not None:
                                    try:
                                        if hasattr(_social_engine_instance, 'show_alert_on_map'):
                                            _social_engine_instance.show_alert_on_map(msg, is_error=True)
                                    except Exception:
                                        pass
                                    try:
                                        ui = getattr(_social_engine_instance, 'taskmng_js', None)
                                        if ui is not None:
                                            ui.show_information(f"<b>{msg}</b>")
                                    except Exception:
                                        pass
                            except Exception:
                                pass
                            return {
                                "success": False,
                                "message": f"Insufficient balance. Selecting this profession requires {int(cost)}."
                            }

                        money_before = float(current_money)
                        config.money = current_money - cost
                        deducted = cost

                        try:
                            money_after = float(getattr(config, 'money', 0) or 0)
                            msg = (
                                f"Profession updated to {str(new_profession)}. "
                                f"Paid: ${float(cost):.2f}. "
                                f"Money: ${money_before:.2f} -> ${money_after:.2f}."
                            )
                            if _social_engine_instance is not None:
                                try:
                                    if hasattr(_social_engine_instance, 'show_alert_on_map'):
                                        _social_engine_instance.show_alert_on_map(msg, is_error=False)
                                except Exception:
                                    pass
                                try:
                                    ui = getattr(_social_engine_instance, 'taskmng_js', None)
                                    if ui is not None:
                                        ui.show_information(f"<b>{msg}</b>")
                                except Exception:
                                    pass
                        except Exception:
                            pass

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

            from db.write_queue import db_write_async
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
            if 'membership' in data and hasattr(config, 'membership'):
                _updates['membership'] = getattr(config, 'membership', 0)
            if 'level' in data and hasattr(config, 'level'):
                _updates['level'] = getattr(config, 'level', 0)
            if 'profession' in data:
                _updates['profession'] = config.profession
            if hasattr(config, 'money'):
                _updates['money'] = config.money
            if 'handle_after_trade' in data and hasattr(config, 'handle_after_trade'):
                _updates['handle_after_trade'] = data.get('handle_after_trade')
            if 'handle_content' in data and hasattr(config, 'handle_content'):
                _updates['handle_content'] = data.get('handle_content')
            if 'goods_or_service_description' in data and hasattr(config, 'goods_or_service_description'):
                _updates['goods_or_service_description'] = data.get('goods_or_service_description')
            if 'goods_or_service_price' in data and hasattr(config, 'goods_or_service_price'):
                _updates['goods_or_service_price'] = data.get('goods_or_service_price')

            _money_after = getattr(config, 'money', None)
            def _update_user(session):
                rec = session.query(AiChatCfg).filter_by(id=_config_id).first()
                if rec:
                    for k, v in _updates.items():
                        if hasattr(rec, k):
                            setattr(rec, k, v)
            await db_write_async(_update_user, description="service_async_update_user_info")
            return {
                "success": True,
                "message": "User info updated successfully",
                "data": {
                    "deducted": deducted,
                    "money": _money_after
                }
            }
        except Exception as e:
            logger.error(f"Error updating user info: {e}")
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

            from db.write_queue import db_write_async
            _config_id = config.id
            _map_updates = {
                'map_type': config.map_type,
                'map_api_key': config.map_api_key,
                'map_id': config.map_id,
            }
            if hasattr(config, 'memo'):
                _map_updates['memo'] = config.memo
            if map_type_changing:
                for _f in ('route_start', 'route_end', 'route_current_position',
                           'route', 'route_status', 'home_position',
                           'positionx', 'positiony', 'positionz'):
                    _map_updates[_f] = getattr(config, _f, None)

            def _update_map(session):
                rec = session.query(AiChatCfg).filter_by(id=_config_id).first()
                if rec:
                    for k, v in _map_updates.items():
                        setattr(rec, k, v)
            await db_write_async(_update_map, description="service_async_update_map_config")

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
                agent_type = str(memo_data.get('agent_type') or '').strip().lower()

                if agent_type == 'remote':
                    provider_name = str(memo_data.get('llm_provider') or '').strip() or "N/A"
                    model_name = str(memo_data.get('model_description') or '').strip() or "N/A"
                    return {
                        "success": True,
                        "data": {
                            "provider": provider_name,
                            "model": model_name,
                            "agent": agent_name
                        }
                    }

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
