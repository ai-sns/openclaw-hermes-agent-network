# -*- coding: utf-8 -*-
"""LLM configuration service layer."""
import asyncio
import json
import re
import time
import uuid
from typing import List, Dict, Any, Optional
from datetime import datetime
from sqlalchemy.orm import Session
from db.database import get_db_session as get_session
from db.models.agent import LLMConfig
from .llm_schemas import LLMConfigCreate, LLMConfigUpdate, LlmTestRequest
from openai import AsyncOpenAI

from runtime.shared.llm_endpoints import normalize_openai_base_url, normalize_provider
from runtime.shared.claude_client import ClaudeClient


class LLMConfigService:
    """Service for managing LLM configurations."""

    def __init__(self, db: Optional[Session] = None):
        self.db = db or get_session()

    def get_all(self, active_only: bool = True) -> List[Dict[str, Any]]:
        """Get all LLM configurations."""
        query = self.db.query(LLMConfig).filter(LLMConfig.is_delete == False)

        if active_only:
            query = query.filter(LLMConfig.is_active == True)

        configs = query.order_by(LLMConfig.position, LLMConfig.id).all()
        return [self._to_dict(config) for config in configs]

    def get_default_config(self) -> Optional[Dict[str, Any]]:
        """Get the default LLM configuration (is_default=True and is_active=True)."""
        config = self.db.query(LLMConfig).filter(
            LLMConfig.is_default == True,
            LLMConfig.is_active == True,
            LLMConfig.is_delete == False
        ).first()
        return self._to_dict(config) if config else None

    def get_by_config_id(self, config_id: str) -> Optional[Dict[str, Any]]:
        """Get configuration by config_id."""
        config = self.db.query(LLMConfig).filter(
            LLMConfig.config_id == config_id,
            LLMConfig.is_delete == False
        ).first()

        return self._to_dict(config) if config else None

    def create(self, data: LLMConfigCreate) -> str:
        """Create new LLM configuration."""
        # Generate unique config_id
        config_id = f"llm_{uuid.uuid4().hex[:12]}"

        # Prepare data
        config_data = data.dict()
        config_data["config_id"] = config_id

        # Handle custom_params
        if config_data.get("custom_params"):
            config_data["custom_params"] = json.dumps(config_data["custom_params"])

        # If this is set as default, unset other defaults
        if config_data.get("is_default"):
            self._unset_other_defaults()

        from db.write_queue import db_write
        def _do(session):
            c = LLMConfig(**config_data)
            session.add(c)
        db_write(_do, description="llm_service_create")

        return config_id

    def update(self, config_id: str, data: LLMConfigUpdate):
        """Update LLM configuration."""
        config = self.db.query(LLMConfig).filter(
            LLMConfig.config_id == config_id,
            LLMConfig.is_delete == False
        ).first()

        if not config:
            raise ValueError(f"Config not found: {config_id}")

        update_data = data.dict(exclude_unset=True)

        # Handle custom_params
        if "custom_params" in update_data and update_data["custom_params"]:
            update_data["custom_params"] = json.dumps(update_data["custom_params"])

        # If this is set as default, unset other defaults
        if update_data.get("is_default"):
            self._unset_other_defaults(exclude_id=config.id)

        # Update fields
        for key, value in update_data.items():
            setattr(config, key, value)

        from db.write_queue import db_write
        _cid = config_id
        _update_data = update_data
        def _do(session):
            rec = session.query(LLMConfig).filter(LLMConfig.config_id == _cid, LLMConfig.is_delete == False).first()
            if rec:
                for key, value in _update_data.items():
                    setattr(rec, key, value)
                rec.update_time = datetime.now()
        db_write(_do, description="llm_service_update")

    def delete(self, config_id: str):
        """Soft delete LLM configuration."""
        config = self.db.query(LLMConfig).filter(
            LLMConfig.config_id == config_id,
            LLMConfig.is_delete == False
        ).first()

        if not config:
            raise ValueError(f"Config not found: {config_id}")

        from db.write_queue import db_write
        _cid = config_id
        def _do(session):
            rec = session.query(LLMConfig).filter(LLMConfig.config_id == _cid).first()
            if rec:
                session.delete(rec)
        db_write(_do, description="llm_service_delete")

    async def test_connection(self, test_data: LlmTestRequest) -> Dict[str, Any]:
        """Test LLM connection."""
        provider = normalize_provider(getattr(test_data, 'provider', '') or '')
        raw_endpoint = str(test_data.api_endpoint or '').strip()
        if not raw_endpoint:
            raise ValueError('api_endpoint is required')

        if provider == 'claude':
            t0 = time.perf_counter()
            client = ClaudeClient(api_key=test_data.api_key, api_endpoint=raw_endpoint)
            try:
                result = await asyncio.wait_for(
                    client.create(
                        model=test_data.model_name,
                        system="You are a helpful assistant.",
                        messages=[{"role": "user", "content": "hello"}],
                        tools=None,
                        max_tokens=512,
                        temperature=0,
                    ),
                    timeout=15.0,
                )
            except asyncio.TimeoutError as e:
                raise TimeoutError('Connection test timed out') from e

            latency_ms = int((time.perf_counter() - t0) * 1000)
            reply = str((result or {}).get('text') or '').strip()

            success_message = "Connection test succeeded"
            if not reply:
                reply = '(model returned empty content)'
                success_message = "Connection succeeded (model returned empty content)"

            return {
                "status": "success",
                "message": success_message,
                "latency_ms": latency_ms,
                "reply": reply,
                "model": test_data.model_name,
                "provider": provider,
                "base_url": client.api_endpoint,
            }

        base_url = normalize_openai_base_url(raw_endpoint)
        base_url = re.sub(r"/v1/?$", "/v1", base_url, flags=re.IGNORECASE)
        base_url = base_url.rstrip('/')

        client = AsyncOpenAI(api_key=test_data.api_key, base_url=base_url)

        t0 = time.perf_counter()
        messages = [{"role": "user", "content": "hello"}]
        try:
            resp = await asyncio.wait_for(
                client.chat.completions.create(
                    model=test_data.model_name,
                    messages=messages,
                    temperature=0,
                    max_tokens=512,
                ),
                timeout=15.0,
            )
        except asyncio.TimeoutError as e:
            raise TimeoutError('Connection test timed out') from e
        finally:
            try:
                await client.close()
            except Exception:
                pass

        latency_ms = int((time.perf_counter() - t0) * 1000)
        # Try regular content first, then fall back to reasoning_content for
        # reasoning models (e.g. DeepSeek-Reasoner) which may emit the visible
        # answer under a different field.
        reply = ''
        try:
            msg = resp.choices[0].message
            reply = (getattr(msg, 'content', None) or '').strip()
            if not reply:
                reply = (getattr(msg, 'reasoning_content', None) or '').strip()
        except Exception:
            reply = ''

        # If the API call returned successfully (no exception) but produced no
        # visible text, the connection itself is still considered working: the
        # endpoint, key and model are valid. Report success with a placeholder
        # reply so the UI does not surface a misleading error.
        success_message = "Connection test succeeded"
        if not reply:
            reply = '(model returned empty content)'
            success_message = "Connection succeeded (model returned empty content)"

        return {
            "status": "success",
            "message": success_message,
            "latency_ms": latency_ms,
            "reply": reply,
            "model": test_data.model_name,
            "provider": provider,
            "base_url": base_url,
        }

    def import_configs(self, configs: List[LLMConfigCreate]) -> Dict[str, Any]:
        """Import multiple configurations."""
        created = []
        errors = []

        for config in configs:
            try:
                config_id = self.create(config)
                created.append(config_id)
            except Exception as e:
                errors.append({"config": config.name, "error": str(e)})

        return {
            "created": len(created),
            "errors": len(errors),
            "error_details": errors
        }

    def export_all(self) -> List[Dict[str, Any]]:
        """Export all configurations."""
        configs = self.get_all(active_only=False)

        # Remove sensitive fields
        for config in configs:
            if "api_key" in config and config["api_key"]:
                config["api_key"] = "***REDACTED***"

        return configs

    def _unset_other_defaults(self, exclude_id: Optional[int] = None):
        """Unset is_default for all other configs."""
        query = self.db.query(LLMConfig).filter(
            LLMConfig.is_default == True,
            LLMConfig.is_delete == False
        )

        if exclude_id:
            query = query.filter(LLMConfig.id != exclude_id)

        configs = query.all()
        _ids = [c.id for c in configs]
        if _ids:
            from db.write_queue import db_write
            def _do(session):
                for _id in _ids:
                    rec = session.query(LLMConfig).filter(LLMConfig.id == _id).first()
                    if rec:
                        rec.is_default = False
            db_write(_do, description="llm_service_unset_defaults")

    def _to_dict(self, config: LLMConfig) -> Dict[str, Any]:
        """Convert model to dict."""
        if not config:
            return None

        data = {
            "id": config.id,
            "config_id": config.config_id,
            "name": config.name,
            "provider": config.provider,
            "plugin_id": config.plugin_id,
            "api_endpoint": config.api_endpoint,
            "api_key": config.api_key,
            "model_name": config.model_name,
            "temperature": config.temperature,
            "max_tokens": config.max_tokens,
            "top_p": config.top_p,
            "frequency_penalty": config.frequency_penalty,
            "presence_penalty": config.presence_penalty,
            "stream": config.stream,
            "custom_params": json.loads(config.custom_params) if config.custom_params else None,
            "description": config.description,
            "is_active": config.is_active,
            "is_default": config.is_default,
            "position": config.position,
            "create_time": config.create_time.isoformat() if config.create_time else None,
            "update_time": config.update_time.isoformat() if config.update_time else None
        }
        return data
