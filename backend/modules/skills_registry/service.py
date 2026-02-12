from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

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
            db.query(AgentDocSkill).filter(AgentDocSkill.agent_id == agent_id).delete()
            for idx, key in enumerate(skill_keys):
                db.add(
                    AgentDocSkill(
                        agent_id=agent_id,
                        skill_key=str(key),
                        enabled=True,
                        priority=max(0, (len(skill_keys) - idx)),
                    )
                )
            db.commit()
        except Exception:
            db.rollback()
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
