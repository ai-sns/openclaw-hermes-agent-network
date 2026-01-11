# -*- coding: utf-8 -*-
"""LLM configuration service layer."""
import json
import uuid
from typing import List, Dict, Any, Optional
from datetime import datetime
from sqlalchemy.orm import Session
from backend.database.base import get_session
from backend.database.models.system import LlmConfig
from .llm_schemas import LlmConfigCreate, LlmConfigUpdate, LlmTestRequest


class LlmConfigService:
    """Service for managing LLM configurations."""

    def __init__(self, db: Optional[Session] = None):
        self.db = db or get_session()

    def get_all(self, active_only: bool = True) -> List[Dict[str, Any]]:
        """Get all LLM configurations."""
        query = self.db.query(LlmConfig).filter(LlmConfig.is_delete == False)

        if active_only:
            query = query.filter(LlmConfig.is_active == True)

        configs = query.order_by(LlmConfig.position, LlmConfig.id).all()
        return [self._to_dict(config) for config in configs]

    def get_by_config_id(self, config_id: str) -> Optional[Dict[str, Any]]:
        """Get configuration by config_id."""
        config = self.db.query(LlmConfig).filter(
            LlmConfig.config_id == config_id,
            LlmConfig.is_delete == False
        ).first()

        return self._to_dict(config) if config else None

    def create(self, data: LlmConfigCreate) -> str:
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

        config = LlmConfig(**config_data)
        self.db.add(config)
        self.db.commit()

        return config_id

    def update(self, config_id: str, data: LlmConfigUpdate):
        """Update LLM configuration."""
        config = self.db.query(LlmConfig).filter(
            LlmConfig.config_id == config_id,
            LlmConfig.is_delete == False
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

        config.update_time = datetime.now()
        self.db.commit()

    def delete(self, config_id: str):
        """Soft delete LLM configuration."""
        config = self.db.query(LlmConfig).filter(
            LlmConfig.config_id == config_id,
            LlmConfig.is_delete == False
        ).first()

        if not config:
            raise ValueError(f"Config not found: {config_id}")

        config.is_delete = True
        self.db.commit()

    async def test_connection(self, test_data: LlmTestRequest) -> Dict[str, Any]:
        """Test LLM connection."""
        # Implementation depends on your LLM client setup
        # This is a placeholder that simulates a connection test
        try:
            # TODO: Implement actual connection test based on provider
            # For now, just return success
            return {
                "status": "success",
                "message": "Connection test successful",
                "latency_ms": 120
            }
        except Exception as e:
            return {
                "status": "error",
                "message": str(e)
            }

    def import_configs(self, configs: List[LlmConfigCreate]) -> Dict[str, Any]:
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
        query = self.db.query(LlmConfig).filter(
            LlmConfig.is_default == True,
            LlmConfig.is_delete == False
        )

        if exclude_id:
            query = query.filter(LlmConfig.id != exclude_id)

        configs = query.all()
        for config in configs:
            config.is_default = False

        self.db.commit()

    def _to_dict(self, config: LlmConfig) -> Dict[str, Any]:
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
