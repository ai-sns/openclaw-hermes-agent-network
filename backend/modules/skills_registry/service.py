from __future__ import annotations

import json
import zipfile
import uuid
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from fastapi import HTTPException, UploadFile

from backend.config.database import get_db_session
from backend.database.models.agent import AgentDocSkill
from backend.database.models.system import SkillMng
from backend.modules.skills_registry.registry import DocSkill, get_docskill_registry
from backend.modules.tools.tool_executor import get_tool_executor


class DocSkillsService:
    def __init__(self):
        self.registry = get_docskill_registry()

    def refresh(self) -> None:
        self.registry.refresh()

    def list_skills(self, agent_id: Optional[int] = None, eligible_only: bool = False) -> List[Dict[str, Any]]:
        self.registry.refresh()
        skills = self._list_for_agent(agent_id)

        results: List[Dict[str, Any]] = []
        for s in skills:
            eligible, missing = self.registry.is_eligible(s)
            if eligible_only and not eligible:
                continue
            results.append(
                {
                    "skill_key": s.skill_key,
                    "name": s.name,
                    "description": s.description,
                    "location": s.location,
                    "source": s.source,
                    "eligible": eligible,
                    "missing": missing,
                    "runner": s.runner,
                    "install": s.install,
                    "requires": s.requires,
                }
            )
        return results

    def get_skill(self, skill_key: str) -> Optional[Dict[str, Any]]:
        self.registry.refresh()
        s = self.registry.get(skill_key)
        if not s:
            return None
        eligible, missing = self.registry.is_eligible(s)
        return {
            "skill_key": s.skill_key,
            "name": s.name,
            "description": s.description,
            "location": s.location,
            "source": s.source,
            "eligible": eligible,
            "missing": missing,
            "runner": s.runner,
            "install": s.install,
            "requires": s.requires,
            "frontmatter": s.frontmatter,
        }

    def read_skill_markdown(self, skill_key: str) -> Optional[str]:
        self.registry.refresh()
        return self.registry.read_skill_markdown(skill_key)

    def write_skill_markdown(self, skill_key: str, markdown: str) -> None:
        self.registry.write_skill_markdown(skill_key, markdown)

    def delete_skill(self, skill_key: str) -> None:
        self.registry.delete_skill(skill_key)

    def import_skill_zip(self, file: UploadFile) -> Dict[str, Any]:
        """Import a DocSkill zip into workspace skills/.

        Rules:
        - Accept only .zip uploads
        - Allow SKILL.md at zip root
        - Extract into a new folder under skills/
        - Validate frontmatter contains runner.kind and runner.target
        """

        filename = (file.filename or '').lower()
        if not filename.endswith('.zip'):
            raise HTTPException(status_code=400, detail='Only .zip files are supported')

        raw = file.file.read()
        if not raw:
            raise HTTPException(status_code=400, detail='Empty file')

        project_root = Path(__file__).parent.parent.parent.parent
        workspace_dir = (project_root / 'skills').resolve()
        workspace_dir.mkdir(parents=True, exist_ok=True)

        tmp_dir = workspace_dir / f"_tmp_import_{uuid.uuid4().hex[:10]}"
        tmp_dir.mkdir(parents=True, exist_ok=True)
        tmp_zip = tmp_dir / 'skill.zip'
        tmp_zip.write_bytes(raw)

        try:
            with zipfile.ZipFile(tmp_zip, 'r') as zf:
                names = zf.namelist()
                if not names:
                    raise HTTPException(status_code=400, detail='Zip is empty')

                # Find SKILL.md (prefer root)
                skill_md_candidates = [n for n in names if n and n.lower().endswith('skill.md') and not n.endswith('/')]
                if not skill_md_candidates:
                    raise HTTPException(status_code=400, detail='SKILL.md not found in zip')

                skill_md_path = None
                for c in skill_md_candidates:
                    if '/' not in c.strip('/') and '\\' not in c:
                        skill_md_path = c
                        break
                if not skill_md_path:
                    # fallback to shortest path
                    skill_md_path = sorted(skill_md_candidates, key=len)[0]

                zip_root_prefix = Path(skill_md_path).parent

                # Derive target folder name
                folder_name = Path(skill_md_path).parent.name
                if not folder_name:
                    folder_name = Path(file.filename or 'imported_skill').stem
                folder_name = ''.join(ch for ch in folder_name if ch.isalnum() or ch in ('-', '_')).strip('_-')
                if not folder_name:
                    folder_name = f"imported_skill_{uuid.uuid4().hex[:6]}"

                target_dir = (workspace_dir / folder_name).resolve()
                if target_dir.exists():
                    target_dir = (workspace_dir / f"{folder_name}_{uuid.uuid4().hex[:6]}").resolve()
                target_dir.mkdir(parents=True, exist_ok=True)

                target_root = target_dir.resolve()

                for member in zf.infolist():
                    member_name = member.filename
                    if not member_name or member_name.endswith('/'):
                        continue

                    if member_name.startswith('/') or member_name.startswith('\\'):
                        raise HTTPException(status_code=400, detail='Zip contains absolute paths')

                    dest_rel = Path(member_name)
                    if zip_root_prefix and zip_root_prefix != Path('.'):
                        try:
                            if dest_rel.parts[: len(zip_root_prefix.parts)] == zip_root_prefix.parts:
                                dest_rel = dest_rel.relative_to(zip_root_prefix)
                        except Exception:
                            dest_rel = Path(member_name)
                    dest = (target_dir / dest_rel).resolve()
                    if target_root not in dest.parents and dest != target_root:
                        raise HTTPException(status_code=400, detail='Zip contains unsafe paths')

                    dest.parent.mkdir(parents=True, exist_ok=True)
                    with zf.open(member, 'r') as src, open(dest, 'wb') as out:
                        out.write(src.read())

                # Ensure SKILL.md exists after extraction (in expected place).
                extracted_skill_md = (target_dir / 'SKILL.md').resolve()
                if not extracted_skill_md.exists():
                    raise HTTPException(status_code=400, detail='SKILL.md not found after extraction')

                parsed = self.registry._parse_skill_md(extracted_skill_md)
                if not parsed:
                    raise HTTPException(status_code=400, detail='Failed to parse SKILL.md frontmatter')

                runner = parsed.runner or {}
                kind = runner.get('kind')
                target = runner.get('target')
                if not kind or not target:
                    raise HTTPException(status_code=400, detail='SKILL.md runner.kind and runner.target are required')

                # Refresh and return imported skill
                self.registry.refresh()
                imported = self.registry.get(parsed.skill_key) or parsed
                return {
                    "skill_key": imported.skill_key,
                    "name": imported.name,
                    "description": imported.description,
                    "location": imported.location,
                    "source": imported.source,
                    "runner": imported.runner,
                }
        finally:
            try:
                if tmp_dir.exists():
                    for p in tmp_dir.rglob('*'):
                        pass
                    import shutil as _shutil
                    _shutil.rmtree(tmp_dir, ignore_errors=True)
            except Exception:
                pass

    def build_prompt_for_agent(self, agent_id: Optional[int]) -> str:
        skills = self._list_for_agent(agent_id)
        eligible_skills = [s for s in skills if self.registry.is_eligible(s)[0]]
        return self.registry.build_available_skills_prompt(eligible_skills)

    def get_agent_skill_keys(self, agent_id: int) -> List[str]:
        db = get_db_session()
        try:
            rows = (
                db.query(AgentDocSkill)
                .filter(AgentDocSkill.agent_id == agent_id, AgentDocSkill.enabled == True)
                .order_by(AgentDocSkill.priority.desc(), AgentDocSkill.create_time.asc())
                .all()
            )
            return [r.skill_key for r in rows]
        finally:
            db.close()

    def set_agent_skill_keys(self, agent_id: int, skill_keys: List[str]) -> None:
        db = get_db_session()
        try:
            from db.write_queue import db_write
            _aid = agent_id
            _keys = list(skill_keys)
            _count = len(skill_keys)
            def _do(session):
                session.query(AgentDocSkill).filter(AgentDocSkill.agent_id == _aid).delete()
                for idx, key in enumerate(_keys):
                    session.add(
                        AgentDocSkill(
                            agent_id=_aid,
                            skill_key=str(key),
                            enabled=True,
                            priority=max(0, (_count - idx)),
                        )
                    )
            db_write(_do, description="skills_registry_set_agent_skills")
        except Exception:
            raise
        finally:
            db.close()

    async def run_skill(self, skill_key: str, params: Dict[str, Any]) -> Dict[str, Any]:
        self.registry.refresh()
        s = self.registry.get(skill_key)
        if not s:
            return {"success": False, "error": f"Skill not found: {skill_key}"}

        runner = s.runner or {}
        kind = runner.get("kind")
        target = runner.get("target")

        if kind == "exec_skill":
            if not target:
                return {"success": False, "error": "runner.target missing"}
            return await self._run_exec_skill(str(target), params)

        if kind == "python_file":
            if not target:
                return {"success": False, "error": "runner.target missing"}
            return await self._run_python_file(s, str(target), params)

        if kind == "node_file":
            if not target:
                return {"success": False, "error": "runner.target missing"}
            return await self._run_node_file(s, str(target), params)

        if kind == "command":
            return {
                "success": False,
                "error": "command runner is not auto-executed in Phase 1",
                "suggestion": {"command": target, "note": "Copy and run manually"},
            }

        return {"success": False, "error": f"Unknown runner kind: {kind}"}

    def _list_for_agent(self, agent_id: Optional[int]) -> List[DocSkill]:
        all_skills = self.registry.list_all()
        if agent_id is None:
            return all_skills

        enabled_keys = self.get_agent_skill_keys(agent_id)
        if not enabled_keys:
            return []

        enabled_set = set(enabled_keys)
        filtered = [s for s in all_skills if s.skill_key in enabled_set]
        # keep stable ordering by enabled_keys priority if possible
        key_to_skill = {s.skill_key: s for s in filtered}
        ordered = [key_to_skill[k] for k in enabled_keys if k in key_to_skill]
        return ordered

    async def _run_exec_skill(self, skill_id: str, params: Dict[str, Any]) -> Dict[str, Any]:
        db = get_db_session()
        try:
            skill_obj = db.query(SkillMng).filter(SkillMng.skill_id == skill_id, SkillMng.is_delete == False).first()
            if not skill_obj:
                return {"success": False, "error": f"ExecSkill not found: {skill_id}"}
            skill_data = {c.name: getattr(skill_obj, c.name) for c in skill_obj.__table__.columns}
        finally:
            db.close()

        executor = get_tool_executor()
        result = await executor.execute_skill(skill_id, skill_data, params)
        return {"success": True, "result": result}

    async def _run_python_file(self, doc_skill: DocSkill, target: str, params: Dict[str, Any]) -> Dict[str, Any]:
        base_dir = Path(doc_skill.location).parent
        path = Path(target)
        if not path.is_absolute():
            path = (base_dir / path).resolve()

        if not path.exists():
            return {"success": False, "error": f"python_file not found: {str(path)}"}

        executor = get_tool_executor()
        # using existing executor helper
        exec_result = await executor._execute_python_file(str(path), params)

        parsed = None
        try:
            stdout = (exec_result or {}).get("stdout") if isinstance(exec_result, dict) else None
            if isinstance(stdout, str):
                stdout_trimmed = stdout.strip()
                if stdout_trimmed.startswith("{") and stdout_trimmed.endswith("}"):
                    parsed = json.loads(stdout_trimmed)
        except Exception:
            parsed = None

        if isinstance(exec_result, dict):
            exec_result = {**exec_result, "parsed": parsed}

        return {"success": True, "result": exec_result}

    async def _run_node_file(self, doc_skill: DocSkill, target: str, params: Dict[str, Any]) -> Dict[str, Any]:
        base_dir = Path(doc_skill.location).parent
        path = Path(target)
        if not path.is_absolute():
            path = (base_dir / path).resolve()

        if not path.exists():
            return {"success": False, "error": f"node_file not found: {str(path)}"}

        executor = get_tool_executor()
        exec_result = await executor._execute_javascript_file(str(path), params)

        parsed = None
        try:
            stdout = (exec_result or {}).get("stdout") if isinstance(exec_result, dict) else None
            if isinstance(stdout, str):
                stdout_trimmed = stdout.strip()
                if stdout_trimmed.startswith("{") and stdout_trimmed.endswith("}"):
                    parsed = json.loads(stdout_trimmed)
        except Exception:
            parsed = None

        if isinstance(exec_result, dict):
            exec_result = {**exec_result, "parsed": parsed}

        return {"success": True, "result": exec_result}


_service: Optional[DocSkillsService] = None


def get_docskills_service() -> DocSkillsService:
    global _service
    if _service is None:
        _service = DocSkillsService()
    return _service
