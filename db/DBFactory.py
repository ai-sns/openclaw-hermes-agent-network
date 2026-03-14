import os

import sqlite3

from sqlalchemy import create_engine, Column, Integer, String, event
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import NullPool
from pathlib import Path

from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Boolean, Text, Float
from sqlalchemy.orm import relationship
from sqlalchemy import desc, asc
from sqlalchemy import or_, and_

Base = declarative_base()
DBPath = os.path.join(Path(__file__).resolve().parent, "db.sqlite")
print("DBPath", DBPath)
SQL_DATABASE_URL = fr"sqlite:///{DBPath}"
engine = create_engine(
    SQL_DATABASE_URL,
    connect_args={"check_same_thread": False, "timeout": 30},
    poolclass=NullPool,
)


@event.listens_for(engine, "connect")
def _sqlite_on_connect(dbapi_connection, connection_record):
    try:
        cursor = dbapi_connection.cursor()
        try:
            cursor.execute("PRAGMA journal_mode=WAL")
        except Exception:
            pass
        try:
            cursor.execute("PRAGMA synchronous=NORMAL")
        except Exception:
            pass
        try:
            cursor.execute("PRAGMA busy_timeout=30000")
        except Exception:
            pass
        try:
            cursor.execute("PRAGMA foreign_keys=ON")
        except Exception:
            pass
        cursor.close()
    except Exception:
        pass


Session = sessionmaker(bind=engine)

import time
import logging
_dbfactory_logger = logging.getLogger(__name__)


def _commit_with_retry(session, max_retries=3, base_delay=0.5):
    """Commit a session with retry on database lock errors (exponential backoff)."""
    for attempt in range(1, max_retries + 1):
        try:
            session.commit()
            return
        except Exception as e:
            err_msg = str(e).lower()
            if 'database is locked' in err_msg and attempt < max_retries:
                wait = base_delay * (2 ** (attempt - 1))
                _dbfactory_logger.warning(
                    "[DBFactory] database is locked on commit (attempt %d/%d), retrying in %.1fs...",
                    attempt, max_retries, wait
                )
                session.rollback()
                time.sleep(wait)
            else:
                raise


class User(Base):
    __tablename__ = 'users'

    id = Column(Integer, primary_key=True)
    name = Column(String)
    age = Column(Integer)


class Company(Base):
    __tablename__ = 'company'

    id = Column(Integer, primary_key=True)
    companyname = Column(String)
    employee = Column(Integer)


class AIChatMessages(Base):
    __tablename__ = 'ai_chat_messages'
    id = Column(Integer, primary_key=True, autoincrement=True)
    conversation_id = Column(String(50))
    agent_id = Column(Integer, default=None)
    flag = Column(Integer)
    title = Column(Text, default=None)
    content = Column(Text)
    attachment_list = Column(Text)
    document_content = Column(Text)
    image_json = Column(Text)
    km_list = Column(Text)
    km_content = Column(Text)
    owner_name = Column(String(100))
    owner_account = Column(String(100))
    friend_name = Column(String(100))
    friend_account = Column(String(100))
    create_time = Column(DateTime, default=datetime.now)
    is_delete = Column(Boolean, default=False)
    is_first = Column(Boolean, default=False)
    stick_time = Column(DateTime, nullable=True)
    label = Column(String(50))


def add_AIChatMessages(conversation_id, flag, title, content, owner_name, owner_account, friend_name, friend_account,
                       is_first=False, attachment_list="", document_content="", image_json="", km_list="",
                       km_content=""):
    session = Session()
    try:
        try:
            from backend.apps.sns.message_formatter import format_internal_xmpp_message_for_storage
            content = format_internal_xmpp_message_for_storage(content)
        except Exception:
            pass

        ai_friend = AIChatMessages(conversation_id=conversation_id, flag=flag, title=title, content=content,
                                   owner_name=owner_name, owner_account=owner_account, friend_name=friend_name,
                                   friend_account=friend_account, is_first=is_first, attachment_list=attachment_list,
                                   document_content=document_content, image_json=image_json, km_list=km_list,
                                   km_content=km_content)
        session.add(ai_friend)
        _commit_with_retry(session)
    finally:
        session.close()


def query_map_activity_previous(last_record_id=None, count=20, type_str=None):
    session = Session()

    query = session.query(MapActivity)

    if last_record_id is not None:
        query = query.filter(MapActivity.id < last_record_id)

    if type_str:
        query = query.filter(MapActivity.type == type_str)

    records = query.order_by(MapActivity.id.desc()).limit(count).all()

    session.close()
    return records


def query_AIChatMessages_All_previous(last_record_id=None, count=20, **kwargs):
    session = Session()
    query = session.query(AIChatMessages)
    if last_record_id is not None:
        query = query.filter(AIChatMessages.id < last_record_id)
    records = query.filter_by(**kwargs).order_by(desc(AIChatMessages.create_time)).limit(count).all()
    session.close()
    return records


def query_AIChatMessages_All(label: bool = False, limit: int = None, **kwargs):
    session = Session()

    if label:
        query = session.query(AIChatMessages).filter(AIChatMessages.label.isnot(None)).filter_by(
            **kwargs).order_by(desc(AIChatMessages.stick_time),
                               desc(AIChatMessages.create_time))
    else:
        query = session.query(AIChatMessages).filter_by(**kwargs).order_by(desc(AIChatMessages.stick_time),
                                                                           desc(AIChatMessages.create_time))

    if limit is not None:
        query = query.limit(limit)

    records = query.all()
    session.close()
    return records


def query_AIChatMessages(**kwargs):
    session = Session()
    record = session.query(AIChatMessages).filter_by(**kwargs).first()
    session.close()
    return record


def query_AIChatMessages_ById(id):
    session = Session()
    res = session.query(AIChatMessages).filter(AIChatMessages.is_first == True, AIChatMessages.id == id).one_or_none()
    session.close()

    return res


def query_AIChatMessages_ByLabel(is_first, owner_account, friend_account):
    session = Session()

    res = session.query(AIChatMessages.label).filter(AIChatMessages.is_first == True,
                                                     AIChatMessages.owner_account == owner_account,
                                                     AIChatMessages.friend_account == friend_account, ).distinct().all()
    session.close()
    if res is None:
        labels = []
    else:
        labels = [i.label for i in res if i.label is not None]
    return labels


def query_AIChatMessages_Search_Content(label: bool = False, **kwargs):
    session = Session()

    is_first = kwargs.get('is_first', None)
    owner_account = kwargs.get('owner_account', None)
    friend_account = kwargs.get('friend_account', None)

    title_keyword = kwargs.get('title', None)
    content_keyword = kwargs.get('content', None)

    query = session.query(AIChatMessages)

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

    tasks = query.order_by(desc(AIChatMessages.stick_time), desc(AIChatMessages.create_time)).limit(50000).all()

    session.close()
    return tasks


def query_AIChatMessages_Search_First(agent_id, task_id, label: bool = False):
    session = Session()

    if bool:
        first_task = session.query(AIChatMessages) \
            .filter(AIChatMessages.agent_id == agent_id, AIChatMessages.conversation_id == task_id,
                    AIChatMessages.is_first == True) \
            .first()
    else:
        first_task = session.query(AIChatMessages) \
            .filter(AIChatMessages.agent_id == agent_id, AIChatMessages.conversation_id == task_id,
                    AIChatMessages.is_first == True, AgentTask.label is not None) \
            .first()

    session.close()
    return first_task


def update_AIChatMessages(id, **kwargs):
    session = Session()
    record = session.query(AIChatMessages).filter_by(id=id).first()
    if record:
        for key, value in kwargs.items():
            setattr(record, key, value)
        session.commit()
    session.close()


def update_AIChatMessages_stick(id, value=None, key: str = 'stick_time'):
    session = Session()
    task = session.query(AIChatMessages).filter_by(id=id).first()
    if task:
        setattr(task, key, value)
        session.commit()
    session.close()


def delete_AIChatMessages(id):
    session = Session()
    record = session.query(AIChatMessages).filter_by(id=id).first()
    if record:
        session.delete(record)
        session.commit()
    session.close()


def query_AIChat_Content(id, **kwargs):
    session = Session()
    res = session.query(AIChatMessages).filter(AIChatMessages.is_first == True, AIChatMessages.id == id).one_or_none()
    if res:
        conversation_id = res.conversation_id
    tasks = session.query(AIChatMessages).filter(AIChatMessages.conversation_id == conversation_id).order_by(
        asc(AIChatMessages.create_time)).all()

    session.close()

    return tasks


def query_AIChat_Search_Content(**kwargs):
    session = Session()

    is_first = kwargs.get('is_first', None)
    agent_id = kwargs.get('agent_id', None)

    title_keyword = kwargs.get('title', None)
    problem_keyword = kwargs.get('problem', None)
    answer_keyword = kwargs.get('answer', None)

    query = session.query(AgentTask)

    if is_first is not None:
        query = query.filter(AgentTask.is_first == is_first)
    if agent_id is not None:
        query = query.filter(AgentTask.agent_id == agent_id)

    if title_keyword == "":
        query = query.filter(AgentTask.is_first == True)

    search_terms = []
    if title_keyword:
        search_terms.append(AgentTask.title.contains(title_keyword))
    if problem_keyword:
        search_terms.append(AgentTask.problem.contains(problem_keyword))
    if answer_keyword:
        search_terms.append(AgentTask.answer.contains(answer_keyword))

    if search_terms:
        query = query.filter(or_(*search_terms))

    tasks = query.order_by(desc(AgentTask.create_time)).limit(50000).all()

    session.close()
    return tasks


def query_AIChat_Search_First(agent_id, task_id):
    session = Session()

    first_task = session.query(AgentTask) \
        .filter(AgentTask.agent_id == agent_id, AgentTask.task_id == task_id, AgentTask.is_first == True) \
        .first()

    session.close()
    return first_task


class AIFriend(Base):
    __tablename__ = 'ai_friend'
    id = Column(Integer, primary_key=True, autoincrement=True)
    account = Column(String(100))
    nick_name = Column(String(200))
    groups = Column(Text)
    owner_sns_account = Column(String(100))
    memo = Column(Text)
    sign = Column(String(200))
    subscription = Column(String(100))
    name = Column(String(200))
    borndate = Column(String(100))
    gender = Column(Integer)
    area = Column(String(100))
    city = Column(String(100))
    address = Column(String(200))
    mail = Column(String(100))
    phone = Column(String(100))
    organization = Column(String(200))
    title = Column(String(100))
    position = Column(String(100))
    new_message_flag = Column(Boolean, default=False)
    last_message_time = Column(DateTime)
    is_delete = Column(Boolean, default=False)
    create_time = Column(DateTime, default=datetime.now)


def add_AIFriend(account, nick_name, groups, owner_sns_account, memo, sign, subscription, name, borndate, gender, area, city, address, mail, phone, organization, title, position):
    session = Session()
    ai_friend = AIFriend(account=account, nick_name=nick_name, groups=groups, owner_sns_account=owner_sns_account, memo=memo, sign=sign, subscription=subscription, name=name, borndate=borndate, gender=gender, area=area, city=city, address=address, mail=mail, phone=phone, organization=organization, title=title, position=position)
    session.add(ai_friend)
    session.commit()
    session.close()


def query_AIFriend_All(**kwargs):
    session = Session()
    records = session.query(AIFriend).filter_by(**kwargs).all()
    session.close()
    return records


def query_AIFriend_All_Orderby_Updatetime(**kwargs):
    session = Session()
    records = session.query(AIFriend).filter_by(**kwargs).order_by(desc(AIFriend.last_message_time)).all()
    session.close()
    return records


def query_AIFriend(**kwargs):
    session = Session()
    record = session.query(AIFriend).filter_by(**kwargs).first()
    session.close()
    return record


def update_AIFriend_ById(id, **kwargs):
    session = Session()
    record = session.query(AIFriend).filter_by(id=id).first()
    if record:
        for key, value in kwargs.items():
            setattr(record, key, value)
        session.commit()
    session.close()


def update_AIFriend(account, owner_sns_account, **kwargs):
    session = Session()
    record = session.query(AIFriend).filter_by(account=account, owner_sns_account=owner_sns_account).first()
    if record:
        for key, value in kwargs.items():
            setattr(record, key, value)
        session.commit()
    session.close()


def delete_AIFriend(id):
    session = Session()
    record = session.query(AIFriend).filter_by(id=id).first()
    if record:
        session.delete(record)
        session.commit()
    session.close()


class AIChatInform(Base):
    __tablename__ = 'ai_chat_inform'
    id = Column(Integer, primary_key=True, autoincrement=True)
    inform_id = Column(String(50))
    title = Column(Text, default=None)
    content = Column(Text)
    type = Column(String(100))
    status = Column(String(100))
    owner_name = Column(String(100))
    owner_account = Column(String(100))
    friend_name = Column(String(100))
    friend_account = Column(String(100))
    create_time = Column(DateTime, default=datetime.now)
    is_delete = Column(Boolean, default=False)


def add_AIChatInform(inform_id, title, content, type, status, owner_name, owner_account, friend_name, friend_account):
    session = Session()
    ai_friend = AIChatInform(inform_id=inform_id, title=title, content=content, type=type, status=status, owner_name=owner_name, owner_account=owner_account, friend_name=friend_name, friend_account=friend_account)
    session.add(ai_friend)
    session.commit()
    session.close()


def query_AIChatInform_All(**kwargs):
    session = Session()
    records = session.query(AIChatInform).filter_by(**kwargs).all()
    session.close()
    return records


def query_AIChatInform(**kwargs):
    session = Session()
    record = session.query(AIChatInform).filter_by(**kwargs).first()
    session.close()
    return record


def update_AIChatInform(id, **kwargs):
    session = Session()
    record = session.query(AIChatInform).filter_by(id=id).first()
    if record:
        for key, value in kwargs.items():
            setattr(record, key, value)
        session.commit()
    session.close()


def delete_AIChatInform(id):
    session = Session()
    record = session.query(AIChatInform).filter_by(id=id).first()
    if record:
        session.delete(record)
        session.commit()
    session.close()


class AgentTask(Base):
    __tablename__ = 'agent_task'
    id = Column(Integer, primary_key=True, autoincrement=True)
    task_id = Column(String(50))
    title = Column(String(500), default=None)
    problem = Column(Text)
    answer = Column(Text)
    attachment_list = Column(Text)
    document_content = Column(Text)
    image_json = Column(Text)
    km_list = Column(Text)
    km_content = Column(Text)
    model_name = Column(String(100))
    agent_id = Column(String(200))
    create_time = Column(DateTime, default=datetime.now)
    is_delete = Column(Boolean, default=False)
    is_first = Column(Boolean, default=False)
    stick_time = Column(DateTime, nullable=True)
    label = Column(String(50))


def add_AgentTask(task_id, title, problem, answer, model_name, agent_id, is_first=True, attachment_list="",
                  document_content="", image_json=""):
    session = Session()
    new_task = AgentTask(task_id=task_id, title=title, problem=problem, answer=answer, model_name=model_name,
                         agent_id=agent_id, is_first=is_first, attachment_list=attachment_list,
                         document_content=document_content, image_json=image_json)
    session.add(new_task)
    session.flush()
    record_id = new_task.id
    session.refresh(new_task)
    try:
        session.commit()
    except Exception as e:
        print(e)
    print("--->start insert db6")
    session.close()
    return (record_id)


def query_AgentTask(label: bool = False, **kwargs):
    session = Session()
    try:
        filter_expr = []
        for key, value in kwargs.items():
            filter_expr.append(getattr(AgentTask, key) == value)

        if label:
            filter_expr.append(AgentTask.label.isnot(None))

        tasks = session.query(AgentTask).filter(*filter_expr).order_by(desc(AgentTask.stick_time),
                                                                       desc(AgentTask.create_time)).limit(500).all()


    except Exception as e:
        print(e)
        tasks = []
    session.close()
    return tasks


def query_AgentTask_By_Id(id):
    session = Session()
    record = session.query(AgentTask).filter_by(id=id).first()
    session.close()
    return record


def query_AgentTask_ByLabel(agent_id):
    session = Session()

    res = session.query(AgentTask.label).filter(AgentTask.is_first == True,
                                                AgentTask.agent_id == agent_id).distinct().all()
    session.close()
    if res is None:
        labels = []
    else:
        labels = [i.label for i in res if i.label is not None]
    return labels


def query_AgentTask_ById(id):
    session = Session()
    res = session.query(AgentTask).filter(AgentTask.is_first == True, AgentTask.id == id).one_or_none()
    session.close()

    return res


def query_AgentTask_Content(id, **kwargs):
    session = Session()
    task_id = ""
    res = session.query(AgentTask).filter(AgentTask.is_first == True, AgentTask.id == id).one_or_none()
    if res:
        task_id = res.task_id
        tasks = session.query(AgentTask).filter(AgentTask.task_id == task_id).order_by(asc(AgentTask.create_time)).all()
    else:
        tasks = []

    session.close()

    return tasks


def query_AgentTask_Search_Content(label: bool = False, **kwargs):
    session = Session()

    is_first = kwargs.get('is_first', None)
    agent_id = kwargs.get('agent_id', None)

    title_keyword = kwargs.get('title', None)
    problem_keyword = kwargs.get('problem', None)
    answer_keyword = kwargs.get('answer', None)

    query = session.query(AgentTask)

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

    tasks = query.order_by(desc(AgentTask.stick_time), desc(AgentTask.create_time)).limit(50000).all()

    session.close()
    return tasks


def query_AgentTask_Search_First(agent_id, task_id, label: bool = False):
    session = Session()

    if label:
        first_task = session.query(AgentTask) \
            .filter(AgentTask.agent_id == agent_id, AgentTask.task_id == task_id, AgentTask.is_first == True) \
            .first()
    else:
        first_task = session.query(AgentTask) \
            .filter(AgentTask.agent_id == agent_id, AgentTask.task_id == task_id, AgentTask.is_first == True,
                    AgentTask.label is not None) \
            .first()

    session.close()
    return first_task


def update_AgentTask(id, **kwargs):
    session = Session()
    task = session.query(AgentTask).filter_by(id=id).first()
    if task:
        for key, value in kwargs.items():
            setattr(task, key, value)
        session.commit()
    session.close()


def update_AgentTask_stick(id, action: int = 1, key: str = 'stick_time'):
    session = Session()
    if action == 1:
        value = datetime.now()
    else:
        value = None
    task = session.query(AgentTask).filter_by(id=id).first()
    if task:
        setattr(task, key, value)
        session.commit()
    session.close()


def delete_AgentTask(id):
    session = Session()
    task = session.query(AgentTask).filter_by(id=id).first()
    if task:
        session.delete(task)
        session.commit()
    session.close()


def deleteTasksFromDatabase(id_value):
    session = Session()
    try:
        task = session.query(AgentTask).filter_by(id=id_value).first()
        if task:
            task_id = task.task_id

            session.query(AgentTask).filter_by(task_id=task_id).delete()
            session.commit()
    except Exception as e:
        print(e)
        session.rollback()
    finally:
        session.close()


class AgentCfg(Base):
    __tablename__ = 'agent_cfg'
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(String(100))
    name = Column(String(200))
    memo = Column(String(200))
    borndate = Column(DateTime, nullable=True, default=None)
    borncontry = Column(String(100))
    language = Column(String(100))
    gender = Column(Integer)
    joinfederation = Column(Boolean, default=False)
    syncfederation = Column(Boolean, default=False)
    federationid = Column(String(150))
    defaultmodel = Column(String(200))
    defaultrole = Column(String(200))
    lastmodel = Column(String(200))
    lastrole = Column(String(200))
    specialization = Column(Text)
    plugins = Column(Text)
    kms = Column(Text)
    last_plugins = Column(Text)
    last_kms = Column(Text)
    prompt = Column(Text)
    snsaccount = Column(String(100))
    snsnickname = Column(String(100))
    islimittotalmessage = Column(Boolean, default=True)
    islimitmessagepp = Column(Boolean, default=True)
    totalmessages = Column(Integer)
    ppmessages = Column(Integer)
    readfile = Column(Boolean, default=True)
    writefile = Column(Boolean, default=True)
    deletefile = Column(Boolean, default=True)
    execfile = Column(Boolean, default=True)
    uselastmodel = Column(Boolean, default=False)
    uselastrole = Column(Boolean, default=False)
    uselastplugins = Column(Boolean, default=False)
    uselastkms = Column(Boolean, default=False)
    callpluginbyinstruct = Column(Boolean, default=True)
    modelfrequent = Column(Boolean, default=False)
    rolefrequent = Column(Boolean, default=False)
    multimodelfrequent = Column(Boolean, default=False)
    multimodellastmodel = Column(String(500))
    multimodellastrole = Column(String(100))
    autorunrounds = Column(Integer)
    position = Column(Integer, default=9999)
    is_show = Column(Boolean, default=True)
    is_delete = Column(Boolean, default=False)
    create_time = Column(DateTime, default=datetime.now)


def add_AgentCfg(user_id, name, memo, borndate, borncontry, language, gender, joinfederation, syncfederation, federationid, defaultmodel, defaultrole, lastmodel, lastrole, specialization, plugins, kms, last_plugins, last_kms, prompt, snsaccount, snsnickname, islimittotalmessage, islimitmessagepp, totalmessages, ppmessages, readfile, writefile, deletefile, execfile, uselastmodel, uselastrole, uselastplugins, uselastkms, callpluginbyinstruct, modelfrequent, rolefrequent, multimodelfrequent, autorunrounds):
    session = Session()
    agentcfg = AgentCfg(user_id=user_id, name=name, memo=memo, borndate=borndate, borncontry=borncontry, language=language, gender=gender, joinfederation=joinfederation, syncfederation=syncfederation, federationid=federationid, defaultmodel=defaultmodel, defaultrole=defaultrole, lastmodel=lastmodel, lastrole=lastrole, specialization=specialization, plugins=plugins, kms=kms, last_plugins=last_plugins, last_kms=last_kms, prompt=prompt, snsaccount=snsaccount, snsnickname=snsnickname, islimittotalmessage=islimittotalmessage, islimitmessagepp=islimitmessagepp, totalmessages=totalmessages, ppmessages=ppmessages, readfile=readfile, writefile=writefile, deletefile=deletefile, execfile=execfile, uselastmodel=uselastmodel, uselastrole=uselastrole, uselastplugins=uselastplugins, uselastkms=uselastkms, callpluginbyinstruct=callpluginbyinstruct, modelfrequent=modelfrequent,
                        rolefrequent=rolefrequent, multimodelfrequent=multimodelfrequent, autorunrounds=autorunrounds)
    session.add(agentcfg)
    session.commit()
    session.close()


def query_AgentCfg_All(**kwargs):
    session = Session()
    agents = session.query(AgentCfg).filter_by(**kwargs).order_by(asc(AgentCfg.position)).all()
    for agent in agents:
        print(f"ID: {agent.id}, Name: {agent.name}, Memo: {agent.memo}")
    session.close()
    return agents


def query_AgentCfg(**kwargs):
    session = Session()
    agent = session.query(AgentCfg).filter_by(**kwargs).first()
    session.close()
    return agent


def update_AgentCfg(id, **kwargs):
    session = Session()
    agent = session.query(AgentCfg).filter_by(id=id).first()
    if agent:
        for key, value in kwargs.items():
            setattr(agent, key, value)
        session.commit()
    session.close()


def update_AgentCfg_by_user_id(user_id, **kwargs):
    session = Session()
    agent = session.query(AgentCfg).filter_by(user_id=user_id).first()
    if agent:
        for key, value in kwargs.items():
            setattr(agent, key, value)
        session.commit()
    session.close()


def delete_AgentCfg(user_id):
    session = Session()
    agent = session.query(AgentCfg).filter_by(user_id=user_id).first()
    if agent:
        session.delete(agent)
        session.commit()
    session.close()


def get_agent_system_prompt(name):
    session = Session()
    agentcfg = session.query(AgentCfg).filter_by(name=name).first()

    return agentcfg.prompt if agentcfg else None


def get_agent_specialization_description(name):
    session = Session()
    agentcfg = session.query(AgentCfg).filter_by(name=name).first()

    return agentcfg.specialization if agentcfg else None


class AgentTaskMulti(Base):
    __tablename__ = 'agent_task_multi'
    id = Column(Integer, primary_key=True, autoincrement=True)
    task_id = Column(String(50))
    topic = Column(String(500), default=None)
    content = Column(Text)
    owner = Column(String(100))
    group_id = Column(String(200))
    attachment_list = Column(Text)
    document_content = Column(Text)
    image_json = Column(Text)
    km_list = Column(Text)
    km_content = Column(Text)
    model_name = Column(String(100))
    agent_id = Column(String(200))
    create_time = Column(DateTime, default=datetime.now)
    is_delete = Column(Boolean, default=False)
    is_first = Column(Boolean, default=False)
    stick_time = Column(DateTime, nullable=True)
    label = Column(String(50))


def add_AgentTaskMulti(task_id, topic, content, owner, group_id, is_first=True, attachment_list="", document_content="",
                       image_json="", model_name="", agent_id=""):
    session = Session()
    new_task = AgentTaskMulti(task_id=task_id, topic=topic, content=content, owner=owner, group_id=group_id,
                              is_first=is_first, attachment_list=attachment_list, document_content=document_content,
                              image_json=image_json, model_name=model_name, agent_id=agent_id)
    session.add(new_task)
    session.flush()
    record_id = new_task.id
    session.refresh(new_task)
    try:
        session.commit()
    except Exception as e:
        print(e)

    session.close()
    return (record_id)


def query_AgentTaskMulti(label: bool = False, **kwargs):
    session = Session()
    title = ""

    try:
        filter_expr = []
        for key, value in kwargs.items():
            filter_expr.append(getattr(AgentTaskMulti, key) == value)

        if label:
            filter_expr.append(AgentTaskMulti.label.isnot(None))

        tasks = session.query(AgentTaskMulti).filter(*filter_expr).order_by(desc(AgentTaskMulti.stick_time),
                                                                            desc(AgentTaskMulti.create_time)).limit(
            500).all()



    except Exception as e:
        print(e)
        tasks = []
    session.close()
    return tasks


def query_AgentTaskMulti_ById(id):
    session = Session()
    res = session.query(AgentTaskMulti).filter(AgentTaskMulti.is_first == True, AgentTaskMulti.id == id).one_or_none()
    session.close()

    return res


def query_AgentTaskMulti_ByLabel(group_id):
    session = Session()

    res = session.query(AgentTaskMulti.label).filter(AgentTaskMulti.is_first == True,
                                                     AgentTaskMulti.group_id == group_id).distinct().all()
    session.close()
    if res is None:
        labels = []
    else:
        labels = [i.label for i in res if i.label is not None]
    return labels


def query_AgentTaskMulti_Search_Content(label: bool = False, **kwargs):
    session = Session()

    is_first = kwargs.get('is_first', None)

    group_id = kwargs.get('group_id', None)

    title_keyword = kwargs.get('title', None)
    topic_keyword = kwargs.get('topic', None)
    answer_keyword = kwargs.get('answer', None)

    query = session.query(AgentTaskMulti)

    if is_first is not None:
        query = query.filter(AgentTaskMulti.is_first == is_first)
    if group_id is not None:
        query = query.filter(AgentTaskMulti.group_id == group_id)

    if title_keyword == "":
        query = query.filter(AgentTaskMulti.is_first == True)

    if label:
        query = query.filter(AgentTaskMulti.label.isnot(None))

    search_terms = []
    if title_keyword:
        search_terms.append(AgentTaskMulti.title.contains(title_keyword))
    if topic_keyword:
        search_terms.append(AgentTaskMulti.topic.contains(topic_keyword))
    if answer_keyword:
        search_terms.append(AgentTaskMulti.answer.contains(answer_keyword))

    if search_terms:
        query = query.filter(or_(*search_terms))

    tasks = query.order_by(
        desc(AgentTaskMulti.stick_time),
        desc(AgentTaskMulti.create_time)).limit(50000).all()

    session.close()
    return tasks


def query_AgentTaskMulti_Search_First(agent_id, task_id, label: bool = False):
    session = Session()

    if label:
        first_task = session.query(AgentTaskMulti) \
            .filter(AgentTaskMulti.agent_id == agent_id, AgentTaskMulti.task_id == task_id,
                    AgentTaskMulti.is_first == True) \
            .first()
    else:
        first_task = session.query(AgentTaskMulti) \
            .filter(AgentTaskMulti.agent_id == agent_id, AgentTaskMulti.task_id == task_id,
                    AgentTaskMulti.is_first == True, AgentTaskMulti.label is not None) \
            .first()

    session.close()
    return first_task


def query_AgentTaskMulti_Content(id, **kwargs):
    session = Session()
    res = session.query(AgentTaskMulti).filter(AgentTaskMulti.is_first == True, AgentTaskMulti.id == id).one_or_none()
    if res:
        task_id = res.task_id
    tasks = session.query(AgentTaskMulti).filter(AgentTaskMulti.task_id == task_id).order_by(
        asc(AgentTaskMulti.create_time)).all()

    session.close()

    return tasks


def update_AgentTaskMulti(id, **kwargs):
    session = Session()
    task = session.query(AgentTaskMulti).filter_by(id=id).first()
    if task:
        for key, value in kwargs.items():
            setattr(task, key, value)
        session.commit()
    session.close()


def update_AgentTaskMulti_stick(id, action: int = 1, key: str = 'stick_time'):
    session = Session()
    if action == 1:
        value = datetime.now()
    else:
        value = None
    task = session.query(AgentTaskMulti).filter_by(id=id).first()
    if task:
        setattr(task, key, value)
        session.commit()
    session.close()


def delete_AgentTaskMulti(id):
    session = Session()
    task = session.query(AgentTaskMulti).filter_by(id=id).first()
    if task:
        session.delete(task)
        session.commit()
    session.close()


def deleteMultiTasksFromDatabase(id_value):
    session = Session()
    try:
        task = session.query(AgentTaskMulti).filter_by(id=id_value).first()
        if task:
            task_id = task.task_id

            session.query(AgentTaskMulti).filter_by(task_id=task_id).delete()
            session.commit()
    except Exception as e:
        print(e)
        session.rollback()
    finally:
        session.close()


class MutiAgentCfg(Base):
    __tablename__ = 'mutiagent_cfg'
    id = Column(Integer, primary_key=True, autoincrement=True)
    group_id = Column(String(100))
    name = Column(String(200))
    memo = Column(String(200))
    agents = Column(Text)
    agentcommander = Column(String(500))

    specialization = Column(String(100))
    plugins = Column(String(500))
    kms = Column(String(500))
    prompt = Column(Text)

    islimittotalmessage = Column(Boolean, default=True)
    islimitmessagepp = Column(Boolean, default=True)
    totalmessages = Column(Integer)
    ppmessages = Column(Integer)

    readfile = Column(Boolean, default=True)
    writefile = Column(Boolean, default=True)
    deletefile = Column(Boolean, default=True)
    execfile = Column(Boolean, default=True)
    autorunrounds = Column(Integer)
    position = Column(Integer, default=9999)
    is_show = Column(Boolean, default=True)
    is_delete = Column(Boolean, default=False)
    create_time = Column(DateTime, default=datetime.now)


def add_MutiAgentCfg(group_id, name, memo, agents, agentcommander, specialization, plugins, kms, prompt, islimittotalmessage, islimitmessagepp, totalmessages, ppmessages, readfile, writefile, deletefile, execfile, autorunrounds):
    session = Session()
    mutiAgentCfg = MutiAgentCfg(group_id=group_id, name=name, memo=memo, agents=agents, agentcommander=agentcommander, specialization=specialization, plugins=plugins, kms=kms, prompt=prompt, islimittotalmessage=islimittotalmessage, islimitmessagepp=islimitmessagepp, totalmessages=totalmessages, ppmessages=ppmessages, readfile=readfile, writefile=writefile, deletefile=deletefile, execfile=execfile, autorunrounds=autorunrounds)
    session.add(mutiAgentCfg)
    session.flush()
    record_id = mutiAgentCfg.id
    session.refresh(mutiAgentCfg)
    try:
        session.commit()
    except Exception as e:
        print(e)

    session.close()
    return (record_id)


def query_MutiAgentCfg_All(**kwargs):
    session = Session()
    records = session.query(MutiAgentCfg).filter_by(**kwargs).order_by(asc(MutiAgentCfg.position)).all()

    session.close()
    return records


def query_MutiAgentCfg(**kwargs):
    session = Session()
    record = session.query(MutiAgentCfg).filter_by(**kwargs).first()
    session.close()
    return record


def update_MutiAgentCfg(id, **kwargs):
    session = Session()
    record = session.query(MutiAgentCfg).filter_by(id=id).first()
    if record:
        for key, value in kwargs.items():
            setattr(record, key, value)
        session.commit()
    session.close()


def update_MutiAgentCfg_by_group_id(group_id, **kwargs):
    session = Session()
    record = session.query(MutiAgentCfg).filter_by(group_id=group_id).first()
    if record:
        for key, value in kwargs.items():
            setattr(record, key, value)
        session.commit()
    session.close()


def delete_MutiAgentCfg(group_id):
    session = Session()
    record = session.query(MutiAgentCfg).filter_by(group_id=group_id).first()
    if record:
        session.delete(record)
        session.commit()
    session.close()


class AiChatCfg(Base):
    __tablename__ = 'aichat_cfg'
    id = Column(Integer, primary_key=True, autoincrement=True)

    user_id = Column(String(100))
    account = Column(String(100))
    password = Column(String(256))
    nickname = Column(String(100))
    sign = Column(String(200))
    status = Column(String(100))
    humantakeover = Column(Integer, default=0)
    name = Column(String(200))
    borndate = Column(DateTime, default=datetime.now)
    gender = Column(Integer)
    area = Column(String(100))
    state = Column(String(100))
    city = Column(String(100))
    community = Column(String(100))
    street_block = Column(String(100))
    address = Column(String(200))
    mail = Column(String(100))
    imaccount = Column(String(100))
    phone = Column(String(100))
    organization = Column(String(200))
    title = Column(String(100))
    orgposition = Column(String(100))
    memo = Column(String(200))
    islimittotalmessage = Column(Boolean, default=True)
    islimitmessagepp = Column(Boolean, default=True)
    totalmessages = Column(Integer)
    ppmessages = Column(Integer)
    serveraddress = Column(String(100))
    port = Column(Integer)
    ssl = Column(Boolean)
    resource = Column(String(100))
    proxyused = Column(Boolean)
    proxyaddress = Column(String(100))
    proxyport = Column(Integer)
    proxyssl = Column(Boolean)
    savepasswordlocal = Column(Boolean, default=True)
    autoconnect = Column(Boolean, default=True)
    sendreceipt = Column(Boolean, default=True)
    sendreadflag = Column(Boolean, default=True)
    sendchatstatus = Column(Boolean, default=True)
    sendgroupchatstatus = Column(Boolean, default=True)
    agreeallfriendrequest = Column(Boolean, default=True)
    position = Column(Integer, default=9999)
    is_show = Column(Boolean, default=True)
    is_delete = Column(Boolean, default=False)
    create_time = Column(DateTime, default=datetime.now)

    nationid = Column(String(100))
    nationpassword = Column(String(100))
    sns_url = Column(Text)
    avatar = Column(Text)
    avatar3d = Column(Text)
    house3d = Column(Text)
    map_type = Column(String(100))
    map_api_key = Column(Text)
    map_id = Column(Text)
    current_position = Column(String(100))
    current_place = Column(String(500))
    last_position = Column(String(100))
    home_position = Column(String(100))
    positionx = Column(Float)
    positiony = Column(Float)
    positionz = Column(Float)
    route_start = Column(String(500))
    route_end = Column(String(500))
    route_status = Column(String(100))
    route_current_position = Column(String(100))
    route_points = Column(Text)
    route = Column(Text)
    level = Column(Integer)
    credit = Column(Integer)
    money = Column(Float)
    token_unit = Column(String(100))
    life_point = Column(Integer)
    energy_point = Column(Integer)
    move_point = Column(Integer)
    exp_point = Column(Integer)
    iq_point = Column(Integer)
    profession = Column(String(200))
    handle_after_trade = Column(String(200))
    handle_content = Column(Text)
    goods_or_service_description = Column(Text)
    goods_or_service_price = Column(String(100))
    event_before_decistion = Column(String(200))
    event_after_decistion = Column(String(200))
    event_receive_msg = Column(String(200))
    event_before_send_msg = Column(String(200))
    event_before_move = Column(String(200))
    event_after_move = Column(String(200))
    event_before_use_tool = Column(String(200))
    event_after_use_tool = Column(String(200))


def add_AiChatCfg(user_id, account, password, nickname, sign, status, humantakeover, name, borndate, gender, area, state, city, community, street_block, address, mail, imaccount, phone, organization, title, orgposition, memo, islimittotalmessage, islimitmessagepp, totalmessages, ppmessages, serveraddress, port, ssl, resource, proxyused, proxyaddress, proxyport, proxyssl, savepasswordlocal, autoconnect, sendreceipt, sendreadflag, sendchatstatus, sendgroupchatstatus, agreeallfriendrequest, nationid, nationpassword, sns_url, avatar, avatar3d, house3d, map_type, map_api_key, map_id, current_position, home_position, positionx, positiony, positionz, route_start, route_end, route_status, route_current_position, route_points, route, level=1, credit=100, money=100, token_unit="k", life_point=4, energy_point=3, move_point=3, exp_point=4, iq_point=5):
    session = Session()
    aichatCfg = AiChatCfg(
        user_id=user_id, account=account, password=password, nickname=nickname,
        sign=sign, status=status, humantakeover=humantakeover, name=name,
        borndate=borndate, gender=gender, area=area, state=state, city=city, community=community, street_block=street_block, address=address,
        mail=mail, imaccount=imaccount, phone=phone, organization=organization,
        title=title, orgposition=orgposition, memo=memo,
        islimittotalmessage=islimittotalmessage, islimitmessagepp=islimitmessagepp,
        totalmessages=totalmessages, ppmessages=ppmessages,
        serveraddress=serveraddress, port=port, ssl=ssl, resource=resource,
        proxyused=proxyused, proxyaddress=proxyaddress, proxyport=proxyport,
        proxyssl=proxyssl, savepasswordlocal=savepasswordlocal,
        autoconnect=autoconnect, sendreceipt=sendreceipt, sendreadflag=sendreadflag,
        sendchatstatus=sendchatstatus, sendgroupchatstatus=sendgroupchatstatus,
        agreeallfriendrequest=agreeallfriendrequest, nationid=nationid,
        nationpassword=nationpassword, sns_url=sns_url, avatar=avatar,
        avatar3d=avatar3d, house3d=house3d, map_type=map_type,
        map_api_key=map_api_key, map_id=map_id, current_position=current_position, home_position=home_position,
        positionx=positionx, positiony=positiony, positionz=positionz,
        route_start=route_start, route_end=route_end, route_status=route_status,
        route_current_position=route_current_position, route_points=route_points, route=route,
        level=level, credit=credit, money=money, token_unit=token_unit, life_point=life_point, energy_point=energy_point, move_point=move_point, exp_point=exp_point, iq_point=iq_point
    )
    session.add(aichatCfg)
    session.flush()
    record_id = aichatCfg.id
    session.refresh(aichatCfg)
    try:
        session.commit()
    except Exception as e:
        print(e)
    print("--->start insert db6")
    session.close()
    return record_id


def query_AiChatCfg_All(**kwargs):
    session = Session()
    records = session.query(AiChatCfg).filter_by(**kwargs).order_by(asc(AiChatCfg.position)).all()

    session.close()
    return records


def query_AiChatCfg_Search_Content(**kwargs):
    session = Session()

    nickname_keyword = kwargs.get('nickname', None)
    account_keyword = kwargs.get('account', None)

    query = session.query(AiChatCfg)

    search_terms = []
    if nickname_keyword:
        search_terms.append(AiChatCfg.nickname.contains(nickname_keyword))
    if account_keyword:
        search_terms.append(AiChatCfg.account.contains(account_keyword))

    if search_terms:
        query = query.filter(or_(*search_terms))

    tasks = query.order_by(desc(AiChatCfg.create_time)).limit(50000).all()

    session.close()
    return tasks


def query_AiChatCfg(**kwargs):
    session = Session()
    record = session.query(AiChatCfg).filter_by(**kwargs).first()
    session.close()
    return record


def query_AiChatCfg_map():
    session = Session()
    record = session.query(AiChatCfg).first()
    session.close()
    return record


def query_AiChatCfg_common():
    session = Session()
    record = session.query(AiChatCfg).offset(1).limit(1).first()
    session.close()
    return record


def query_AiChatCfg_map_setting(**kwargs):
    session = Session()

    record = session.query(AiChatCfg).filter_by(**kwargs).first()
    session.close()

    if record:
        fields = {
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
            "route_points": getattr(record, "route_points", None),
            "route": record.route
        }
        return fields
    else:
        return None


def update_AiChatCfg_map(**kwargs):
    session = Session()
    try:
        record = session.query(AiChatCfg).first()
        if record:
            for key, value in kwargs.items():
                setattr(record, key, value)
            _commit_with_retry(session)
    finally:
        session.close()


def update_AiChatCfg(id, **kwargs):
    session = Session()
    record = session.query(AiChatCfg).filter_by(id=id).first()
    if record:
        for key, value in kwargs.items():
            setattr(record, key, value)
        session.commit()
    session.close()


def update_AiChatCfg_by_user_id(user_id, **kwargs):
    session = Session()
    record = session.query(AiChatCfg).filter_by(user_id=user_id).first()
    if record:
        for key, value in kwargs.items():
            setattr(record, key, value)
        session.commit()
    session.close()


def delete_AiChatCfg(user_id):
    session = Session()
    record = session.query(AiChatCfg).filter_by(user_id=user_id).first()
    if record:
        session.delete(record)
        session.commit()
    session.close()


class HumanChatCfg(Base):
    __tablename__ = 'humanchat_cfg'
    id = Column(Integer, primary_key=True, autoincrement=True)

    user_id = Column(String(100))

    account = Column(String(100))
    password = Column(String(256))
    nickname = Column(String(100))
    sign = Column(String(200))
    status = Column(String(100))

    name = Column(String(200))
    borndate = Column(DateTime, default=datetime.now)
    gender = Column(Integer)
    area = Column(String(100))
    city = Column(String(100))
    address = Column(String(200))
    mail = Column(String(100))
    imaccount = Column(String(100))
    phone = Column(String(100))
    organization = Column(String(200))
    title = Column(String(100))
    orgposition = Column(String(100))
    memo = Column(String(200))

    serveraddress = Column(String(100))
    port = Column(Integer)
    ssl = Column(Boolean)
    resource = Column(String(100))
    proxyused = Column(Boolean)
    proxyaddress = Column(String(100))
    proxyport = Column(Integer)
    proxyssl = Column(Boolean)

    savepasswordlocal = Column(Boolean, default=True)
    autoconnect = Column(Boolean, default=True)
    sendreceipt = Column(Boolean, default=True)
    sendreadflag = Column(Boolean, default=True)
    sendchatstatus = Column(Boolean, default=True)
    sendgroupchatstatus = Column(Boolean, default=True)
    autoaway = Column(Boolean, default=True)
    autona = Column(Boolean, default=True)
    agreeallfriendrequest = Column(Boolean, default=True)

    is_delete = Column(Boolean, default=False)
    create_time = Column(DateTime, default=datetime.now)


def add_HumanChatCfg(user_id, account, password, nickname, sign, status, name, borndate, gender, area, city, address, mail, imaccount, phone, organization, title, orgposition, memo, serveraddress, port, ssl, resource, proxyused, proxyaddress, proxyport, proxyssl, savepasswordlocal, autoconnect, sendreceipt, sendreadflag, sendchatstatus, sendgroupchatstatus, autoaway, autona, agreeallfriendrequest):
    session = Session()
    humanChatCfg = HumanChatCfg(user_id=user_id, account=account, password=password, nickname=nickname, sign=sign, status=status, name=name, borndate=borndate, gender=gender, area=area, city=city, address=address, mail=mail, imaccount=imaccount, phone=phone, organization=organization, title=title, orgposition=orgposition, memo=memo, serveraddress=serveraddress, port=port, ssl=ssl, resource=resource, proxyused=proxyused, proxyaddress=proxyaddress, proxyport=proxyport, proxyssl=proxyssl, savepasswordlocal=savepasswordlocal, autoconnect=autoconnect, sendreceipt=sendreceipt, sendreadflag=sendreadflag, sendchatstatus=sendchatstatus, sendgroupchatstatus=sendgroupchatstatus, autoaway=autoaway, autona=autona, agreeallfriendrequest=agreeallfriendrequest)
    session.add(humanChatCfg)
    session.commit()
    session.close()


def query_HumanChatCfg_All(**kwargs):
    session = Session()
    records = session.query(HumanChatCfg).filter_by(**kwargs).all()

    session.close()
    return records


def query_HumanChatCfg(**kwargs):
    session = Session()
    record = session.query(HumanChatCfg).filter_by(**kwargs).first()
    session.close()
    return record


def update_HumanChatCfg(id, **kwargs):
    session = Session()
    record = session.query(HumanChatCfg).filter_by(id=id).first()
    if record:
        for key, value in kwargs.items():
            setattr(record, key, value)
        session.commit()
    session.close()


def delete_HumanChatCfg(id):
    session = Session()
    record = session.query(HumanChatCfg).filter_by(id=id).first()
    if record:
        session.delete(record)
        session.commit()
    session.close()


class KMCfg(Base):
    __tablename__ = 'km_cfg'
    id = Column(Integer, primary_key=True, autoincrement=True)
    km_id = Column(String(100))
    name = Column(String(200))
    memo = Column(String(200))
    label = Column(String(100))

    kmpath = Column(String(250))
    vectorization = Column(Boolean, default=True)
    stopvectorization = Column(Boolean, default=False)
    kmtype = Column(String(100))
    vectortype = Column(String(150))
    embeddingmodel = Column(String(150))

    textblocklength = Column(Integer)
    overlaplength = Column(Integer)
    titleaugment = Column(Boolean, default=True)

    position = Column(Integer, default=9999)
    is_show = Column(Boolean, default=True)
    config_param = Column(Text)
    is_delete = Column(Boolean, default=False)
    create_time = Column(DateTime, default=datetime.now)


def add_KMCfg(km_id, name, memo, label, kmpath, vectorization, stopvectorization, kmtype, vectortype, embeddingmodel, textblocklength, overlaplength, titleaugment, config_param):
    session = Session()
    kmCfg = KMCfg(km_id=km_id, name=name, memo=memo, label=label, kmpath=kmpath, kmtype=kmtype, vectorization=vectorization, stopvectorization=stopvectorization, vectortype=vectortype, embeddingmodel=embeddingmodel, textblocklength=textblocklength, overlaplength=overlaplength, titleaugment=titleaugment, config_param=config_param)
    session.add(kmCfg)
    session.commit()
    session.close()


def query_KMCfg_All(**kwargs):
    session = Session()
    records = session.query(KMCfg).filter_by(**kwargs).order_by(asc(KMCfg.position)).all()

    session.close()
    return records


def query_KMCfg(**kwargs):
    session = Session()
    record = session.query(KMCfg).filter_by(**kwargs).first()
    session.close()
    return record


def update_KMCfg(id, **kwargs):
    session = Session()
    record = session.query(KMCfg).filter_by(id=id).first()
    if record:
        for key, value in kwargs.items():
            setattr(record, key, value)
        session.commit()
    session.close()


def update_KMCfg_by_kmid(km_id, **kwargs):
    session = Session()
    record = session.query(KMCfg).filter_by(km_id=km_id).first()
    if record:
        for key, value in kwargs.items():
            setattr(record, key, value)
        session.commit()
    session.close()


def delete_KMCfg(km_id):
    session = Session()
    record = session.query(KMCfg).filter_by(km_id=km_id).first()
    if record:
        session.delete(record)
        session.commit()
    session.close()


class KMData(Base):
    __tablename__ = 'km_data'
    id = Column(Integer, primary_key=True, autoincrement=True)
    km_id = Column(String(100))

    filename = Column(String(200))
    filenum = Column(Integer, default=1)

    textblocklength = Column(Integer, default=1)
    overlaplength = Column(Integer, default=1)
    waitvectorization = Column(Boolean, default=False)
    is_delete = Column(Boolean, default=False)
    create_time = Column(DateTime, default=datetime.now)


def add_KMData(km_id, filename, filenum, textblocklength, overlaplength, waitvectorization):
    session = Session()
    kmData = KMData(km_id=km_id, filename=filename, filenum=filenum, textblocklength=textblocklength, overlaplength=overlaplength, waitvectorization=waitvectorization)
    session.add(kmData)
    session.flush()
    record_id = kmData.id
    session.refresh(kmData)
    try:
        session.commit()
    except Exception as e:
        print(e)
    print("--->start insert db6")
    session.close()
    return (record_id)


def query_KMData_All(**kwargs):
    session = Session()
    records = session.query(KMData).filter_by(**kwargs).all()

    session.close()
    return records


def query_KMData(**kwargs):
    session = Session()
    record = session.query(KMData).filter_by(**kwargs).first()
    session.close()
    return record


def update_KMData(id, **kwargs):
    session = Session()
    record = session.query(KMData).filter_by(id=id).first()
    if record:
        for key, value in kwargs.items():
            setattr(record, key, value)
        session.commit()
    session.close()


def delete_KMData(id):
    session = Session()
    record = session.query(KMData).filter_by(id=id).first()
    if record:
        session.delete(record)
        session.commit()
    session.close()


class PluginMng(Base):
    __tablename__ = 'pluginmng'
    id = Column(Integer, primary_key=True, autoincrement=True)

    plugin_id = Column(String(100))
    company = Column(String(200))
    company_abbr = Column(String(100))
    name = Column(String(100))
    version = Column(String(100))
    alias_name = Column(String(100))
    filename = Column(String(200))
    run_mode = Column(String(100))
    run_scope = Column(String(100))
    instruction = Column(String(100))

    runtime_main = Column(String(200))
    runtime_test = Column(String(200))
    description = Column(Text)

    plugin_directory = Column(String(100))
    plugin_type = Column(String(100))
    plugin_executed = Column(String(100))
    plugin_event = Column(String(100))
    plugin_title = Column(Text)
    detail = Column(Text)
    confirm_needed = Column(Boolean, default=True)
    can_be_sold = Column(Boolean, default=False)
    used_in_sns = Column(Boolean, default=False)

    creator = Column(String(100))

    is_delete = Column(Boolean, default=False)
    create_time = Column(DateTime, default=datetime.now)


def add_PluginMng(plugin_id, company, company_abbr, name, version, alias_name, filename, runtime_main, runtime_test, description, plugin_directory, plugin_type, plugin_executed, plugin_event, plugin_title, detail, creator, run_mode="", run_scope="", instruction="", used_in_sns=0):
    session = Session()
    pluginMng = PluginMng(plugin_id=plugin_id, company=company, company_abbr=company_abbr, name=name, version=version, alias_name=alias_name, filename=filename, run_mode=run_mode, run_scope=run_scope, instruction=instruction, runtime_main=runtime_main, runtime_test=runtime_test, description=description, plugin_directory=plugin_directory, plugin_type=plugin_type, plugin_executed=plugin_executed, plugin_event=plugin_event, plugin_title=plugin_title, detail=detail, creator=creator, used_in_sns=used_in_sns)
    session.add(pluginMng)
    session.commit()
    session.close()


def copy_plugin_record(plugin_id, new_plugin_id, **kwargs):
    session = Session()
    try:
        record_to_copy = session.query(PluginMng).filter_by(plugin_id=plugin_id).first()
        if not record_to_copy:
            print(f"No record found with plugin_id: {plugin_id}")
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
        session.commit()
        return new_record
    except Exception as e:
        session.rollback()
        print(f"Error occurred while copying record: {e}")
    finally:
        session.close()


def query_PluginMng_All(**kwargs):
    session = Session()
    records = session.query(PluginMng).filter_by(**kwargs).all()

    session.close()
    return records


def query_PluginMng_All_Tool(**kwargs):
    session = Session()
    try:
        query = session.query(PluginMng)
        plugin_types = ["Tool_Headless", "Tool_Gui"]

        if plugin_types:
            query = query.filter(or_(PluginMng.plugin_type == plugin_type for plugin_type in plugin_types))

        if kwargs:
            query = query.filter_by(**kwargs)

        records = query.order_by(desc(PluginMng.run_mode)).all()
    finally:
        session.close()

    return records


def query_PluginMng_All_Tool_Search(**kwargs):
    session = Session()
    try:
        query = session.query(PluginMng)
        plugin_types = ["Tool_Headless", "Tool_Gui"]

        query = query.filter(or_(PluginMng.plugin_type == plugin_type for plugin_type in plugin_types))
        query = query.filter(PluginMng.plugin_event.contains("search_before_ask"))

        if kwargs:
            query = query.filter_by(**kwargs)

        records = query.order_by(desc(PluginMng.run_mode)).all()
    finally:
        session.close()

    return records


def query_PluginMng(**kwargs):
    session = Session()
    record = session.query(PluginMng).filter_by(**kwargs).first()
    session.close()
    return record


def update_PluginMng(id, **kwargs):
    session = Session()
    record = session.query(PluginMng).filter_by(id=id).first()
    if record:
        for key, value in kwargs.items():
            setattr(record, key, value)
        session.commit()
    session.close()


def delete_PluginMng(**kwargs):
    session = Session()
    record = session.query(PluginMng).filter_by(**kwargs).first()
    if record:
        session.delete(record)
        session.commit()
    session.close()


class FunctionMng(Base):
    __tablename__ = 'function_mng'

    id = Column(Integer, primary_key=True, autoincrement=True)

    function_id = Column(String(100))
    name = Column(String(100))
    instruction = Column(String(100))
    file_path = Column(String(200))
    requirement = Column(Text)
    parameter = Column(Text)
    description = Column(String(100))
    detail = Column(Text)
    function_type = Column(String(100))
    function_event = Column(String(100))
    confirm_needed = Column(Boolean, default=True)
    can_be_sold = Column(Boolean, default=False)
    used_in_sns = Column(Boolean, default=False)
    creator = Column(String(100))
    is_delete = Column(Boolean, default=False)
    create_time = Column(DateTime, default=datetime.now)


def add_function_mng(function_id, name, instruction, file_path, requirement, parameter,
                     description, detail, function_type, function_event, creator, used_in_sns=0):
    session = Session()
    new_function = FunctionMng(
        function_id=function_id, name=name, instruction=instruction, file_path=file_path,
        requirement=requirement, parameter=parameter, description=description, detail=detail,
        function_type=function_type, function_event=function_event, creator=creator, used_in_sns=used_in_sns
    )

    session.add(new_function)
    session.flush()
    record_id = new_function.id
    session.refresh(new_function)
    try:
        session.commit()
    except Exception as e:
        print(e)
    print("--->start insert db6")
    session.close()
    return (record_id)


def query_function_mng_all(**kwargs):
    session = Session()
    records = session.query(FunctionMng).filter_by(**kwargs).all()
    session.close()
    return records


def query_function_mng(**kwargs):
    session = Session()
    record = session.query(FunctionMng).filter_by(**kwargs).first()
    session.close()
    return record


def update_function_mng(function_id, **kwargs):
    session = Session()
    record = session.query(FunctionMng).filter_by(function_id=function_id).first()
    if record:
        for key, value in kwargs.items():
            setattr(record, key, value)
        session.commit()
    session.close()


def update_function_mng_with_id(id, **kwargs):
    session = Session()
    record = session.query(FunctionMng).filter_by(id=id).first()
    if record:
        for key, value in kwargs.items():
            setattr(record, key, value)
        session.commit()
    session.close()


def delete_function_mng(**kwargs):
    session = Session()
    record = session.query(FunctionMng).filter_by(**kwargs).first()
    if record:
        session.delete(record)
        session.commit()
    session.close()


class McpMng(Base):
    __tablename__ = 'mcp_mng'

    id = Column(Integer, primary_key=True, autoincrement=True)

    mcp_id = Column(String(100))
    name = Column(String(100))
    instruction = Column(String(100))
    file_path = Column(String(200))
    requirement = Column(Text)
    parameter = Column(Text)
    description = Column(String(100))
    detail = Column(Text)
    mcp_type = Column(String(100))
    mcp_event = Column(String(100))
    confirm_needed = Column(Boolean, default=True)
    can_be_sold = Column(Boolean, default=False)
    used_in_sns = Column(Boolean, default=False)
    creator = Column(String(100))
    is_delete = Column(Boolean, default=False)
    create_time = Column(DateTime, default=datetime.now)


def add_mcp_mng(mcp_id, name, instruction, file_path, requirement, parameter,
                description, detail, mcp_type, mcp_event, creator, used_in_sns=0):
    session = Session()
    new_mcp = McpMng(
        mcp_id=mcp_id, name=name, instruction=instruction, file_path=file_path,
        requirement=requirement, parameter=parameter, description=description, detail=detail,
        mcp_type=mcp_type, mcp_event=mcp_event, creator=creator, used_in_sns=used_in_sns
    )

    session.add(new_mcp)
    session.flush()
    record_id = new_mcp.id
    session.refresh(new_mcp)
    try:
        session.commit()
    except Exception as e:
        print(e)
    print("--->start insert db6")
    session.close()
    return (record_id)


def query_mcp_mng_all(**kwargs):
    session = Session()
    records = session.query(McpMng).filter_by(**kwargs).all()
    session.close()
    return records


def query_mcp_mng(**kwargs):
    session = Session()
    record = session.query(McpMng).filter_by(**kwargs).first()
    session.close()
    return record


def update_mcp_mng(mcp_id, **kwargs):
    session = Session()
    record = session.query(McpMng).filter_by(mcp_id=mcp_id).first()
    if record:
        for key, value in kwargs.items():
            setattr(record, key, value)
        session.commit()
    session.close()


def update_mcp_mng_with_id(id, **kwargs):
    session = Session()
    record = session.query(McpMng).filter_by(id=id).first()
    if record:
        for key, value in kwargs.items():
            setattr(record, key, value)
        session.commit()
    session.close()


def delete_mcp_mng(**kwargs):
    session = Session()
    record = session.query(McpMng).filter_by(**kwargs).first()
    if record:
        session.delete(record)
        session.commit()
    session.close()


class SkillMng(Base):
    __tablename__ = 'skill_mng'

    id = Column(Integer, primary_key=True, autoincrement=True)

    skill_id = Column(String(100))
    name = Column(String(100))
    instruction = Column(String(100))
    file_path = Column(String(200))
    requirement = Column(Text)
    parameter = Column(Text)
    description = Column(String(100))
    detail = Column(Text)
    skill_type = Column(String(100))
    skill_event = Column(String(100))
    confirm_needed = Column(Boolean, default=True)
    can_be_sold = Column(Boolean, default=False)
    used_in_sns = Column(Boolean, default=False)
    creator = Column(String(100))
    is_delete = Column(Boolean, default=False)
    create_time = Column(DateTime, default=datetime.now)


def add_skill_mng(skill_id, name, instruction, file_path, requirement, parameter,
                  description, detail, skill_type, skill_event, creator, used_in_sns=0):
    session = Session()
    new_skill = SkillMng(
        skill_id=skill_id, name=name, instruction=instruction, file_path=file_path,
        requirement=requirement, parameter=parameter, description=description, detail=detail,
        skill_type=skill_type, skill_event=skill_event, creator=creator, used_in_sns=used_in_sns
    )

    session.add(new_skill)
    session.flush()
    record_id = new_skill.id
    session.refresh(new_skill)
    try:
        session.commit()
    except Exception as e:
        print(e)
    print("--->start insert db6")
    session.close()
    return (record_id)


def query_skill_mng_all(**kwargs):
    session = Session()
    records = session.query(SkillMng).filter_by(**kwargs).all()
    session.close()
    return records


def query_skill_mng(**kwargs):
    session = Session()
    record = session.query(SkillMng).filter_by(**kwargs).first()
    session.close()
    return record


def update_skill_mng(skill_id, **kwargs):
    session = Session()
    record = session.query(SkillMng).filter_by(skill_id=skill_id).first()
    if record:
        for key, value in kwargs.items():
            setattr(record, key, value)
        session.commit()
    session.close()


def update_skill_mng_with_id(id, **kwargs):
    session = Session()
    record = session.query(SkillMng).filter_by(id=id).first()
    if record:
        for key, value in kwargs.items():
            setattr(record, key, value)
        session.commit()
    session.close()


def delete_skill_mng(**kwargs):
    session = Session()
    record = session.query(SkillMng).filter_by(**kwargs).first()
    if record:
        session.delete(record)
        session.commit()
    session.close()


class WebMng(Base):
    __tablename__ = 'web_mng'

    id = Column(Integer, primary_key=True, autoincrement=True)

    web_id = Column(String(100))
    name = Column(String(100))
    title = Column(String(100))
    type = Column(String(100))
    description = Column(Text)
    filename = Column(String(200))
    url = Column(String(500))
    position = Column(Integer, default=999)
    creator = Column(String(100))
    is_delete = Column(Boolean, default=False)
    create_time = Column(DateTime, default=datetime.now)


def add_web_mng(web_id, name, title, type, description,
                filename, url):
    session = Session()
    new_web = WebMng(
        web_id=web_id, name=name, title=title,
        type=type, description=description, filename=filename, url=url
    )

    session.add(new_web)
    session.flush()
    record_id = new_web.id
    session.refresh(new_web)
    try:
        session.commit()
    except Exception as e:
        print(e)
    print("--->start insert db6")
    session.close()
    return (record_id)


def query_web_mng_all(**kwargs):
    session = Session()
    records = session.query(WebMng).filter_by(**kwargs).order_by(asc(WebMng.position)).all()
    session.close()
    return records


def query_web_mng(**kwargs):
    session = Session()
    record = session.query(WebMng).filter_by(**kwargs).first()
    session.close()
    return record


def update_web_mng(web_id, **kwargs):
    session = Session()
    record = session.query(WebMng).filter_by(web_id=web_id).first()
    if record:
        for key, value in kwargs.items():
            setattr(record, key, value)
        session.commit()
    session.close()


def delete_web_mng(**kwargs):
    session = Session()
    record = session.query(WebMng).filter_by(**kwargs).first()
    if record:
        session.delete(record)
        session.commit()
    session.close()


class WorkflowMng(Base):
    __tablename__ = 'workflow_mng'

    id = Column(Integer, primary_key=True, autoincrement=True)
    workflow_id = Column(String(100))
    title = Column(String(100))
    description = Column(Text)
    instruction = Column(String(100))
    workflow_event = Column(String(100))
    detail = Column(Text)
    timer_desc = Column(String(200))
    timer_cron = Column(String(200))
    run_agent_name = Column(String(200))
    run_agent_id = Column(String(200))
    creator = Column(String(100))
    is_delete = Column(Boolean, default=False)
    create_time = Column(DateTime, default=datetime.now)


def add_workflow_mng(workflow_id, title, description, instruction,
                     detail, timer_desc, timer_cron, run_agent_name, run_agent_id):
    session = Session()
    workflow_mng = WorkflowMng(
        workflow_id=workflow_id,
        title=title,
        description=description,
        instruction=instruction,
        detail=detail,
        timer_desc=timer_desc,
        timer_cron=timer_cron,
        run_agent_name=run_agent_name,
        run_agent_id=run_agent_id
    )

    session.add(workflow_mng)
    session.flush()
    record_id = workflow_mng.id
    session.refresh(workflow_mng)
    session.commit()
    session.close()
    return record_id


def query_workflow_mng_all(**kwargs):
    session = Session()
    try:
        records = session.query(WorkflowMng).filter_by(**kwargs).all()
        return records
    finally:
        session.close()


def query_workflow_mng(**kwargs):
    session = Session()
    try:
        record = session.query(WorkflowMng).filter_by(**kwargs).first()
        return record
    finally:
        session.close()


def update_workflow_mng(id, **kwargs):
    session = Session()
    try:
        record = session.query(WorkflowMng).filter_by(id=id).first()
        if record:
            for key, value in kwargs.items():
                setattr(record, key, value)
            session.commit()
    except Exception as e:
        session.rollback()
        print(f"更新工作流记录失败: {e}")
    finally:
        session.close()


def delete_workflow_mng(**kwargs):
    session = Session()
    try:
        record = session.query(WorkflowMng).filter_by(**kwargs).first()
        if record:
            session.delete(record)
            session.commit()
    except Exception as e:
        session.rollback()
        print(f"删除工作流记录失败: {e}")
    finally:
        session.close()


def copy_workflow(workflow_id, new_workflow_id):
    session = Session()
    try:
        original_record = session.query(WorkflowMng).filter_by(workflow_id=workflow_id).first()
        if original_record:
            new_workflow = WorkflowMng(
                workflow_id=new_workflow_id,
                title=original_record.title + "-Copy",
                description=original_record.description,
                instruction=original_record.instruction,
                workflow_event=original_record.workflow_event,
                detail=original_record.detail,
                timer_desc=original_record.timer_desc,
                timer_cron=original_record.timer_cron,
                creator=original_record.creator,
                is_delete=False,
                create_time=datetime.now()
            )
            session.add(new_workflow)
            session.commit()
            return new_workflow
        else:
            print("未找到指定的工作流记录")
            return None
    except Exception as e:
        session.rollback()
        print(f"拷贝工作流记录失败: {e}")
    finally:
        session.close()


class TaskSchedule(Base):
    __tablename__ = 'task_schedule'

    id = Column(Integer, primary_key=True, autoincrement=True)
    title = Column(String(100))
    description = Column(Text)
    task_type = Column(String(100))
    task_id = Column(String(100))
    org_id = Column(String(100))
    parameter = Column(Text)
    schedule_time = Column(DateTime)
    run_time = Column(DateTime)
    run_result = Column(Text)
    status = Column(String(100), default="0")
    timer_desc = Column(String(200))
    timer_cron = Column(String(200))
    run_agent_name = Column(String(200))
    run_agent_id = Column(String(200))
    creator = Column(String(100))
    is_delete = Column(Boolean, default=False)
    create_time = Column(DateTime, default=datetime.now)


def add_task_schedule_mng(title, description, task_type,
                          task_id, org_id, parameter, schedule_time, timer_desc, timer_cron, run_agent_name, run_agent_id):
    session = Session()
    task_schedule = TaskSchedule(
        title=title,
        description=description,
        task_type=task_type,
        task_id=task_id,
        org_id=org_id,
        parameter=parameter,
        schedule_time=schedule_time,
        timer_desc=timer_desc,
        timer_cron=timer_cron,
        run_agent_name=run_agent_name,
        run_agent_id=run_agent_id
    )

    session.add(task_schedule)
    session.flush()
    record_id = task_schedule.id
    session.refresh(task_schedule)
    session.commit()
    session.close()
    return record_id


def query_task_schedule_all(**kwargs):
    session = Session()
    try:
        records = session.query(TaskSchedule).filter_by(**kwargs).all()
        return records
    finally:
        session.close()


def query_task_schedule(**kwargs):
    session = Session()
    try:
        record = session.query(TaskSchedule).filter_by(**kwargs).first()
        return record
    finally:
        session.close()


def update_task_schedule(id, **kwargs):
    session = Session()
    try:
        record = session.query(TaskSchedule).filter_by(id=id).first()
        if record:
            for key, value in kwargs.items():
                setattr(record, key, value)
            session.commit()
    except Exception as e:
        session.rollback()
        print(f"更新记录失败: {e}")
    finally:
        session.close()


def delete_task_schedule(**kwargs):
    session = Session()
    try:
        record = session.query(TaskSchedule).filter_by(**kwargs).first()
        if record:
            session.delete(record)
            session.commit()
    except Exception as e:
        session.rollback()
        print(f"删除记录失败: {e}")
    finally:
        session.close()


class NoteMng(Base):
    __tablename__ = 'note_mng'

    id = Column(Integer, primary_key=True, autoincrement=True)

    note_id = Column(String(100))
    title = Column(String(100))
    file_name = Column(String(200))
    content = Column(Text)
    km_id = Column(String(100))
    tag_1 = Column(String(100))
    tag_2 = Column(String(100))
    tag_3 = Column(String(100))
    waitvectorization = Column(Boolean, default=False)
    creator = Column(String(100))
    is_delete = Column(Boolean, default=False)
    create_time = Column(DateTime, default=datetime.now)
    stick_time = Column(DateTime, nullable=True)
    label = Column(String(50))


def add_note_mng(note_id, title, file_name, content, km_id, tag_1, tag_2,
                 tag_3, waitvectorization, label):
    session = Session()
    new_note = NoteMng(
        note_id=note_id, title=title, file_name=file_name, content=content, km_id=km_id,
        tag_1=tag_1, tag_2=tag_2, tag_3=tag_3, waitvectorization=waitvectorization, label=label
    )
    session.add(new_note)
    session.flush()
    record_id = new_note.id
    session.refresh(new_note)
    try:
        session.commit()
    except Exception as e:
        print(e)
    print("--->start insert db6")
    session.close()
    return (record_id)


def query_note_mng_all(count, label: bool = False, **kwargs):
    session = Session()
    if label:
        if count == -1:
            records = session.query(NoteMng).filter(NoteMng.label.isnot(None)).filter_by(**kwargs).order_by(
                desc(NoteMng.stick_time),
                desc(NoteMng.create_time)).all()
        else:
            records = session.query(NoteMng).filter(NoteMng.label.isnot(None)).filter_by(**kwargs).order_by(
                desc(NoteMng.stick_time),
                desc(NoteMng.create_time)).limit(
                count).all()
    else:
        if count == -1:
            records = session.query(NoteMng).filter_by(**kwargs).order_by(desc(NoteMng.stick_time),
                                                                          desc(
                                                                              NoteMng.create_time)).all()
        else:
            records = session.query(NoteMng).filter_by(**kwargs).order_by(desc(NoteMng.stick_time),
                                                                          desc(NoteMng.create_time)).limit(
                count).all()
    session.close()
    return records


def query_note_mng(**kwargs):
    session = Session()
    record = session.query(NoteMng).filter_by(**kwargs).first()
    session.close()
    return record


def query_note_mng_ById(id):
    session = Session()
    res = session.query(NoteMng).filter(NoteMng.id == id).one_or_none()
    session.close()

    return res


def query_note_mng_ByLabel(km_id):
    session = Session()

    res = session.query(NoteMng.label).filter(NoteMng.km_id == km_id).distinct().all()
    session.close()
    if res is None:
        labels = []
    else:
        labels = [i.label for i in res if i.label is not None]
    return labels


def update_note_mng(note_id, **kwargs):
    session = Session()
    record = session.query(NoteMng).filter_by(note_id=note_id).first()
    if record:
        for key, value in kwargs.items():
            setattr(record, key, value)
        session.commit()
    session.close()


def update_note_mng_stick(id, value=None, key: str = 'stick_time'):
    session = Session()
    task = session.query(NoteMng).filter_by(id=id).first()
    if task:
        setattr(task, key, value)
        session.commit()
    session.close()


def update_note_mng_by_recordid(id, **kwargs):
    session = Session()
    record = session.query(NoteMng).filter_by(id=id).first()
    if record:
        for key, value in kwargs.items():
            setattr(record, key, value)
        session.commit()
    session.close()


def delete_note_mng(**kwargs):
    session = Session()
    record = session.query(NoteMng).filter_by(**kwargs).first()
    if record:
        session.delete(record)
        session.commit()
    session.close()


def query_Note_mng_Search_Content(count, label: bool = False, **kwargs):
    session = Session()

    title_keyword = kwargs.get('title', None)
    content_keyword = kwargs.get('content', None)

    query = session.query(NoteMng)

    if label:
        query = query.filter(NoteMng.label.isnot(None))

    search_terms = []
    if title_keyword:
        search_terms.append(NoteMng.title.contains(title_keyword))
    if content_keyword:
        search_terms.append(NoteMng.content.contains(content_keyword))

    if search_terms:
        query = query.filter(or_(*search_terms))

    if count == -1:
        records = query.order_by(
            desc(NoteMng.stick_time),
            desc(NoteMng.create_time)).limit(50000).all()
    else:
        records = query.order_by(
            desc(NoteMng.stick_time),
            desc(NoteMng.create_time)).limit(count).all()

    session.close()
    return records


class SystemCfg(Base):
    __tablename__ = 'system_cfg'
    id = Column(Integer, primary_key=True, autoincrement=True)

    autorun = Column(Boolean, default=False)
    showtaskbar = Column(Boolean, default=False)
    updateinfo = Column(Boolean, default=False)
    minirunontray = Column(Boolean, default=False)
    closebuttontype = Column(String(100))
    style = Column(String(500))

    showinfo = Column(Boolean, default=True)
    showinfoicon = Column(Boolean, default=True)
    infosound = Column(Boolean, default=True)
    agent_server = Column(Text)
    ai_sns_server = Column(Text)
    conversation_timeout_seconds = Column(Integer, default=60)
    contact_cooldown_seconds = Column(Integer, default=300)
    contact_recent_limit = Column(Integer, default=3)
    process_info_compact_every_n = Column(Integer, default=50)
    process_info_plan_summary_every_n = Column(Integer, default=5)
    memory_enabled = Column(Boolean, default=True)
    memory_embedding_enabled = Column(Boolean, default=False)
    is_delete = Column(Boolean, default=False)
    create_time = Column(DateTime, default=datetime.now)


def _ensure_system_cfg_columns():
    try:
        conn = sqlite3.connect(DBPath)
        cursor = conn.cursor()
        cursor.execute("PRAGMA table_info(system_cfg)")
        columns = [row[1] for row in cursor.fetchall()]

        if 'conversation_timeout_seconds' not in columns:
            cursor.execute("ALTER TABLE system_cfg ADD COLUMN conversation_timeout_seconds INTEGER DEFAULT 60")
        if 'contact_cooldown_seconds' not in columns:
            cursor.execute("ALTER TABLE system_cfg ADD COLUMN contact_cooldown_seconds INTEGER DEFAULT 300")
        if 'contact_recent_limit' not in columns:
            cursor.execute("ALTER TABLE system_cfg ADD COLUMN contact_recent_limit INTEGER DEFAULT 3")
        if 'process_info_compact_every_n' not in columns:
            cursor.execute("ALTER TABLE system_cfg ADD COLUMN process_info_compact_every_n INTEGER DEFAULT 50")
        if 'process_info_plan_summary_every_n' not in columns:
            cursor.execute("ALTER TABLE system_cfg ADD COLUMN process_info_plan_summary_every_n INTEGER DEFAULT 5")
        if 'memory_enabled' not in columns:
            cursor.execute("ALTER TABLE system_cfg ADD COLUMN memory_enabled INTEGER DEFAULT 1")
        if 'memory_embedding_enabled' not in columns:
            cursor.execute("ALTER TABLE system_cfg ADD COLUMN memory_embedding_enabled INTEGER DEFAULT 0")
        conn.commit()
    except Exception:
        try:
            conn.rollback()
        except Exception:
            pass
    finally:
        try:
            conn.close()
        except Exception:
            pass


def add_SystemCfg(autorun, showtaskbar, updateinfo, minirunontray, closebuttontype, style, showinfo, showinfoicon, infosound):
    session = Session()
    systemCfg = SystemCfg(autorun=autorun, showtaskbar=showtaskbar, updateinfo=updateinfo, minirunontray=minirunontray, closebuttontype=closebuttontype, style=style, showinfo=showinfo, showinfoicon=showinfoicon, infosound=infosound)
    session.add(systemCfg)
    session.commit()
    session.close()


def query_SystemCfg_All(**kwargs):
    session = Session()
    records = session.query(SystemCfg).filter_by(**kwargs).all()

    session.close()
    return records


def query_SystemCfg(**kwargs):
    session = Session()
    record = session.query(SystemCfg).filter_by(**kwargs).first()
    session.close()
    return record


def update_SystemCfg(id, **kwargs):
    session = Session()
    record = session.query(SystemCfg).filter_by(id=id).first()
    if record:
        for key, value in kwargs.items():
            setattr(record, key, value)
        session.commit()
    session.close()


def delete_SystemCfg(id):
    session = Session()
    record = session.query(SystemCfg).filter_by(id=id).first()
    if record:
        session.delete(record)
        session.commit()
    session.close()


class LogsMng(Base):
    __tablename__ = 'logsmng'
    id = Column(Integer, primary_key=True, autoincrement=True)

    logs_id = Column(String(100))
    content = Column(Text)
    type = Column(String(200))

    is_delete = Column(Boolean, default=False)
    create_time = Column(DateTime, default=datetime.now)


def add_LogsMng(logs_id, content, type):
    session = Session()
    logsMng = LogsMng(logs_id=logs_id, content=content, type=type)
    session.add(logsMng)
    session.commit()
    session.close()


def query_LogsMng_All(**kwargs):
    session = Session()
    records = session.query(LogsMng).filter_by(**kwargs).all()

    session.close()
    return records


def query_LogsMng(**kwargs):
    session = Session()
    record = session.query(LogsMng).filter_by(**kwargs).first()
    session.close()
    return record


def update_LogsMng(id, **kwargs):
    session = Session()
    record = session.query(LogsMng).filter_by(id=id).first()
    if record:
        for key, value in kwargs.items():
            setattr(record, key, value)
        session.commit()
    session.close()


def delete_LogsMng(id):
    session = Session()
    record = session.query(LogsMng).filter_by(id=id).first()
    if record:
        session.delete(record)
        session.commit()
    session.close()


class SysConfig(Base):
    __tablename__ = 'config'
    id = Column(Integer, primary_key=True, autoincrement=True)
    lang = Column(String(20))


def query_config_lang(**kwargs):
    session = Session()
    record = session.query(SysConfig).filter_by(**kwargs).first()
    lang = record.lang
    session.close()
    return lang


def update_config_lang(lang, **kwargs):
    session = Session()
    record = session.query(SysConfig).filter_by(**kwargs).first()
    record.lang = lang
    session.commit()
    session.close()
    return lang


class Question(Base):
    __tablename__ = 'question'
    id = Column(Integer, primary_key=True, autoincrement=True)
    question = Column(String)
    tag = Column(String(20))
    create_time = Column(DateTime, default=datetime.now)


def add_Question(question, tag):
    session = Session()
    systemCfg = add_Question(question=question, tag=tag)
    session.add(systemCfg)
    session.commit()
    session.close()


def query_Question_All(**kwargs):
    session = Session()
    records = session.query(Question).filter_by(**kwargs).all()
    session.close()
    return records


def query_Question_limit(num: int = 0, **kwargs):
    session = Session()
    if num <= 0:
        records = session.query(Question).filter_by(**kwargs).all()
    else:
        records = session.query(Question).filter_by(**kwargs).limit(num).all()

    session.close()
    return records


def query_Question(**kwargs):
    session = Session()
    record = session.query(Question).filter_by(**kwargs).first()
    session.close()
    return record


def update_Question(id, **kwargs):
    session = Session()
    record = session.query(Question).filter_by(id=id).first()
    if record:
        for key, value in kwargs.items():
            setattr(record, key, value)
        session.commit()
    session.close()


def delete_Question(id):
    session = Session()
    record = session.query(Question).filter_by(id=id).first()
    if record:
        session.delete(record)
        session.commit()
    session.close()


class Prompt(Base):
    __tablename__ = 'prompts'
    id = Column(Integer, primary_key=True, autoincrement=True)
    title = Column(String)
    content = Column(String)
    question = Column(String)
    tags = Column(String)
    model_name = Column(String(100))
    position = Column(Integer)

    prompt_frequents = relationship("PromptFrequent", back_populates="prompt")


def get_prompt_by_title(title):
    session = Session()
    prompt = session.query(Prompt).filter_by(title=title).first()

    session.close()
    return prompt.content if prompt else None


def get_prompt_by_id(id):
    session = Session()
    prompt = session.query(Prompt).filter_by(id=id).first()

    session.close()
    return prompt.content if prompt else None


def get_all_prompt(**kwargs):
    session = Session()
    try:
        filter_expr = [getattr(Prompt, key) == value for key, value in kwargs.items()]
        result = session.query(Prompt).filter(*filter_expr).order_by(desc(Prompt.id)).all()
        return result
    except Exception as e:
        print(f"Error querying single MapCfg: {e}")
        return None
    finally:
        session.close()


def get_all_prompt_by_modelname(model_name):
    session = Session()

    try:
        prompts = session.query(Prompt).filter(
            (Prompt.model_name == model_name) | (Prompt.model_name.is_(None)) | (Prompt.model_name == '')
        ).all()

        return prompts

    except Exception as e:
        print(f"An error occurred: {e}")
        return []

    finally:
        session.close()


def update_prompt(id, **kwargs):
    session = Session()
    record = session.query(Prompt).filter_by(id=id).first()
    if record:
        for key, value in kwargs.items():
            setattr(record, key, value)
        session.commit()
    session.close()


def upsert_prompt_by_title(title: str, content: str) -> bool:
    session = Session()
    try:
        record = session.query(Prompt).filter_by(title=title).first()
        if record:
            record.content = content
            session.commit()
            return True

        record = Prompt(title=title, content=content)
        session.add(record)
        session.commit()
        return True
    except Exception:
        try:
            session.rollback()
        except Exception:
            pass
        return False
    finally:
        session.close()


class KeyValue(Base):
    __tablename__ = 'key_value'

    id = Column(Integer, primary_key=True, autoincrement=True)
    key = Column(String, nullable=False)
    value = Column(String, nullable=False)


def add_key_value(key: str, value: str):
    session = Session()
    new_entry = KeyValue(key=key, value=value)
    session.add(new_entry)
    session.commit()


def get_key_value(key: str):
    session = Session()
    result = session.query(KeyValue).filter_by(key=key).first()
    return result.value if result else None


def get_all_key_values() -> list:
    session = Session()
    records = session.query(KeyValue).all()
    return records


def search_key_values(search_text: str) -> list:
    session = Session()
    records = session.query(KeyValue).filter(KeyValue.key.like(f'%{search_text}%')).all()
    return records


def update_key_value(key: str, new_value: str):
    session = Session()
    entry = session.query(KeyValue).filter_by(key=key).first()
    if entry:
        entry.value = new_value
        session.commit()


def delete_key_value(key: str):
    session = Session()
    entry = session.query(KeyValue).filter_by(key=key).first()
    if entry:
        session.delete(entry)
        session.commit()


class ModelMetrics(Base):
    __tablename__ = 'model_metrics'
    id = Column(Integer, primary_key=True)
    connector_name = Column(String)
    model_name = Column(String)
    price = Column(Float)
    speed = Column(Integer)
    understanding = Column(Integer)
    summarizing = Column(Integer)
    knowledge = Column(Integer)
    logical_reasoning = Column(Integer)
    math = Column(Integer)
    coding = Column(Integer)
    writing = Column(Integer)
    attachment = Column(Integer)
    image_recognition = Column(Integer)
    image_generation = Column(Integer)
    video_generation = Column(Integer)
    video_recognition = Column(Integer)
    searching = Column(Integer)
    tool_ability = Column(String)


class MapCfg(Base):
    __tablename__ = 'map_cfg'

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(String(100))
    account = Column(String(100))
    password = Column(String(256))
    nickname = Column(String(100))
    sign = Column(String(200))
    status = Column(String(100))
    humantakeover = Column(Integer, default=0)
    name = Column(String(200))
    borndate = Column(DateTime)
    gender = Column(Integer)
    area = Column(String(100))
    city = Column(String(100))
    address = Column(String(200))
    mail = Column(String(100))
    imaccount = Column(String(100))
    phone = Column(String(100))
    organization = Column(String(200))
    title = Column(String(100))
    orgposition = Column(String(100))
    memo = Column(String(200))
    serveraddress = Column(String(100))
    port = Column(Integer)
    ssl = Column(Boolean)
    resource = Column(String(100))
    proxyused = Column(Boolean)
    proxyaddress = Column(String(100))
    proxyport = Column(Integer)
    proxyssl = Column(Boolean)
    savepasswordlocal = Column(Boolean)
    autoconnect = Column(Boolean)
    sendreceipt = Column(Boolean)
    sendreadflag = Column(Boolean)
    sendchatstatus = Column(Boolean)
    sendgroupchatstatus = Column(Boolean)
    agreeallfriendrequest = Column(Boolean)
    level = Column(Integer)
    credit = Column(Integer)
    money = Column(Integer, default=0)
    token_unit = Column(String(100))
    growth = Column(Integer)
    tech = Column(Integer)
    knowledge = Column(Integer)
    speed = Column(Integer)
    Intelligence = Column(Integer)
    init_address = Column(String(500))
    init_lng = Column(Float)
    init_lat = Column(Float)
    current_address = Column(String(500))
    current_lng = Column(Float)
    current_lat = Column(Float)
    nation_id = Column(String(200))
    avatar = Column(String(1000))
    talk_persons_concurrent_limit = Column(Integer)
    talk_rounds_limit = Column(Integer)
    position = Column(Integer, default=9999)
    is_show = Column(Boolean, default=True)
    is_delete = Column(Boolean)
    create_time = Column(DateTime, default=datetime.now)


def add_map_cfg(**kwargs):
    session = Session()
    try:
        new_cfg = MapCfg(**kwargs)
        session.add(new_cfg)
        session.commit()
        session.refresh(new_cfg)
        return new_cfg.id
    except Exception as e:
        session.rollback()
        print(f"Error adding MapCfg: {e}")
        return None
    finally:
        session.close()


def query_map_cfg(**kwargs):
    session = Session()
    try:
        filter_expr = [getattr(MapCfg, key) == value for key, value in kwargs.items()]
        results = session.query(MapCfg).filter(*filter_expr).order_by(desc(MapCfg.create_time)).all()
        return results
    except Exception as e:
        print(f"Error querying MapCfg: {e}")
        return []
    finally:
        session.close()


def query_single_map_cfg(**kwargs):
    session = Session()
    try:
        filter_expr = [getattr(MapCfg, key) == value for key, value in kwargs.items()]
        result = session.query(MapCfg).filter(*filter_expr).order_by(desc(MapCfg.create_time)).first()
        return result
    except Exception as e:
        print(f"Error querying single MapCfg: {e}")
        return None
    finally:
        session.close()


def update_map_cfg(cfg_id, **kwargs):
    session = Session()
    try:
        cfg = session.query(MapCfg).filter_by(id=cfg_id).first()
        if cfg:
            for key, value in kwargs.items():
                setattr(cfg, key, value)
            session.commit()
            print(f"MapCfg {cfg_id} updated successfully.")
    except Exception as e:
        session.rollback()
        print(f"Error updating MapCfg: {e}")
    finally:
        session.close()


def delete_map_cfg(cfg_id):
    session = Session()
    try:
        cfg = session.query(MapCfg).filter_by(id=cfg_id).first()
        if cfg:
            session.delete(cfg)
            session.commit()
            print(f"MapCfg {cfg_id} deleted successfully.")
    except Exception as e:
        session.rollback()
        print(f"Error deleting MapCfg: {e}")
    finally:
        session.close()


class MapTask(Base):
    __tablename__ = 'map_task'

    id = Column(Integer, primary_key=True, autoincrement=True)
    task_id = Column(String(50))
    title = Column(String(500))
    detail = Column(Text)
    result = Column(Text)
    sub_task_list = Column(Text)
    current_sub_task = Column(Text)
    process_info_list = Column(Text)
    current_place = Column(String(500))
    current_position = Column(String(100))
    task_summary = Column(Text)
    status = Column(Integer, default=0)
    rating = Column(Integer)
    comment = Column(Text)
    agent_id = Column(String(200))
    model_name = Column(String(100))
    create_time = Column(DateTime, default=datetime.now)
    is_delete = Column(Boolean, default=False)


def add_map_task(**kwargs):
    session = Session()
    try:
        new_task = MapTask(**kwargs)
        session.add(new_task)
        session.commit()
        session.refresh(new_task)
        return new_task.id
    except Exception as e:
        session.rollback()
        print(f"Error adding MapTask: {e}")
        return None
    finally:
        session.close()


def query_map_tasks(**kwargs):
    session = Session()
    try:
        filter_expr = [getattr(MapTask, key) == value for key, value in kwargs.items()]
        results = session.query(MapTask).filter(*filter_expr).order_by(desc(MapTask.create_time)).all()
        return results
    except Exception as e:
        print(f"Error querying MapTask: {e}")
        return []
    finally:
        session.close()


def query_single_map_task(**kwargs):
    session = Session()
    try:
        filter_expr = [getattr(MapTask, key) == value for key, value in kwargs.items()]
        result = session.query(MapTask).filter(*filter_expr).order_by(desc(MapTask.create_time)).first()
        return result
    except Exception as e:
        print(f"Error querying single MapTask: {e}")
        return None
    finally:
        session.close()


def update_map_task(id, **kwargs):
    session = Session()
    try:
        task = session.query(MapTask).filter_by(id=id).first()
        if task:
            for key, value in kwargs.items():
                setattr(task, key, value)
            session.commit()
            print(f"MapTask {id} updated successfully.")
    except Exception as e:
        session.rollback()
        print(f"Error updating MapTask: {e}")
    finally:
        session.close()


def delete_map_task(task_id):
    session = Session()
    try:
        task = session.query(MapTask).filter_by(id=task_id).first()
        if task:
            session.delete(task)
            session.commit()
            print(f"MapTask {task_id} deleted successfully.")
    except Exception as e:
        session.rollback()
        print(f"Error deleting MapTask: {e}")
    finally:
        session.close()


class MapTool(Base):
    __tablename__ = 'map_tool'

    id = Column(Integer, primary_key=True, autoincrement=True)
    plugin_id = Column(String(100))
    name = Column(String(100))
    plugin_title = Column(String(100))
    plugin_type = Column(String(100))
    instruction = Column(Text)
    description = Column(Text(200))
    run_mode = Column(String(100))
    run_scope = Column(String(100))
    plugin_directory = Column(String(100))
    plugin_executed = Column(String(100))
    plugin_event = Column(String(100))
    detail = Column(Text(2000))
    company = Column(String(200))
    company_abbr = Column(String(100))
    version = Column(String(100))
    alias_name = Column(String(100))
    filename = Column(String(200))
    runtime_main = Column(String(200))
    runtime_test = Column(String(200))
    get_from_name = Column(String(200))
    get_from_account = Column(String(200))
    get_time = Column(DateTime, default=datetime.now)
    pay = Column(Float, default=100)
    pay_method = Column(String(100))
    trade_id = Column(String(100))
    confirm_needed = Column(Boolean, default=True)
    can_be_sold = Column(Boolean, default=False)
    creator = Column(String(100))
    is_delete = Column(Boolean, default=False)
    create_time = Column(DateTime, default=datetime.now)


def add_map_tool(**kwargs):
    session = Session()
    try:
        new_tech = MapTool(**kwargs)
        session.add(new_tech)
        session.commit()
        session.refresh(new_tech)
        return new_tech.id
    except Exception as e:
        session.rollback()
        print(f"Error adding MapTech: {e}")
        return None
    finally:
        session.close()


def query_map_tools(**kwargs):
    session = Session()
    try:
        filter_expr = [getattr(MapTool, key) == value for key, value in kwargs.items()]
        results = session.query(MapTool).filter(*filter_expr).order_by(desc(MapTool.create_time)).all()
        return results
    except Exception as e:
        print(f"Error querying MapTech: {e}")
        return []
    finally:
        session.close()


def query_single_map_tool(**kwargs):
    session = Session()
    try:
        filter_expr = [getattr(MapTool, key) == value for key, value in kwargs.items()]
        result = session.query(MapTool).filter(*filter_expr).order_by(desc(MapTool.create_time)).first()
        return result
    except Exception as e:
        print(f"Error querying single MapTech: {e}")
        return None
    finally:
        session.close()


def update_map_tool(tech_id, **kwargs):
    session = Session()
    try:
        tech = session.query(MapTool).filter_by(id=tech_id).first()
        if tech:
            for key, value in kwargs.items():
                setattr(tech, key, value)
            session.commit()
            print(f"MapTech {tech_id} updated successfully.")
    except Exception as e:
        session.rollback()
        print(f"Error updating MapTech: {e}")
    finally:
        session.close()


def delete_map_tool(tech_id):
    session = Session()
    try:
        tech = session.query(MapTool).filter_by(id=tech_id).first()
        if tech:
            session.delete(tech)
            session.commit()
            print(f"MapTech {tech_id} deleted successfully.")
    except Exception as e:
        session.rollback()
        print(f"Error deleting MapTech: {e}")
    finally:
        session.close()


class MapTrade(Base):
    __tablename__ = 'map_trade'

    id = Column(Integer, primary_key=True, autoincrement=True)
    trade_id = Column(String(50))
    trade_type = Column(String(100))
    title = Column(String(500))
    detail = Column(Text)
    link = Column(Text)
    trade_with_name = Column(String(200))
    trade_with_account = Column(String(200))
    trade_with_company = Column(Boolean, default=False)
    pay = Column(Float, default=100)
    pay_method = Column(Text, default="as_coin")
    status = Column(Integer, default=0)
    create_time = Column(DateTime, default=datetime.now)
    is_delete = Column(Boolean, default=False)


def add_map_trade(**kwargs):
    session = Session()
    try:
        new_trade = MapTrade(**kwargs)
        session.add(new_trade)
        session.commit()
        session.refresh(new_trade)
        return new_trade.id
    except Exception as e:
        session.rollback()
        print(f"Error adding MapTrade: {e}")
        return None
    finally:
        session.close()


def query_map_trades(**kwargs):
    session = Session()
    try:
        filter_expr = [getattr(MapTrade, key) == value for key, value in kwargs.items()]
        results = session.query(MapTrade).filter(*filter_expr).order_by(desc(MapTrade.create_time)).all()
        return results
    except Exception as e:
        print(f"Error querying MapTrade: {e}")
        return []
    finally:
        session.close()


def query_single_map_trade(**kwargs):
    session = Session()
    try:
        filter_expr = [getattr(MapTrade, key) == value for key, value in kwargs.items()]
        result = session.query(MapTrade).filter(*filter_expr).order_by(desc(MapTrade.create_time)).first()
        return result
    except Exception as e:
        print(f"Error querying single MapTrade: {e}")
        return None
    finally:
        session.close()


def update_map_trade(trade_id, **kwargs):
    session = Session()
    try:
        trade = session.query(MapTrade).filter_by(trade_id=trade_id).first()
        if trade:
            for key, value in kwargs.items():
                setattr(trade, key, value)
            session.commit()
            print(f"MapTrade {trade_id} updated successfully.")
    except Exception as e:
        session.rollback()
        print(f"Error updating MapTrade: {e}")
    finally:
        session.close()


def delete_map_trade(trade_id):
    session = Session()
    try:
        trade = session.query(MapTrade).filter_by(id=trade_id).first()
        if trade:
            session.delete(trade)
            session.commit()
            print(f"MapTrade {trade_id} deleted successfully.")
    except Exception as e:
        session.rollback()
        print(f"Error deleting MapTrade: {e}")
    finally:
        session.close()


class MapVisit(Base):
    __tablename__ = 'map_visit'

    id = Column(Integer, primary_key=True, autoincrement=True)
    visit_id = Column(String(50))
    title = Column(String(500))
    detail = Column(Text)
    place_type = Column(String(100))
    address = Column(Text)
    lng = Column(Float)
    lat = Column(Float)
    owner_name = Column(String(200))
    owner_account = Column(String(100))
    owner_type = Column(String(50))
    is_free = Column(Boolean, default=True)
    trade_id = Column(String(100))
    create_time = Column(DateTime, default=datetime.now)
    is_delete = Column(Boolean, default=False)


def add_map_visit(**kwargs):
    session = Session()
    try:
        new_visit = MapVisit(**kwargs)
        session.add(new_visit)
        session.commit()
        session.refresh(new_visit)
        return new_visit.id
    except Exception as e:
        session.rollback()
        print(f"Error adding MapVisit: {e}")
        return None
    finally:
        session.close()


def query_map_visits(**kwargs):
    session = Session()
    try:
        filter_expr = [getattr(MapVisit, key) == value for key, value in kwargs.items()]
        results = session.query(MapVisit).filter(*filter_expr).order_by(desc(MapVisit.create_time)).all()
        return results
    except Exception as e:
        print(f"Error querying MapVisit: {e}")
        return []
    finally:
        session.close()


def query_single_map_visit(**kwargs):
    session = Session()
    try:
        filter_expr = [getattr(MapVisit, key) == value for key, value in kwargs.items()]
        result = session.query(MapVisit).filter(*filter_expr).order_by(desc(MapVisit.create_time)).first()
        return result
    except Exception as e:
        print(f"Error querying single MapVisit: {e}")
        return None
    finally:
        session.close()


def update_map_visit(visit_id, **kwargs):
    session = Session()
    try:
        visit = session.query(MapVisit).filter_by(id=visit_id).first()
        if visit:
            for key, value in kwargs.items():
                setattr(visit, key, value)
            session.commit()
            print(f"MapVisit {visit_id} updated successfully.")
    except Exception as e:
        session.rollback()
        print(f"Error updating MapVisit: {e}")
    finally:
        session.close()


def delete_map_visit(visit_id):
    session = Session()
    try:
        visit = session.query(MapVisit).filter_by(id=visit_id).first()
        if visit:
            session.delete(visit)
            session.commit()
            print(f"MapVisit {visit_id} deleted successfully.")
    except Exception as e:
        session.rollback()
        print(f"Error deleting MapVisit: {e}")
    finally:
        session.close()


class LlmFrequent(Base):
    __tablename__ = 'llm_frequent'

    id = Column(Integer, primary_key=True, autoincrement=True)
    plugin_id = Column(String(100))
    name = Column(String(100))
    short_name = Column(String(100))
    model_type = Column(String(100))
    alias_name = Column(String(100))
    position = Column(Integer)
    belong_to_agent_id = Column(String(100))
    creator = Column(String(100))
    is_delete = Column(Boolean)
    create_time = Column(DateTime, default=datetime.now)


def add_llm_frequent(**kwargs):
    session = Session()
    try:
        new_frequent = LlmFrequent(**kwargs)
        session.add(new_frequent)
        session.commit()
        session.refresh(new_frequent)
        return new_frequent.id
    except Exception as e:
        session.rollback()
        print(f"Error adding LlmFrequent: {e}")
        return None
    finally:
        session.close()


def query_llm_frequents(**kwargs):
    session = Session()
    try:
        filter_expr = [getattr(LlmFrequent, key) == value for key, value in kwargs.items()]
        results = session.query(LlmFrequent).filter(*filter_expr).order_by(
            asc(LlmFrequent.position)).all()
        return results
    except Exception as e:
        print(f"Error querying LlmFrequent: {e}")
        return []
    finally:
        session.close()


def query_single_llm_frequent(**kwargs):
    session = Session()
    try:
        filter_expr = [getattr(LlmFrequent, key) == value for key, value in kwargs.items()]
        result = session.query(LlmFrequent).filter(*filter_expr).first()
        return result
    except Exception as e:
        print(f"Error querying single LlmFrequent: {e}")
        return None
    finally:
        session.close()


def update_llm_frequent(frequent_id, **kwargs):
    session = Session()
    try:
        frequent = session.query(LlmFrequent).filter_by(id=frequent_id).first()
        if frequent:
            for key, value in kwargs.items():
                setattr(frequent, key, value)
            session.commit()
            print(f"LlmFrequent {frequent_id} updated successfully.")
    except Exception as e:
        session.rollback()
        print(f"Error updating LlmFrequent: {e}")
    finally:
        session.close()


def delete_llm_frequent(frequent_id):
    session = Session()
    try:
        frequent = session.query(LlmFrequent).filter_by(id=frequent_id).first()
        if frequent:
            session.delete(frequent)
            session.commit()
            print(f"LlmFrequent {frequent_id} deleted successfully.")
    except Exception as e:
        session.rollback()
        print(f"Error deleting LlmFrequent: {e}")
    finally:
        session.close()


class PromptFrequent(Base):
    __tablename__ = 'prompt_frequent'

    id = Column(Integer, primary_key=True, autoincrement=True)
    prompt_id = Column(String(100), ForeignKey('prompts.id'))
    title = Column(String(100))
    position = Column(Integer)
    belong_to_agent_id = Column(String(100))
    creator = Column(String(100))
    is_delete = Column(Boolean, default=0)
    create_time = Column(DateTime, default=datetime.now)

    prompt = relationship("Prompt", back_populates="prompt_frequents")


def add_prompt_frequent(**kwargs):
    session = Session()
    try:
        new_frequent = PromptFrequent(**kwargs)
        session.add(new_frequent)
        session.commit()
        session.refresh(new_frequent)
        return new_frequent.id
    except Exception as e:
        session.rollback()
        print(f"Error adding PromptFrequent: {e}")
        return None
    finally:
        session.close()


def query_prompt_frequents(**kwargs):
    session = Session()
    try:
        filter_expr = [getattr(PromptFrequent, key) == value for key, value in kwargs.items()]
        results = session.query(PromptFrequent).filter(*filter_expr).order_by(
            asc(PromptFrequent.position)).all()
        return results
    except Exception as e:
        print(f"Error querying PromptFrequent: {e}")
        return []
    finally:
        session.close()


def get_prompt_frequent_by_agent_id(agent_id):
    session = Session()
    try:
        query_result = session.query(PromptFrequent).filter(
            PromptFrequent.is_delete == 0, PromptFrequent.belong_to_agent_id == agent_id
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

    except Exception as e:
        print(f"Error querying PromptFrequent: {e}")
        return []
    finally:
        session.close()


def query_single_prompt_frequent(**kwargs):
    session = Session()
    try:
        filter_expr = [getattr(PromptFrequent, key) == value for key, value in kwargs.items()]
        result = session.query(PromptFrequent).filter(*filter_expr).first()
        return result
    except Exception as e:
        print(f"Error querying single PromptFrequent: {e}")
        return None
    finally:
        session.close()


def update_prompt_frequent(frequent_id, **kwargs):
    session = Session()
    try:
        frequent = session.query(PromptFrequent).filter_by(id=frequent_id).first()
        if frequent:
            for key, value in kwargs.items():
                setattr(frequent, key, value)
            session.commit()
            print(f"PromptFrequent {frequent_id} updated successfully.")
    except Exception as e:
        session.rollback()
        print(f"Error updating PromptFrequent: {e}")
    finally:
        session.close()


def delete_prompt_frequent(frequent_id):
    session = Session()
    try:
        frequent = session.query(PromptFrequent).filter_by(id=frequent_id).first()
        if frequent:
            session.delete(frequent)
            session.commit()
            print(f"PromptFrequent {frequent_id} deleted successfully.")
    except Exception as e:
        session.rollback()
        print(f"Error deleting PromptFrequent: {e}")
    finally:
        session.close()


class SystemInit(Base):
    __tablename__ = 'system_init'

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(100))
    avatar = Column(Text)
    password = Column(String(128))
    confirm_password = Column(String(128))
    profile = Column(String(500))
    llm = Column(String(100))
    llm_server = Column(String(500))
    api_key = Column(String(200))
    avatar3d = Column(Text)
    account = Column(String(128))
    account_password = Column(String(128))
    sns_url = Column(Text)
    map = Column(String)
    map_api_key = Column(String(128))
    map_id = Column(String(128))
    status = Column(Integer)
    is_delete = Column(Boolean, default=False)
    create_time = Column(DateTime, default=datetime.utcnow)


def add_SystemInit(name, avatar, password, confirm_password, profile, llm, llm_server, api_key, avatar3d,
                   account, account_password, sns_url, map, map_api_key, map_id, status):
    session = Session()
    system_init = SystemInit(
        name=name,
        avatar=avatar,
        password=password,
        confirm_password=confirm_password,
        profile=profile,
        llm=llm,
        llm_server=llm_server,
        api_key=api_key,
        avatar3d=avatar3d,
        account=account,
        account_password=account_password,
        sns_url=sns_url,
        map=map,
        map_api_key=map_api_key,
        map_id=map_id,
        status=status
    )
    session.add(system_init)
    session.commit()
    session.close()


def query_SystemInit_All(**kwargs):
    session = Session()
    records = session.query(SystemInit).filter_by(**kwargs).all()
    session.close()
    return records


def query_SystemInit(**kwargs):
    session = Session()
    record = session.query(SystemInit).filter_by(**kwargs).first()
    session.close()
    return record


def update_SystemInit_ById(id, **kwargs):
    session = Session()
    record = session.query(SystemInit).filter_by(id=id).first()
    if record:
        for key, value in kwargs.items():
            setattr(record, key, value)
        session.commit()
    session.close()


def delete_SystemInit(id):
    session = Session()
    record = session.query(SystemInit).filter_by(id=id).first()
    if record:
        record.is_delete = True
        session.commit()
    session.close()


class MapActivity(Base):
    __tablename__ = 'map_activity'
    id = Column(Integer, primary_key=True, autoincrement=True)
    activity_id = Column(String(50))
    content = Column(Text)
    type = Column(String(100))
    create_time = Column(DateTime, default=datetime.now)
    is_delete = Column(Boolean, default=False)


def add_map_activity(activity_id, content, type):
    session = Session()
    try:
        new_activity = MapActivity(activity_id=activity_id, content=content, type=type)
        session.add(new_activity)
        _commit_with_retry(session, max_retries=5, base_delay=0.2)
        return True
    except Exception as e:
        err_msg = str(e).lower()
        try:
            session.rollback()
        except Exception:
            pass
        if 'database is locked' in err_msg:
            _dbfactory_logger.error(
                "[DBFactory] database is locked: failed to add map activity, skipping. activity_id=%s",
                activity_id,
            )
            return False
        raise
    finally:
        session.close()


def query_map_activity_all(**kwargs):
    session = Session()
    records = session.query(MapActivity).filter_by(**kwargs).all()
    session.close()
    return records


def query_map_activity_previous(last_record_id=None, count=20, type_str=None):
    session = Session()

    query = session.query(MapActivity)

    if last_record_id is not None:
        query = query.filter(MapActivity.id < last_record_id)

    if type_str:
        query = query.filter(MapActivity.type == type_str)

    records = query.order_by(MapActivity.id.desc()).limit(count).all()

    session.close()
    return records


def query_map_activity(**kwargs):
    session = Session()
    record = session.query(MapActivity).filter_by(**kwargs).first()
    session.close()
    return record


def update_map_activity_by_id(activity_id, **kwargs):
    session = Session()
    record = session.query(MapActivity).filter_by(activity_id=activity_id).first()
    if record:
        for key, value in kwargs.items():
            setattr(record, key, value)
        session.commit()
    session.close()


def delete_map_activity(activity_id):
    session = Session()
    record = session.query(MapActivity).filter_by(activity_id=activity_id).first()
    if record:
        session.delete(record)
        session.commit()
    session.close()


class MapPresetMsg(Base):
    __tablename__ = 'map_preset_msg'
    id = Column(Integer, primary_key=True, autoincrement=True)
    content = Column(Text)
    position = Column(Integer, default=0)
    create_time = Column(DateTime, default=datetime.now)
    is_delete = Column(Boolean, default=False)


def add_map_preset_msg(content):
    session = Session()
    try:
        new_msg = MapPresetMsg(content=content)
        session.add(new_msg)
        session.commit()
    except Exception as e:
        session.rollback()
        raise e
    finally:
        session.close()


def query_map_preset_msg_all(**kwargs):
    session = Session()
    try:
        records = session.query(MapPresetMsg).filter_by(**kwargs).all()
    finally:
        session.close()
    return records


def query_map_preset_msg_previous(last_record_id=None, count=20):
    session = Session()
    query = session.query(MapPresetMsg)

    if last_record_id is not None:
        query = query.filter(MapPresetMsg.id < last_record_id)

    records = query.order_by(MapPresetMsg.id.desc()).limit(count).all()
    session.close()
    return records


def query_map_preset_msg(**kwargs):
    session = Session()
    try:
        record = session.query(MapPresetMsg).filter_by(**kwargs).first()
    finally:
        session.close()
    return record


def update_map_preset_msg_by_id(msg_id, **kwargs):
    session = Session()
    try:
        record = session.query(MapPresetMsg).filter_by(id=msg_id).first()
        if record:
            for key, value in kwargs.items():
                setattr(record, key, value)
            session.commit()
    except Exception as e:
        session.rollback()
        raise e
    finally:
        session.close()


def delete_map_preset_msg(content):
    session = Session()
    try:
        record = session.query(MapPresetMsg).filter_by(content=content).first()
        if record:
            session.delete(record)
            session.commit()
    except Exception as e:
        session.rollback()
        raise e
    finally:
        session.close()


class ChatPresetMsg(Base):
    __tablename__ = 'chat_preset_msg'
    id = Column(Integer, primary_key=True, autoincrement=True)
    content = Column(Text)
    position = Column(Integer, default=0)
    create_time = Column(DateTime, default=datetime.now)
    is_delete = Column(Boolean, default=False)


def add_chat_preset_msg(content):
    session = Session()
    try:
        new_msg = ChatPresetMsg(content=content)
        session.add(new_msg)
        session.commit()
    except Exception as e:
        session.rollback()
        raise e
    finally:
        session.close()


def query_chat_preset_msg_all(**kwargs):
    session = Session()
    try:
        records = session.query(ChatPresetMsg).filter_by(**kwargs).all()
    finally:
        session.close()
    return records


def query_chat_preset_msg_previous(last_record_id=None, count=20):
    session = Session()
    query = session.query(ChatPresetMsg)

    if last_record_id is not None:
        query = query.filter(ChatPresetMsg.id < last_record_id)

    records = query.order_by(ChatPresetMsg.id.desc()).limit(count).all()
    session.close()
    return records


def query_chat_preset_msg(**kwargs):
    session = Session()
    try:
        record = session.query(ChatPresetMsg).filter_by(**kwargs).first()
    finally:
        session.close()
    return record


def update_chat_preset_msg_by_id(msg_id, **kwargs):
    session = Session()
    try:
        record = session.query(ChatPresetMsg).filter_by(id=msg_id).first()
        if record:
            for key, value in kwargs.items():
                setattr(record, key, value)
            session.commit()
    except Exception as e:
        session.rollback()
        raise e
    finally:
        session.close()


def delete_chat_preset_msg(content):
    session = Session()
    try:
        record = session.query(ChatPresetMsg).filter_by(content=content).first()
        if record:
            session.delete(record)
            session.commit()
    except Exception as e:
        session.rollback()
        raise e
    finally:
        session.close()


class ToolList(Base):
    __tablename__ = 'tool_list'

    id = Column(String, primary_key=True)
    name = Column(String)
    description = Column(Text)
    plugin_type = Column(String)
    confirm_needed = Column(Boolean)
    can_be_sold = Column(Boolean)


def query_tool_list(**kwargs):
    session = Session()
    try:
        filter_expr = [getattr(ToolList, key) == value for key, value in kwargs.items()]

        results = session.query(ToolList).filter(*filter_expr).order_by(desc(ToolList.id)).all()
        return results
    except Exception as e:
        print(f"Error querying ToolList: {e}")
        return []
    finally:
        session.close()


def query_single_tool(**kwargs):
    session = Session()
    try:
        filter_expr = [getattr(ToolList, key) == value for key, value in kwargs.items()]

        result = session.query(ToolList).filter(*filter_expr).order_by(desc(ToolList.id)).first()
        return result
    except Exception as e:
        print(f"Error querying single ToolList: {e}")
        return None
    finally:
        session.close()


Base.metadata.create_all(engine)
_ensure_system_cfg_columns()
if __name__ == "__main__":
    agent = query_AgentCfg(id=1)



