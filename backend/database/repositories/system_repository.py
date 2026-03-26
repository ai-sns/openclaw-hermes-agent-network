"""System repository with specialized CRUD operations."""
from typing import List, Optional
from datetime import datetime
from sqlalchemy import desc, asc, or_
from .base import BaseRepository
from ..models.system import (
    SystemCfg, LogsMng, SysConfig, SystemInit, KeyValue,
    PluginMng, FunctionMng, McpMng, SkillMng, WebMng, WorkflowMng,
    TaskSchedule, Prompt, PromptFrequent, LlmFrequent,
    Question, ModelMetrics, ToolList
)
from backend.config.database import get_db_session as get_session


class SystemCfgRepository(BaseRepository[SystemCfg]):
    """System configuration repository."""

    def __init__(self):
        super().__init__(SystemCfg)


class LogsMngRepository(BaseRepository[LogsMng]):
    """Logs management repository."""

    def __init__(self):
        super().__init__(LogsMng)


class SysConfigRepository(BaseRepository[SysConfig]):
    """System config repository."""

    def __init__(self):
        super().__init__(SysConfig)

    def get_language(self, **kwargs) -> Optional[str]:
        """Get system language."""
        session = get_session()
        try:
            record = session.query(self.model).filter_by(**kwargs).first()
            return record.lang if record else None
        finally:
            session.close()

    def update_language(self, lang: str, **kwargs):
        """Update system language."""
        from db.write_queue import db_write
        _model = self.model
        _kwargs = kwargs
        def _do(session):
            record = session.query(_model).filter_by(**_kwargs).first()
            if record:
                record.lang = lang
        db_write(_do, description="repo_update_language")


class SystemInitRepository(BaseRepository[SystemInit]):
    """System initialization repository."""

    def __init__(self):
        super().__init__(SystemInit)


class KeyValueRepository(BaseRepository[KeyValue]):
    """Key-value storage repository."""

    def __init__(self):
        super().__init__(KeyValue)

    def get_value(self, key: str) -> Optional[str]:
        """Get value by key."""
        session = get_session()
        try:
            result = session.query(self.model).filter_by(key=key).first()
            return result.value if result else None
        finally:
            session.close()

    def search_keys(self, search_text: str) -> List[KeyValue]:
        """Search keys by text."""
        session = get_session()
        try:
            return session.query(self.model).filter(KeyValue.key.like(f'%{search_text}%')).all()
        finally:
            session.close()

    def update_value(self, key: str, new_value: str):
        """Update value by key."""
        self.update_by_filter({'key': key}, value=new_value)

    def delete_by_key(self, key: str):
        """Delete by key."""
        self.delete_by_filter(key=key)


class PluginMngRepository(BaseRepository[PluginMng]):
    """Plugin management repository."""

    def __init__(self):
        super().__init__(PluginMng)

    def get_all_tools(self, **kwargs) -> List[PluginMng]:
        """Get all tool plugins."""
        session = get_session()
        try:
            query = session.query(self.model)
            plugin_types = ["Tool_Headless", "Tool_Gui"]
            query = query.filter(or_(PluginMng.plugin_type == pt for pt in plugin_types))

            if kwargs:
                query = query.filter_by(**kwargs)

            return query.order_by(desc(PluginMng.run_mode)).all()
        finally:
            session.close()

    def get_search_tools(self, **kwargs) -> List[PluginMng]:
        """Get search tool plugins."""
        session = get_session()
        try:
            query = session.query(self.model)
            plugin_types = ["Tool_Headless", "Tool_Gui"]
            query = query.filter(or_(PluginMng.plugin_type == pt for pt in plugin_types))
            query = query.filter(PluginMng.plugin_event.contains("search_before_ask"))

            if kwargs:
                query = query.filter_by(**kwargs)

            return query.order_by(desc(PluginMng.run_mode)).all()
        finally:
            session.close()

    def copy_plugin(self, plugin_id: str, new_plugin_id: str, **kwargs) -> Optional[PluginMng]:
        """Copy plugin record."""
        from db.write_queue import db_write
        def _do(session):
            record_to_copy = session.query(PluginMng).filter_by(plugin_id=plugin_id).first()
            if not record_to_copy:
                return None
            new_record = PluginMng(
                plugin_id=new_plugin_id,
                company=kwargs.get('company', record_to_copy.company),
                company_abbr=kwargs.get('company_abbr', record_to_copy.company_abbr),
                name=kwargs.get('name', record_to_copy.name),
                version=kwargs.get('version', record_to_copy.version),
                alias_name=kwargs.get('alias_name', record_to_copy.alias_name),
                filename=kwargs.get('filename', record_to_copy.filename),
                run_mode=kwargs.get('run_mode', record_to_copy.run_mode),
                run_scope=kwargs.get('run_scope', record_to_copy.run_scope),
                instruction=kwargs.get('instruction', record_to_copy.instruction),
                runtime_main=kwargs.get('runtime_main', record_to_copy.runtime_main),
                runtime_test=kwargs.get('runtime_test', record_to_copy.runtime_test),
                description=kwargs.get('description', record_to_copy.description),
                plugin_directory=kwargs.get('plugin_directory', record_to_copy.plugin_directory),
                plugin_type=kwargs.get('plugin_type', record_to_copy.plugin_type),
                plugin_executed=kwargs.get('plugin_executed', record_to_copy.plugin_executed),
                plugin_event=kwargs.get('plugin_event', record_to_copy.plugin_event),
                plugin_title=kwargs.get('plugin_title', record_to_copy.plugin_title),
                detail=kwargs.get('detail', record_to_copy.detail),
                creator=kwargs.get('creator', record_to_copy.creator),
                is_delete=record_to_copy.is_delete,
                create_time=datetime.now()
            )
            session.add(new_record)
            return new_record
        return db_write(_do, description="repo_copy_plugin")


class FunctionMngRepository(BaseRepository[FunctionMng]):
    """Function management repository."""

    def __init__(self):
        super().__init__(FunctionMng)

    def create_with_id(self, **kwargs) -> int:
        """Create function and return its ID."""
        from db.write_queue import db_write
        _model = self.model
        def _do(session):
            func = _model(**kwargs)
            session.add(func)
            session.flush()
            return func.id
        return db_write(_do, description="repo_create_function_mng")

    def update_by_function_id(self, function_id: str, **kwargs):
        """Update function by function_id."""
        self.update_by_filter({'function_id': function_id}, **kwargs)


class McpMngRepository(BaseRepository[McpMng]):
    """MCP management repository."""

    def __init__(self):
        super().__init__(McpMng)

    def create_with_id(self, **kwargs) -> int:
        """Create MCP and return its ID."""
        from db.write_queue import db_write
        _model = self.model
        def _do(session):
            mcp = _model(**kwargs)
            session.add(mcp)
            session.flush()
            return mcp.id
        return db_write(_do, description="repo_create_mcp_mng")

    def update_by_mcp_id(self, mcp_id: str, **kwargs):
        """Update MCP by mcp_id."""
        self.update_by_filter({'mcp_id': mcp_id}, **kwargs)


class SkillMngRepository(BaseRepository[SkillMng]):
    """Skill management repository."""

    def __init__(self):
        super().__init__(SkillMng)

    def create_with_id(self, **kwargs) -> int:
        """Create skill and return its ID."""
        from db.write_queue import db_write
        _model = self.model
        def _do(session):
            skill = _model(**kwargs)
            session.add(skill)
            session.flush()
            return skill.id
        return db_write(_do, description="repo_create_skill_mng")

    def update_by_skill_id(self, skill_id: str, **kwargs):
        """Update skill by skill_id."""
        self.update_by_filter({'skill_id': skill_id}, **kwargs)


class WebMngRepository(BaseRepository[WebMng]):
    """Web management repository."""

    def __init__(self):
        super().__init__(WebMng)

    def create_with_id(self, **kwargs) -> int:
        """Create web entry and return its ID."""
        from db.write_queue import db_write
        _model = self.model
        def _do(session):
            web = _model(**kwargs)
            session.add(web)
            session.flush()
            return web.id
        return db_write(_do, description="repo_create_web_mng")

    def get_all_ordered(self, **kwargs) -> List[WebMng]:
        """Get all web entries ordered by position."""
        session = get_session()
        try:
            return session.query(self.model).filter_by(**kwargs).order_by(asc(WebMng.position)).all()
        finally:
            session.close()

    def update_by_web_id(self, web_id: str, **kwargs):
        """Update web entry by web_id."""
        self.update_by_filter({'web_id': web_id}, **kwargs)


class WorkflowMngRepository(BaseRepository[WorkflowMng]):
    """Workflow management repository."""

    def __init__(self):
        super().__init__(WorkflowMng)

    def create_with_id(self, **kwargs) -> int:
        """Create workflow and return its ID."""
        from db.write_queue import db_write
        _model = self.model
        def _do(session):
            workflow = _model(**kwargs)
            session.add(workflow)
            session.flush()
            return workflow.id
        return db_write(_do, description="repo_create_workflow_mng")

    def copy_workflow(self, workflow_id: str, new_workflow_id: str) -> Optional[WorkflowMng]:
        """Copy workflow record."""
        from db.write_queue import db_write
        def _do(session):
            original = session.query(WorkflowMng).filter_by(workflow_id=workflow_id).first()
            if not original:
                return None
            new_workflow = WorkflowMng(
                workflow_id=new_workflow_id,
                title=original.title + "-Copy",
                description=original.description,
                instruction=original.instruction,
                workflow_event=original.workflow_event,
                detail=original.detail,
                timer_desc=original.timer_desc,
                timer_cron=original.timer_cron,
                creator=original.creator,
                is_delete=False,
                create_time=datetime.now()
            )
            session.add(new_workflow)
            return new_workflow
        return db_write(_do, description="repo_copy_workflow")


class TaskScheduleRepository(BaseRepository[TaskSchedule]):
    """Task schedule repository."""

    def __init__(self):
        super().__init__(TaskSchedule)

    def create_with_id(self, **kwargs) -> int:
        """Create task schedule and return its ID."""
        from db.write_queue import db_write
        _model = self.model
        def _do(session):
            schedule = _model(**kwargs)
            session.add(schedule)
            session.flush()
            return schedule.id
        return db_write(_do, description="repo_create_task_schedule")


class PromptRepository(BaseRepository[Prompt]):
    """Prompt repository."""

    def __init__(self):
        super().__init__(Prompt)

    def get_by_title(self, title: str) -> Optional[str]:
        """Get prompt content by title."""
        session = get_session()
        try:
            prompt = session.query(self.model).filter_by(title=title).first()
            return prompt.content if prompt else None
        finally:
            session.close()

    def get_content_by_id(self, id: int) -> Optional[str]:
        """Get prompt content by ID."""
        session = get_session()
        try:
            prompt = session.query(self.model).filter_by(id=id).first()
            return prompt.content if prompt else None
        finally:
            session.close()

    def get_all_ordered(self, **kwargs) -> List[Prompt]:
        """Get all prompts ordered by ID desc."""
        session = get_session()
        try:
            filter_expr = [getattr(self.model, key) == value for key, value in kwargs.items()]
            return session.query(self.model).filter(*filter_expr).order_by(desc(Prompt.id)).all()
        finally:
            session.close()

    def get_by_model_name(self, model_name: str) -> List[Prompt]:
        """Get prompts by model name (including empty/null)."""
        session = get_session()
        try:
            return session.query(self.model).filter(
                (Prompt.model_name == model_name) |
                (Prompt.model_name.is_(None)) |
                (Prompt.model_name == '')
            ).all()
        finally:
            session.close()


class PromptFrequentRepository(BaseRepository[PromptFrequent]):
    """Prompt frequent repository."""

    def __init__(self):
        super().__init__(PromptFrequent)

    def create_with_id(self, **kwargs) -> int:
        """Create prompt frequent and return its ID."""
        from db.write_queue import db_write
        _model = self.model
        def _do(session):
            frequent = _model(**kwargs)
            session.add(frequent)
            session.flush()
            return frequent.id
        return db_write(_do, description="repo_create_prompt_frequent")

    def get_all_ordered(self, **kwargs) -> List[PromptFrequent]:
        """Get all prompt frequents ordered by position."""
        session = get_session()
        try:
            filter_expr = [getattr(self.model, key) == value for key, value in kwargs.items()]
            return session.query(self.model).filter(*filter_expr).order_by(asc(PromptFrequent.position)).all()
        finally:
            session.close()

    def get_by_agent_id(self, agent_id: str) -> List[dict]:
        """Get prompt frequents by agent ID with prompt details."""
        session = get_session()
        try:
            query_result = session.query(self.model).filter(
                PromptFrequent.is_delete == 0,
                PromptFrequent.belong_to_agent_id == agent_id
            ).join(Prompt).order_by(PromptFrequent.position.asc()).all()

            return [
                {
                    "id": pf.id,
                    "prompt_id": pf.prompt_id,
                    "title": pf.prompt.title,
                    "content": pf.prompt.content,
                    "tags": pf.prompt.tags,
                    "creator": pf.creator,
                    "create_time": pf.create_time,
                    "is_delete": pf.is_delete
                }
                for pf in query_result
            ]
        finally:
            session.close()


class LlmFrequentRepository(BaseRepository[LlmFrequent]):
    """LLM frequent repository."""

    def __init__(self):
        super().__init__(LlmFrequent)

    def create_with_id(self, **kwargs) -> int:
        """Create LLM frequent and return its ID."""
        from db.write_queue import db_write
        _model = self.model
        def _do(session):
            frequent = _model(**kwargs)
            session.add(frequent)
            session.flush()
            return frequent.id
        return db_write(_do, description="repo_create_llm_frequent")

    def get_all_ordered(self, **kwargs) -> List[LlmFrequent]:
        """Get all LLM frequents ordered by position."""
        session = get_session()
        try:
            filter_expr = [getattr(self.model, key) == value for key, value in kwargs.items()]
            return session.query(self.model).filter(*filter_expr).order_by(asc(LlmFrequent.position)).all()
        finally:
            session.close()


class QuestionRepository(BaseRepository[Question]):
    """Question repository."""

    def __init__(self):
        super().__init__(Question)

    def get_limited(self, num: int = 0, **kwargs) -> List[Question]:
        """Get questions with optional limit."""
        session = get_session()
        try:
            query = session.query(self.model).filter_by(**kwargs)
            if num > 0:
                query = query.limit(num)
            return query.all()
        finally:
            session.close()


class ModelMetricsRepository(BaseRepository[ModelMetrics]):
    """Model metrics repository."""

    def __init__(self):
        super().__init__(ModelMetrics)


class ToolListRepository:
    """Tool list view repository (read-only)."""

    def __init__(self):
        self.model = ToolList

    def get_all(self, **kwargs) -> List[ToolList]:
        """Get all tools from view."""
        session = get_session()
        try:
            filter_expr = [getattr(self.model, key) == value for key, value in kwargs.items()]
            return session.query(self.model).filter(*filter_expr).order_by(desc(ToolList.id)).all()
        finally:
            session.close()

    def get_single(self, **kwargs) -> Optional[ToolList]:
        """Get single tool from view."""
        session = get_session()
        try:
            filter_expr = [getattr(self.model, key) == value for key, value in kwargs.items()]
            return session.query(self.model).filter(*filter_expr).order_by(desc(ToolList.id)).first()
        finally:
            session.close()
