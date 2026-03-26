# -*- coding: utf-8 -*-
"""Role configuration service layer."""
import uuid
from typing import List, Dict, Any, Optional
from datetime import datetime
from sqlalchemy.orm import Session
from backend.database.base import get_session
from backend.database.models.system import RoleConfig
from .role_schemas import RoleConfigCreate, RoleConfigUpdate


class RoleConfigService:
    """Service for managing role configurations."""

    def __init__(self, db: Optional[Session] = None):
        self.db = db or get_session()

    def get_all(self, active_only: bool = True, category: Optional[str] = None) -> List[Dict[str, Any]]:
        """Get all role configurations."""
        query = self.db.query(RoleConfig).filter(RoleConfig.is_delete == False)

        if active_only:
            query = query.filter(RoleConfig.is_active == True)

        if category:
            query = query.filter(RoleConfig.category == category)

        roles = query.order_by(RoleConfig.position, RoleConfig.id).all()
        return [self._to_dict(role) for role in roles]

    def get_presets(self) -> List[Dict[str, Any]]:
        """Get preset role templates."""
        roles = self.db.query(RoleConfig).filter(
            RoleConfig.is_preset == True,
            RoleConfig.is_delete == False
        ).order_by(RoleConfig.position).all()

        return [self._to_dict(role) for role in roles]

    def get_by_role_id(self, role_id: str) -> Optional[Dict[str, Any]]:
        """Get configuration by role_id."""
        role = self.db.query(RoleConfig).filter(
            RoleConfig.role_id == role_id,
            RoleConfig.is_delete == False
        ).first()

        return self._to_dict(role) if role else None

    def create(self, data: RoleConfigCreate) -> str:
        """Create new role configuration."""
        # Generate unique role_id
        role_id = f"role_{uuid.uuid4().hex[:12]}"

        # Prepare data
        role_data = data.dict()
        role_data["role_id"] = role_id
        role_data["role_type"] = "custom"  # User-created roles are custom

        # If this is set as default, unset other defaults
        if role_data.get("is_default"):
            self._unset_other_defaults()

        from db.write_queue import db_write
        def _do(session):
            r = RoleConfig(**role_data)
            session.add(r)
        db_write(_do, description="role_service_create")

        return role_id

    def update(self, role_id: str, data: RoleConfigUpdate):
        """Update role configuration."""
        role = self.db.query(RoleConfig).filter(
            RoleConfig.role_id == role_id,
            RoleConfig.is_delete == False
        ).first()

        if not role:
            raise ValueError(f"Role not found: {role_id}")

        update_data = data.dict(exclude_unset=True)

        # If this is set as default, unset other defaults
        if update_data.get("is_default"):
            self._unset_other_defaults(exclude_id=role.id)

        # Update fields
        for key, value in update_data.items():
            setattr(role, key, value)

        from db.write_queue import db_write
        _rid = role_id
        _update_data = update_data
        def _do(session):
            rec = session.query(RoleConfig).filter(RoleConfig.role_id == _rid, RoleConfig.is_delete == False).first()
            if rec:
                for key, value in _update_data.items():
                    setattr(rec, key, value)
                rec.update_time = datetime.now()
        db_write(_do, description="role_service_update")

    def delete(self, role_id: str):
        """Soft delete role configuration."""
        role = self.db.query(RoleConfig).filter(
            RoleConfig.role_id == role_id,
            RoleConfig.is_delete == False
        ).first()

        if not role:
            raise ValueError(f"Role not found: {role_id}")

        # Prevent deletion of preset roles
        if role.is_preset:
            raise ValueError("Cannot delete preset roles. You can disable them instead.")

        from db.write_queue import db_write
        _rid = role_id
        def _do(session):
            rec = session.query(RoleConfig).filter(RoleConfig.role_id == _rid, RoleConfig.is_delete == False).first()
            if rec:
                rec.is_delete = True
        db_write(_do, description="role_service_delete")

    def import_configs(self, configs: List[RoleConfigCreate]) -> Dict[str, Any]:
        """Import multiple configurations."""
        created = []
        errors = []

        for config in configs:
            try:
                role_id = self.create(config)
                created.append(role_id)
            except Exception as e:
                errors.append({"config": config.name, "error": str(e)})

        return {
            "created": len(created),
            "errors": len(errors),
            "error_details": errors
        }

    def export_all(self) -> List[Dict[str, Any]]:
        """Export all configurations."""
        return self.get_all(active_only=False)

    def _unset_other_defaults(self, exclude_id: Optional[int] = None):
        """Unset is_default for all other configs."""
        query = self.db.query(RoleConfig).filter(
            RoleConfig.is_default == True,
            RoleConfig.is_delete == False
        )

        if exclude_id:
            query = query.filter(RoleConfig.id != exclude_id)

        roles = query.all()
        _ids = [r.id for r in roles]
        if _ids:
            from db.write_queue import db_write
            def _do(session):
                for _id in _ids:
                    rec = session.query(RoleConfig).filter(RoleConfig.id == _id).first()
                    if rec:
                        rec.is_default = False
            db_write(_do, description="role_service_unset_defaults")

    def _to_dict(self, role: RoleConfig) -> Dict[str, Any]:
        """Convert model to dict."""
        if not role:
            return None

        data = {
            "id": role.id,
            "role_id": role.role_id,
            "name": role.name,
            "display_name": role.display_name or role.name,
            "system_prompt": role.system_prompt,
            "greeting_message": role.greeting_message,
            "role_type": role.role_type,
            "category": role.category,
            "avatar": role.avatar,
            "description": role.description,
            "tags": role.tags,
            "is_active": role.is_active,
            "is_default": role.is_default,
            "is_preset": role.is_preset,
            "position": role.position,
            "usage_count": role.usage_count,
            "create_time": role.create_time.isoformat() if role.create_time else None,
            "update_time": role.update_time.isoformat() if role.update_time else None
        }
        return data
