"""Chat repository with specialized CRUD operations."""
from typing import List, Optional
from datetime import datetime
from sqlalchemy import desc, asc, or_, func
from sqlalchemy.orm import aliased
from .base import BaseRepository
from ..models.chat import AIChatMessages, AIFriend, AiChatCfg
from backend.config.database import get_db_session as get_session


class AIChatMessagesRepository(BaseRepository[AIChatMessages]):
    """AI chat messages repository."""

    def __init__(self):
        super().__init__(AIChatMessages)

    def get_previous_messages(self, last_record_id: Optional[int] = None, count: int = 20, **kwargs) -> List[AIChatMessages]:
        """Get previous messages with pagination."""
        session = get_session()
        try:
            query = session.query(self.model)
            if last_record_id is not None:
                query = query.filter(AIChatMessages.id < last_record_id)
            return query.filter_by(**kwargs).order_by(desc(AIChatMessages.create_time)).limit(count).all()
        finally:
            session.close()

    def get_all_ordered(self, label: bool = False, **kwargs) -> List[AIChatMessages]:
        """Get all messages ordered by stick time and create time."""
        session = get_session()
        try:
            query = session.query(self.model)
            if label:
                query = query.filter(AIChatMessages.label.isnot(None))

            return query.filter_by(**kwargs).order_by(
                desc(AIChatMessages.stick_time), desc(AIChatMessages.create_time)
            ).limit(20).all()
        finally:
            session.close()

    def get_conversation_summaries(self, limit: int = 50, agent_id: Optional[int] = None) -> List[dict]:
        session = get_session()
        try:
            last_message_sq = session.query(
                AIChatMessages.conversation_id.label('conversation_id'),
                func.max(AIChatMessages.create_time).label('last_message_time')
            ).filter(
                AIChatMessages.is_delete == False,
            )
            if agent_id is not None:
                last_message_sq = last_message_sq.filter(AIChatMessages.agent_id == agent_id)
            last_message_sq = last_message_sq.group_by(AIChatMessages.conversation_id).subquery()

            first_msg = aliased(AIChatMessages)
            q = session.query(
                first_msg.conversation_id,
                first_msg.agent_id,
                first_msg.title,
                first_msg.content,
                first_msg.stick_time,
                first_msg.label,
                last_message_sq.c.last_message_time,
            ).join(
                last_message_sq,
                last_message_sq.c.conversation_id == first_msg.conversation_id,
            ).filter(
                first_msg.is_first == True,
                first_msg.is_delete == False,
            )
            if agent_id is not None:
                q = q.filter(first_msg.agent_id == agent_id)

            rows = q.order_by(
                desc(first_msg.stick_time),
                desc(last_message_sq.c.last_message_time),
            ).limit(limit).all()

            result = []
            for r in rows:
                result.append({
                    'conversation_id': r[0],
                    'agent_id': r[1],
                    'title': r[2] or (r[3] or '')[:50],
                    'first_message': (r[3] or '')[:100],
                    'stick_time': r[4],
                    'label': r[5],
                    'last_message_time': r[6],
                })
            return result
        finally:
            session.close()

    def get_labels(self, is_first: bool, owner_account: str, friend_account: str) -> List[str]:
        """Get distinct labels."""
        session = get_session()
        try:
            res = session.query(AIChatMessages.label).filter(
                AIChatMessages.is_first == True,
                AIChatMessages.owner_account == owner_account,
                AIChatMessages.friend_account == friend_account
            ).distinct().all()
            return [i.label for i in res if i.label is not None]
        finally:
            session.close()

    def search_content(self, label: bool = False, **kwargs) -> List[AIChatMessages]:
        """Search messages by title or content."""
        session = get_session()
        try:
            is_first = kwargs.get('is_first')
            owner_account = kwargs.get('owner_account')
            friend_account = kwargs.get('friend_account')
            title_keyword = kwargs.get('title')
            content_keyword = kwargs.get('content')

            query = session.query(self.model)

            if is_first is not None:
                query = query.filter(AIChatMessages.is_first == is_first)
            if owner_account is not None:
                query = query.filter(AIChatMessages.owner_account == owner_account)
            if friend_account is not None:
                query = query.filter(AIChatMessages.friend_account == friend_account)
            if title_keyword == "":
                query = query.filter(AIChatMessages.is_first == True)
            if label:
                query = query.filter(AIChatMessages.label.isnot(None))

            search_terms = []
            if title_keyword:
                search_terms.append(AIChatMessages.title.contains(title_keyword))
            if content_keyword:
                search_terms.append(AIChatMessages.content.contains(content_keyword))

            if search_terms:
                query = query.filter(or_(*search_terms))

            return query.order_by(desc(AIChatMessages.stick_time), desc(AIChatMessages.create_time)).limit(50000).all()
        finally:
            session.close()

    def get_conversation_content(self, id: int) -> List[AIChatMessages]:
        """Get full conversation content by first message ID."""
        session = get_session()
        try:
            first_msg = session.query(self.model).filter(
                AIChatMessages.is_first == True, AIChatMessages.id == id
            ).one_or_none()

            if not first_msg:
                return []

            return session.query(self.model).filter(
                AIChatMessages.conversation_id == first_msg.conversation_id
            ).order_by(asc(AIChatMessages.create_time)).all()
        finally:
            session.close()

    def update_stick_time(self, id: int, value: Optional[datetime] = None):
        """Update stick time."""
        self.update(id, stick_time=value)

    def get_first_by_conversation_id(self, conversation_id: str) -> Optional[AIChatMessages]:
        session = get_session()
        try:
            return session.query(self.model).filter(
                AIChatMessages.conversation_id == conversation_id,
                AIChatMessages.is_first == True,
                AIChatMessages.is_delete == False,
            ).order_by(desc(AIChatMessages.create_time)).first()
        finally:
            session.close()

    def soft_delete_conversation(self, conversation_id: str) -> int:
        from db.write_queue import db_write
        _cid = conversation_id
        def _do(session):
            affected = session.query(AIChatMessages).filter(
                AIChatMessages.conversation_id == _cid,
                AIChatMessages.is_delete == False,
            ).update({AIChatMessages.is_delete: True}, synchronize_session=False)
            return int(affected or 0)
        return db_write(_do, description="repo_soft_delete_conversation")

    def update_conversation_title(self, conversation_id: str, title: str) -> bool:
        from db.write_queue import db_write
        _cid = conversation_id
        _title = title
        def _do(session):
            affected = session.query(AIChatMessages).filter(
                AIChatMessages.conversation_id == _cid,
                AIChatMessages.is_first == True,
                AIChatMessages.is_delete == False,
            ).update({AIChatMessages.title: _title}, synchronize_session=False)
            return bool(affected)
        return db_write(_do, description="repo_update_conversation_title")

    def update_conversation_tag(self, conversation_id: str, tag: Optional[str]) -> bool:
        from db.write_queue import db_write
        clean_tag = None
        if tag is not None:
            t = str(tag).strip()
            clean_tag = t if t else None
        _cid = conversation_id
        _tag = clean_tag
        def _do(session):
            affected = session.query(AIChatMessages).filter(
                AIChatMessages.conversation_id == _cid,
                AIChatMessages.is_first == True,
                AIChatMessages.is_delete == False,
            ).update({AIChatMessages.label: _tag}, synchronize_session=False)
            return bool(affected)
        return db_write(_do, description="repo_update_conversation_tag")

    def toggle_conversation_pin(self, conversation_id: str) -> tuple[bool, Optional[datetime]]:
        from db.write_queue import db_write
        _cid = conversation_id
        def _do(session):
            first = session.query(AIChatMessages).filter(
                AIChatMessages.conversation_id == _cid,
                AIChatMessages.is_first == True,
                AIChatMessages.is_delete == False,
            ).order_by(desc(AIChatMessages.create_time)).first()
            if not first:
                return False, None
            new_value = None if first.stick_time else datetime.now()
            first.stick_time = new_value
            return True, new_value
        return db_write(_do, description="repo_toggle_conversation_pin")

    def get_tag_stats(self, agent_id: Optional[int] = None) -> List[dict]:
        session = get_session()
        try:
            q = session.query(AIChatMessages.label, func.count(AIChatMessages.id))
            q = q.filter(
                AIChatMessages.is_first == True,
                AIChatMessages.is_delete == False,
                AIChatMessages.label.isnot(None),
                AIChatMessages.label != "",
            )
            if agent_id is not None:
                q = q.filter(AIChatMessages.agent_id == agent_id)

            rows = q.group_by(AIChatMessages.label).order_by(AIChatMessages.label.asc()).all()
            return [{"tag": r[0], "count": int(r[1] or 0)} for r in rows]
        finally:
            session.close()


class AIFriendRepository(BaseRepository[AIFriend]):
    """AI friend repository."""

    def __init__(self):
        super().__init__(AIFriend)

    def get_all_ordered_by_update_time(self, **kwargs) -> List[AIFriend]:
        """Get all friends ordered by last message time."""
        session = get_session()
        try:
            return session.query(self.model).filter_by(**kwargs).order_by(desc(AIFriend.last_message_time)).all()
        finally:
            session.close()

    def update_by_account(self, account: str, owner_sns_account: str, **kwargs):
        """Update friend by account and owner."""
        filters = {'account': account, 'owner_sns_account': owner_sns_account}
        self.update_by_filter(filters, **kwargs)


class AiChatCfgRepository(BaseRepository[AiChatCfg]):
    """AI chat configuration repository."""

    def __init__(self):
        super().__init__(AiChatCfg)

    def create_with_id(self, **kwargs) -> int:
        """Create configuration and return its ID."""
        from db.write_queue import db_write
        _model = self.model
        def _do(session):
            cfg = _model(**kwargs)
            session.add(cfg)
            session.flush()
            return cfg.id
        return db_write(_do, description="repo_create_aichat_cfg")

    def get_all_ordered(self, **kwargs) -> List[AiChatCfg]:
        """Get all configurations ordered by position."""
        session = get_session()
        try:
            return session.query(self.model).filter_by(**kwargs).order_by(asc(AiChatCfg.position)).all()
        finally:
            session.close()

    def search_content(self, **kwargs) -> List[AiChatCfg]:
        """Search configurations by nickname or account."""
        session = get_session()
        try:
            nickname_keyword = kwargs.get('nickname')
            account_keyword = kwargs.get('account')

            query = session.query(self.model)

            search_terms = []
            if nickname_keyword:
                search_terms.append(AiChatCfg.nickname.contains(nickname_keyword))
            if account_keyword:
                search_terms.append(AiChatCfg.account.contains(account_keyword))

            if search_terms:
                query = query.filter(or_(*search_terms))

            return query.order_by(desc(AiChatCfg.create_time)).limit(50000).all()
        finally:
            session.close()

    def get_map_config(self) -> Optional[AiChatCfg]:
        """Get first map configuration."""
        session = get_session()
        try:
            return session.query(self.model).first()
        finally:
            session.close()

    def get_common_config(self) -> Optional[AiChatCfg]:
        """Get common configuration (second record)."""
        session = get_session()
        try:
            return session.query(self.model).offset(1).limit(1).first()
        finally:
            session.close()

    def get_map_settings(self, **kwargs) -> Optional[dict]:
        """Get map settings as dictionary."""
        session = get_session()
        try:
            record = session.query(self.model).filter_by(**kwargs).first()
            if record:
                return {
                    "nick_name": record.nickname,
                    "account": record.account,
                    "profile": record.sign,
                    "profession": record.profession,
                    "nationid": record.nationid,
                    "nationpassword": record.nationpassword,
                    "sns_url": record.sns_url,
                    "status": record.status,
                    "avatar": record.avatar,
                    "avatar3d": record.avatar3d,
                    "house3d": record.house3d,
                    "map_type": record.map_type,
                    "map_api_key": record.map_api_key,
                    "map_id": record.map_id,
                    "current_position": record.current_position,
                    "home_position": record.home_position,
                    "positionx": record.positionx,
                    "positiony": record.positiony,
                    "positionz": record.positionz,
                    "route_start": record.route_start,
                    "route_end": record.route_end,
                    "route_status": record.route_status,
                    "route_current_position": record.route_current_position,
                    "route": record.route
                }
            return None
        finally:
            session.close()

    def update_map_config(self, **kwargs):
        """Update first map configuration."""
        from db.write_queue import db_write
        _model = self.model
        def _do(session):
            record = session.query(_model).first()
            if record:
                for key, value in kwargs.items():
                    setattr(record, key, value)
        db_write(_do, description="repo_update_map_config")
