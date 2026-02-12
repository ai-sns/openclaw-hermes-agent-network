from __future__ import annotations

import json
import os
import shutil
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import yaml


@dataclass(frozen=True)
class DocSkill:
    skill_key: str
    name: str
    description: str
    location: str
    source: str
    frontmatter: Dict[str, Any]
    requires: Dict[str, Any]
    install: Any
    runner: Optional[Dict[str, Any]]


class DocSkillRegistry:
    def __init__(
        self,
        workspace_dir: str,
        managed_dir: str,
    ):
        self.workspace_dir = Path(workspace_dir)
        self.managed_dir = Path(managed_dir)
        self._cache: Dict[str, DocSkill] = {}
        self._cache_time: Optional[datetime] = None

    def refresh(self) -> None:
        self._cache = self._scan_all()
        self._cache_time = datetime.now()

    def _scan_all(self) -> Dict[str, DocSkill]:
        skills: Dict[str, DocSkill] = {}

        for base_dir, source in [
            (self.managed_dir, "managed"),
            (self.workspace_dir, "workspace"),
        ]:
            if not base_dir.exists():
                continue

            for skill_md in base_dir.rglob("SKILL.md"):
                parsed = self._parse_skill_md(skill_md)
                if not parsed:
                    continue

                doc_skill = parsed
                skills[doc_skill.skill_key] = doc_skill

        return skills

    def _parse_skill_md(self, path: Path) -> Optional[DocSkill]:
        try:
            raw = path.read_text(encoding="utf-8")
        except Exception:
            return None

        fm, _body = self._split_frontmatter(raw)
        if not fm:
            return None

        name = str(fm.get("name") or "").strip()
        if not name:
            return None

        skill_key = str(fm.get("skill_key") or fm.get("skillKey") or name).strip()
        description = str(fm.get("description") or "").strip()

        requires = fm.get("requires") or {}
        if isinstance(requires, str):
            try:
                requires = json.loads(requires)
            except Exception:
                requires = {}
        if not isinstance(requires, dict):
            requires = {}

        install = fm.get("install")
        runner = fm.get("runner")

        location = str(path.resolve())
        source = "workspace" if self.workspace_dir in path.parents else "managed"

        return DocSkill(
            skill_key=skill_key,
            name=name,
            description=description,
            location=location,
            source=source,
            frontmatter=fm,
            requires=requires,
            install=install,
            runner=runner if isinstance(runner, dict) else None,
        )

    def _split_frontmatter(self, text: str) -> Tuple[Dict[str, Any], str]:
        if not text.startswith("---"):
            return {}, text

        parts = text.split("---", 2)
        if len(parts) < 3:
            return {}, text

        fm_text = parts[1]
        body = parts[2]
        try:
            fm = yaml.safe_load(fm_text) or {}
        except Exception:
            fm = {}

        if not isinstance(fm, dict):
            return {}, text

        return fm, body

    def list_all(self) -> List[DocSkill]:
        if not self._cache:
            self.refresh()
        return list(self._cache.values())

    def get(self, skill_key: str) -> Optional[DocSkill]:
        if not self._cache:
            self.refresh()
        return self._cache.get(skill_key)

    def is_eligible(self, skill: DocSkill) -> Tuple[bool, List[str]]:
        missing: List[str] = []
        requires = skill.requires or {}

        os_req = requires.get("os")
        if os_req:
            os_name = "win32" if os.name == "nt" else os.uname().sysname.lower()
            if isinstance(os_req, str):
                if os_req.lower() not in os_name.lower():
                    missing.append(f"os:{os_req}")
            elif isinstance(os_req, list):
                if not any(str(x).lower() in os_name.lower() for x in os_req):
                    missing.append(f"os:{os_req}")

        bins = requires.get("bins")
        if isinstance(bins, str):
            bins = [bins]
        if isinstance(bins, list):
            for b in bins:
                if b and not shutil.which(str(b)):
                    missing.append(f"bin:{b}")

        any_bins = requires.get("anyBins")
        if isinstance(any_bins, str):
            any_bins = [any_bins]
        if isinstance(any_bins, list) and any_bins:
            if not any(shutil.which(str(b)) for b in any_bins if b):
                missing.append("anyBins:" + ",".join(str(b) for b in any_bins))

        always = requires.get("always")
        if always is True:
            return True, []

        return len(missing) == 0, missing

    def build_available_skills_prompt(self, skills: List[DocSkill]) -> str:
        if not skills:
            return ""

        lines: List[str] = []
        lines.append("\n\nSkills (mandatory):")
        lines.append("- First scan <available_skills> and decide whether a skill is applicable.")
        lines.append("- If a skill is applicable, call read_skill with its skill_key to read its SKILL.md, then follow it.")
        lines.append("- After reading SKILL.md: if it declares a frontmatter runner, call run_doc_skill with that skill_key to execute it, then use the execution result to answer the user.")
        lines.append("- Do not read multiple skills at once; read at most one relevant skill.")
        lines.append("\n<available_skills>")
        for s in sorted(skills, key=lambda x: x.skill_key.lower()):
            lines.append(f"<skill>")
            lines.append(f"<skill_key>{s.skill_key}</skill_key>")
            lines.append(f"<name>{s.name}</name>")
            if s.description:
                lines.append(f"<description>{s.description}</description>")
            lines.append(f"<location>{s.location}</location>")
            lines.append(f"</skill>")
        lines.append("</available_skills>")
        return "\n".join(lines)

    def read_skill_markdown(self, skill_key: str) -> Optional[str]:
        skill = self.get(skill_key)
        if not skill:
            return None
        try:
            return Path(skill.location).read_text(encoding="utf-8")
        except Exception:
            return None

    def write_skill_markdown(self, skill_key: str, markdown: str) -> None:
        skill = self.get(skill_key)
        if not skill:
            raise ValueError(f"Skill not found: {skill_key}")

        skill_path = self._get_workspace_skill_path(skill)
        skill_path.write_text(markdown or "", encoding="utf-8")
        self.refresh()

    def delete_skill(self, skill_key: str) -> None:
        skill = self.get(skill_key)
        if not skill:
            raise ValueError(f"Skill not found: {skill_key}")

        skill_path = self._get_workspace_skill_path(skill)
        skill_dir = skill_path.parent

        workspace_root = self.workspace_dir.resolve()
        skill_dir_resolved = skill_dir.resolve()
        if str(skill_dir_resolved) == str(workspace_root):
            raise PermissionError("Refusing to delete workspace skills root")

        shutil.rmtree(str(skill_dir_resolved))
        self.refresh()

    def _get_workspace_skill_path(self, skill: DocSkill) -> Path:
        if skill.source != "workspace":
            raise PermissionError("Only workspace skills can be modified")

        workspace_root = self.workspace_dir.resolve()
        skill_path = Path(skill.location).resolve()

        try:
            common = os.path.commonpath([str(workspace_root), str(skill_path)])
        except Exception:
            common = ""

        if str(common) != str(workspace_root):
            raise PermissionError("Invalid skill path")

        if skill_path.name.lower() != "skill.md":
            raise PermissionError("Only SKILL.md can be modified")

        return skill_path


_registry: Optional[DocSkillRegistry] = None


def get_docskill_registry() -> DocSkillRegistry:
    global _registry
    if _registry is None:
        project_root = Path(__file__).parent.parent.parent.parent
        workspace_dir = project_root / "skills"
        managed_dir = project_root / "db" / "skills"
        _registry = DocSkillRegistry(str(workspace_dir), str(managed_dir))
    return _registry
