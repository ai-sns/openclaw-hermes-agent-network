# -*- coding: utf-8 -*-
"""
Tools module - Business logic service
"""
import logging
from typing import List, Optional
from datetime import datetime
import uuid
import json
import zipfile
import shutil
from pathlib import Path

from sqlalchemy.orm import Session
from fastapi import HTTPException
from fastapi import UploadFile

from ...database.models.system import PluginMng, FunctionMng, McpMng, SkillMng
from .schemas import (
    PluginCreate, PluginUpdate, PluginResponse,
    MCPCreate, MCPUpdate, MCPResponse,
    FunctionCreate, FunctionUpdate, FunctionResponse,
    SkillCreate, SkillUpdate, SkillResponse
)
from .tool_executor import get_tool_executor

logger = logging.getLogger(__name__)


class ToolsService:
    """Tools service for managing plugins, MCP, functions, and skills"""

    def __init__(self, db: Session):
        """Initialize tools service with database session"""
        self.db = db

    # ==================== Plugin Methods ====================

    def create_plugin(self, plugin: PluginCreate) -> PluginResponse:
        """Create a new plugin"""
        try:
            plugin_id = self._generate_id("PL")
            db_plugin = PluginMng(
                plugin_id=plugin_id,
                **plugin.model_dump()
            )
            self.db.add(db_plugin)
            self.db.commit()
            self.db.refresh(db_plugin)
            return PluginResponse.model_validate(db_plugin)
        except Exception as e:
            self.db.rollback()
            logger.error(f"Error creating plugin: {e}")
            raise

    def get_plugin(self, plugin_id: str) -> Optional[PluginResponse]:
        """Get plugin by ID"""
        db_plugin = self.db.query(PluginMng).filter(
            PluginMng.plugin_id == plugin_id,
            PluginMng.is_delete == False
        ).first()
        return PluginResponse.model_validate(db_plugin) if db_plugin else None

    def get_all_plugins(self, used_in_sns: Optional[bool] = None) -> List[PluginResponse]:
        """Get all plugins"""
        q = self.db.query(PluginMng).filter(
            PluginMng.is_delete == False
        )

        if used_in_sns is not None:
            q = q.filter(PluginMng.used_in_sns == used_in_sns)

        db_plugins = q.order_by(PluginMng.create_time.desc()).all()
        return [PluginResponse.model_validate(p) for p in db_plugins]

    def update_plugin(self, plugin_id: str, plugin: PluginUpdate) -> Optional[PluginResponse]:
        """Update plugin"""
        try:
            db_plugin = self.db.query(PluginMng).filter(
                PluginMng.plugin_id == plugin_id,
                PluginMng.is_delete == False
            ).first()

            if not db_plugin:
                return None

            update_data = plugin.model_dump(exclude_unset=True)
            for key, value in update_data.items():
                setattr(db_plugin, key, value)

            self.db.commit()
            self.db.refresh(db_plugin)
            return PluginResponse.model_validate(db_plugin)
        except Exception as e:
            self.db.rollback()
            logger.error(f"Error updating plugin: {e}")
            raise

    def delete_plugin(self, plugin_id: str) -> bool:
        """Soft delete plugin"""
        try:
            db_plugin = self.db.query(PluginMng).filter(
                PluginMng.plugin_id == plugin_id,
                PluginMng.is_delete == False
            ).first()

            if not db_plugin:
                return False

            db_plugin.is_delete = True
            self.db.commit()

            # Best-effort cleanup for extracted renderer plugins.
            # This keeps DB soft-delete semantics, but also frees disk space.
            try:
                if (db_plugin.plugin_type or '').lower() == 'renderer' and db_plugin.plugin_directory:
                    uploads_root = (Path('uploads') / 'plugins').resolve()
                    plugin_dir = Path(str(db_plugin.plugin_directory)).resolve()

                    # Only allow deletion of uploads/plugins/<plugin_id> to avoid unsafe deletes.
                    if plugin_dir.parent == uploads_root and plugin_dir.name == str(plugin_id):
                        shutil.rmtree(plugin_dir, ignore_errors=True)
            except Exception as e:
                logger.warning(f"Renderer plugin directory cleanup failed for {plugin_id}: {e}")

            return True
        except Exception as e:
            self.db.rollback()
            logger.error(f"Error deleting plugin: {e}")
            raise

    def import_renderer_plugin_zip(self, file: UploadFile, used_in_sns: bool = True) -> PluginResponse:
        """Import a renderer plugin from a zip upload and register it in DB"""
        filename = (file.filename or '').lower()
        if not filename.endswith('.zip'):
            raise HTTPException(status_code=400, detail='Only .zip files are supported')

        uploads_root = Path('uploads') / 'plugins'
        uploads_root.mkdir(parents=True, exist_ok=True)

        raw_bytes = file.file.read()
        if not raw_bytes:
            raise HTTPException(status_code=400, detail='Empty file')

        try:
            tmp_dir = uploads_root / f"_tmp_{datetime.now().strftime('%Y%m%d%H%M%S')}_{str(uuid.uuid4().int)[:6]}"
            tmp_dir.mkdir(parents=True, exist_ok=True)
            tmp_zip = tmp_dir / 'plugin.zip'
            tmp_zip.write_bytes(raw_bytes)

            with zipfile.ZipFile(tmp_zip, 'r') as zf:
                names = zf.namelist()
                manifest_candidates = [n for n in names if n.endswith('plugin.json') and not n.endswith('/plugin.json/')]
                if not manifest_candidates:
                    raise HTTPException(status_code=400, detail='plugin.json not found in zip')

                manifest_path = sorted(manifest_candidates, key=len)[0]
                manifest_raw = zf.read(manifest_path).decode('utf-8')
                manifest = json.loads(manifest_raw)

                plugin_name = str(manifest.get('name') or '').strip()
                plugin_version = str(manifest.get('version') or '1.0.0').strip()
                plugin_desc = str(manifest.get('description') or '').strip()
                plugin_entry = str(manifest.get('entry') or '').strip()
                plugin_alias = str(manifest.get('id') or '').strip()

                if not plugin_name:
                    raise HTTPException(status_code=400, detail='plugin.json: name is required')
                if not plugin_entry:
                    raise HTTPException(status_code=400, detail='plugin.json: entry is required')

                plugin_id = self._generate_id('PL')
                target_dir = uploads_root / plugin_id
                target_dir.mkdir(parents=True, exist_ok=True)

                target_dir_resolved = target_dir.resolve()
                for member in zf.infolist():
                    member_name = member.filename
                    if not member_name or member_name.endswith('/'):
                        continue

                    if member_name.startswith('/') or member_name.startswith('\\'):
                        raise HTTPException(status_code=400, detail='Zip contains absolute paths')

                    dest = (target_dir / member_name).resolve()
                    if target_dir_resolved not in dest.parents and dest != target_dir_resolved:
                        raise HTTPException(status_code=400, detail='Zip contains unsafe paths')

                    dest.parent.mkdir(parents=True, exist_ok=True)
                    with zf.open(member, 'r') as src, open(dest, 'wb') as out:
                        shutil.copyfileobj(src, out)

                manifest_dir = Path(manifest_path).parent
                entry_rel = (manifest_dir / plugin_entry).as_posix()
                entry_rel = entry_rel.lstrip('./')

                if entry_rel.startswith('/') or entry_rel.startswith('\\') or '..' in Path(entry_rel).parts:
                    raise HTTPException(status_code=400, detail='plugin.json: entry contains unsafe path')

                entry_fs = target_dir / entry_rel
                if not entry_fs.exists():
                    raise HTTPException(status_code=400, detail=f'Entry file not found after extract: {entry_rel}')

                entry_url = f"/uploads/plugins/{plugin_id}/{entry_rel}"

                db_plugin = PluginMng(
                    plugin_id=plugin_id,
                    name=plugin_name,
                    version=plugin_version,
                    alias_name=plugin_alias or None,
                    description=plugin_desc or None,
                    filename=entry_url,
                    plugin_directory=str(target_dir).replace('\\', '/'),
                    plugin_type='renderer',
                    confirm_needed=True,
                    used_in_sns=bool(used_in_sns)
                )

                self.db.add(db_plugin)
                self.db.commit()
                self.db.refresh(db_plugin)
                return PluginResponse.model_validate(db_plugin)
        except HTTPException:
            self.db.rollback()
            raise
        except Exception as e:
            self.db.rollback()
            logger.error(f"Error importing renderer plugin zip: {e}")
            raise
        finally:
            try:
                if 'tmp_dir' in locals() and tmp_dir.exists():
                    shutil.rmtree(tmp_dir, ignore_errors=True)
            except Exception:
                pass

    # ==================== MCP Methods ====================

    def create_mcp(self, mcp: MCPCreate) -> MCPResponse:
        """Create a new MCP"""
        try:
            mcp_id = self._generate_id("MC")
            db_mcp = McpMng(
                mcp_id=mcp_id,
                **mcp.model_dump()
            )
            self.db.add(db_mcp)
            self.db.commit()
            self.db.refresh(db_mcp)
            return MCPResponse.model_validate(db_mcp)
        except Exception as e:
            self.db.rollback()
            logger.error(f"Error creating MCP: {e}")
            raise

    def get_mcp(self, mcp_id: str) -> Optional[MCPResponse]:
        """Get MCP by ID"""
        db_mcp = self.db.query(McpMng).filter(
            McpMng.mcp_id == mcp_id,
            McpMng.is_delete == False
        ).first()
        return MCPResponse.model_validate(db_mcp) if db_mcp else None

    def get_all_mcps(self) -> List[MCPResponse]:
        """Get all MCPs"""
        db_mcps = self.db.query(McpMng).filter(
            McpMng.is_delete == False
        ).order_by(McpMng.create_time.desc()).all()
        return [MCPResponse.model_validate(m) for m in db_mcps]

    def update_mcp(self, mcp_id: str, mcp: MCPUpdate) -> Optional[MCPResponse]:
        """Update MCP"""
        try:
            db_mcp = self.db.query(McpMng).filter(
                McpMng.mcp_id == mcp_id,
                McpMng.is_delete == False
            ).first()

            if not db_mcp:
                return None

            update_data = mcp.model_dump(exclude_unset=True)
            for key, value in update_data.items():
                setattr(db_mcp, key, value)

            self.db.commit()
            self.db.refresh(db_mcp)
            return MCPResponse.model_validate(db_mcp)
        except Exception as e:
            self.db.rollback()
            logger.error(f"Error updating MCP: {e}")
            raise

    def delete_mcp(self, mcp_id: str) -> bool:
        """Soft delete MCP"""
        try:
            db_mcp = self.db.query(McpMng).filter(
                McpMng.mcp_id == mcp_id,
                McpMng.is_delete == False
            ).first()

            if not db_mcp:
                return False

            db_mcp.is_delete = True
            self.db.commit()
            return True
        except Exception as e:
            self.db.rollback()
            logger.error(f"Error deleting MCP: {e}")
            raise

    # ==================== Function Methods ====================

    def create_function(self, function: FunctionCreate) -> FunctionResponse:
        """Create a new function"""
        try:
            function_id = self._generate_id("FN")
            db_function = FunctionMng(
                function_id=function_id,
                **function.model_dump()
            )
            self.db.add(db_function)
            self.db.commit()
            self.db.refresh(db_function)
            return FunctionResponse.model_validate(db_function)
        except Exception as e:
            self.db.rollback()
            logger.error(f"Error creating function: {e}")
            raise

    def get_function(self, function_id: str) -> Optional[FunctionResponse]:
        """Get function by ID"""
        db_function = self.db.query(FunctionMng).filter(
            FunctionMng.function_id == function_id,
            FunctionMng.is_delete == False
        ).first()
        return FunctionResponse.model_validate(db_function) if db_function else None

    def get_all_functions(self) -> List[FunctionResponse]:
        """Get all functions"""
        db_functions = self.db.query(FunctionMng).filter(
            FunctionMng.is_delete == False
        ).order_by(FunctionMng.create_time.desc()).all()
        return [FunctionResponse.model_validate(f) for f in db_functions]

    def update_function(self, function_id: str, function: FunctionUpdate) -> Optional[FunctionResponse]:
        """Update function"""
        try:
            db_function = self.db.query(FunctionMng).filter(
                FunctionMng.function_id == function_id,
                FunctionMng.is_delete == False
            ).first()

            if not db_function:
                return None

            update_data = function.model_dump(exclude_unset=True)
            for key, value in update_data.items():
                setattr(db_function, key, value)

            self.db.commit()
            self.db.refresh(db_function)
            return FunctionResponse.model_validate(db_function)
        except Exception as e:
            self.db.rollback()
            logger.error(f"Error updating function: {e}")
            raise

    def delete_function(self, function_id: str) -> bool:
        """Soft delete function"""
        try:
            db_function = self.db.query(FunctionMng).filter(
                FunctionMng.function_id == function_id,
                FunctionMng.is_delete == False
            ).first()

            if not db_function:
                return False

            db_function.is_delete = True
            self.db.commit()
            return True
        except Exception as e:
            self.db.rollback()
            logger.error(f"Error deleting function: {e}")
            raise

    # ==================== Skill (Computer Use) Methods ====================

    def create_skill(self, skill: SkillCreate) -> SkillResponse:
        """Create a new skill"""
        try:
            skill_id = self._generate_id("SK")
            db_skill = SkillMng(
                skill_id=skill_id,
                **skill.model_dump()
            )
            self.db.add(db_skill)
            self.db.commit()
            self.db.refresh(db_skill)
            return SkillResponse.model_validate(db_skill)
        except Exception as e:
            self.db.rollback()
            logger.error(f"Error creating skill: {e}")
            raise

    def get_skill(self, skill_id: str) -> Optional[SkillResponse]:
        """Get skill by ID"""
        db_skill = self.db.query(SkillMng).filter(
            SkillMng.skill_id == skill_id,
            SkillMng.is_delete == False
        ).first()
        return SkillResponse.model_validate(db_skill) if db_skill else None

    def get_all_skills(self) -> List[SkillResponse]:
        """Get all skills"""
        db_skills = self.db.query(SkillMng).filter(
            SkillMng.is_delete == False
        ).order_by(SkillMng.create_time.desc()).all()

        return [SkillResponse.model_validate(s) for s in db_skills]

    def update_skill(self, skill_id: str, skill: SkillUpdate) -> Optional[SkillResponse]:
        """Update skill"""
        try:
            db_skill = self.db.query(SkillMng).filter(
                SkillMng.skill_id == skill_id,
                SkillMng.is_delete == False
            ).first()

            if not db_skill:
                return None

            update_data = skill.model_dump(exclude_unset=True)
            for key, value in update_data.items():
                setattr(db_skill, key, value)

            self.db.commit()
            self.db.refresh(db_skill)
            return SkillResponse.model_validate(db_skill)
        except Exception as e:
            self.db.rollback()
            logger.error(f"Error updating skill: {e}")
            raise

    def delete_skill(self, skill_id: str) -> bool:
        """Soft delete skill"""
        try:
            db_skill = self.db.query(SkillMng).filter(
                SkillMng.skill_id == skill_id,
                SkillMng.is_delete == False
            ).first()

            if not db_skill:
                return False

            db_skill.is_delete = True
            self.db.commit()
            return True
        except Exception as e:
            self.db.rollback()
            logger.error(f"Error deleting skill: {e}")
            raise

    # ==================== Utility Methods ====================

    def _generate_id(self, prefix: str) -> str:
        """Generate unique ID with prefix"""
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
        random_part = str(uuid.uuid4().int)[:5]
        return f"{prefix}{timestamp}{random_part}"

    # ==================== Execution Methods ====================

    async def execute_plugin(self, plugin_id: str, params: dict) -> dict:
        """Execute a plugin with real code execution"""
        plugin = self.get_plugin(plugin_id)
        if not plugin:
            raise ValueError(f"Plugin not found: {plugin_id}")

        logger.info(f"Executing plugin: {plugin.name} ({plugin_id})")

        # Get the executor and execute with real code
        executor = get_tool_executor()

        # Convert plugin response to dict for executor
        plugin_data = {
            "name": plugin.name,
            "description": plugin.description,
            "instruction": plugin.instruction,
            "runtime_main": plugin.runtime_main,
            "filename": plugin.filename,
            "plugin_directory": plugin.plugin_directory,
            "plugin_type": plugin.plugin_type
        }

        return await executor.execute_plugin(plugin_id, plugin_data, params)

    async def execute_mcp(self, mcp_id: str, params: dict) -> dict:
        """Execute/test MCP connection with real process execution"""
        mcp = self.get_mcp(mcp_id)
        if not mcp:
            raise ValueError(f"MCP not found: {mcp_id}")

        logger.info(f"Testing MCP: {mcp.name} ({mcp_id})")

        # Get the executor and execute with real MCP server test
        executor = get_tool_executor()

        # Convert MCP response to dict for executor
        mcp_data = {
            "name": mcp.name,
            "description": mcp.description,
            "instruction": mcp.instruction,
            "file_path": mcp.file_path,
            "mcp_type": mcp.mcp_type,
            "parameter": mcp.parameter,
            "requirement": mcp.requirement
        }

        return await executor.execute_mcp(mcp_id, mcp_data, params)

    async def execute_function(self, function_id: str, params: dict) -> dict:
        """Execute a function with real code execution"""
        function = self.get_function(function_id)
        if not function:
            raise ValueError(f"Function not found: {function_id}")

        logger.info(f"Executing function: {function.name} ({function_id})")

        # Get the executor and execute with real code
        executor = get_tool_executor()

        # Convert function response to dict for executor
        function_data = {
            "name": function.name,
            "description": function.description,
            "instruction": function.instruction,
            "file_path": function.file_path,
            "function_type": function.function_type,
            "parameter": function.parameter
        }

        return await executor.execute_function(function_id, function_data, params)

    async def execute_skill(self, skill_id: str, params: dict) -> dict:
        """Execute a computer use skill with real system operations"""
        skill = self.get_skill(skill_id)
        if not skill:
            raise ValueError(f"Skill not found: {skill_id}")

        logger.info(f"Executing skill: {skill.name} ({skill_id})")

        # Get the executor and execute with real system operations
        executor = get_tool_executor()

        # Convert skill response to dict for executor
        skill_data = {
            "name": skill.name,
            "description": skill.description,
            "instruction": skill.instruction,
            "skill_type": skill.skill_type,
            "file_path": skill.file_path,
            "parameter": skill.parameter
        }

        return await executor.execute_skill(skill_id, skill_data, params)
