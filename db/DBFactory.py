import os

import sqlite3

from sqlalchemy import create_engine, Column, Integer, String, event
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import NullPool
from pathlib import Path

from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, Boolean, Text, Float
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

from db.write_queue import db_write


def _commit_with_retry(session, max_retries=3, base_delay=0.5):
    """Deprecated: kept only for backward compatibility with memory_store imports.
    New code should use db_write() from db.write_queue instead."""
    session.commit()


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
    try:
        from backend.apps.sns.message_formatter import format_internal_xmpp_message_for_storage
        content = format_internal_xmpp_message_for_storage(content)
    except Exception:
        pass

    def _do(session):
        record = AIChatMessages(conversation_id=conversation_id, flag=flag, title=title, content=content,
                                owner_name=owner_name, owner_account=owner_account, friend_name=friend_name,
                                friend_account=friend_account, is_first=is_first, attachment_list=attachment_list,
                                document_content=document_content, image_json=image_json, km_list=km_list,
                                km_content=km_content)
        session.add(record)
    db_write(_do, description="add_AIChatMessages")


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


def update_AIChatMessages(id, **kwargs):
    def _do(session):
        record = session.query(AIChatMessages).filter_by(id=id).first()
        if record:
            for key, value in kwargs.items():
                setattr(record, key, value)
    db_write(_do, description="update_AIChatMessages")


def update_AIChatMessages_stick(id, value=None, key: str = 'stick_time'):
    def _do(session):
        task = session.query(AIChatMessages).filter_by(id=id).first()
        if task:
            setattr(task, key, value)
    db_write(_do, description="update_AIChatMessages_stick")


def delete_AIChatMessages(id):
    def _do(session):
        record = session.query(AIChatMessages).filter_by(id=id).first()
        if record:
            session.delete(record)
    db_write(_do, description="delete_AIChatMessages")


def query_AIChat_Content(id, **kwargs):
    session = Session()
    res = session.query(AIChatMessages).filter(AIChatMessages.is_first == True, AIChatMessages.id == id).one_or_none()
    if res:
        conversation_id = res.conversation_id
    tasks = session.query(AIChatMessages).filter(AIChatMessages.conversation_id == conversation_id).order_by(
        asc(AIChatMessages.create_time)).all()

    session.close()

    return tasks


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
    def _do(session):
        ai_friend = AIFriend(account=account, nick_name=nick_name, groups=groups, owner_sns_account=owner_sns_account, memo=memo, sign=sign, subscription=subscription, name=name, borndate=borndate, gender=gender, area=area, city=city, address=address, mail=mail, phone=phone, organization=organization, title=title, position=position)
        session.add(ai_friend)
    db_write(_do, description="add_AIFriend")


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
    def _do(session):
        record = session.query(AIFriend).filter_by(id=id).first()
        if record:
            for key, value in kwargs.items():
                setattr(record, key, value)
    db_write(_do, description="update_AIFriend_ById")


def update_AIFriend(account, owner_sns_account, **kwargs):
    def _do(session):
        record = session.query(AIFriend).filter_by(account=account, owner_sns_account=owner_sns_account).first()
        if record:
            for key, value in kwargs.items():
                setattr(record, key, value)
    db_write(_do, description="update_AIFriend")


def delete_AIFriend(id):
    def _do(session):
        record = session.query(AIFriend).filter_by(id=id).first()
        if record:
            session.delete(record)
    db_write(_do, description="delete_AIFriend")


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
    def _do(session):
        agentcfg = AgentCfg(user_id=user_id, name=name, memo=memo, borndate=borndate, borncontry=borncontry, language=language, gender=gender, joinfederation=joinfederation, syncfederation=syncfederation, federationid=federationid, defaultmodel=defaultmodel, defaultrole=defaultrole, lastmodel=lastmodel, lastrole=lastrole, specialization=specialization, plugins=plugins, kms=kms, last_plugins=last_plugins, last_kms=last_kms, prompt=prompt, snsaccount=snsaccount, snsnickname=snsnickname, islimittotalmessage=islimittotalmessage, islimitmessagepp=islimitmessagepp, totalmessages=totalmessages, ppmessages=ppmessages, readfile=readfile, writefile=writefile, deletefile=deletefile, execfile=execfile, uselastmodel=uselastmodel, uselastrole=uselastrole, uselastplugins=uselastplugins, uselastkms=uselastkms, callpluginbyinstruct=callpluginbyinstruct, modelfrequent=modelfrequent,
                            rolefrequent=rolefrequent, multimodelfrequent=multimodelfrequent, autorunrounds=autorunrounds)
        session.add(agentcfg)
    db_write(_do, description="add_AgentCfg")


def query_AgentCfg_All(**kwargs):
    session = Session()
    # Exclude soft-deleted agents by default
    if 'is_delete' not in kwargs:
        kwargs['is_delete'] = False
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
    def _do(session):
        agent = session.query(AgentCfg).filter_by(id=id).first()
        if agent:
            for key, value in kwargs.items():
                setattr(agent, key, value)
    db_write(_do, description="update_AgentCfg")


def update_AgentCfg_by_user_id(user_id, **kwargs):
    def _do(session):
        agent = session.query(AgentCfg).filter_by(user_id=user_id).first()
        if agent:
            for key, value in kwargs.items():
                setattr(agent, key, value)
    db_write(_do, description="update_AgentCfg_by_user_id")


def delete_AgentCfg(user_id):
    def _do(session):
        agent = session.query(AgentCfg).filter_by(user_id=user_id).first()
        if agent:
            session.delete(agent)
    db_write(_do, description="delete_AgentCfg")


def get_agent_system_prompt(name):
    session = Session()
    agentcfg = session.query(AgentCfg).filter_by(name=name).first()

    return agentcfg.prompt if agentcfg else None


def get_agent_specialization_description(name):
    session = Session()
    agentcfg = session.query(AgentCfg).filter_by(name=name).first()

    return agentcfg.specialization if agentcfg else None


class AiChatCfg(Base):
    __tablename__ = 'aichat_cfg'
    id = Column(Integer, primary_key=True, autoincrement=True)

    user_id = Column(String(100))
    account = Column(String(100))
    password = Column(String(256))
    nickname = Column(String(100))
    sign = Column(String(200))
    status = Column(String(100))
    membership = Column(Integer)
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
    def _do(session):
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
        return aichatCfg.id
    return db_write(_do, description="add_AiChatCfg")


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
    def _do(session):
        record = session.query(AiChatCfg).first()
        if record:
            for key, value in kwargs.items():
                setattr(record, key, value)
    db_write(_do, description="update_AiChatCfg_map")


def update_AiChatCfg(id, **kwargs):
    def _do(session):
        record = session.query(AiChatCfg).filter_by(id=id).first()
        if record:
            for key, value in kwargs.items():
                setattr(record, key, value)
    db_write(_do, description="update_AiChatCfg")


def update_AiChatCfg_by_user_id(user_id, **kwargs):
    def _do(session):
        record = session.query(AiChatCfg).filter_by(user_id=user_id).first()
        if record:
            for key, value in kwargs.items():
                setattr(record, key, value)
    db_write(_do, description="update_AiChatCfg_by_user_id")


def delete_AiChatCfg(user_id):
    def _do(session):
        record = session.query(AiChatCfg).filter_by(user_id=user_id).first()
        if record:
            session.delete(record)
    db_write(_do, description="delete_AiChatCfg")


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
    def _do(session):
        kmCfg = KMCfg(km_id=km_id, name=name, memo=memo, label=label, kmpath=kmpath, kmtype=kmtype, vectorization=vectorization, stopvectorization=stopvectorization, vectortype=vectortype, embeddingmodel=embeddingmodel, textblocklength=textblocklength, overlaplength=overlaplength, titleaugment=titleaugment, config_param=config_param)
        session.add(kmCfg)
    db_write(_do, description="add_KMCfg")


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
    def _do(session):
        record = session.query(KMCfg).filter_by(id=id).first()
        if record:
            for key, value in kwargs.items():
                setattr(record, key, value)
    db_write(_do, description="update_KMCfg")


def update_KMCfg_by_kmid(km_id, **kwargs):
    def _do(session):
        record = session.query(KMCfg).filter_by(km_id=km_id).first()
        if record:
            for key, value in kwargs.items():
                setattr(record, key, value)
    db_write(_do, description="update_KMCfg_by_kmid")


def delete_KMCfg(km_id):
    def _do(session):
        record = session.query(KMCfg).filter_by(km_id=km_id).first()
        if record:
            session.delete(record)
    db_write(_do, description="delete_KMCfg")


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
    def _do(session):
        kmData = KMData(km_id=km_id, filename=filename, filenum=filenum, textblocklength=textblocklength, overlaplength=overlaplength, waitvectorization=waitvectorization)
        session.add(kmData)
        session.flush()
        return kmData.id
    return db_write(_do, description="add_KMData")


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
    def _do(session):
        record = session.query(KMData).filter_by(id=id).first()
        if record:
            for key, value in kwargs.items():
                setattr(record, key, value)
    db_write(_do, description="update_KMData")


def delete_KMData(id):
    def _do(session):
        record = session.query(KMData).filter_by(id=id).first()
        if record:
            session.delete(record)
    db_write(_do, description="delete_KMData")


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
    def _do(session):
        pluginMng = PluginMng(plugin_id=plugin_id, company=company, company_abbr=company_abbr, name=name, version=version, alias_name=alias_name, filename=filename, run_mode=run_mode, run_scope=run_scope, instruction=instruction, runtime_main=runtime_main, runtime_test=runtime_test, description=description, plugin_directory=plugin_directory, plugin_type=plugin_type, plugin_executed=plugin_executed, plugin_event=plugin_event, plugin_title=plugin_title, detail=detail, creator=creator, used_in_sns=used_in_sns)
        session.add(pluginMng)
    db_write(_do, description="add_PluginMng")


def copy_plugin_record(plugin_id, new_plugin_id, **kwargs):
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
    return db_write(_do, description="copy_plugin_record")


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
    def _do(session):
        record = session.query(PluginMng).filter_by(id=id).first()
        if record:
            for key, value in kwargs.items():
                setattr(record, key, value)
    db_write(_do, description="update_PluginMng")


def delete_PluginMng(**kwargs):
    def _do(session):
        record = session.query(PluginMng).filter_by(**kwargs).first()
        if record:
            session.delete(record)
    db_write(_do, description="delete_PluginMng")


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
    def _do(session):
        new_function = FunctionMng(
            function_id=function_id, name=name, instruction=instruction, file_path=file_path,
            requirement=requirement, parameter=parameter, description=description, detail=detail,
            function_type=function_type, function_event=function_event, creator=creator, used_in_sns=used_in_sns
        )
        session.add(new_function)
        session.flush()
        return new_function.id
    return db_write(_do, description="add_function_mng")


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
    def _do(session):
        record = session.query(FunctionMng).filter_by(function_id=function_id).first()
        if record:
            for key, value in kwargs.items():
                setattr(record, key, value)
    db_write(_do, description="update_function_mng")


def update_function_mng_with_id(id, **kwargs):
    def _do(session):
        record = session.query(FunctionMng).filter_by(id=id).first()
        if record:
            for key, value in kwargs.items():
                setattr(record, key, value)
    db_write(_do, description="update_function_mng_with_id")


def delete_function_mng(**kwargs):
    def _do(session):
        record = session.query(FunctionMng).filter_by(**kwargs).first()
        if record:
            session.delete(record)
    db_write(_do, description="delete_function_mng")


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
    def _do(session):
        new_mcp = McpMng(
            mcp_id=mcp_id, name=name, instruction=instruction, file_path=file_path,
            requirement=requirement, parameter=parameter, description=description, detail=detail,
            mcp_type=mcp_type, mcp_event=mcp_event, creator=creator, used_in_sns=used_in_sns
        )
        session.add(new_mcp)
        session.flush()
        return new_mcp.id
    return db_write(_do, description="add_mcp_mng")


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
    def _do(session):
        record = session.query(McpMng).filter_by(mcp_id=mcp_id).first()
        if record:
            for key, value in kwargs.items():
                setattr(record, key, value)
    db_write(_do, description="update_mcp_mng")


def update_mcp_mng_with_id(id, **kwargs):
    def _do(session):
        record = session.query(McpMng).filter_by(id=id).first()
        if record:
            for key, value in kwargs.items():
                setattr(record, key, value)
    db_write(_do, description="update_mcp_mng_with_id")


def delete_mcp_mng(**kwargs):
    def _do(session):
        record = session.query(McpMng).filter_by(**kwargs).first()
        if record:
            session.delete(record)
    db_write(_do, description="delete_mcp_mng")


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
    def _do(session):
        new_skill = SkillMng(
            skill_id=skill_id, name=name, instruction=instruction, file_path=file_path,
            requirement=requirement, parameter=parameter, description=description, detail=detail,
            skill_type=skill_type, skill_event=skill_event, creator=creator, used_in_sns=used_in_sns
        )
        session.add(new_skill)
        session.flush()
        return new_skill.id
    return db_write(_do, description="add_skill_mng")


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
    def _do(session):
        record = session.query(SkillMng).filter_by(skill_id=skill_id).first()
        if record:
            for key, value in kwargs.items():
                setattr(record, key, value)
    db_write(_do, description="update_skill_mng")


def update_skill_mng_with_id(id, **kwargs):
    def _do(session):
        record = session.query(SkillMng).filter_by(id=id).first()
        if record:
            for key, value in kwargs.items():
                setattr(record, key, value)
    db_write(_do, description="update_skill_mng_with_id")


def delete_skill_mng(**kwargs):
    def _do(session):
        record = session.query(SkillMng).filter_by(**kwargs).first()
        if record:
            session.delete(record)
    db_write(_do, description="delete_skill_mng")


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
    def _do(session):
        new_web = WebMng(
            web_id=web_id, name=name, title=title,
            type=type, description=description, filename=filename, url=url
        )
        session.add(new_web)
        session.flush()
        return new_web.id
    return db_write(_do, description="add_web_mng")


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
    def _do(session):
        record = session.query(WebMng).filter_by(web_id=web_id).first()
        if record:
            for key, value in kwargs.items():
                setattr(record, key, value)
    db_write(_do, description="update_web_mng")


def delete_web_mng(**kwargs):
    def _do(session):
        record = session.query(WebMng).filter_by(**kwargs).first()
        if record:
            session.delete(record)
    db_write(_do, description="delete_web_mng")


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
    def _do(session):
        new_note = NoteMng(
            note_id=note_id, title=title, file_name=file_name, content=content, km_id=km_id,
            tag_1=tag_1, tag_2=tag_2, tag_3=tag_3, waitvectorization=waitvectorization, label=label
        )
        session.add(new_note)
        session.flush()
        return new_note.id
    return db_write(_do, description="add_note_mng")


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
    def _do(session):
        record = session.query(NoteMng).filter_by(note_id=note_id).first()
        if record:
            for key, value in kwargs.items():
                setattr(record, key, value)
    db_write(_do, description="update_note_mng")


def update_note_mng_stick(id, value=None, key: str = 'stick_time'):
    def _do(session):
        task = session.query(NoteMng).filter_by(id=id).first()
        if task:
            setattr(task, key, value)
    db_write(_do, description="update_note_mng_stick")


def update_note_mng_by_recordid(id, **kwargs):
    def _do(session):
        record = session.query(NoteMng).filter_by(id=id).first()
        if record:
            for key, value in kwargs.items():
                setattr(record, key, value)
    db_write(_do, description="update_note_mng_by_recordid")


def delete_note_mng(**kwargs):
    def _do(session):
        record = session.query(NoteMng).filter_by(**kwargs).first()
        if record:
            session.delete(record)
    db_write(_do, description="delete_note_mng")


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
    log_retention_days = Column(Integer, default=3)
    tool_check_every_n = Column(Integer, default=0)
    tool_check_before_review_enabled = Column(Boolean, default=False)
    agent_card_before_review_enabled = Column(Boolean, default=False)
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
        if 'log_retention_days' not in columns:
            cursor.execute("ALTER TABLE system_cfg ADD COLUMN log_retention_days INTEGER DEFAULT 3")
        if 'tool_check_every_n' not in columns:
            cursor.execute("ALTER TABLE system_cfg ADD COLUMN tool_check_every_n INTEGER DEFAULT 0")
        if 'tool_check_before_review_enabled' not in columns:
            cursor.execute("ALTER TABLE system_cfg ADD COLUMN tool_check_before_review_enabled INTEGER DEFAULT 0")
        if 'agent_card_before_review_enabled' not in columns:
            cursor.execute("ALTER TABLE system_cfg ADD COLUMN agent_card_before_review_enabled INTEGER DEFAULT 0")
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
    def _do(session):
        systemCfg = SystemCfg(autorun=autorun, showtaskbar=showtaskbar, updateinfo=updateinfo, minirunontray=minirunontray, closebuttontype=closebuttontype, style=style, showinfo=showinfo, showinfoicon=showinfoicon, infosound=infosound)
        session.add(systemCfg)
    db_write(_do, description="add_SystemCfg")


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
    def _do(session):
        record = session.query(SystemCfg).filter_by(id=id).first()
        if record:
            for key, value in kwargs.items():
                setattr(record, key, value)
    db_write(_do, description="update_SystemCfg")


def delete_SystemCfg(id):
    def _do(session):
        record = session.query(SystemCfg).filter_by(id=id).first()
        if record:
            session.delete(record)
    db_write(_do, description="delete_SystemCfg")


class Prompt(Base):
    __tablename__ = 'prompts'
    id = Column(Integer, primary_key=True, autoincrement=True)
    title = Column(String)
    content = Column(String)
    question = Column(String)
    tags = Column(String)
    model_name = Column(String(100))
    position = Column(Integer)


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
    def _do(session):
        record = session.query(Prompt).filter_by(id=id).first()
        if record:
            for key, value in kwargs.items():
                setattr(record, key, value)
    db_write(_do, description="update_prompt")


def upsert_prompt_by_title_with_tags(title: str, content: str, tags: str = "") -> bool:
    """Upsert a prompt by title. Sets tags only on initial insert (does not overwrite existing tags)."""
    def _do(session):
        record = session.query(Prompt).filter_by(title=title).first()
        if record:
            record.content = content
            return True
        record = Prompt(title=title, content=content, tags=tags)
        session.add(record)
        return True
    try:
        return db_write(_do, description="upsert_prompt_by_title_with_tags")
    except Exception:
        return False


def upsert_prompt_by_title(title: str, content: str) -> bool:
    def _do(session):
        record = session.query(Prompt).filter_by(title=title).first()
        if record:
            record.content = content
            return True
        record = Prompt(title=title, content=content)
        session.add(record)
        return True
    try:
        return db_write(_do, description="upsert_prompt_by_title")
    except Exception:
        return False


class KeyValue(Base):
    __tablename__ = 'key_value'

    id = Column(Integer, primary_key=True, autoincrement=True)
    key = Column(String, nullable=False)
    value = Column(String, nullable=False)


def add_key_value(key: str, value: str):
    def _do(session):
        new_entry = KeyValue(key=key, value=value)
        session.add(new_entry)
    db_write(_do, description="add_key_value")


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
    def _do(session):
        entry = session.query(KeyValue).filter_by(key=key).first()
        if entry:
            entry.value = new_value
    db_write(_do, description="update_key_value")


def delete_key_value(key: str):
    def _do(session):
        entry = session.query(KeyValue).filter_by(key=key).first()
        if entry:
            session.delete(entry)
    db_write(_do, description="delete_key_value")


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
    def _do(session):
        new_trade = MapTrade(**kwargs)
        session.add(new_trade)
        session.flush()
        return new_trade.id
    return db_write(_do, description="add_map_trade")


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
    def _do(session):
        trade = session.query(MapTrade).filter_by(trade_id=trade_id).first()
        if trade:
            for key, value in kwargs.items():
                setattr(trade, key, value)
            if "create_time" not in kwargs:
                trade.create_time = datetime.now()
    db_write(_do, description="update_map_trade")


def delete_map_trade(trade_id):
    def _do(session):
        trade = session.query(MapTrade).filter_by(id=trade_id).first()
        if trade:
            session.delete(trade)
    db_write(_do, description="delete_map_trade")


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
    url = Column(Text)
    coord_key = Column(String(80))
    owner_name = Column(String(200))
    owner_account = Column(String(100))
    owner_type = Column(String(50))
    is_free = Column(Boolean, default=True)
    trade_id = Column(String(100))
    create_time = Column(DateTime, default=datetime.now)
    is_delete = Column(Boolean, default=False)


def add_map_visit(**kwargs):
    def _do(session):
        new_visit = MapVisit(**kwargs)
        session.add(new_visit)
        session.flush()
        return new_visit.id
    return db_write(_do, description="add_map_visit")


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
    def _do(session):
        visit = session.query(MapVisit).filter_by(id=visit_id).first()
        if visit:
            for key, value in kwargs.items():
                setattr(visit, key, value)
    db_write(_do, description="update_map_visit")


def delete_map_visit(visit_id):
    def _do(session):
        visit = session.query(MapVisit).filter_by(id=visit_id).first()
        if visit:
            session.delete(visit)
    db_write(_do, description="delete_map_visit")


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
    def _do(session):
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
    db_write(_do, description="add_SystemInit")


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
    def _do(session):
        record = session.query(SystemInit).filter_by(id=id).first()
        if record:
            for key, value in kwargs.items():
                setattr(record, key, value)
    db_write(_do, description="update_SystemInit_ById")


def delete_SystemInit(id):
    def _do(session):
        record = session.query(SystemInit).filter_by(id=id).first()
        if record:
            record.is_delete = True
    db_write(_do, description="delete_SystemInit")


class MapActivity(Base):
    __tablename__ = 'map_activity'
    id = Column(Integer, primary_key=True, autoincrement=True)
    activity_id = Column(String(50))
    content = Column(Text)
    type = Column(String(100))
    create_time = Column(DateTime, default=datetime.now)
    is_delete = Column(Boolean, default=False)


def add_map_activity(activity_id, content, type):
    def _do(session):
        new_activity = MapActivity(activity_id=activity_id, content=content, type=type)
        session.add(new_activity)
        return True
    try:
        return db_write(_do, description="add_map_activity")
    except Exception as e:
        _dbfactory_logger.error(
            "[DBFactory] Failed to add map activity. activity_id=%s, error=%s",
            activity_id, e,
        )
        return False


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
    def _do(session):
        record = session.query(MapActivity).filter_by(activity_id=activity_id).first()
        if record:
            for key, value in kwargs.items():
                setattr(record, key, value)
    db_write(_do, description="update_map_activity_by_id")


def delete_map_activity(activity_id):
    def _do(session):
        record = session.query(MapActivity).filter_by(activity_id=activity_id).first()
        if record:
            session.delete(record)
    db_write(_do, description="delete_map_activity")


class MapPresetMsg(Base):
    __tablename__ = 'map_preset_msg'
    id = Column(Integer, primary_key=True, autoincrement=True)
    content = Column(Text)
    position = Column(Integer, default=0)
    create_time = Column(DateTime, default=datetime.now)
    is_delete = Column(Boolean, default=False)


def add_map_preset_msg(content):
    def _do(session):
        new_msg = MapPresetMsg(content=content)
        session.add(new_msg)
    db_write(_do, description="add_map_preset_msg")


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
    def _do(session):
        record = session.query(MapPresetMsg).filter_by(id=msg_id).first()
        if record:
            for key, value in kwargs.items():
                setattr(record, key, value)
    db_write(_do, description="update_map_preset_msg_by_id")


def delete_map_preset_msg(content):
    def _do(session):
        record = session.query(MapPresetMsg).filter_by(content=content).first()
        if record:
            session.delete(record)
    db_write(_do, description="delete_map_preset_msg")


Base.metadata.create_all(engine)
_ensure_system_cfg_columns()
if __name__ == "__main__":
    agent = query_AgentCfg(id=1)



