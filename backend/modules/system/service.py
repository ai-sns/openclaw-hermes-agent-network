# -*- coding: utf-8 -*-
"""
System module - Service layer
"""
import logging
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime

import os
import asyncio
from pathlib import Path
from urllib.parse import urlparse

import httpx
from PIL import Image, ImageChops, ImageDraw, ImageOps

from db.DBFactory import query_SystemCfg, update_SystemCfg, Session, SystemCfg as DBSystemCfg
from backend.config.settings import get_settings
from backend.database.repositories import WebMngRepository, SystemInitRepository, AiChatCfgRepository
from backend.database.models.system import WebMng

logger = logging.getLogger(__name__)


class SystemService:
    """Service for managing system configuration"""

    def __init__(self):
        self.web_mng_repo = WebMngRepository()

    @staticmethod
    def get_system_config() -> Dict[str, Any]:
        """Get system configuration"""
        config = query_SystemCfg(is_delete=False)
        settings = get_settings()

        return {
            "theme": getattr(config, 'theme', 'dark'),
            "language": getattr(config, 'language', 'zh'),
            "minirunontray": getattr(config, 'minirunontray', True),
            "agent_server": getattr(config, 'agent_server', None),
            "ai_sns_server": getattr(config, 'ai_sns_server', None),
            "conversation_timeout_seconds": getattr(config, 'conversation_timeout_seconds', 60),
            "contact_cooldown_seconds": getattr(config, 'contact_cooldown_seconds', 300),
            "contact_recent_limit": getattr(config, 'contact_recent_limit', 3),
            "process_info_compact_every_n": getattr(config, 'process_info_compact_every_n', 50),
            "process_info_plan_summary_every_n": getattr(config, 'process_info_plan_summary_every_n', 5),
            "memory_enabled": bool(getattr(config, 'memory_enabled', True)),
            "memory_embedding_enabled": bool(getattr(config, 'memory_embedding_enabled', False)),
            "tools": {
                "page_size": settings.tools.page_size
            }
        }

    @staticmethod
    def update_system_config(**kwargs) -> None:
        """Update system configuration"""
        allowed_keys = {
            "autorun",
            "showtaskbar",
            "updateinfo",
            "minirunontray",
            "closebuttontype",
            "style",
            "showinfo",
            "showinfoicon",
            "infosound",
            "agent_server",
            "ai_sns_server",
            "conversation_timeout_seconds",
            "contact_cooldown_seconds",
            "contact_recent_limit",
            "process_info_compact_every_n",
            "process_info_plan_summary_every_n",
            "memory_enabled",
            "memory_embedding_enabled",
        }

        payload = {k: v for k, v in kwargs.items() if k in allowed_keys}
        if not payload:
            return

        for k in (
            "conversation_timeout_seconds",
            "contact_cooldown_seconds",
            "contact_recent_limit",
            "process_info_compact_every_n",
            "process_info_plan_summary_every_n",
        ):
            if k in payload and payload[k] is not None:
                try:
                    payload[k] = int(payload[k])
                except (TypeError, ValueError):
                    payload.pop(k, None)

        for k in ("process_info_compact_every_n", "process_info_plan_summary_every_n"):
            if k in payload:
                if payload[k] is None:
                    payload.pop(k, None)
                    continue
                if payload[k] < 0:
                    payload.pop(k, None)

        if "memory_enabled" in payload:
            try:
                payload["memory_enabled"] = bool(payload["memory_enabled"])
            except Exception:
                payload.pop("memory_enabled", None)

        if "memory_embedding_enabled" in payload:
            try:
                payload["memory_embedding_enabled"] = bool(payload["memory_embedding_enabled"])
            except Exception:
                payload.pop("memory_embedding_enabled", None)

        # If memory is disabled, embedding must be disabled as well.
        if payload.get("memory_enabled") is False:
            payload["memory_embedding_enabled"] = False

        record = query_SystemCfg(is_delete=False)
        if record:
            update_SystemCfg(record.id, **payload)
            try:
                from backend.apps.sns.service_async import apply_runtime_system_config
                apply_runtime_system_config(payload)
            except Exception:
                pass
            return

        session = Session()
        try:
            session.add(DBSystemCfg(**payload, is_delete=False, create_time=datetime.now()))
            session.commit()
            try:
                from backend.apps.sns.service_async import apply_runtime_system_config
                apply_runtime_system_config(payload)
            except Exception:
                pass
        finally:
            session.close()

    def get_web_mng(self) -> List[Dict[str, Any]]:
        """Get all web management items"""
        items = self.web_mng_repo.get_all_ordered(is_delete=False)
        return [
            {
                "id": item.id,
                "web_id": item.web_id,
                "name": item.name,
                "title": item.title,
                "type": item.type,
                "description": item.description,
                "filename": item.filename,
                "url": item.url,
                "position": item.position,
                "creator": item.creator,
                "is_delete": item.is_delete,
                "create_time": item.create_time.isoformat() if item.create_time else None
            }
            for item in items
        ]

    def create_web_mng(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Create new web management item"""
        import random
        import string

        # Generate web_id if not provided
        if 'web_id' not in data:
            data['web_id'] = ''.join(random.choices(string.ascii_uppercase + string.digits, k=20))

        # Set defaults
        data.setdefault('position', 999)
        data.setdefault('creator', 'User')
        data.setdefault('is_delete', False)
        data.setdefault('create_time', datetime.now())

        item = self.web_mng_repo.create(**data)

        return {
            "id": item.id,
            "web_id": item.web_id,
            "name": item.name,
            "type": item.type,
            "url": item.url
        }

    def update_web_mng(self, item_id: int, data: Dict[str, Any]) -> Dict[str, Any]:
        """Update web management item"""
        # Remove fields that shouldn't be updated
        data.pop('id', None)
        data.pop('web_id', None)
        data.pop('create_time', None)

        self.web_mng_repo.update(item_id, **data)
        item = self.web_mng_repo.get_by_id(item_id)

        return {
            "id": item.id,
            "web_id": item.web_id,
            "name": item.name,
            "title": item.title,
            "type": item.type,
            "description": item.description,
            "filename": item.filename,
            "url": item.url,
            "position": item.position
        }

    def delete_web_mng(self, item_id: int) -> None:
        """Delete web management item (soft delete)"""
        self.web_mng_repo.update(item_id, is_delete=True)

    def reorder_web_mng(self, items: List[Dict[str, Any]]) -> None:
        """Reorder web management items"""
        for item in items:
            item_id = item.get('id')
            position = item.get('position')
            if item_id is not None and position is not None:
                self.web_mng_repo.update(item_id, position=position)


class SystemInitWizardService:
    def __init__(self):
        self.system_init_repo = SystemInitRepository()
        self.ai_chat_cfg_repo = AiChatCfgRepository()

    @staticmethod
    def _get_first_record() -> Any:
        repo = SystemInitRepository()
        records = repo.get_all(is_delete=False)
        return records[0] if records else None

    @staticmethod
    def _split_map_value(value: str, map_type: str) -> str:
        if not value:
            return ""
        parts = value.split(',')
        if map_type == "Google":
            if len(parts) >= 1 and parts[0] != "N/A":
                return parts[0]
            return ""
        if len(parts) >= 2 and parts[1] not in ("N/A", "do_not_need_map_id"):
            return parts[1]
        if len(parts) >= 2 and parts[1] == "do_not_need_map_id":
            return "do_not_need_map_id"
        return ""

    @staticmethod
    def _combine_map_values(map_type: str, map_api_key: str, map_id: str) -> Dict[str, str]:
        map_api_key = (map_api_key or "").strip()
        map_id = (map_id or "").strip()
        if map_type == "Google":
            return {
                "map_api_key": f"{map_api_key},N/A",
                "map_id": f"{map_id},N/A",
            }
        return {
            "map_api_key": f"N/A,{map_api_key}",
            "map_id": "N/A,do_not_need_map_id",
        }

    def get_draft(self) -> Dict[str, Any]:
        record = self._get_first_record()
        if not record:
            return {}

        map_type = record.map or "Google"
        return {
            "id": record.id,
            "name": record.name,
            "avatar": record.avatar,
            "password": record.password,
            "confirm_password": record.confirm_password,
            "profile": record.profile,
            "llm": record.llm,
            "llm_server": record.llm_server,
            "api_key": record.api_key,
            "avatar3d": record.avatar3d,
            "account": record.account,
            "account_password": record.account_password,
            "sns_url": record.sns_url,
            "map": map_type,
            "map_api_key": self._split_map_value(record.map_api_key, map_type),
            "map_id": self._split_map_value(record.map_id, map_type),
            "status": record.status,
        }

    def save_draft(self, data: Dict[str, Any]) -> Dict[str, Any]:
        record = self._get_first_record()

        map_type = data.get("map") or (record.map if record else "Google") or "Google"
        combined = self._combine_map_values(map_type, data.get("map_api_key") or "", data.get("map_id") or "")

        payload = {
            "name": data.get("name"),
            "avatar": data.get("avatar"),
            "password": data.get("password"),
            "confirm_password": data.get("confirm_password"),
            "profile": data.get("profile"),
            "llm": data.get("llm"),
            "llm_server": data.get("llm_server"),
            "api_key": data.get("api_key"),
            "avatar3d": data.get("avatar3d"),
            "account": data.get("account"),
            "account_password": data.get("account_password"),
            "sns_url": data.get("sns_url"),
            "map": map_type,
            "map_api_key": combined["map_api_key"],
            "map_id": combined["map_id"],
            "status": 0,
            "is_delete": False,
        }

        if record:
            self.system_init_repo.update(record.id, **payload)
            return {"id": record.id}
        created = self.system_init_repo.create(**payload)
        return {"id": created.id}

    def list_avatar3d(self, request_base_url: str) -> List[Dict[str, str]]:
        base = request_base_url.rstrip('/')
        folder = Path("scripts") / "avatar3d"
        if not folder.exists():
            return []

        glb_files = {p.stem: p.name for p in folder.glob("*.glb")}
        png_files = {p.stem: p.name for p in folder.glob("*.png")}

        keys = sorted(set(glb_files.keys()) & set(png_files.keys()))
        return [
            {
                "key": key,
                "png_url": f"{base}/scripts/avatar3d/{png_files[key]}",
                "glb_url": f"{base}/scripts/avatar3d/{glb_files[key]}",
            }
            for key in keys
        ]

    @staticmethod
    def _save_uploaded_avatar(file_bytes: bytes, filename: str) -> str:
        avatars_dir = Path("images") / "avatars"
        avatars_dir.mkdir(parents=True, exist_ok=True)
        file_path = avatars_dir / filename
        file_path.write_bytes(file_bytes)
        return filename

    @staticmethod
    def _generate_avatar_map(avatar_filename: str) -> str:
        avatars_dir = Path("images") / "avatars"
        avatar_path = avatars_dir / avatar_filename
        if not avatar_path.exists():
            raise FileNotFoundError(str(avatar_path))

        pin_path = Path("pin.png")
        if not pin_path.exists():
            pin_path = Path("images") / "pin.png"
        if not pin_path.exists():
            raise FileNotFoundError(str(pin_path))

        pin = ImageOps.exif_transpose(Image.open(pin_path)).convert("RGBA")
        avatar = ImageOps.exif_transpose(Image.open(avatar_path)).convert("RGBA")

        size = 70
        if avatar.width <= 0 or avatar.height <= 0:
            raise ValueError("Invalid avatar image")

        scale = max(size / float(avatar.width), size / float(avatar.height))
        resized_w = max(size, int(round(avatar.width * scale)))
        resized_h = max(size, int(round(avatar.height * scale)))
        avatar_resized = avatar.resize((resized_w, resized_h), Image.LANCZOS)

        left = max(0, (avatar_resized.width - size) // 2)
        top = max(0, (avatar_resized.height - size) // 2)
        avatar_square = avatar_resized.crop((left, top, left + size, top + size))

        oversample = 4
        hi = size * oversample

        clip_mask_hi = Image.new("L", (hi, hi), 0)
        clip_draw = ImageDraw.Draw(clip_mask_hi)
        clip_draw.ellipse((2 * oversample, 2 * oversample, hi - 2 * oversample, hi - 2 * oversample), fill=255)
        clip_mask = clip_mask_hi.resize((size, size), Image.LANCZOS)

        alpha = avatar_square.split()[-1]
        avatar_square.putalpha(ImageChops.multiply(alpha, clip_mask))

        border_hi = Image.new("RGBA", (hi, hi), (0, 0, 0, 0))
        border_draw_hi = ImageDraw.Draw(border_hi)
        border_draw_hi.ellipse(
            (1 * oversample, 1 * oversample, hi - 2 * oversample, hi - 2 * oversample),
            outline=(255, 255, 255, 255),
            width=2 * oversample,
        )
        border = border_hi.resize((size, size), Image.LANCZOS)

        avatar_marker = Image.alpha_composite(avatar_square, border)

        composite = Image.new("RGBA", pin.size, (0, 0, 0, 0))
        composite.paste(pin, (0, 0), pin)
        composite.paste(avatar_marker, (1, 2), avatar_marker)

        target_w = max(1, pin.size[0] // 2)
        target_h = max(1, pin.size[1] // 2)
        factor = min(target_w / float(composite.size[0]), target_h / float(composite.size[1]))
        next_w = max(1, int(round(composite.size[0] * factor)))
        next_h = max(1, int(round(composite.size[1] * factor)))
        scaled = composite.resize((next_w, next_h), Image.LANCZOS)
        name_without_ext, _ext = os.path.splitext(avatar_filename)
        map_filename = f"{name_without_ext}_map.png"
        out_path = avatars_dir / map_filename
        scaled.save(out_path, format="PNG", optimize=True)
        return map_filename

    def upload_avatar(self, file_bytes: bytes, file_extension: str) -> Dict[str, str]:
        import uuid

        ext = (file_extension or "").lower()
        if ext not in (".png", ".jpg", ".jpeg", ".bmp", ".webp"):
            ext = ".png"

        filename = f"{uuid.uuid4()}{ext}"
        avatar_filename = self._save_uploaded_avatar(file_bytes, filename)
        avatar_map_filename = self._generate_avatar_map(avatar_filename)
        return {
            "avatar": avatar_filename,
            "avatar_map": avatar_map_filename,
        }

    async def test_llm(self, llm: str, llm_server: str, api_key: str) -> Dict[str, Any]:
        llm_server = (llm_server or "").strip()
        api_key = (api_key or "").strip()
        if not llm_server:
            return {"success": False, "message": "LLM Server cannot be empty"}
        if not api_key:
            return {"success": False, "message": "API Key cannot be empty"}

        try:
            parsed = urlparse(llm_server)
            if parsed.scheme not in ("http", "https") or not parsed.netloc:
                return {"success": False, "message": "Invalid LLM Server format"}
        except Exception:
            return {"success": False, "message": "Invalid LLM Server format"}

        headers = {
            "Authorization": f"Bearer {api_key}",
            "Accept": "application/json",
        }

        models_url = llm_server
        if "/chat/completions" in llm_server:
            models_url = llm_server.replace("/chat/completions", "/models")
        elif llm_server.endswith("/messages"):
            models_url = llm_server[:-len("/messages")] + "/models"

        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.get(models_url, headers=headers)
                if resp.status_code in (200, 201):
                    return {"success": True, "message": "LLM configuration test passed", "data": {"status": resp.status_code}}
                if resp.status_code in (401, 403):
                    return {"success": False, "message": "Invalid API Key or insufficient permissions", "data": {"status": resp.status_code}}

                fallback = await client.request("HEAD", llm_server, headers=headers)
                if fallback.status_code < 500:
                    return {"success": True, "message": f"LLM Server is reachable (HTTP {fallback.status_code}), but API Key or model list could not be verified", "data": {"status": fallback.status_code}}
                return {"success": False, "message": f"LLM Server returned an unexpected response (HTTP {fallback.status_code})", "data": {"status": fallback.status_code}}
        except httpx.RequestError as e:
            return {"success": False, "message": f"Failed to connect to LLM Server: {str(e)}"}
        except Exception as e:
            return {"success": False, "message": str(e) or "LLM test failed"}

    async def test_xmpp(self, account: str, account_password: str) -> Dict[str, Any]:
        account = (account or "").strip()
        account_password_raw = account_password or ""
        account_password = account_password_raw
        if not account:
            return {"success": False, "message": "XMPP account cannot be empty"}
        if not (account_password or "").strip():
            return {"success": False, "message": "XMPP password cannot be empty"}
        if "@" not in account:
            return {"success": False, "message": "Invalid XMPP account format"}

        try:
            import slixmpp
        except Exception as e:
            return {"success": False, "message": f"slixmpp is not installed or unavailable: {str(e)}"}

        account_no_resource = account.split("/", 1)[0]

        domain_part = account_no_resource.split("@", 1)[1]
        domain_part = domain_part.split("/", 1)[0]

        host = domain_part
        port_override: Optional[int] = None
        if ":" in domain_part:
            maybe_host, maybe_port = domain_part.rsplit(":", 1)
            if maybe_host and maybe_port.isdigit():
                host = maybe_host
                port_override = int(maybe_port)

        jid = account_no_resource
        if port_override is not None:
            # Keep socket host/port override, but JID must not contain ":port"
            local_part = jid.split("@", 1)[0]
            jid = f"{local_part}@{host}"

        if not host:
            return {"success": False, "message": "Invalid XMPP account format"}

        logger.info(
            "[InitWizard][XMPP Test] Prepared credentials | raw_account=%s | sanitized_jid=%s | host=%s | port_override=%s | password=%s",
            account,
            jid,
            host,
            port_override if port_override is not None else "default:5222",
            account_password,
        )

        loop = asyncio.get_running_loop()

        class _TestXMPPClient(slixmpp.ClientXMPP):
            def __init__(self, jid: str, password: str, done_future: asyncio.Future):
                super().__init__(jid, password)
                self._done_future = done_future
                self._connected_target: Optional[str] = None
                self._fail_task: Optional[asyncio.Task] = None

                # Align with SNS module: prefer simple SASL (PLAIN) over TLS
                # to avoid servers rejecting SCRAM variants.
                self.auth_mechanisms = {"PLAIN"}

                self.add_event_handler("session_start", self._on_session_start)
                self.add_event_handler("failed_auth", self._on_failed_auth)
                self.add_event_handler("connection_failed", self._on_connection_failed)
                self.add_event_handler("socket_error", self._on_socket_error)
                self.add_event_handler("disconnected", self._on_disconnected)
                self.add_event_handler("stream_features", self._on_stream_features)

                self.register_plugin('xep_0030')
                self.register_plugin('xep_0199')

            async def _resolve(self, payload: Dict[str, Any]):
                if not self._done_future.done():
                    self._done_future.set_result(payload)

            async def _on_session_start(self, _event):
                try:
                    self.send_presence()
                    await self.get_roster()
                except Exception:
                    pass

                msg = "XMPP login succeeded"
                if self._connected_target:
                    msg = f"{msg}({self._connected_target})"
                logger.info(
                    "[InitWizard][XMPP Test] session_start | boundjid=%s | requested_jid=%s",
                    self.boundjid,
                    self.requested_jid,
                )
                if self._fail_task:
                    self._fail_task.cancel()
                await self._resolve({"success": True, "message": msg})
                self.disconnect(wait=False)

            async def _on_failed_auth(self, _event):
                logger.warning(
                    "[InitWizard][XMPP Test] failed_auth | requested_jid=%s",
                    getattr(self, "requested_jid", None),
                )
                # Do not immediately abort; allow a short window for a second mechanism to succeed (as seen in SNS client)
                if self._fail_task:
                    self._fail_task.cancel()
                async def _delayed_fail():
                    try:
                        await asyncio.sleep(3)
                        if not self._done_future.done():
                            await self._resolve({"success": False, "message": "XMPP authentication failed (invalid account or password)"})
                            self.disconnect(wait=False)
                    except asyncio.CancelledError:
                        return
                self._fail_task = asyncio.create_task(_delayed_fail())

            async def _on_connection_failed(self, event):
                detail = (str(event) or "").strip()
                msg = "XMPP connection failed"
                if self._connected_target:
                    msg = f"{msg}({self._connected_target})"
                if detail:
                    msg = f"{msg}: {detail}"
                await self._resolve({"success": False, "message": msg})

            async def _on_socket_error(self, event):
                detail = (str(event) or "").strip()
                msg = "XMPP socket error"
                if self._connected_target:
                    msg = f"{msg}({self._connected_target})"
                if detail:
                    msg = f"{msg}: {detail}"
                await self._resolve({"success": False, "message": msg})

            async def _on_disconnected(self, _event):
                if not self._done_future.done():
                    msg = "XMPP disconnected"
                    if self._connected_target:
                        msg = f"{msg}({self._connected_target})"
                    self._done_future.set_result({"success": False, "message": msg})

            async def _on_stream_features(self, _event):
                try:
                    mechs = getattr(self.auth, "mechanisms", None)
                    logger.info(
                        "[InitWizard][XMPP Test] stream_features | advertised_mechs=%s | auth_mechanisms=%s",
                        mechs,
                        getattr(self, "auth_mechanisms", None),
                    )
                except Exception:
                    pass

        fut: asyncio.Future = loop.create_future()
        xmpp = _TestXMPPClient(jid, account_password, fut)

        try:
            if port_override is not None:
                xmpp._connected_target = f"{host}:{port_override}"
                xmpp.connect(address=(host, port_override))
            else:
                xmpp._connected_target = f"{host}:5222"
                xmpp.connect()
        except Exception as e:
            try:
                xmpp.disconnect(wait=False)
            except Exception:
                pass
            return {"success": False, "message": f"Failed to connect to XMPP server: {str(e)}"}

        try:
            try:
                result = await asyncio.wait_for(fut, timeout=12.0)
            except asyncio.TimeoutError:
                result = {"success": False, "message": f"XMPP login timed out (12s) ({xmpp._connected_target})"}
        finally:
            try:
                xmpp.disconnect(wait=False)
            except Exception:
                pass
            # Give slixmpp a moment to clean up
            try:
                await asyncio.wait_for(xmpp.disconnected, timeout=3.0)
            except (asyncio.TimeoutError, Exception):
                pass

        if isinstance(result, dict) and "success" in result:
            return result
        return {"success": False, "message": "XMPP test failed"}

    async def test_map(self, map_type: str, map_api_key: str, map_id: str) -> Dict[str, Any]:
        map_type = (map_type or "").strip() or "Google"
        map_api_key = (map_api_key or "").strip()
        map_id = (map_id or "").strip()

        if not map_api_key:
            return {"success": False, "message": "Map API Key cannot be empty"}

        if map_type == "Google" and not map_id:
            return {"success": False, "message": "Map ID cannot be empty"}

        if map_type == "Baidu":
            url = f"https://api.map.baidu.com/api?v=3.0&ak={map_api_key}"
        else:
            qs = f"key={map_api_key}"
            if map_id:
                qs = qs + f"&map_ids={map_id}"
            url = f"https://maps.googleapis.com/maps/api/js?{qs}"

        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.get(url)
                if resp.status_code == 200:
                    return {"success": True, "message": "Map configuration test passed", "data": {"status": resp.status_code}}
                if resp.status_code in (401, 403):
                    return {"success": False, "message": "Invalid map key or insufficient permissions", "data": {"status": resp.status_code}}
                return {"success": False, "message": f"Map service returned an unexpected response (HTTP {resp.status_code})", "data": {"status": resp.status_code}}
        except httpx.RequestError as e:
            return {"success": False, "message": f"Failed to connect to map service: {str(e)}"}
        except Exception as e:
            return {"success": False, "message": str(e) or "Map test failed"}

    async def fetch_captcha(self) -> Dict[str, Any]:
        cfg = query_SystemCfg(is_delete=False)
        base = (getattr(cfg, 'ai_sns_server', None) or '').rstrip('/')
        if not base:
            raise ValueError("ai_sns_server is not configured")
        url = f"{base}/api/captcha/"
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.get(url)
            resp.raise_for_status()
            return {
                "captcha_id": resp.headers.get("X-Captcha-ID", ""),
                "content": resp.content,
                "content_type": resp.headers.get("content-type", "image/png"),
            }

    async def register_remote(self, data: Dict[str, Any], avatar_map_filename: str) -> Dict[str, Any]:
        avatars_dir = Path("images") / "avatars"
        avatar_map_path = avatars_dir / avatar_map_filename
        if not avatar_map_path.exists():
            raise FileNotFoundError(str(avatar_map_path))

        cfg = query_SystemCfg(is_delete=False)
        base = (getattr(cfg, 'ai_sns_server', None) or '').rstrip('/')
        if not base:
            raise ValueError("ai_sns_server is not configured")
        register_url = f"{base}/api/register/"
        files = {"avatar_file": (avatar_map_path.name, avatar_map_path.read_bytes(), "image/png")}

        async with httpx.AsyncClient(timeout=60.0) as client:
            resp = await client.post(register_url, data=data, files=files)
            if resp.status_code not in (200, 201):
                raise ValueError(f"Remote register failed: {resp.status_code} - {resp.text}")
            return resp.json()

    def submit(self, draft: Dict[str, Any], nation_id: str) -> None:
        record = self._get_first_record()
        if not record:
            raise ValueError("SystemInit not found")
        self.system_init_repo.update(record.id, status=1)

        sns_record = self.ai_chat_cfg_repo.get_map_config()
        if sns_record:
            map_type_text = draft.get("map") or record.map or "Google"
            map_type_value = "0" if map_type_text == "Google" else "1"
            combined = self._combine_map_values(map_type_text, draft.get("map_api_key") or "", draft.get("map_id") or "")
            self.ai_chat_cfg_repo.update(
                sns_record.id,
                nationid=nation_id,
                avatar=record.avatar,
                name=record.name,
                nationpassword=record.password,
                sign=record.profile,
                avatar3d=record.avatar3d,
                account=record.account,
                password=record.account_password,
                sns_url=record.sns_url,
                map_type=map_type_value,
                map_api_key=combined["map_api_key"],
                map_id=combined["map_id"],
            )
