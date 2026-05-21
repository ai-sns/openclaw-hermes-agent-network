import os

import sqlite3

from sqlalchemy import create_engine, Column, Integer, String, event
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import NullPool
from pathlib import Path

from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, Boolean, Text, Float
from sqlalchemy import desc, asc
from sqlalchemy import or_, and_

from db.base import Base
from db.models.aisns import AIChatMessages, AIFriend, AISnsCfg, MapTrade, MapVisit, MapActivity, MapPresetMsg
from db.models.agent import AgentCfg, AgentDocSkill, Prompt, LLMConfig, RoleConfig
from db.models.km import KeyValue, KMCfg, KMData, NoteMng
from db.models.tools import PluginMng, FunctionMng, McpMng, SkillMng
from db.models.web import WebMng
from db.models.system import SystemCfg, SystemInit
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


from contextlib import contextmanager


@contextmanager
def _session_scope():
    """Yield a SQLAlchemy session that is always closed, even on exception.

    Use this instead of the bare ``session = Session(); ... session.close()``
    pattern to guarantee session release on exception paths.
    """
    session = Session()
    try:
        yield session
    finally:
        session.close()

import time
import logging
_dbfactory_logger = logging.getLogger(__name__)

from db.write_queue import db_write


def _commit_with_retry(session, max_retries=3, base_delay=0.5):
    """Deprecated: kept only for backward compatibility with memory_store imports.
    New code should use db_write() from db.write_queue instead."""
    session.commit()




def add_AIChatMessages(conversation_id, flag, title, content, owner_name, owner_account, friend_name, friend_account,
                       is_first=False, attachment_list="", document_content="", image_json="", km_list="",
                       km_content=""):
    try:
        from runtime.apps.sns.message_formatter import format_internal_xmpp_message_for_storage
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
    with _session_scope() as session:

        query = session.query(MapActivity)

        if last_record_id is not None:
            query = query.filter(MapActivity.id < last_record_id)

        if type_str:
            query = query.filter(MapActivity.type == type_str)

        records = query.order_by(MapActivity.id.desc()).limit(count).all()

        return records


def query_AIChatMessages_All_previous(last_record_id=None, count=20, **kwargs):
    with _session_scope() as session:
        query = session.query(AIChatMessages)
        if last_record_id is not None:
            query = query.filter(AIChatMessages.id < last_record_id)
        records = query.filter_by(**kwargs).order_by(desc(AIChatMessages.create_time)).limit(count).all()
        return records


def query_AIChatMessages_All(label: bool = False, limit: int = None, **kwargs):
    with _session_scope() as session:

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
        return records


def query_AIChatMessages(**kwargs):
    with _session_scope() as session:
        record = session.query(AIChatMessages).filter_by(**kwargs).first()
        return record


def query_AIChatMessages_ById(id):
    with _session_scope() as session:
        res = session.query(AIChatMessages).filter(AIChatMessages.is_first == True, AIChatMessages.id == id).one_or_none()

        return res


def query_AIChatMessages_ByLabel(is_first, owner_account, friend_account):
    with _session_scope() as session:

        res = session.query(AIChatMessages.label).filter(AIChatMessages.is_first == True,
                                                         AIChatMessages.owner_account == owner_account,
                                                         AIChatMessages.friend_account == friend_account, ).distinct().all()
        if res is None:
            labels = []
        else:
            labels = [i.label for i in res if i.label is not None]
        return labels


def query_AIChatMessages_Search_Content(label: bool = False, **kwargs):
    with _session_scope() as session:

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
    with _session_scope() as session:
        res = session.query(AIChatMessages).filter(AIChatMessages.is_first == True, AIChatMessages.id == id).one_or_none()
        if res:
            conversation_id = res.conversation_id
        tasks = session.query(AIChatMessages).filter(AIChatMessages.conversation_id == conversation_id).order_by(
            asc(AIChatMessages.create_time)).all()


        return tasks




def add_AIFriend(account, nick_name, groups, owner_sns_account, memo, sign, subscription, name, borndate, gender, area, city, address, mail, phone, organization, title, position):
    def _do(session):
        ai_friend = AIFriend(account=account, nick_name=nick_name, groups=groups, owner_sns_account=owner_sns_account, memo=memo, sign=sign, subscription=subscription, name=name, borndate=borndate, gender=gender, area=area, city=city, address=address, mail=mail, phone=phone, organization=organization, title=title, position=position)
        session.add(ai_friend)
    db_write(_do, description="add_AIFriend")


def query_AIFriend_All(**kwargs):
    with _session_scope() as session:
        records = session.query(AIFriend).filter_by(**kwargs).all()
        return records


def query_AIFriend_All_Orderby_Updatetime(**kwargs):
    with _session_scope() as session:
        records = session.query(AIFriend).filter_by(**kwargs).order_by(desc(AIFriend.last_message_time)).all()
        return records


def query_AIFriend(**kwargs):
    with _session_scope() as session:
        record = session.query(AIFriend).filter_by(**kwargs).first()
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




def add_AgentCfg(user_id, name, memo, borndate, borncontry, language, gender, joinfederation, syncfederation, federationid, defaultmodel, defaultrole, lastmodel, lastrole, specialization, plugins, kms, last_plugins, last_kms, prompt, snsaccount, snsnickname, islimittotalmessage, islimitmessagepp, totalmessages, ppmessages, readfile, writefile, deletefile, execfile, uselastmodel, uselastrole, uselastplugins, uselastkms, callpluginbyinstruct, modelfrequent, rolefrequent, multimodelfrequent, autorunrounds):
    def _do(session):
        agentcfg = AgentCfg(user_id=user_id, name=name, memo=memo, borndate=borndate, borncontry=borncontry, language=language, gender=gender, joinfederation=joinfederation, syncfederation=syncfederation, federationid=federationid, defaultmodel=defaultmodel, defaultrole=defaultrole, lastmodel=lastmodel, lastrole=lastrole, specialization=specialization, plugins=plugins, kms=kms, last_plugins=last_plugins, last_kms=last_kms, prompt=prompt, snsaccount=snsaccount, snsnickname=snsnickname, islimittotalmessage=islimittotalmessage, islimitmessagepp=islimitmessagepp, totalmessages=totalmessages, ppmessages=ppmessages, readfile=readfile, writefile=writefile, deletefile=deletefile, execfile=execfile, uselastmodel=uselastmodel, uselastrole=uselastrole, uselastplugins=uselastplugins, uselastkms=uselastkms, callpluginbyinstruct=callpluginbyinstruct, modelfrequent=modelfrequent,
                            rolefrequent=rolefrequent, multimodelfrequent=multimodelfrequent, autorunrounds=autorunrounds)
        session.add(agentcfg)
    db_write(_do, description="add_AgentCfg")


def query_AgentCfg_All(**kwargs):
    with _session_scope() as session:
        # Exclude soft-deleted agents by default
        if 'is_delete' not in kwargs:
            kwargs['is_delete'] = False
        agents = session.query(AgentCfg).filter_by(**kwargs).order_by(asc(AgentCfg.position)).all()
        for agent in agents:
            print(f"ID: {agent.id}, Name: {agent.name}, Memo: {agent.memo}")
        return agents


def query_AgentCfg(**kwargs):
    with _session_scope() as session:
        agent = session.query(AgentCfg).filter_by(**kwargs).first()
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
    with _session_scope() as session:
        agentcfg = session.query(AgentCfg).filter_by(name=name).first()

        return agentcfg.prompt if agentcfg else None


def get_agent_specialization_description(name):
    with _session_scope() as session:
        agentcfg = session.query(AgentCfg).filter_by(name=name).first()

        return agentcfg.specialization if agentcfg else None




def add_AISnsCfg(user_id, account, password, nickname, sign, status, humantakeover, name, borndate, gender, area, state, city, community, street_block, address, mail, imaccount, phone, organization, title, orgposition, memo, islimittotalmessage, islimitmessagepp, totalmessages, ppmessages, serveraddress, port, ssl, resource, proxyused, proxyaddress, proxyport, proxyssl, savepasswordlocal, autoconnect, sendreceipt, sendreadflag, sendchatstatus, sendgroupchatstatus, agreeallfriendrequest, nationid, nationpassword, sns_url, avatar, avatar3d, house3d, map_type, map_api_key, map_id, current_position, home_position, positionx, positiony, positionz, route_start, route_end, route_status, route_current_position, route_points, route, level=1, credit=100, money=100, token_unit="k", life_point=4, energy_point=3, move_point=3, exp_point=4, iq_point=5):
    def _do(session):
        aisnsCfg = AISnsCfg(
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
        session.add(aisnsCfg)
        session.flush()
        return aisnsCfg.id
    return db_write(_do, description="add_AISnsCfg")


def query_AISnsCfg_All(**kwargs):
    with _session_scope() as session:
        records = session.query(AISnsCfg).filter_by(**kwargs).order_by(asc(AISnsCfg.position)).all()

        return records


def query_AISnsCfg_Search_Content(**kwargs):
    with _session_scope() as session:

        nickname_keyword = kwargs.get('nickname', None)
        account_keyword = kwargs.get('account', None)

        query = session.query(AISnsCfg)

        search_terms = []
        if nickname_keyword:
            search_terms.append(AISnsCfg.nickname.contains(nickname_keyword))
        if account_keyword:
            search_terms.append(AISnsCfg.account.contains(account_keyword))

        if search_terms:
            query = query.filter(or_(*search_terms))

        tasks = query.order_by(desc(AISnsCfg.create_time)).limit(50000).all()

        return tasks


def query_AISnsCfg(**kwargs):
    with _session_scope() as session:
        record = session.query(AISnsCfg).filter_by(**kwargs).first()
        return record


def query_AISnsCfg_map():
    with _session_scope() as session:
        record = session.query(AISnsCfg).first()
        return record


def query_AISnsCfg_common():
    with _session_scope() as session:
        record = session.query(AISnsCfg).offset(1).limit(1).first()
        return record


def query_AISnsCfg_map_setting(**kwargs):
    with _session_scope() as session:

        record = session.query(AISnsCfg).filter_by(**kwargs).first()

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


def update_AISnsCfg_map(**kwargs):
    def _do(session):
        record = session.query(AISnsCfg).first()
        if record:
            for key, value in kwargs.items():
                setattr(record, key, value)
    db_write(_do, description="update_AISnsCfg_map")


def update_AISnsCfg(id, **kwargs):
    def _do(session):
        record = session.query(AISnsCfg).filter_by(id=id).first()
        if record:
            for key, value in kwargs.items():
                setattr(record, key, value)
    db_write(_do, description="update_AISnsCfg")


def update_AISnsCfg_by_user_id(user_id, **kwargs):
    def _do(session):
        record = session.query(AISnsCfg).filter_by(user_id=user_id).first()
        if record:
            for key, value in kwargs.items():
                setattr(record, key, value)
    db_write(_do, description="update_AISnsCfg_by_user_id")


def delete_AISnsCfg(user_id):
    def _do(session):
        record = session.query(AISnsCfg).filter_by(user_id=user_id).first()
        if record:
            session.delete(record)
    db_write(_do, description="delete_AISnsCfg")




def add_KMCfg(km_id, name, memo, label, kmpath, vectorization, stopvectorization, kmtype, vectortype, embeddingmodel, textblocklength, overlaplength, titleaugment, config_param):
    def _do(session):
        kmCfg = KMCfg(km_id=km_id, name=name, memo=memo, label=label, kmpath=kmpath, kmtype=kmtype, vectorization=vectorization, stopvectorization=stopvectorization, vectortype=vectortype, embeddingmodel=embeddingmodel, textblocklength=textblocklength, overlaplength=overlaplength, titleaugment=titleaugment, config_param=config_param)
        session.add(kmCfg)
    db_write(_do, description="add_KMCfg")


def query_KMCfg_All(**kwargs):
    with _session_scope() as session:
        records = session.query(KMCfg).filter_by(**kwargs).order_by(asc(KMCfg.position)).all()

        return records


def query_KMCfg(**kwargs):
    with _session_scope() as session:
        record = session.query(KMCfg).filter_by(**kwargs).first()
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


def delete_KMCfg(id):
    def _do(session):
        record = session.query(KMCfg).filter_by(id=id).first()
        if record:
            session.delete(record)
    db_write(_do, description="delete_KMCfg")




def add_KMData(km_id, filename, filenum, textblocklength, overlaplength, waitvectorization):
    def _do(session):
        kmData = KMData(km_id=km_id, filename=filename, filenum=filenum, textblocklength=textblocklength, overlaplength=overlaplength, waitvectorization=waitvectorization)
        session.add(kmData)
        session.flush()
        return kmData.id
    return db_write(_do, description="add_KMData")


def query_KMData_All(**kwargs):
    with _session_scope() as session:
        records = session.query(KMData).filter_by(**kwargs).all()

        return records


def query_KMData(**kwargs):
    with _session_scope() as session:
        record = session.query(KMData).filter_by(**kwargs).first()
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
    with _session_scope() as session:
        records = session.query(PluginMng).filter_by(**kwargs).all()

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
    with _session_scope() as session:
        record = session.query(PluginMng).filter_by(**kwargs).first()
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
    with _session_scope() as session:
        records = session.query(FunctionMng).filter_by(**kwargs).all()
        return records


def query_function_mng(**kwargs):
    with _session_scope() as session:
        record = session.query(FunctionMng).filter_by(**kwargs).first()
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
    with _session_scope() as session:
        records = session.query(McpMng).filter_by(**kwargs).all()
        return records


def query_mcp_mng(**kwargs):
    with _session_scope() as session:
        record = session.query(McpMng).filter_by(**kwargs).first()
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
    with _session_scope() as session:
        records = session.query(SkillMng).filter_by(**kwargs).all()
        return records


def query_skill_mng(**kwargs):
    with _session_scope() as session:
        record = session.query(SkillMng).filter_by(**kwargs).first()
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
    with _session_scope() as session:
        records = session.query(WebMng).filter_by(**kwargs).order_by(asc(WebMng.position)).all()
        return records


def query_web_mng(**kwargs):
    with _session_scope() as session:
        record = session.query(WebMng).filter_by(**kwargs).first()
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
    with _session_scope() as session:
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
        return records


def query_note_mng(**kwargs):
    with _session_scope() as session:
        record = session.query(NoteMng).filter_by(**kwargs).first()
        return record


def query_note_mng_ById(id):
    with _session_scope() as session:
        res = session.query(NoteMng).filter(NoteMng.id == id).one_or_none()

        return res


def query_note_mng_ByLabel(km_id):
    with _session_scope() as session:

        res = session.query(NoteMng.label).filter(NoteMng.km_id == km_id).distinct().all()
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
    with _session_scope() as session:

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

        return records




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
        if 'language' not in columns:
            cursor.execute("ALTER TABLE system_cfg ADD COLUMN language TEXT DEFAULT 'en'")
        if 'a2a_server_enabled' not in columns:
            cursor.execute("ALTER TABLE system_cfg ADD COLUMN a2a_server_enabled INTEGER DEFAULT 0")
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
    with _session_scope() as session:
        records = session.query(SystemCfg).filter_by(**kwargs).all()

        return records


def query_SystemCfg(**kwargs):
    with _session_scope() as session:
        record = session.query(SystemCfg).filter_by(**kwargs).first()
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




def get_prompt_by_title(title):
    with _session_scope() as session:
        prompt = session.query(Prompt).filter_by(title=title).first()

        return prompt.content if prompt else ""


def get_prompt_by_id(id):
    with _session_scope() as session:
        prompt = session.query(Prompt).filter_by(id=id).first()

        return prompt.content if prompt else ""


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




def add_key_value(key: str, value: str):
    def _do(session):
        new_entry = KeyValue(key=key, value=value)
        session.add(new_entry)
    db_write(_do, description="add_key_value")


def get_key_value(key: str):
    with _session_scope() as session:
        result = session.query(KeyValue).filter_by(key=key).first()
        return result.value if result else None


def get_all_key_values() -> list:
    with _session_scope() as session:
        records = session.query(KeyValue).all()
        return records


def search_key_values(search_text: str) -> list:
    with _session_scope() as session:
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
    with _session_scope() as session:
        records = session.query(SystemInit).filter_by(**kwargs).all()
        return records


def query_SystemInit(**kwargs):
    with _session_scope() as session:
        record = session.query(SystemInit).filter_by(**kwargs).first()
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
            session.delete(record)
    db_write(_do, description="delete_SystemInit")




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
    with _session_scope() as session:
        records = session.query(MapActivity).filter_by(**kwargs).all()
        return records


def query_map_activity_previous(last_record_id=None, count=20, type_str=None):
    with _session_scope() as session:

        query = session.query(MapActivity)

        if last_record_id is not None:
            query = query.filter(MapActivity.id < last_record_id)

        if type_str:
            query = query.filter(MapActivity.type == type_str)

        records = query.order_by(MapActivity.id.desc()).limit(count).all()

        return records


def query_map_activity(**kwargs):
    with _session_scope() as session:
        record = session.query(MapActivity).filter_by(**kwargs).first()
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
    with _session_scope() as session:
        query = session.query(MapPresetMsg)

        if last_record_id is not None:
            query = query.filter(MapPresetMsg.id < last_record_id)

        records = query.order_by(MapPresetMsg.id.desc()).limit(count).all()
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



