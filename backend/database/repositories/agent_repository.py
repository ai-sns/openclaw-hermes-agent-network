"""Agent repository with specialized CRUD operations."""
from typing import List, Optional
from datetime import datetime
from sqlalchemy import desc, asc, or_
from .base import BaseRepository
from ..models.agent import AgentCfg, AgentTask, AgentTaskMulti, MutiAgentCfg
from backend.config.database import get_db_session as get_session


class AgentCfgRepository(BaseRepository[AgentCfg]):
    """Agent configuration repository."""

    def __init__(self):
        super().__init__(AgentCfg)

    def get_all_ordered(self, **filters) -> List[AgentCfg]:
        """Get all agents ordered by position."""
        session = get_session()
        try:
            return session.query(self.model).filter_by(**filters).order_by(asc(AgentCfg.position)).all()
        finally:
            session.close()

    def get_system_prompt(self, name: str) -> Optional[str]:
        """Get agent system prompt by name."""
        session = get_session()
        try:
            agent = session.query(self.model).filter_by(name=name).first()
            return agent.prompt if agent else None
        finally:
            session.close()

    def get_specialization(self, name: str) -> Optional[str]:
        """Get agent specialization by name."""
        session = get_session()
        try:
            agent = session.query(self.model).filter_by(name=name).first()
            return agent.specialization if agent else None
        finally:
            session.close()


class AgentTaskRepository(BaseRepository[AgentTask]):
    """Agent task repository."""

    def __init__(self):
        super().__init__(AgentTask)

    def create_with_id(self, **kwargs) -> int:
        """Create task and return its ID."""
        from db.write_queue import db_write
        _model = self.model
        def _do(session):
            task = _model(**kwargs)
            session.add(task)
            session.flush()
            return task.id
        return db_write(_do, description="repo_create_agent_task")

    def get_with_label_filter(self, label: bool = False, **kwargs) -> List[AgentTask]:
        """Get tasks with optional label filter."""
        session = get_session()
        try:
            filter_expr = [getattr(self.model, key) == value for key, value in kwargs.items()]
            if label:
                filter_expr.append(AgentTask.label.isnot(None))

            return session.query(self.model).filter(*filter_expr).order_by(
                desc(AgentTask.stick_time), desc(AgentTask.create_time)
            ).limit(500).all()
        except Exception as e:
            return []
        finally:
            session.close()

    def get_labels_by_agent(self, agent_id: str) -> List[str]:
        """Get distinct labels for an agent."""
        session = get_session()
        try:
            res = session.query(AgentTask.label).filter(
                AgentTask.is_first == True,
                AgentTask.agent_id == agent_id
            ).distinct().all()
            return [i.label for i in res if i.label is not None]
        finally:
            session.close()

    def get_conversation_content(self, id: int) -> List[AgentTask]:
        """Get full conversation content by first message ID."""
        session = get_session()
        try:
            first_msg = session.query(self.model).filter(
                AgentTask.is_first == True, AgentTask.id == id
            ).one_or_none()

            if not first_msg:
                return []

            return session.query(self.model).filter(
                AgentTask.task_id == first_msg.task_id
            ).order_by(asc(AgentTask.create_time)).all()
        finally:
            session.close()

    def search_content(self, label: bool = False, **kwargs) -> List[AgentTask]:
        """Search tasks by title, problem, or answer."""
        session = get_session()
        try:
            is_first = kwargs.get('is_first')
            agent_id = kwargs.get('agent_id')
            title_keyword = kwargs.get('title')
            problem_keyword = kwargs.get('problem')
            answer_keyword = kwargs.get('answer')

            query = session.query(self.model)

            if is_first is not None:
                query = query.filter(AgentTask.is_first == is_first)
            if agent_id is not None:
                query = query.filter(AgentTask.agent_id == agent_id)
            if title_keyword == "":
                query = query.filter(AgentTask.is_first == True)
            if label:
                query = query.filter(AgentTask.label.isnot(None))

            search_terms = []
            if title_keyword:
                search_terms.append(AgentTask.title.contains(title_keyword))
            if problem_keyword:
                search_terms.append(AgentTask.problem.contains(problem_keyword))
            if answer_keyword:
                search_terms.append(AgentTask.answer.contains(answer_keyword))

            if search_terms:
                query = query.filter(or_(*search_terms))

            return query.order_by(desc(AgentTask.stick_time), desc(AgentTask.create_time)).limit(50000).all()
        finally:
            session.close()

    def update_stick_time(self, id: int, action: int = 1):
        """Update stick time (pin/unpin)."""
        value = datetime.now() if action == 1 else None
        self.update(id, stick_time=value)

    def delete_by_task_id(self, id_value: int):
        """Delete all tasks with same task_id."""
        from db.write_queue import db_write
        _model = self.model
        def _do(session):
            task = session.query(_model).filter_by(id=id_value).first()
            if task:
                session.query(_model).filter_by(task_id=task.task_id).delete()
        db_write(_do, description="repo_delete_agent_task_by_task_id")


class AgentTaskMultiRepository(BaseRepository[AgentTaskMulti]):
    """Multi-agent task repository."""

    def __init__(self):
        super().__init__(AgentTaskMulti)

    def create_with_id(self, **kwargs) -> int:
        """Create task and return its ID."""
        from db.write_queue import db_write
        _model = self.model
        def _do(session):
            task = _model(**kwargs)
            session.add(task)
            session.flush()
            return task.id
        return db_write(_do, description="repo_create_agent_task_multi")

    def get_with_label_filter(self, label: bool = False, **kwargs) -> List[AgentTaskMulti]:
        """Get tasks with optional label filter."""
        session = get_session()
        try:
            filter_expr = [getattr(self.model, key) == value for key, value in kwargs.items()]
            if label:
                filter_expr.append(AgentTaskMulti.label.isnot(None))

            return session.query(self.model).filter(*filter_expr).order_by(
                desc(AgentTaskMulti.stick_time), desc(AgentTaskMulti.create_time)
            ).limit(500).all()
        except Exception as e:
            return []
        finally:
            session.close()

    def get_labels_by_group(self, group_id: str) -> List[str]:
        """Get distinct labels for a group."""
        session = get_session()
        try:
            res = session.query(AgentTaskMulti.label).filter(
                AgentTaskMulti.is_first == True,
                AgentTaskMulti.group_id == group_id
            ).distinct().all()
            return [i.label for i in res if i.label is not None]
        finally:
            session.close()

    def get_conversation_content(self, id: int) -> List[AgentTaskMulti]:
        """Get full conversation content by first message ID."""
        session = get_session()
        try:
            first_msg = session.query(self.model).filter(
                AgentTaskMulti.is_first == True, AgentTaskMulti.id == id
            ).one_or_none()

            if not first_msg:
                return []

            return session.query(self.model).filter(
                AgentTaskMulti.task_id == first_msg.task_id
            ).order_by(asc(AgentTaskMulti.create_time)).all()
        finally:
            session.close()

    def update_stick_time(self, id: int, action: int = 1):
        """Update stick time (pin/unpin)."""
        value = datetime.now() if action == 1 else None
        self.update(id, stick_time=value)

    def delete_by_task_id(self, id_value: int):
        """Delete all tasks with same task_id."""
        from db.write_queue import db_write
        _model = self.model
        def _do(session):
            task = session.query(_model).filter_by(id=id_value).first()
            if task:
                session.query(_model).filter_by(task_id=task.task_id).delete()
        db_write(_do, description="repo_delete_agent_task_multi_by_task_id")


class MutiAgentCfgRepository(BaseRepository[MutiAgentCfg]):
    """Multi-agent configuration repository."""

    def __init__(self):
        super().__init__(MutiAgentCfg)

    def create_with_id(self, **kwargs) -> int:
        """Create configuration and return its ID."""
        from db.write_queue import db_write
        _model = self.model
        def _do(session):
            cfg = _model(**kwargs)
            session.add(cfg)
            session.flush()
            return cfg.id
        return db_write(_do, description="repo_create_muti_agent_cfg")

    def get_all_ordered(self, **filters) -> List[MutiAgentCfg]:
        """Get all configurations ordered by position."""
        session = get_session()
        try:
            return session.query(self.model).filter_by(**filters).order_by(asc(MutiAgentCfg.position)).all()
        finally:
            session.close()
