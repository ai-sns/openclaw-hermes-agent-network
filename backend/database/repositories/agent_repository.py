"""Agent repository with specialized CRUD operations."""
from typing import List, Optional
from datetime import datetime
from sqlalchemy import desc, asc, or_
from .base import BaseRepository
from ..models.agent import AgentCfg
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
