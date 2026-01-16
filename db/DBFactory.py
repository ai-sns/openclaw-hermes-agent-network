import os

from sqlalchemy import create_engine, Column, Integer, String
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
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
engine = create_engine(SQL_DATABASE_URL)

Session = sessionmaker(bind=engine)


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


# aichat_messages
class AIChatMessages(Base):
    __tablename__ = 'ai_chat_messages'
    id = Column(Integer, primary_key=True, autoincrement=True)
    conversation_id = Column(String(50), doc="对话id")
    agent_id = Column(Integer, default=None, doc="Agent ID (多Agent支持)")
    flag = Column(Integer, doc="0为发送，1为接收")
    title = Column(Text, default=None, doc="标题，缺省使用第一条信息字段")
    content = Column(Text, doc="消息内容")
    attachment_list = Column(Text, doc="附件列表，是一个元组")
    document_content = Column(Text, doc="所有的文档类型的附件内容")
    image_json = Column(Text, doc="所有图片base64的内容json列表")
    km_list = Column(Text, doc="召回的知识库内容列表")
    km_content = Column(Text, doc="召回的知识库的全部内容")
    owner_name = Column(String(100), doc="")
    owner_account = Column(String(100), doc="")
    friend_name = Column(String(100), doc="")
    friend_account = Column(String(100), doc="")
    create_time = Column(DateTime, default=datetime.now, doc="创建时间")
    is_delete = Column(Boolean, default=False, doc="软删除")
    is_first = Column(Boolean, default=False, doc="是否第一句对话")
    stick_time = Column(DateTime, nullable=True, doc="置顶操作时间")  # --> 置顶字段
    label = Column(String(50), doc="分类标签")  # --> 标签字段


def add_AIChatMessages(conversation_id, flag, title, content, owner_name, owner_account, friend_name, friend_account,
                       is_first=False, attachment_list="", document_content="", image_json="", km_list="",
                       km_content=""):
    session = Session()
    ai_friend = AIChatMessages(conversation_id=conversation_id, flag=flag, title=title, content=content,
                               owner_name=owner_name, owner_account=owner_account, friend_name=friend_name,
                               friend_account=friend_account, is_first=is_first, attachment_list=attachment_list,
                               document_content=document_content, image_json=image_json, km_list=km_list,
                               km_content=km_content)
    session.add(ai_friend)
    session.commit()
    session.close()


def query_map_activity_previous(last_record_id=None, count=20, type_str=None):
    """查询小于 last_record_id 的活动记录，返回 count 个记录，
    记录按降序排列。如果 type_str 不为空，则返回 type 等于 type_str 的记录。
    如果 last_record_id 为 None，则不应用此筛选条件。"""

    session = Session()

    # 基础查询：创建查询对象
    query = session.query(MapActivity)

    # 如果 last_record_id 不是 None，添加 id < last_record_id 的筛选条件
    if last_record_id is not None:
        query = query.filter(MapActivity.id < last_record_id)

    # 如果 type_str 不为空，添加 type 的筛选条件
    if type_str:
        query = query.filter(MapActivity.type == type_str)

    # 执行查询，按 id 降序排列，并限制返回的记录数量
    records = query.order_by(MapActivity.id.desc()).limit(count).all()

    session.close()
    return records


def query_AIChatMessages_All_previous(last_record_id=None, count=20,**kwargs):
    session = Session()
    query = session.query(AIChatMessages)
    if last_record_id is not None:
        query = query.filter(AIChatMessages.id < last_record_id)
    records = query.filter_by(**kwargs).order_by(desc(AIChatMessages.create_time)).limit(count).all()
    session.close()
    return records

def query_AIChatMessages_All(label: bool = False, limit: int = None, **kwargs):
    session = Session()
    # 添加label不为None的条件
    if label:
        query = session.query(AIChatMessages).filter(AIChatMessages.label.isnot(None)).filter_by(
            **kwargs).order_by(desc(AIChatMessages.stick_time),
                               desc(AIChatMessages.create_time))
    else:
        query = session.query(AIChatMessages).filter_by(**kwargs).order_by(desc(AIChatMessages.stick_time),
                                                                             desc(AIChatMessages.create_time))

    # 应用limit（如果提供）
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
    # 首先获取所有不同的 label
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

    # 提取常规过滤条件
    is_first = kwargs.get('is_first', None)
    owner_account = kwargs.get('owner_account', None)
    friend_account = kwargs.get('friend_account', None)

    # 搜索关键词
    title_keyword = kwargs.get('title', None)
    content_keyword = kwargs.get('content', None)

    # 构建初始查询
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

    # 添加搜索条件
    search_terms = []
    if title_keyword:
        search_terms.append(AIChatMessages.title.contains(title_keyword))
    if content_keyword:
        search_terms.append(AIChatMessages.content.contains(content_keyword))

    if search_terms:
        query = query.filter(or_(*search_terms))

    # 获取结果
    tasks = query.order_by(desc(AIChatMessages.stick_time), desc(AIChatMessages.create_time)).limit(50000).all()

    session.close()
    return tasks


def query_AIChatMessages_Search_First(agent_id, task_id, label: bool = False):
    session = Session()

    # 查找特定 agent_id 和 task_id 且 is_first 为 True 的记录
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

    # for task in tasks:
    #     print(f"ID: {task.id}, qes: {task.problem},ans:{task.answer}")
    session.close()

    return tasks


def query_AIChat_Search_Content(**kwargs):
    session = Session()

    # 提取常规过滤条件
    is_first = kwargs.get('is_first', None)
    agent_id = kwargs.get('agent_id', None)

    # 搜索关键词
    title_keyword = kwargs.get('title', None)
    problem_keyword = kwargs.get('problem', None)
    answer_keyword = kwargs.get('answer', None)

    # 构建初始查询
    query = session.query(AgentTask)

    if is_first is not None:
        query = query.filter(AgentTask.is_first == is_first)
    if agent_id is not None:
        query = query.filter(AgentTask.agent_id == agent_id)

    if title_keyword == "":
        query = query.filter(AgentTask.is_first == True)

    # 添加搜索条件
    search_terms = []
    if title_keyword:
        search_terms.append(AgentTask.title.contains(title_keyword))
    if problem_keyword:
        search_terms.append(AgentTask.problem.contains(problem_keyword))
    if answer_keyword:
        search_terms.append(AgentTask.answer.contains(answer_keyword))

    if search_terms:
        query = query.filter(or_(*search_terms))

    # 获取结果
    tasks = query.order_by(desc(AgentTask.create_time)).limit(50000).all()

    session.close()
    return tasks


def query_AIChat_Search_First(agent_id, task_id):
    session = Session()

    # 查找特定 agent_id 和 task_id 且 is_first 为 True 的记录
    first_task = session.query(AgentTask) \
        .filter(AgentTask.agent_id == agent_id, AgentTask.task_id == task_id, AgentTask.is_first == True) \
        .first()

    session.close()
    return first_task


# ai_friend
class AIFriend(Base):
    __tablename__ = 'ai_friend'
    id = Column(Integer, primary_key=True, autoincrement=True)
    account = Column(String(100), doc="帐号")
    nick_name = Column(String(200), doc="")
    groups = Column(Text, doc="")
    owner_sns_account = Column(String(100), doc="所有人帐号")
    memo = Column(Text, doc="")
    sign = Column(String(200), doc="状态信息(个人签名)")
    subscription = Column(String(100), doc="加好友状态")
    name = Column(String(200), doc="Real Name")
    borndate = Column(String(100), doc="生日")
    gender = Column(Integer, doc="")
    area = Column(String(100), doc="国家及地区")
    city = Column(String(100), doc="城市")
    address = Column(String(200), doc="地址")
    mail = Column(String(100), doc="")
    phone = Column(String(100), doc="")
    organization = Column(String(200), doc="组织")
    title = Column(String(100), doc="头衔")
    position = Column(String(100), doc="角色")
    new_message_flag = Column(Boolean, default=False, doc="是否有新消息")
    last_message_time = Column(DateTime, doc="创建时间")
    is_delete = Column(Boolean, default=False, doc="软删除")
    create_time = Column(DateTime, default=datetime.now, doc="创建时间")


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


# ai_chat_inform
class AIChatInform(Base):
    __tablename__ = 'ai_chat_inform'
    id = Column(Integer, primary_key=True, autoincrement=True)
    inform_id = Column(String(50), doc="通知id")
    title = Column(Text, default=None, doc="标题，缺省使用第一条信息字段")
    content = Column(Text, doc="消息内容")
    type = Column(String(100), doc="消息类型")
    status = Column(String(100), doc="消息状态")
    owner_name = Column(String(100), doc="")
    owner_account = Column(String(100), doc="")
    friend_name = Column(String(100), doc="")
    friend_account = Column(String(100), doc="")
    create_time = Column(DateTime, default=datetime.now, doc="创建时间")
    is_delete = Column(Boolean, default=False, doc="软删除")


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


# Agent Task
class AgentTask(Base):
    __tablename__ = 'agent_task'
    id = Column(Integer, primary_key=True, autoincrement=True)
    task_id = Column(String(50), doc="任务id")
    title = Column(String(500), default=None, doc="标题，缺省使用第一个问题的problem字段")
    problem = Column(Text, doc="问题")
    answer = Column(Text, doc="回答")
    attachment_list = Column(Text, doc="附件列表，是一个元组")
    document_content = Column(Text, doc="所有的文档类型的附件内容")
    image_json = Column(Text, doc="所有图片base64的内容json列表")
    km_list = Column(Text, doc="召回的知识库内容列表")
    km_content = Column(Text, doc="召回的知识库的全部内容")
    model_name = Column(String(100), doc="回答问题的模型的名称")
    agent_id = Column(String(200), doc="agent id")
    create_time = Column(DateTime, default=datetime.now, doc="创建时间")
    is_delete = Column(Boolean, default=False, doc="软删除")
    is_first = Column(Boolean, default=False, doc="是否第一句对话")
    stick_time = Column(DateTime, nullable=True, doc="置顶操作时间")  # --> 置顶字段
    label = Column(String(50), doc="分类标签")  # --> 标签字段


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
        # 构建过滤条件
        filter_expr = []
        for key, value in kwargs.items():
            filter_expr.append(getattr(AgentTask, key) == value)

        # 添加label不为None的条件
        if label:
            filter_expr.append(AgentTask.label.isnot(None))
        # 查询并过滤记录
        tasks = session.query(AgentTask).filter(*filter_expr).order_by(desc(AgentTask.stick_time),
                                                                       desc(AgentTask.create_time)).limit(500).all()
        # for task in tasks:
        #     print(f"ID: {task.id}, Name: {task.problem}")
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
    # 首先获取所有不同的 label
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

    # 提取常规过滤条件
    is_first = kwargs.get('is_first', None)
    agent_id = kwargs.get('agent_id', None)

    # 搜索关键词
    title_keyword = kwargs.get('title', None)
    problem_keyword = kwargs.get('problem', None)
    answer_keyword = kwargs.get('answer', None)

    # 构建初始查询
    query = session.query(AgentTask)

    if is_first is not None:
        query = query.filter(AgentTask.is_first == is_first)
    if agent_id is not None:
        query = query.filter(AgentTask.agent_id == agent_id)

    if title_keyword == "":
        query = query.filter(AgentTask.is_first == True)

    if label:
        query = query.filter(AgentTask.label.isnot(None))

    # 添加搜索条件
    search_terms = []
    if title_keyword:
        search_terms.append(AgentTask.title.contains(title_keyword))
    if problem_keyword:
        search_terms.append(AgentTask.problem.contains(problem_keyword))
    if answer_keyword:
        search_terms.append(AgentTask.answer.contains(answer_keyword))

    if search_terms:
        query = query.filter(or_(*search_terms))

    # 获取结果
    tasks = query.order_by(desc(AgentTask.stick_time), desc(AgentTask.create_time)).limit(50000).all()

    session.close()
    return tasks


def query_AgentTask_Search_First(agent_id, task_id, label: bool = False):
    session = Session()

    # 查找特定 agent_id 和 task_id 且 is_first 为 True 的记录
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
        # 获取task_id
        task = session.query(AgentTask).filter_by(id=id_value).first()
        if task:
            task_id = task.task_id

            # 删除所有task_id相同的记录
            session.query(AgentTask).filter_by(task_id=task_id).delete()
            session.commit()
    except Exception as e:
        print(e)
        session.rollback()
    finally:
        session.close()


# Agent Cfg
class AgentCfg(Base):
    __tablename__ = 'agent_cfg'
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(String(100), doc="")
    name = Column(String(200), doc="")
    memo = Column(String(200), doc="")
    borndate = Column(DateTime, nullable=True, default=None, doc="")
    borncontry = Column(String(100), doc="")
    language = Column(String(100), doc="")
    gender = Column(Integer, doc="")
    joinfederation = Column(Boolean, default=False, doc="")
    syncfederation = Column(Boolean, default=False, doc="")
    federationid = Column(String(150), doc="")
    defaultmodel = Column(String(200), doc="")
    defaultrole = Column(String(200), doc="")
    lastmodel = Column(String(200), doc="")
    lastrole = Column(String(200), doc="")
    specialization = Column(Text, doc="")
    plugins = Column(Text, doc="")
    kms = Column(Text, doc="")
    last_plugins = Column(Text, doc="")
    last_kms = Column(Text, doc="")
    prompt = Column(Text, doc="")
    snsaccount = Column(String(100), doc="")
    snsnickname = Column(String(100), doc="")
    islimittotalmessage = Column(Boolean, default=True, doc="")
    islimitmessagepp = Column(Boolean, default=True, doc="")
    totalmessages = Column(Integer, doc="")
    ppmessages = Column(Integer, doc="")
    readfile = Column(Boolean, default=True, doc="")
    writefile = Column(Boolean, default=True, doc="")
    deletefile = Column(Boolean, default=True, doc="")
    execfile = Column(Boolean, default=True, doc="")
    uselastmodel = Column(Boolean, default=False, doc="")
    uselastrole = Column(Boolean, default=False, doc="")
    uselastplugins = Column(Boolean, default=False, doc="")
    uselastkms = Column(Boolean, default=False, doc="")
    callpluginbyinstruct = Column(Boolean, default=True, doc="")
    modelfrequent = Column(Boolean, default=False, doc="")
    rolefrequent = Column(Boolean, default=False, doc="")
    multimodelfrequent = Column(Boolean, default=False, doc="")
    multimodellastmodel = Column(String(500), doc="")
    multimodellastrole = Column(String(100), doc="")
    autorunrounds = Column(Integer, doc="")
    position = Column(Integer, default=9999, doc="")
    is_show = Column(Boolean, default=True, doc="是否显示")
    is_delete = Column(Boolean, default=False, doc="软删除")
    create_time = Column(DateTime, default=datetime.now, doc="创建时间")


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
    # 使用 session.query() 方法查询，filter_by 对应 title 字段
    session = Session()
    agentcfg = session.query(AgentCfg).filter_by(name=name).first()
    # 如果查询到结果，返回 content，否则返回 None
    return agentcfg.prompt if agentcfg else None


def get_agent_specialization_description(name):
    # 使用 session.query() 方法查询，filter_by 对应 title 字段
    session = Session()
    agentcfg = session.query(AgentCfg).filter_by(name=name).first()
    # 如果查询到结果，返回 content，否则返回 None
    return agentcfg.specialization if agentcfg else None


# MutiAgent Task
class AgentTaskMulti(Base):
    __tablename__ = 'agent_task_multi'
    id = Column(Integer, primary_key=True, autoincrement=True)
    task_id = Column(String(50), doc="内容id")
    topic = Column(String(500), default=None, doc="标题群交流的主体")
    content = Column(Text, doc="内容")
    owner = Column(String(100), doc="该内容的发送者")
    group_id = Column(String(200), doc="群id")
    attachment_list = Column(Text, doc="附件列表，是一个元组")
    document_content = Column(Text, doc="所有的文档类型的附件内容")
    image_json = Column(Text, doc="所有图片base64的内容json列表")
    km_list = Column(Text, doc="召回的知识库内容列表")
    km_content = Column(Text, doc="召回的知识库的全部内容")
    model_name = Column(String(100), doc="回答问题的模型的名称")
    agent_id = Column(String(200), doc="agent id")
    create_time = Column(DateTime, default=datetime.now, doc="创建时间")
    is_delete = Column(Boolean, default=False, doc="软删除")
    is_first = Column(Boolean, default=False, doc="是否第一句对话")
    stick_time = Column(DateTime, nullable=True, doc="置顶操作时间")  # --> 置顶字段
    label = Column(String(50), doc="分类标签")  # --> 标签字段


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
        # 构建过滤条件
        filter_expr = []
        for key, value in kwargs.items():
            filter_expr.append(getattr(AgentTaskMulti, key) == value)

        # 添加label不为None的条件
        if label:
            filter_expr.append(AgentTaskMulti.label.isnot(None))
        # 查询并过滤记录
        tasks = session.query(AgentTaskMulti).filter(*filter_expr).order_by(desc(AgentTaskMulti.stick_time),
                                                                            desc(AgentTaskMulti.create_time)).limit(
            500).all()

        # for task in tasks:
        #     print(f"ID: {task.id}, Name: {task.content}")
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
    # 首先获取所有不同的 label
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

    # 提取常规过滤条件
    is_first = kwargs.get('is_first', None)
    # agent_id = kwargs.get('agent_id', None)
    group_id = kwargs.get('group_id', None)
    # 搜索关键词
    title_keyword = kwargs.get('title', None)
    topic_keyword = kwargs.get('topic', None)
    answer_keyword = kwargs.get('answer', None)

    # 构建初始查询
    query = session.query(AgentTaskMulti)

    if is_first is not None:
        query = query.filter(AgentTaskMulti.is_first == is_first)
    if group_id is not None:
        query = query.filter(AgentTaskMulti.group_id == group_id)

    if title_keyword == "":
        query = query.filter(AgentTaskMulti.is_first == True)

    if label:
        query = query.filter(AgentTaskMulti.label.isnot(None))
    # 添加搜索条件
    search_terms = []
    if title_keyword:
        search_terms.append(AgentTaskMulti.title.contains(title_keyword))
    if topic_keyword:
        search_terms.append(AgentTaskMulti.topic.contains(topic_keyword))
    if answer_keyword:
        search_terms.append(AgentTaskMulti.answer.contains(answer_keyword))

    if search_terms:
        query = query.filter(or_(*search_terms))

    # 获取结果
    tasks = query.order_by(
        desc(AgentTaskMulti.stick_time),
        desc(AgentTaskMulti.create_time)).limit(50000).all()

    session.close()
    return tasks


def query_AgentTaskMulti_Search_First(agent_id, task_id, label: bool = False):
    session = Session()

    # 查找特定 agent_id 和 task_id 且 is_first 为 True 的记录
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
    #
    # for task in tasks:
    #     print(f"ID: {task.id}, content: {task.content}")
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
        # 获取task_id
        task = session.query(AgentTaskMulti).filter_by(id=id_value).first()
        if task:
            task_id = task.task_id
            # 删除所有task_id相同的记录
            session.query(AgentTaskMulti).filter_by(task_id=task_id).delete()
            session.commit()
    except Exception as e:
        print(e)
        session.rollback()
    finally:
        session.close()


# MutiAgent Cfg
class MutiAgentCfg(Base):
    __tablename__ = 'mutiagent_cfg'
    id = Column(Integer, primary_key=True, autoincrement=True)
    group_id = Column(String(100), doc="")
    name = Column(String(200), doc="")
    memo = Column(String(200), doc="")
    agents = Column(Text, doc="参与的智能体")
    agentcommander = Column(String(500), doc="智能体指挥官，群主")

    specialization = Column(String(100), doc="专长领域")
    plugins = Column(String(500), doc="")
    kms = Column(String(500), doc="")
    prompt = Column(Text, doc="")

    islimittotalmessage = Column(Boolean, default=True, doc="")
    islimitmessagepp = Column(Boolean, default=True, doc="")
    totalmessages = Column(Integer, doc="")
    ppmessages = Column(Integer, doc="")

    readfile = Column(Boolean, default=True, doc="")
    writefile = Column(Boolean, default=True, doc="")
    deletefile = Column(Boolean, default=True, doc="")
    execfile = Column(Boolean, default=True, doc="")
    autorunrounds = Column(Integer, doc="")
    position = Column(Integer, default=9999, doc="")
    is_show = Column(Boolean, default=True, doc="是否显示")
    is_delete = Column(Boolean, default=False, doc="软删除")
    create_time = Column(DateTime, default=datetime.now, doc="创建时间")


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
    # for record in records:
    #     print(f"ID: {record.id}, Name: {record.name}, Memo: {record.memo}")
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


# AiChat Cfg
class AiChatCfg(Base):
    __tablename__ = 'aichat_cfg'
    id = Column(Integer, primary_key=True, autoincrement=True)

    # Original fields
    user_id = Column(String(100), doc="")
    account = Column(String(100), doc="帐号")
    password = Column(String(256), doc="密码哈希值")
    nickname = Column(String(100), doc="昵称")
    sign = Column(String(200), doc="状态信息(个人签名)")
    status = Column(String(100), doc="在线状态")
    humantakeover = Column(Integer, default=0, doc="是否人类接管")
    name = Column(String(200), doc="")
    borndate = Column(DateTime, default=datetime.now, doc="生日")
    gender = Column(Integer, doc="")
    area = Column(String(100), doc="国家及地区")
    state = Column(String(100), doc="联邦")
    city = Column(String(100), doc="城市")
    community = Column(String(100), doc="社区")
    street_block = Column(String(100), doc="街区")
    address = Column(String(200), doc="地址")
    mail = Column(String(100), doc="")
    imaccount = Column(String(100), doc="其他im帐号")
    phone = Column(String(100), doc="")
    organization = Column(String(200), doc="组织")
    title = Column(String(100), doc="头衔")
    orgposition = Column(String(100), doc="角色")
    memo = Column(String(200), doc="")
    islimittotalmessage = Column(Boolean, default=True, doc="")
    islimitmessagepp = Column(Boolean, default=True, doc="")
    totalmessages = Column(Integer, doc="")
    ppmessages = Column(Integer, doc="")
    serveraddress = Column(String(100), doc="")
    port = Column(Integer, doc="")
    ssl = Column(Boolean, doc="")
    resource = Column(String(100), doc="资源")
    proxyused = Column(Boolean, doc="是否使用代理")
    proxyaddress = Column(String(100), doc="")
    proxyport = Column(Integer, doc="")
    proxyssl = Column(Boolean, doc="")
    savepasswordlocal = Column(Boolean, default=True, doc="本地保存密码")
    autoconnect = Column(Boolean, default=True, doc="启动时自动连接")
    sendreceipt = Column(Boolean, default=True, doc="发送消息回执")
    sendreadflag = Column(Boolean, default=True, doc="发送已读标志")
    sendchatstatus = Column(Boolean, default=True, doc="发送聊天状态")
    sendgroupchatstatus = Column(Boolean, default=True, doc="群聊中发送聊天状态")
    agreeallfriendrequest = Column(Boolean, default=True, doc="同意所有联系人请求")
    position = Column(Integer, default=9999, doc="")
    is_show = Column(Boolean, default=True, doc="是否显示")
    is_delete = Column(Boolean, default=False, doc="软删除")
    create_time = Column(DateTime, default=datetime.now, doc="创建时间")

    # New fields
    nationid = Column(String(100), doc="国家ID")
    nationpassword = Column(String(100), doc="国家密码")
    sns_url = Column(Text, doc="社交网络链接")
    avatar = Column(Text, doc="头像")
    avatar3d = Column(Text, doc="3D头像")
    house3d = Column(Text, doc="3D房子")
    map_type = Column(String(100), doc="地图类型")
    map_api_key = Column(Text, doc="地图API钥匙")
    map_id = Column(Text, doc="地图ID")
    current_position = Column(String(100), doc="当前位置")
    current_place = Column(String(500))
    last_position = Column(String(100))
    home_position = Column(String(100), doc="家庭位置")
    positionx = Column(Float, doc="X坐标")
    positiony = Column(Float, doc="Y坐标")
    positionz = Column(Float, doc="Z坐标")
    route_start = Column(String(500), doc="路线开始")
    route_end = Column(String(500), doc="路线结束")
    route_status = Column(String(100), doc="路线状态")
    route_current_position = Column(String(100), doc="当前路线位置")
    route = Column(Text, doc="路线")
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
    event_before_decistion = Column(String(200))
    event_after_decistion = Column(String(200))
    event_receive_msg = Column(String(200))
    event_before_send_msg = Column(String(200))
    event_before_move = Column(String(200))
    event_after_move = Column(String(200))
    event_before_use_tool = Column(String(200))
    event_after_use_tool = Column(String(200))



def add_AiChatCfg(user_id, account, password, nickname, sign, status, humantakeover, name, borndate, gender, area, state, city, community, street_block, address, mail, imaccount, phone, organization, title, orgposition, memo, islimittotalmessage, islimitmessagepp, totalmessages, ppmessages, serveraddress, port, ssl, resource, proxyused, proxyaddress, proxyport, proxyssl, savepasswordlocal, autoconnect, sendreceipt, sendreadflag, sendchatstatus, sendgroupchatstatus, agreeallfriendrequest, nationid, nationpassword, sns_url, avatar, avatar3d, house3d, map_type, map_api_key, map_id, current_position, home_position, positionx, positiony, positionz, route_start, route_end, route_status, route_current_position, route, level=1, credit=100, money=100, token_unit="k", life_point=4, energy_point=3, move_point=3, exp_point=4, iq_point=5):
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
        route_current_position=route_current_position, route=route,
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
    # for record in records:
    #     print(f"ID: {record.id}, Name: {record.nickname}, Memo: {record.memo}")
    session.close()
    return records


def query_AiChatCfg_Search_Content(**kwargs):
    session = Session()

    # 提取常规过滤条件
    # 搜索关键词
    nickname_keyword = kwargs.get('nickname', None)
    account_keyword = kwargs.get('account', None)

    # 构建初始查询
    query = session.query(AiChatCfg)

    # if is_first is not None:
    #     query = query.filter(AgentTaskMulti.is_first == is_first)

    # 添加搜索条件
    search_terms = []
    if nickname_keyword:
        search_terms.append(AiChatCfg.nickname.contains(nickname_keyword))
    if account_keyword:
        search_terms.append(AiChatCfg.account.contains(account_keyword))

    if search_terms:
        query = query.filter(or_(*search_terms))

    # 获取结果
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
    # 获取符合条件的首个记录
    record = session.query(AiChatCfg).filter_by(**kwargs).first()
    session.close()

    # 如果找到了记录，提取新字段的值
    if record:
        # 仅包含新添加的字段
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
            "route": record.route
        }
        return fields
    else:
        # 如果没有找到记录，返回None或空字典
        return None



def update_AiChatCfg_map(**kwargs):
    session = Session()
    record = session.query(AiChatCfg).first()
    if record:
        for key, value in kwargs.items():
            setattr(record, key, value)
        session.commit()
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


# HumanChat Cfg

class HumanChatCfg(Base):
    __tablename__ = 'humanchat_cfg'
    id = Column(Integer, primary_key=True, autoincrement=True)

    user_id = Column(String(100), doc="")

    account = Column(String(100), doc="帐号")
    password = Column(String(256), doc="密码哈希值")
    nickname = Column(String(100), doc="昵称")
    sign = Column(String(200), doc="状态信息(个人签名)")
    status = Column(String(100), doc="在线状态")

    name = Column(String(200), doc="")
    borndate = Column(DateTime, default=datetime.now, doc="生日")
    gender = Column(Integer, doc="")
    area = Column(String(100), doc="国家及地区")
    city = Column(String(100), doc="城市")
    address = Column(String(200), doc="")
    mail = Column(String(100), doc="")
    imaccount = Column(String(100), doc="其他im帐号")
    phone = Column(String(100), doc="")
    organization = Column(String(200), doc="组织")
    title = Column(String(100), doc="头衔")
    orgposition = Column(String(100), doc="角色")
    memo = Column(String(200), doc="")

    serveraddress = Column(String(100), doc="")
    port = Column(Integer, doc="")
    ssl = Column(Boolean, doc="")
    resource = Column(String(100), doc="资源")
    proxyused = Column(Boolean, doc="是否使用代理")
    proxyaddress = Column(String(100), doc="")
    proxyport = Column(Integer, doc="")
    proxyssl = Column(Boolean, doc="")

    savepasswordlocal = Column(Boolean, default=True, doc="本地保存密码")
    autoconnect = Column(Boolean, default=True, doc="启动时自动连接")
    sendreceipt = Column(Boolean, default=True, doc="发送消息回执")
    sendreadflag = Column(Boolean, default=True, doc="发送已读标志")
    sendchatstatus = Column(Boolean, default=True, doc="发送聊天状态")
    sendgroupchatstatus = Column(Boolean, default=True, doc="群聊中发送聊天状态")
    autoaway = Column(Boolean, default=True, doc="自动更新离开状态")
    autona = Column(Boolean, default=True, doc="自动更新不在状态")
    agreeallfriendrequest = Column(Boolean, default=True, doc="同意所有联系人请求")

    is_delete = Column(Boolean, default=False, doc="软删除")
    create_time = Column(DateTime, default=datetime.now, doc="创建时间")


def add_HumanChatCfg(user_id, account, password, nickname, sign, status, name, borndate, gender, area, city, address, mail, imaccount, phone, organization, title, orgposition, memo, serveraddress, port, ssl, resource, proxyused, proxyaddress, proxyport, proxyssl, savepasswordlocal, autoconnect, sendreceipt, sendreadflag, sendchatstatus, sendgroupchatstatus, autoaway, autona, agreeallfriendrequest):
    session = Session()
    humanChatCfg = HumanChatCfg(user_id=user_id, account=account, password=password, nickname=nickname, sign=sign, status=status, name=name, borndate=borndate, gender=gender, area=area, city=city, address=address, mail=mail, imaccount=imaccount, phone=phone, organization=organization, title=title, orgposition=orgposition, memo=memo, serveraddress=serveraddress, port=port, ssl=ssl, resource=resource, proxyused=proxyused, proxyaddress=proxyaddress, proxyport=proxyport, proxyssl=proxyssl, savepasswordlocal=savepasswordlocal, autoconnect=autoconnect, sendreceipt=sendreceipt, sendreadflag=sendreadflag, sendchatstatus=sendchatstatus, sendgroupchatstatus=sendgroupchatstatus, autoaway=autoaway, autona=autona, agreeallfriendrequest=agreeallfriendrequest)
    session.add(humanChatCfg)
    session.commit()
    session.close()


def query_HumanChatCfg_All(**kwargs):
    session = Session()
    records = session.query(HumanChatCfg).filter_by(**kwargs).all()
    # for record in records:
    #     print(f"ID: {record.id}, Name: {record.nickname}, Memo: {record.memo}")
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


# KM Cfg
class KMCfg(Base):
    __tablename__ = 'km_cfg'
    id = Column(Integer, primary_key=True, autoincrement=True)
    km_id = Column(String(100), doc="")
    name = Column(String(200), doc="")
    memo = Column(String(200), doc="")
    label = Column(String(100), doc="")

    kmpath = Column(String(250), doc="")
    vectorization = Column(Boolean, default=True, doc="是否向量化")
    stopvectorization = Column(Boolean, default=False, doc="是否暂停向量化")
    kmtype = Column(String(100), doc="")
    vectortype = Column(String(150), doc="")
    embeddingmodel = Column(String(150), doc="")

    textblocklength = Column(Integer, doc="单段文本最大长度")
    overlaplength = Column(Integer, doc="相邻文本重合长度")
    titleaugment = Column(Boolean, default=True, doc="是否开启中文标题加强")

    position = Column(Integer, default=9999, doc="")
    is_show = Column(Boolean, default=True, doc="是否显示")
    config_param = Column(Text, doc="配置参数")
    is_delete = Column(Boolean, default=False, doc="软删除")
    create_time = Column(DateTime, default=datetime.now, doc="创建时间")


def add_KMCfg(km_id, name, memo, label, kmpath, vectorization, stopvectorization, kmtype, vectortype, embeddingmodel, textblocklength, overlaplength, titleaugment,config_param):
    session = Session()
    kmCfg = KMCfg(km_id=km_id, name=name, memo=memo, label=label, kmpath=kmpath, kmtype=kmtype, vectorization=vectorization, stopvectorization=stopvectorization, vectortype=vectortype, embeddingmodel=embeddingmodel, textblocklength=textblocklength, overlaplength=overlaplength, titleaugment=titleaugment,config_param=config_param)
    session.add(kmCfg)
    session.commit()
    session.close()


def query_KMCfg_All(**kwargs):
    session = Session()
    records = session.query(KMCfg).filter_by(**kwargs).order_by(asc(KMCfg.position)).all()
    # for record in records:
    #     print(f"ID: {record.id}, Name: {record.name}, Memo: {record.memo}")
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


# KM Data
class KMData(Base):
    __tablename__ = 'km_data'
    id = Column(Integer, primary_key=True, autoincrement=True)
    km_id = Column(String(100), doc="与该知识关联的知识库ID")

    filename = Column(String(200), doc="上传的知识文件的名称")
    filenum = Column(Integer, default=1, doc="文档切分后的文件数")

    textblocklength = Column(Integer, default=1, doc="单段文本最大长度")
    overlaplength = Column(Integer, default=1, doc="相邻文本重合长度")
    waitvectorization = Column(Boolean, default=False, doc="等待向量化")
    is_delete = Column(Boolean, default=False, doc="软删除")
    create_time = Column(DateTime, default=datetime.now, doc="创建时间")


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
    # for record in records:
    #     print(f"ID: {record.id}, filename: {record.filename}, filenum: {record.filenum}")
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


# PluginMng
class PluginMng(Base):
    __tablename__ = 'pluginmng'
    id = Column(Integer, primary_key=True, autoincrement=True)

    plugin_id = Column(String(100), doc="与该插件关联的插件ID")
    company = Column(String(200), doc="公司名称")
    company_abbr = Column(String(100), doc="公司简称")
    name = Column(String(100), doc="名称")
    version = Column(String(100), doc="插件版本")
    alias_name = Column(String(100), doc="别名")
    filename = Column(String(200), doc="插件目录")
    run_mode = Column(String(100), doc="运行模式")
    run_scope = Column(String(100), doc="运行范围")
    instruction = Column(String(100), doc="调用该插件的指令")

    runtime_main = Column(String(200), doc="运行时主程序")
    runtime_test = Column(String(200), doc="运行时测试程序")
    description = Column(Text, doc="功能描述")

    plugin_directory = Column(String(100), doc="插件目录")
    plugin_type = Column(String(100), doc="插件类型")
    plugin_executed = Column(String(100), doc="插件运行之后的处理模式")
    plugin_event = Column(String(100), doc="插件事件")
    plugin_title = Column(Text, doc="插件事件描述")
    detail = Column(Text, doc="详细信息")
    confirm_needed = Column(Boolean, default=True)
    can_be_sold = Column(Boolean, default=False)
    used_in_sns = Column(Boolean, default=False)

    creator = Column(String(100), doc="创建人")

    is_delete = Column(Boolean, default=False, doc="软删除")
    create_time = Column(DateTime, default=datetime.now, doc="创建时间")


def add_PluginMng(plugin_id, company, company_abbr, name, version, alias_name, filename, runtime_main, runtime_test, description, plugin_directory, plugin_type, plugin_executed, plugin_event, plugin_title, detail, creator, run_mode="", run_scope="", instruction="",used_in_sns=0):
    session = Session()
    pluginMng = PluginMng(plugin_id=plugin_id, company=company, company_abbr=company_abbr, name=name, version=version, alias_name=alias_name, filename=filename, run_mode=run_mode, run_scope=run_scope, instruction=instruction, runtime_main=runtime_main, runtime_test=runtime_test, description=description, plugin_directory=plugin_directory, plugin_type=plugin_type, plugin_executed=plugin_executed, plugin_event=plugin_event, plugin_title=plugin_title, detail=detail, creator=creator,used_in_sns=used_in_sns)
    session.add(pluginMng)
    session.commit()
    session.close()


def copy_plugin_record(plugin_id, new_plugin_id, **kwargs):
    session = Session()
    try:
        # 查找要拷贝的记录
        record_to_copy = session.query(PluginMng).filter_by(plugin_id=plugin_id).first()
        if not record_to_copy:
            print(f"No record found with plugin_id: {plugin_id}")
            return None

        # 创建拷贝的记录
        new_record = PluginMng(
            plugin_id=new_plugin_id,  # 可以根据需要修改此字段
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
            create_time=datetime.now()  # 新记录的创建时间为当前时间
        )

        # 添加新记录到会话
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
    # for record in records:
    #     print(f"ID: {record.id}, filename: {record.filename}, plugin_id: {record.plugin_id}")
    session.close()
    return records


def query_PluginMng_All_Tool(**kwargs):
    session = Session()  # 创建数据库会话
    try:
        # 构建查询条件
        query = session.query(PluginMng)
        plugin_types = ["Tool_Headless", "Tool_Gui"]

        # 如果提供了文件名列表，添加过滤条件
        if plugin_types:
            query = query.filter(or_(PluginMng.plugin_type == plugin_type for plugin_type in plugin_types))

        # 添加其他过滤条件
        if kwargs:
            query = query.filter_by(**kwargs)

        records = query.order_by(desc(PluginMng.run_mode)).all()  # 执行查询并获取所有记录
    finally:
        session.close()  # 确保会话被关闭

    return records  # 返回查询结果


def query_PluginMng_All_Tool_Search(**kwargs):
    session = Session()  # 创建数据库会话
    try:
        # 构建查询条件
        query = session.query(PluginMng)
        plugin_types = ["Tool_Headless", "Tool_Gui"]

        # 如果提供了文件名列表，添加过滤条件
        query = query.filter(or_(PluginMng.plugin_type == plugin_type for plugin_type in plugin_types))
        query = query.filter(PluginMng.plugin_event.contains("search_before_ask"))
        # 添加其他过滤条件
        if kwargs:
            query = query.filter_by(**kwargs)

        records = query.order_by(desc(PluginMng.run_mode)).all()  # 执行查询并获取所有记录
    finally:
        session.close()  # 确保会话被关闭

    return records  # 返回查询结果


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

    # 主键
    id = Column(Integer, primary_key=True, autoincrement=True)

    # 表字段
    function_id = Column(String(100), doc="功能ID")
    name = Column(String(100), doc="名称")
    instruction = Column(String(100), doc="调用该插件的指令")
    file_path = Column(String(200), doc="文件路径")
    requirement = Column(Text, doc="需求")
    parameter = Column(Text, doc="参数")
    description = Column(String(100), doc="简介")
    detail = Column(Text, doc="描述")
    function_type = Column(String(100), doc="功能类型")
    function_event = Column(String(100), doc="功能事件")
    confirm_needed = Column(Boolean, default=True)
    can_be_sold = Column(Boolean, default=False)
    used_in_sns = Column(Boolean, default=False)
    creator = Column(String(100), doc="创建人")
    is_delete = Column(Boolean, default=False, doc="软删除")
    create_time = Column(DateTime, default=datetime.now, doc="创建时间")


def add_function_mng(function_id, name, instruction, file_path, requirement, parameter,
                     description, detail, function_type, function_event, creator,used_in_sns=0):
    """添加功能管理记录"""
    session = Session()
    new_function = FunctionMng(
        function_id=function_id, name=name, instruction=instruction, file_path=file_path,
        requirement=requirement, parameter=parameter, description=description, detail=detail,
        function_type=function_type, function_event=function_event, creator=creator,used_in_sns=used_in_sns
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
    """查询所有功能管理记录"""
    session = Session()
    records = session.query(FunctionMng).filter_by(**kwargs).all()  # 查询所有符合条件的记录
    session.close()  # 关闭会话
    return records


def query_function_mng(**kwargs):
    """查询单个功能管理记录"""
    session = Session()
    record = session.query(FunctionMng).filter_by(**kwargs).first()  # 查询第一个符合条件的记录
    session.close()  # 关闭会话
    return record


def update_function_mng(function_id, **kwargs):
    """更新功能管理记录"""
    session = Session()
    record = session.query(FunctionMng).filter_by(function_id=function_id).first()  # 查询记录
    if record:
        for key, value in kwargs.items():
            setattr(record, key, value)  # 更新字段
        session.commit()  # 提交事务
    session.close()  # 关闭会话

def update_function_mng_with_id(id, **kwargs):
    """更新功能管理记录"""
    session = Session()
    record = session.query(FunctionMng).filter_by(id=id).first()  # 查询记录
    if record:
        for key, value in kwargs.items():
            setattr(record, key, value)  # 更新字段
        session.commit()  # 提交事务
    session.close()  # 关闭会话


def delete_function_mng(**kwargs):
    """删除功能管理记录"""
    session = Session()
    record = session.query(FunctionMng).filter_by(**kwargs).first()  # 查询记录
    if record:
        session.delete(record)  # 删除记录
        session.commit()  # 提交事务
    session.close()  # 关闭会话


class McpMng(Base):
    __tablename__ = 'mcp_mng'

    # 主键
    id = Column(Integer, primary_key=True, autoincrement=True)

    # 表字段
    mcp_id = Column(String(100), doc="功能ID")
    name = Column(String(100), doc="名称")
    instruction = Column(String(100), doc="调用该插件的指令")
    file_path = Column(String(200), doc="文件路径")
    requirement = Column(Text, doc="需求")
    parameter = Column(Text, doc="参数")
    description = Column(String(100), doc="简介")
    detail = Column(Text, doc="描述")
    mcp_type = Column(String(100), doc="功能类型")
    mcp_event = Column(String(100), doc="功能事件")
    confirm_needed = Column(Boolean, default=True)
    can_be_sold = Column(Boolean, default=False)
    used_in_sns = Column(Boolean, default=False)
    creator = Column(String(100), doc="创建人")
    is_delete = Column(Boolean, default=False, doc="软删除")
    create_time = Column(DateTime, default=datetime.now, doc="创建时间")


def add_mcp_mng(mcp_id, name, instruction, file_path, requirement, parameter,
                description, detail, mcp_type, mcp_event, creator,used_in_sns=0):
    """添加功能管理记录"""
    session = Session()
    new_mcp = McpMng(
        mcp_id=mcp_id, name=name, instruction=instruction, file_path=file_path,
        requirement=requirement, parameter=parameter, description=description, detail=detail,
        mcp_type=mcp_type, mcp_event=mcp_event, creator=creator,used_in_sns=used_in_sns
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
    """查询所有功能管理记录"""
    session = Session()
    records = session.query(McpMng).filter_by(**kwargs).all()  # 查询所有符合条件的记录
    session.close()  # 关闭会话
    return records


def query_mcp_mng(**kwargs):
    """查询单个功能管理记录"""
    session = Session()
    record = session.query(McpMng).filter_by(**kwargs).first()  # 查询第一个符合条件的记录
    session.close()  # 关闭会话
    return record


def update_mcp_mng(mcp_id, **kwargs):
    """更新功能管理记录"""
    session = Session()
    record = session.query(McpMng).filter_by(mcp_id=mcp_id).first()  # 查询记录
    if record:
        for key, value in kwargs.items():
            setattr(record, key, value)  # 更新字段
        session.commit()  # 提交事务
    session.close()  # 关闭会话

def update_mcp_mng_with_id(id, **kwargs):
    """更新功能管理记录"""
    session = Session()
    record = session.query(McpMng).filter_by(id=id).first()  # 查询记录
    if record:
        for key, value in kwargs.items():
            setattr(record, key, value)  # 更新字段
        session.commit()  # 提交事务
    session.close()  # 关闭会话


def delete_mcp_mng(**kwargs):
    """删除功能管理记录"""
    session = Session()
    record = session.query(McpMng).filter_by(**kwargs).first()  # 查询记录
    if record:
        session.delete(record)  # 删除记录
        session.commit()  # 提交事务
    session.close()  # 关闭会话


# skillmng
# SkillMng
class SkillMng(Base):
    __tablename__ = 'skill_mng'

    # 主键
    id = Column(Integer, primary_key=True, autoincrement=True)

    # 表字段
    skill_id = Column(String(100), doc="技能ID")
    name = Column(String(100), doc="名称")
    instruction = Column(String(100), doc="调用该插件的指令")
    file_path = Column(String(200), doc="文件路径")
    requirement = Column(Text, doc="需求")
    parameter = Column(Text, doc="参数")
    description = Column(String(100), doc="简介")
    detail = Column(Text, doc="描述")
    skill_type = Column(String(100), doc="技能类型")
    skill_event = Column(String(100), doc="技能事件")
    confirm_needed = Column(Boolean, default=True)
    can_be_sold = Column(Boolean, default=False)
    used_in_sns = Column(Boolean, default=False)
    creator = Column(String(100), doc="创建人")
    is_delete = Column(Boolean, default=False, doc="软删除")
    create_time = Column(DateTime, default=datetime.now, doc="创建时间")


def add_skill_mng(skill_id, name, instruction, file_path, requirement, parameter,
                  description, detail, skill_type, skill_event, creator,used_in_sns=0):
    """添加技能管理记录"""
    session = Session()
    new_skill = SkillMng(
        skill_id=skill_id, name=name, instruction=instruction, file_path=file_path,
        requirement=requirement, parameter=parameter, description=description, detail=detail,
        skill_type=skill_type, skill_event=skill_event, creator=creator,used_in_sns=used_in_sns
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
    """查询所有技能管理记录"""
    session = Session()
    records = session.query(SkillMng).filter_by(**kwargs).all()  # 查询所有符合条件的记录
    session.close()  # 关闭会话
    return records


def query_skill_mng(**kwargs):
    """查询单个技能管理记录"""
    session = Session()
    record = session.query(SkillMng).filter_by(**kwargs).first()  # 查询第一个符合条件的记录
    session.close()  # 关闭会话
    return record


def update_skill_mng(skill_id, **kwargs):
    """更新技能管理记录"""
    session = Session()
    record = session.query(SkillMng).filter_by(skill_id=skill_id).first()  # 查询记录
    if record:
        for key, value in kwargs.items():
            setattr(record, key, value)  # 更新字段
        session.commit()  # 提交事务
    session.close()  # 关闭会话

def update_skill_mng_with_id(id, **kwargs):
    """更新技能管理记录"""
    session = Session()
    record = session.query(SkillMng).filter_by(id=id).first()  # 查询记录
    if record:
        for key, value in kwargs.items():
            setattr(record, key, value)  # 更新字段
        session.commit()  # 提交事务
    session.close()  # 关闭会话


def delete_skill_mng(**kwargs):
    """删除技能管理记录"""
    session = Session()
    record = session.query(SkillMng).filter_by(**kwargs).first()  # 查询记录
    if record:
        session.delete(record)  # 删除记录
        session.commit()  # 提交事务
    session.close()  # 关闭会话


class WebMng(Base):
    __tablename__ = 'web_mng'

    # 主键
    id = Column(Integer, primary_key=True, autoincrement=True)

    # 表字段
    web_id = Column(String(100), doc="功能ID")
    name = Column(String(100), doc="名称")
    title = Column(String(100), doc="标题")
    type = Column(String(100), doc="类型")
    description = Column(Text, doc="描述")
    filename = Column(String(200), doc="image path")
    url = Column(String(500), doc="url")
    position = Column(Integer, default=999)
    creator = Column(String(100), doc="创建人")
    is_delete = Column(Boolean, default=False, doc="软删除")
    create_time = Column(DateTime, default=datetime.now, doc="创建时间")


def add_web_mng(web_id, name, title, type, description,
                filename, url):
    """添加功能管理记录"""
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
    """查询所有功能管理记录"""
    session = Session()
    records = session.query(WebMng).filter_by(**kwargs).order_by(asc(WebMng.position)).all()  # 查询所有符合条件的记录
    session.close()  # 关闭会话
    return records


def query_web_mng(**kwargs):
    """查询单个功能管理记录"""
    session = Session()
    record = session.query(WebMng).filter_by(**kwargs).first()  # 查询第一个符合条件的记录
    session.close()  # 关闭会话
    return record


def update_web_mng(web_id, **kwargs):
    """更新功能管理记录"""
    session = Session()
    record = session.query(WebMng).filter_by(web_id=web_id).first()  # 查询记录
    if record:
        for key, value in kwargs.items():
            setattr(record, key, value)  # 更新字段
        session.commit()  # 提交事务
    session.close()  # 关闭会话


def delete_web_mng(**kwargs):
    """删除功能管理记录"""
    session = Session()
    record = session.query(WebMng).filter_by(**kwargs).first()  # 查询记录
    if record:
        session.delete(record)  # 删除记录
        session.commit()  # 提交事务
    session.close()  # 关闭会话


class WorkflowMng(Base):
    __tablename__ = 'workflow_mng'

    # 定义表的字段
    id = Column(Integer, primary_key=True, autoincrement=True, doc="主键ID")
    workflow_id = Column(String(100), doc="工作流ID")
    title = Column(String(100), doc="标题")
    description = Column(Text, doc="描述")
    instruction = Column(String(100), doc="调用的指令")
    workflow_event = Column(String(100), doc="工作流事件")
    detail = Column(Text, doc="详细信息")
    timer_desc = Column(String(200), doc="定时描述")
    timer_cron = Column(String(200), doc="定时cron公式")
    run_agent_name = Column(String(200), doc="运行定时的agent名称")
    run_agent_id = Column(String(200), doc="运行定时的agent的id")
    creator = Column(String(100), doc="创建人")
    is_delete = Column(Boolean, default=False, doc="软删除")
    create_time = Column(DateTime, default=datetime.now, doc="创建时间")


def add_workflow_mng(workflow_id, title, description, instruction,
                     detail, timer_desc, timer_cron, run_agent_name, run_agent_id):
    """添加新的工作流管理记录"""
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
    # 添加并提交到数据库
    session.add(workflow_mng)
    session.flush()
    record_id = workflow_mng.id
    session.refresh(workflow_mng)
    session.commit()
    session.close()  # 关闭会话
    return record_id


def query_workflow_mng_all(**kwargs):
    """查询所有工作流管理记录，支持过滤条件"""
    session = Session()
    try:
        # 查询满足条件的所有记录
        records = session.query(WorkflowMng).filter_by(**kwargs).all()
        return records
    finally:
        session.close()  # 关闭会话


def query_workflow_mng(**kwargs):
    """查询单个工作流管理记录，支持过滤条件"""
    session = Session()
    try:
        # 查询满足条件的第一个记录
        record = session.query(WorkflowMng).filter_by(**kwargs).first()
        return record
    finally:
        session.close()  # 关闭会话


def update_workflow_mng(id, **kwargs):
    """更新指定 id 的工作流管理记录"""
    session = Session()
    try:
        # 查询记录
        record = session.query(WorkflowMng).filter_by(id=id).first()
        if record:
            # 更新字段
            for key, value in kwargs.items():
                setattr(record, key, value)
            session.commit()  # 提交更新
    except Exception as e:
        session.rollback()  # 发生错误时回滚
        print(f"更新工作流记录失败: {e}")
    finally:
        session.close()  # 关闭会话


def delete_workflow_mng(**kwargs):
    """删除指定 id 的工作流管理记录"""
    session = Session()
    try:
        # 查询记录
        record = session.query(WorkflowMng).filter_by(**kwargs).first()
        if record:
            session.delete(record)  # 删除记录
            session.commit()  # 提交修改
    except Exception as e:
        session.rollback()  # 发生错误时回滚
        print(f"删除工作流记录失败: {e}")
    finally:
        session.close()  # 关闭会话


def copy_workflow(workflow_id, new_workflow_id):
    """根据 workflow_id 拷贝工作流记录"""
    session = Session()
    try:
        # 查找指定的工作流记录
        original_record = session.query(WorkflowMng).filter_by(workflow_id=workflow_id).first()
        if original_record:
            # 创建新的工作流记录，拷贝字段
            new_workflow = WorkflowMng(
                workflow_id=new_workflow_id,  # 新工作流ID可根据需求修改
                title=original_record.title + "-Copy",
                description=original_record.description,
                instruction=original_record.instruction,
                workflow_event=original_record.workflow_event,
                detail=original_record.detail,
                timer_desc=original_record.timer_desc,
                timer_cron=original_record.timer_cron,
                creator=original_record.creator,
                is_delete=False,  # 新记录默认未删除
                create_time=datetime.now()  # 更新创建时间为当前时间
            )
            session.add(new_workflow)  # 添加新记录
            session.commit()  # 提交事务
            return new_workflow  # 返回新创建的记录
        else:
            print("未找到指定的工作流记录")
            return None
    except Exception as e:
        session.rollback()  # 发生错误时回滚
        print(f"拷贝工作流记录失败: {e}")
    finally:
        session.close()  # 关闭会话


# task_schedule
# 定义 task_schedule 数据模型
class TaskSchedule(Base):
    __tablename__ = 'task_schedule'

    # 定义表的字段
    id = Column(Integer, primary_key=True, autoincrement=True, doc="主键ID")
    title = Column(String(100), doc="标题")
    description = Column(Text, doc="描述")
    task_type = Column(String(100), doc="任务类型")
    task_id = Column(String(100), doc="任务ID")
    org_id = Column(String(100), doc="原来所在表的ID")
    parameter = Column(Text, doc="参数")
    schedule_time = Column(DateTime, doc="预定运行时间")
    run_time = Column(DateTime, doc="实际运行时间")
    run_result = Column(Text, doc="运行结果")
    status = Column(String(100), default="0", doc="状态:0:未运行，1：运行成功，2：运行失败")
    timer_desc = Column(String(200), doc="定时描述")
    timer_cron = Column(String(200), doc="定时cron公式")
    run_agent_name = Column(String(200), doc="运行的agent名称")
    run_agent_id = Column(String(200), doc="运行的agent的id")
    creator = Column(String(100), doc="创建人")
    is_delete = Column(Boolean, default=False, doc="软删除")
    create_time = Column(DateTime, default=datetime.now, doc="创建时间")


def add_task_schedule_mng(title, description, task_type,
                          task_id, org_id, parameter, schedule_time, timer_desc, timer_cron, run_agent_name, run_agent_id):
    """添加新的记录"""
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
    # 添加并提交到数据库
    session.add(task_schedule)
    session.flush()
    record_id = task_schedule.id
    session.refresh(task_schedule)
    session.commit()
    session.close()  # 关闭会话
    return record_id


def query_task_schedule_all(**kwargs):
    """查询所有记录，支持过滤条件"""
    session = Session()
    try:
        # 查询满足条件的所有记录
        records = session.query(TaskSchedule).filter_by(**kwargs).all()
        return records
    finally:
        session.close()  # 关闭会话


def query_task_schedule(**kwargs):
    """查询单个记录，支持过滤条件"""
    session = Session()
    try:
        # 查询满足条件的第一个记录
        record = session.query(TaskSchedule).filter_by(**kwargs).first()
        return record
    finally:
        session.close()  # 关闭会话


def update_task_schedule(id, **kwargs):
    """更新指定 id 的记录"""
    session = Session()
    try:
        # 查询记录
        record = session.query(TaskSchedule).filter_by(id=id).first()
        if record:
            # 更新字段
            for key, value in kwargs.items():
                setattr(record, key, value)
            session.commit()  # 提交更新
    except Exception as e:
        session.rollback()  # 发生错误时回滚
        print(f"更新记录失败: {e}")
    finally:
        session.close()  # 关闭会话


def delete_task_schedule(**kwargs):
    """删除指定 id 的记录"""
    session = Session()
    try:
        # 查询记录
        record = session.query(TaskSchedule).filter_by(**kwargs).first()
        if record:
            session.delete(record)  # 删除记录
            session.commit()  # 提交修改
    except Exception as e:
        session.rollback()  # 发生错误时回滚
        print(f"删除记录失败: {e}")
    finally:
        session.close()  # 关闭会话


# NotesMng

class NoteMng(Base):
    __tablename__ = 'note_mng'

    # 主键
    id = Column(Integer, primary_key=True, autoincrement=True)

    # 表字段
    note_id = Column(String(100), doc="功能ID")
    title = Column(String(100), doc="名称")
    file_name = Column(String(200), doc="文件名称")
    content = Column(Text, doc="内容")
    km_id = Column(String(100), doc="功能ID")
    tag_1 = Column(String(100), doc="tag")
    tag_2 = Column(String(100), doc="tag")
    tag_3 = Column(String(100), doc="tag")
    waitvectorization = Column(Boolean, default=False, doc="等待向量化")
    creator = Column(String(100), doc="创建人")
    is_delete = Column(Boolean, default=False, doc="软删除")
    create_time = Column(DateTime, default=datetime.now, doc="创建时间")
    stick_time = Column(DateTime, nullable=True, doc="置顶操作时间")  # --> 置顶字段
    label = Column(String(50), doc="分类标签")  # --> 标签字段


def add_note_mng(note_id, title, file_name, content, km_id, tag_1, tag_2,
                 tag_3, waitvectorization, label):
    """添加功能管理记录"""
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
    """查询所有功能管理记录"""
    session = Session()
    if label:
        if count == -1:
            records = session.query(NoteMng).filter(NoteMng.label.isnot(None)).filter_by(**kwargs).order_by(
                desc(NoteMng.stick_time),
                desc(NoteMng.create_time)).all()  # 查询所有符合条件的记录
        else:
            records = session.query(NoteMng).filter(NoteMng.label.isnot(None)).filter_by(**kwargs).order_by(
                desc(NoteMng.stick_time),
                desc(NoteMng.create_time)).limit(
                count).all()  # 查询所有符合条件的记录
    else:
        if count == -1:
            records = session.query(NoteMng).filter_by(**kwargs).order_by(desc(NoteMng.stick_time),
                                                                          desc(
                                                                              NoteMng.create_time)).all()  # 查询所有符合条件的记录
        else:
            records = session.query(NoteMng).filter_by(**kwargs).order_by(desc(NoteMng.stick_time),
                                                                          desc(NoteMng.create_time)).limit(
                count).all()  # 查询所有符合条件的记录
    session.close()  # 关闭会话
    return records


def query_note_mng(**kwargs):
    """查询单个功能管理记录"""
    session = Session()
    record = session.query(NoteMng).filter_by(**kwargs).first()  # 查询第一个符合条件的记录
    session.close()  # 关闭会话
    return record


def query_note_mng_ById(id):
    session = Session()
    res = session.query(NoteMng).filter(NoteMng.id == id).one_or_none()
    session.close()

    return res


def query_note_mng_ByLabel(km_id):
    session = Session()
    # 首先获取所有不同的 label
    res = session.query(NoteMng.label).filter(NoteMng.km_id == km_id).distinct().all()
    session.close()
    if res is None:
        labels = []
    else:
        labels = [i.label for i in res if i.label is not None]
    return labels


def update_note_mng(note_id, **kwargs):
    """更新功能管理记录"""
    session = Session()
    record = session.query(NoteMng).filter_by(note_id=note_id).first()  # 查询记录
    if record:
        for key, value in kwargs.items():
            setattr(record, key, value)  # 更新字段
        session.commit()  # 提交事务
    session.close()  # 关闭会话


def update_note_mng_stick(id, value=None, key: str = 'stick_time'):
    session = Session()
    task = session.query(NoteMng).filter_by(id=id).first()
    if task:
        setattr(task, key, value)
        session.commit()
    session.close()


def update_note_mng_by_recordid(id, **kwargs):
    """更新功能管理记录"""
    session = Session()
    record = session.query(NoteMng).filter_by(id=id).first()  # 查询记录
    if record:
        for key, value in kwargs.items():
            setattr(record, key, value)  # 更新字段
        session.commit()  # 提交事务
    session.close()  # 关闭会话


def delete_note_mng(**kwargs):
    """删除功能管理记录"""
    session = Session()
    record = session.query(NoteMng).filter_by(**kwargs).first()  # 查询记录
    if record:
        session.delete(record)  # 删除记录
        session.commit()  # 提交事务
    session.close()  # 关闭会话


def query_Note_mng_Search_Content(count, label: bool = False, **kwargs):
    session = Session()

    # 搜索关键词
    title_keyword = kwargs.get('title', None)
    content_keyword = kwargs.get('content', None)

    # 构建初始查询
    query = session.query(NoteMng)

    if label:
        query = query.filter(NoteMng.label.isnot(None))
    # 添加搜索条件
    search_terms = []
    if title_keyword:
        search_terms.append(NoteMng.title.contains(title_keyword))
    if content_keyword:
        search_terms.append(NoteMng.content.contains(content_keyword))

    if search_terms:
        query = query.filter(or_(*search_terms))

    # 获取结果
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


# System Cfg
class SystemCfg(Base):
    __tablename__ = 'system_cfg'
    id = Column(Integer, primary_key=True, autoincrement=True)

    autorun = Column(Boolean, default=False, doc="开机自动运行")
    showtaskbar = Column(Boolean, default=False, doc="在任务栏显示")
    updateinfo = Column(Boolean, default=False, doc="有更新时提醒升级")
    minirunontray = Column(Boolean, default=False, doc="应用最小化到托盘")  # 增加
    closebuttontype = Column(String(100), doc="点击关闭按钮:隐藏窗口，关闭程序")
    style = Column(String(500), doc="风格：亮色，暗色")

    showinfo = Column(Boolean, default=True, doc="显示通知")
    showinfoicon = Column(Boolean, default=True, doc="通知区域显示图标")
    infosound = Column(Boolean, default=True, doc="通知时播放声音")

    is_delete = Column(Boolean, default=False, doc="软删除")
    create_time = Column(DateTime, default=datetime.now, doc="创建时间")


def add_SystemCfg(autorun, showtaskbar, updateinfo, minirunontray, closebuttontype, style, showinfo, showinfoicon, infosound):
    session = Session()
    systemCfg = SystemCfg(autorun=autorun, showtaskbar=showtaskbar, updateinfo=updateinfo, minirunontray=minirunontray, closebuttontype=closebuttontype, style=style, showinfo=showinfo, showinfoicon=showinfoicon, infosound=infosound)
    session.add(systemCfg)
    session.commit()
    session.close()


def query_SystemCfg_All(**kwargs):
    session = Session()
    records = session.query(SystemCfg).filter_by(**kwargs).all()
    # for record in records:
    #     print(f"ID: {record.id}")
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


# Logs
class LogsMng(Base):
    __tablename__ = 'logsmng'
    id = Column(Integer, primary_key=True, autoincrement=True)

    logs_id = Column(String(100), doc="与该插件关联的插件ID")
    content = Column(Text, doc="日志内容")
    type = Column(String(200), doc="日志类型，比如：bug，警告")

    is_delete = Column(Boolean, default=False, doc="软删除")
    create_time = Column(DateTime, default=datetime.now, doc="创建时间")


def add_LogsMng(logs_id, content, type):
    session = Session()
    logsMng = LogsMng(logs_id=logs_id, content=content, type=type)
    session.add(logsMng)
    session.commit()
    session.close()


def query_LogsMng_All(**kwargs):
    session = Session()
    records = session.query(LogsMng).filter_by(**kwargs).all()
    # for record in records:
    #     print(f"ID: {record.id}, type: {record.type}, logs_id: {record.logs_id}")
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


#  System config
class SysConfig(Base):
    __tablename__ = 'config'
    id = Column(Integer, primary_key=True, autoincrement=True)
    lang = Column(String(20), doc="语言")


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


# --> question
class Question(Base):
    __tablename__ = 'question'
    id = Column(Integer, primary_key=True, autoincrement=True)
    question = Column(String)
    tag = Column(String(20), doc="问题的类别")
    create_time = Column(DateTime, default=datetime.now, doc="创建时间")


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


# Prompt
class Prompt(Base):
    __tablename__ = 'prompts'
    id = Column(Integer, primary_key=True, autoincrement=True)
    title = Column(String)  # 新增的 title 字段
    content = Column(String)
    question = Column(String)
    tags = Column(String)  # Storing tags as comma-separated values
    model_name = Column(String(100), doc="模型的名称")
    position = Column(Integer)
    # 反向关系，表示一个Prompt可以有多个PromptFrequent
    prompt_frequents = relationship("PromptFrequent", back_populates="prompt")


def get_prompt_by_title(title):
    """
    根据给定的 title，查询数据库中的记录并返回对应的 content。

    :param session: SQLAlchemy 会话对象
    :param title: 要查询的 title 值
    :return: 对应的 content 字段值，如果未找到记录则返回 None
    """
    # 使用 session.query() 方法查询，filter_by 对应 title 字段
    session = Session()
    prompt = session.query(Prompt).filter_by(title=title).first()
    # 如果查询到结果，返回 content，否则返回 None
    session.close()
    return prompt.content if prompt else None


def get_prompt_by_id(id):
    # 使用 session.query() 方法查询，filter_by 对应 title 字段
    session = Session()
    prompt = session.query(Prompt).filter_by(id=id).first()
    # 如果查询到结果，返回 content，否则返回 None
    session.close()
    return prompt.content if prompt else None


def get_all_prompt(**kwargs):
    """Query a single MapCfg record with optional filters."""
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
    """
    根据给定的 model_name，查询数据库中的记录并返回对应的 content。

    :param model_name: 要查询的 model_name 值
    :return: 对应的 Prompt 记录列表，如果未找到记录则返回空列表
    """
    # 创建 SQLAlchemy 会话对象
    session = Session()

    try:
        # 使用 session.query() 方法，查询 model_name 等于给定值或为空的记录
        prompts = session.query(Prompt).filter(
            (Prompt.model_name == model_name) | (Prompt.model_name.is_(None)) | (Prompt.model_name == '')
        ).all()

        # 返回查询到的所有记录
        return prompts

    except Exception as e:
        # 在发生异常时记录错误信息
        print(f"An error occurred: {e}")
        return []

    finally:
        # 确保会话在完成后关闭
        session.close()


def update_prompt(id, **kwargs):
    session = Session()
    record = session.query(Prompt).filter_by(id=id).first()
    if record:
        for key, value in kwargs.items():
            setattr(record, key, value)
        session.commit()
    session.close()


# 定义 KeyValue 表
class KeyValue(Base):
    __tablename__ = 'key_value'

    id = Column(Integer, primary_key=True, autoincrement=True)
    key = Column(String, nullable=False)
    value = Column(String, nullable=False)


# 增加一条记录
def add_key_value(key: str, value: str):
    """增加一条 key-value 记录"""
    session = Session()
    new_entry = KeyValue(key=key, value=value)
    session.add(new_entry)
    session.commit()


# 查询记录
def get_key_value(key: str):
    """根据 key 查询 value"""
    session = Session()
    result = session.query(KeyValue).filter_by(key=key).first()
    return result.value if result else None


# 查询多条记录
def get_all_key_values() -> list:
    """获取所有 key-value 记录"""
    session = Session()
    records = session.query(KeyValue).all()
    return records


# 模糊查询
def search_key_values(search_text: str) -> list:
    """根据传入的文本对 key 进行模糊搜索"""
    session = Session()
    records = session.query(KeyValue).filter(KeyValue.key.like(f'%{search_text}%')).all()
    return records


# 更新记录
def update_key_value(key: str, new_value: str):
    """根据 key 更新对应的 value"""
    session = Session()
    entry = session.query(KeyValue).filter_by(key=key).first()
    if entry:
        entry.value = new_value
        session.commit()


# 删除记录
def delete_key_value(key: str):
    """根据 key 删除对应的记录"""
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


# MapCfg model definition
class MapCfg(Base):
    """Model for the map_cfg table"""
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
    """Add a new MapCfg record to the database."""
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
    """Query MapCfg records with optional filters."""
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
    """Query a single MapCfg record with optional filters."""
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
    """Update an existing MapCfg by its ID."""
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
    """Delete a MapCfg by its ID."""
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


# MapTask model definition
class MapTask(Base):
    """Model for the map_task table"""
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
    """Add a new MapTask record to the database."""
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
    """Query MapTask records with optional filters."""
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
    """Query a single MapTask record with optional filters."""
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
    """Update an existing MapTask by its ID."""
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
    """Delete a MapTask by its ID."""
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


# MapTech model definition
class MapTool(Base):
    """Model for the map_tool table"""
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
    """Add a new MapTech record to the database."""
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
    """Query MapTech records with optional filters."""
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
    """Query a single MapTech record with optional filters."""
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
    """Update an existing MapTech by its ID."""
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
    """Delete a MapTech by its ID."""
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


# MapTrade model definition
class MapTrade(Base):
    """Model for the map_trade table"""
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
    """Add a new MapTrade record to the database."""
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
    """Query MapTrade records with optional filters."""
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
    """Query a single MapTrade record with optional filters."""
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
    """Update an existing MapTrade by its ID."""
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
    """Delete a MapTrade by its ID."""
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


# MapVisit model definition
class MapVisit(Base):
    """Model for the map_visit table"""
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
    """Add a new MapVisit record to the database."""
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
    """Query MapVisit records with optional filters."""
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
    """Query a single MapVisit record with optional filters."""
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
    """Update an existing MapVisit by its ID."""
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
    """Delete a MapVisit by its ID."""
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
    """Model for the llm_frequent table"""
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
    """Add a new LlmFrequent record to the database."""
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
    """Query LlmFrequent records with optional filters."""
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
    """Query a single LlmFrequent record with optional filters."""
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
    """Update an existing LlmFrequent by its ID."""
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
    """Delete a LlmFrequent by its ID."""
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
    """Model for the prompt_frequent table"""
    __tablename__ = 'prompt_frequent'

    id = Column(Integer, primary_key=True, autoincrement=True)
    prompt_id = Column(String(100), ForeignKey('prompts.id'))  # 外键关联到Prompt表的id
    title = Column(String(100))
    position = Column(Integer)
    belong_to_agent_id = Column(String(100))
    creator = Column(String(100))
    is_delete = Column(Boolean, default=0)
    create_time = Column(DateTime, default=datetime.now)
    # 通过外键建立与Prompt表的关系
    prompt = relationship("Prompt", back_populates="prompt_frequents")


def add_prompt_frequent(**kwargs):
    """Add a new PromptFrequent record to the database."""
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
    """Query PromptFrequent records with optional filters."""
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
    """获取所属代理ID为指定值的PromptFrequent记录，并按position升序排列"""
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
    """Query a single PromptFrequent record with optional filters."""
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
    """Update an existing PromptFrequent by its ID."""
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
    """Delete a PromptFrequent by its ID."""
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


# 定义模型
class SystemInit(Base):
    __tablename__ = 'system_init'

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(100), doc="姓名")
    avatar = Column(Text, doc="头像链接")
    password = Column(String(128), doc="密码")
    confirm_password = Column(String(128), doc="确认密码")
    profile = Column(String(500), doc="个人简介")
    llm = Column(String(100), doc="LLM信息")
    llm_server = Column(String(500), doc="LLM Server Url")
    api_key = Column(String(200), doc="API密钥")
    avatar3d = Column(Text, doc="3D头像链接")
    account = Column(String(128), doc="帐号")
    account_password = Column(String(128), doc="帐号密码")
    sns_url = Column(Text, doc="社交网络链接")
    map = Column(String, doc="地图")
    map_api_key = Column(String(128), doc="地图API密钥")
    map_id = Column(String(128), doc="地图ID")
    status = Column(Integer, doc="状态")
    is_delete = Column(Boolean, default=False, doc="软删除")
    create_time = Column(DateTime, default=datetime.utcnow, doc="创建时间")


# 增加记录
def add_SystemInit(name, avatar, password, confirm_password, profile, llm, llm_server, api_key, avatar3d,
                   account, account_password, sns_url, map, map_api_key, map_id, status):
    """添加新记录到 system_init 表"""
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


# 查询所有记录
def query_SystemInit_All(**kwargs):
    """查询所有记录，支持过滤条件"""
    session = Session()
    records = session.query(SystemInit).filter_by(**kwargs).all()
    session.close()
    return records


# 查询单条记录
def query_SystemInit(**kwargs):
    """根据条件查询单条记录"""
    session = Session()
    record = session.query(SystemInit).filter_by(**kwargs).first()
    session.close()
    return record


# 更新记录
def update_SystemInit_ById(id, **kwargs):
    """根据 ID 更新记录"""
    session = Session()
    record = session.query(SystemInit).filter_by(id=id).first()
    if record:
        for key, value in kwargs.items():
            setattr(record, key, value)
        session.commit()
    session.close()


# 删除记录
def delete_SystemInit(id):
    """将记录标记为已删除"""
    session = Session()
    record = session.query(SystemInit).filter_by(id=id).first()
    if record:
        record.is_delete = True  # 将 is_delete 标记为 True 进行软删除
        session.commit()
    session.close()


# 定义 map_activity 表的 ORM 类
class MapActivity(Base):
    __tablename__ = 'map_activity'
    id = Column(Integer, primary_key=True, autoincrement=True)
    activity_id = Column(String(50), doc="活动ID")
    content = Column(Text, doc="活动内容")
    type = Column(String(100), doc="活动类型")
    create_time = Column(DateTime, default=datetime.now, doc="创建时间")
    is_delete = Column(Boolean, default=False, doc="软删除")




def add_map_activity(activity_id, content, type):
    """新增活动记录"""
    session = Session()
    new_activity = MapActivity(activity_id=activity_id, content=content, type=type)
    session.add(new_activity)
    session.commit()
    session.close()


def query_map_activity_all(**kwargs):
    """查询所有活动记录，支持筛选条件"""
    session = Session()
    records = session.query(MapActivity).filter_by(**kwargs).all()
    session.close()
    return records


def query_map_activity_previous(last_record_id=None, count=20, type_str=None):
    """查询小于 last_record_id 的活动记录，返回 count 个记录，
    记录按降序排列。如果 type_str 不为空，则返回 type 等于 type_str 的记录。
    如果 last_record_id 为 None，则不应用此筛选条件。"""

    session = Session()

    # 基础查询：创建查询对象
    query = session.query(MapActivity)

    # 如果 last_record_id 不是 None，添加 id < last_record_id 的筛选条件
    if last_record_id is not None:
        query = query.filter(MapActivity.id < last_record_id)

    # 如果 type_str 不为空，添加 type 的筛选条件
    if type_str:
        query = query.filter(MapActivity.type == type_str)

    # 执行查询，按 id 降序排列，并限制返回的记录数量
    records = query.order_by(MapActivity.id.desc()).limit(count).all()

    session.close()
    return records


def query_map_activity(**kwargs):
    """查询符合条件的第一条活动记录"""
    session = Session()
    record = session.query(MapActivity).filter_by(**kwargs).first()
    session.close()
    return record


def update_map_activity_by_id(activity_id, **kwargs):
    """通过ID更新活动记录"""
    session = Session()
    record = session.query(MapActivity).filter_by(activity_id=activity_id).first()
    if record:
        for key, value in kwargs.items():
            setattr(record, key, value)
        session.commit()
    session.close()


def delete_map_activity(activity_id):
    """通过ID删除活动记录"""
    session = Session()
    record = session.query(MapActivity).filter_by(activity_id=activity_id).first()
    if record:
        session.delete(record)
        session.commit()
    session.close()


# 定义 map_preset_msg 表的 ORM 类
class MapPresetMsg(Base):
    __tablename__ = 'map_preset_msg'
    id = Column(Integer, primary_key=True, autoincrement=True)
    content = Column(Text, doc="内容")
    position = Column(Integer, default=0, doc="位置")
    create_time = Column(DateTime, default=datetime.now, doc="创建时间")
    is_delete = Column(Boolean, default=False, doc="软删除")

def add_map_preset_msg(content):
    """新增预设消息记录"""
    session = Session()
    try:
        new_msg = MapPresetMsg(content=content)
        session.add(new_msg)
        session.commit()  # 提交新记录
    except Exception as e:
        session.rollback()  # 发生异常时回滚
        raise e
    finally:
        session.close()  # 确保会话关闭

def query_map_preset_msg_all(**kwargs):
    """查询所有预设消息记录，支持筛选条件"""
    session = Session()
    try:
        records = session.query(MapPresetMsg).filter_by(**kwargs).all()
    finally:
        session.close()  # 确保会话关闭
    return records

def query_map_preset_msg_previous(last_record_id=None, count=20):
    """查询小于 last_record_id 的预设消息记录，返回 count 个记录，按降序排列"""
    session = Session()
    query = session.query(MapPresetMsg)

    if last_record_id is not None:
        query = query.filter(MapPresetMsg.id < last_record_id)

    records = query.order_by(MapPresetMsg.id.desc()).limit(count).all()
    session.close()  # 确保会话关闭
    return records

def query_map_preset_msg(**kwargs):
    """查询符合条件的第一条预设消息记录"""
    session = Session()
    try:
        record = session.query(MapPresetMsg).filter_by(**kwargs).first()
    finally:
        session.close()  # 确保会话关闭
    return record

def update_map_preset_msg_by_id(msg_id, **kwargs):
    """通过ID更新预设消息记录"""
    session = Session()
    try:
        record = session.query(MapPresetMsg).filter_by(id=msg_id).first()
        if record:
            for key, value in kwargs.items():
                setattr(record, key, value)  # 更新属性
            session.commit()  # 提交更改
    except Exception as e:
        session.rollback()  # 发生异常时回滚
        raise e
    finally:
        session.close()  # 确保会话关闭

def delete_map_preset_msg(content):
    """通过ID删除预设消息记录"""
    session = Session()
    try:
        record = session.query(MapPresetMsg).filter_by(content=content).first()
        if record:
            session.delete(record)  # 删除记录
            session.commit()  # 提交更改
    except Exception as e:
        session.rollback()  # 发生异常时回滚
        raise e
    finally:
        session.close()  # 确保会话关闭


# 定义 chat_preset_msg 表的 ORM 类
class ChatPresetMsg(Base):
    __tablename__ = 'chat_preset_msg'
    id = Column(Integer, primary_key=True, autoincrement=True)
    content = Column(Text, doc="内容")
    position = Column(Integer, default=0, doc="位置")
    create_time = Column(DateTime, default=datetime.now, doc="创建时间")
    is_delete = Column(Boolean, default=False, doc="软删除")


def add_chat_preset_msg(content):
    """新增预设消息记录"""
    session = Session()
    try:
        new_msg = ChatPresetMsg(content=content)
        session.add(new_msg)
        session.commit()  # 提交新记录
    except Exception as e:
        session.rollback()  # 发生异常时回滚
        raise e
    finally:
        session.close()  # 确保会话关闭

def query_chat_preset_msg_all(**kwargs):
    """查询所有预设消息记录，支持筛选条件"""
    session = Session()
    try:
        records = session.query(ChatPresetMsg).filter_by(**kwargs).all()
    finally:
        session.close()  # 确保会话关闭
    return records

def query_chat_preset_msg_previous(last_record_id=None, count=20):
    """查询小于 last_record_id 的预设消息记录，返回 count 个记录，按降序排列"""
    session = Session()
    query = session.query(ChatPresetMsg)

    if last_record_id is not None:
        query = query.filter(ChatPresetMsg.id < last_record_id)

    records = query.order_by(ChatPresetMsg.id.desc()).limit(count).all()
    session.close()  # 确保会话关闭
    return records

def query_chat_preset_msg(**kwargs):
    """查询符合条件的第一条预设消息记录"""
    session = Session()
    try:
        record = session.query(ChatPresetMsg).filter_by(**kwargs).first()
    finally:
        session.close()  # 确保会话关闭
    return record

def update_chat_preset_msg_by_id(msg_id, **kwargs):
    """通过ID更新预设消息记录"""
    session = Session()
    try:
        record = session.query(ChatPresetMsg).filter_by(id=msg_id).first()
        if record:
            for key, value in kwargs.items():
                setattr(record, key, value)  # 更新属性
            session.commit()  # 提交更改
    except Exception as e:
        session.rollback()  # 发生异常时回滚
        raise e
    finally:
        session.close()  # 确保会话关闭

def delete_chat_preset_msg(content):
    """通过ID删除预设消息记录"""
    session = Session()
    try:
        record = session.query(ChatPresetMsg).filter_by(content=content).first()
        if record:
            session.delete(record)  # 删除记录
            session.commit()  # 提交更改
    except Exception as e:
        session.rollback()  # 发生异常时回滚
        raise e
    finally:
        session.close()  # 确保会话关闭


# Define the ToolList model corresponding to the view tool_list
class ToolList(Base):
    """Model for the tool_list view"""
    __tablename__ = 'tool_list'

    id = Column(String, primary_key=True)
    name = Column(String)
    description = Column(Text)
    plugin_type = Column(String)
    confirm_needed = Column(Boolean)
    can_be_sold = Column(Boolean)

# Function definitions to interact with the ToolList view

def query_tool_list(**kwargs):
    """Query ToolList records with optional filters."""
    session = Session()
    try:
        # Build filter expressions from kwargs
        filter_expr = [getattr(ToolList, key) == value for key, value in kwargs.items()]
        # Query with filters, sorted by id for consistency
        results = session.query(ToolList).filter(*filter_expr).order_by(desc(ToolList.id)).all()
        return results
    except Exception as e:
        print(f"Error querying ToolList: {e}")
        return []
    finally:
        session.close()

def query_single_tool(**kwargs):
    """Query a single ToolList record with optional filters."""
    session = Session()
    try:
        # Build filter expressions from kwargs
        filter_expr = [getattr(ToolList, key) == value for key, value in kwargs.items()]
        # Query the first record matching the filters
        result = session.query(ToolList).filter(*filter_expr).order_by(desc(ToolList.id)).first()
        return result
    except Exception as e:
        print(f"Error querying single ToolList: {e}")
        return None
    finally:
        session.close()





# 在创建表时，请确保调用 Base.metadata.create_all(engine)


Base.metadata.create_all(engine)
if __name__ == "__main__":
    # Base.metadata.create_all(engine)
    # add_AgentTask('who are you', 'i am chen',1,1,1,1,1)
    # add_AgentTask('how old are you', '30',1,1,1,1,1)
    # print(Path(__file__).resolve())
    # query_users()
    # update_user(1, '王五', 28)
    # delete_user(2)

    # add_AgentCfg('007', 'i am chen7', 1, datetime.now().date(), 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1)
    # query_AgentCfg(user_id="0011",name="i am chen11")
    agent = query_AgentCfg(id=1)
    # print(f"ID: {agent.id}, Name: {agent.name}, Memo: {agent.memo}")

    # update_AgentCfg(1,user_id="0012",name="i am chen12")
