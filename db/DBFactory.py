import os

from sqlalchemy import create_engine, Column, Integer, String
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from pathlib import Path

from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Boolean, Text, Float
from sqlalchemy.orm import relationship
from sqlalchemy import desc,asc
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
    flag  = Column(Integer, doc="0为发送，1为接收")
    title = Column(Text, default=None, doc="标题，缺省使用第一条信息字段")
    content = Column(Text, doc="消息内容")
    attachment_list = Column(Text, doc="附件列表，是一个元组")
    document_content = Column(Text, doc="所有的文档类型的附件内容")
    image_json = Column(Text, doc="所有图片base64的内容json列表")
    km_list = Column(Text, doc="召回的知识库内容列表")
    km_content = Column(Text, doc="召回的知识库的全部内容")
    owner_name = Column(String(100), doc="")
    owner_account =  Column(String(100), doc="")
    friend_name = Column(String(100), doc="")
    friend_account =  Column(String(100), doc="")
    create_time = Column(DateTime, default=datetime.now, doc="创建时间")
    is_delete = Column(Boolean, default=False, doc="软删除")
    is_first =Column(Boolean, default=False, doc="是否第一句对话")


def add_AIChatMessages(conversation_id, flag, title, content, owner_name, owner_account, friend_name, friend_account,is_first=False, attachment_list="", document_content="", image_json="", km_list="", km_content=""):
    session = Session()
    ai_friend = AIChatMessages(conversation_id=conversation_id, flag=flag, title=title, content=content, owner_name=owner_name, owner_account=owner_account, friend_name=friend_name, friend_account=friend_account, is_first=is_first, attachment_list=attachment_list, document_content=document_content, image_json=image_json, km_list=km_list, km_content=km_content)
    session.add(ai_friend)
    session.commit()
    session.close()


def query_AIChatMessages_All(**kwargs):
    session = Session()
    records = session.query(AIChatMessages).filter_by(**kwargs).order_by(desc(AIChatMessages.create_time)).limit(500).all()
    session.close()
    return records


def query_AIChatMessages(**kwargs):
    session = Session()
    record = session.query(AIChatMessages).filter_by(**kwargs).first()
    session.close()
    return record


def update_AIChatMessages(id, **kwargs):
    session = Session()
    record = session.query(AIChatMessages).filter_by(id=id).first()
    if record:
        for key, value in kwargs.items():
            setattr(record, key, value)
        session.commit()
    session.close()


def delete_AIChatMessages(id):
    session = Session()
    record = session.query(AIChatMessages).filter_by(id=id).first()
    if record:
        session.delete(record)
        session.commit()
    session.close()

def query_AIChat_Content(id,**kwargs):
    session = Session()
    res = session.query(AIChatMessages).filter(AIChatMessages.is_first == True,AIChatMessages.id==id).one_or_none()
    if res:
        conversation_id = res.conversation_id
    tasks = session.query(AIChatMessages).filter(AIChatMessages.conversation_id==conversation_id).order_by(asc(AIChatMessages.create_time)).all()

    # for task in tasks:
    #     print(f"ID: {task.id}, qes: {task.problem},ans:{task.answer}")
    session.close()

    return  tasks

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

    if title_keyword=="":
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
    name = Column(String(200), doc="")
    owner_user_id=Column(String(100), doc="所有人userid")
    owner_name = Column(String(200), doc="")
    owner_sns_account=Column(String(100), doc="所有人帐号")
    memo = Column(Text, doc="")
    nickname = Column(String(100), doc="昵称")
    sign = Column(String(200), doc="状态信息(个人签名)")
    borndate = Column(DateTime, default=datetime.now, doc="生日")
    gender = Column(Integer, doc="")
    area = Column(String(100), doc="国家及地区")
    city = Column(String(100), doc="城市")
    address = Column(String(200), doc="地址")
    mail = Column(String(100), doc="")
    phone = Column(String(100), doc="")
    organization = Column(String(200), doc="组织")
    title = Column(String(100), doc="头衔")
    position = Column(String(100), doc="角色")
    is_delete = Column(Boolean, default=False, doc="软删除")
    create_time = Column(DateTime, default=datetime.now, doc="创建时间")

def add_AIFriend(account,name,owner_user_id,owner_name,owner_sns_account,memo,nickname,sign,borndate,gender,area,city,address,mail,phone,organization,title,position):
    session = Session()
    ai_friend = AIFriend(account = account,name = name,owner_user_id=owner_user_id,owner_name=owner_name,owner_sns_account=owner_sns_account,memo = memo,nickname = nickname,sign = sign,borndate = borndate,gender = gender,area = area,city = city,address = address,mail = mail,phone = phone,organization = organization,title = title,position = position)
    session.add(ai_friend)
    session.commit()
    session.close()

def query_AIFriend_All(**kwargs):
    session = Session()
    records = session.query(AIFriend).filter_by(**kwargs).all()
    session.close()
    return records

def query_AIFriend(**kwargs):
    session = Session()
    record = session.query(AIFriend).filter_by(**kwargs).first()
    session.close()
    return record

def update_AIFriend(id, **kwargs):
    session = Session()
    record = session.query(AIFriend).filter_by(id=id).first()
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
    owner_account =  Column(String(100), doc="")
    friend_name = Column(String(100), doc="")
    friend_account =  Column(String(100), doc="")
    create_time = Column(DateTime, default=datetime.now, doc="创建时间")
    is_delete = Column(Boolean, default=False, doc="软删除")



def add_AIChatInform(inform_id,  title, content,type,status, owner_name, owner_account, friend_name, friend_account):
    session = Session()
    ai_friend = AIChatInform(inform_id=inform_id,title=title, content=content, type=type,status=status,owner_name=owner_name, owner_account=owner_account, friend_name=friend_name, friend_account=friend_account)
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
    model_name =  Column(String(100), doc="回答问题的模型的名称")
    agent_id = Column(String(200), doc="agent id")
    create_time = Column(DateTime, default=datetime.now, doc="创建时间")
    is_delete = Column(Boolean, default=False, doc="软删除")
    is_first =Column(Boolean, default=False, doc="是否第一句对话")

def add_AgentTask(task_id,title,problem, answer,model_name,agent_id,is_first=True,attachment_list="",document_content="",image_json=""):
    session = Session()
    new_task = AgentTask(task_id=task_id,title=title,problem=problem, answer=answer,model_name=model_name,agent_id=agent_id,is_first=is_first,attachment_list=attachment_list,document_content=document_content,image_json=image_json)
    session.add(new_task)
    session.flush()
    record_id =  new_task.id
    session.refresh(new_task)
    try:
        session.commit()
    except Exception as e:
        print(e)
    print("--->start insert db6")
    session.close()
    return(record_id)

def query_AgentTask(**kwargs):
    session = Session()
    try:
        # 构建过滤条件
        filter_expr = []
        for key, value in kwargs.items():
            filter_expr.append(getattr(AgentTask, key) == value)

        # 查询并过滤记录
        tasks = session.query(AgentTask).filter(*filter_expr).order_by(desc(AgentTask.create_time)).limit(500).all()
        # for task in tasks:
        #     print(f"ID: {task.id}, Name: {task.problem}")
    except Exception as e:
        print(e)
        tasks = []
    session.close()
    return tasks

def query_AgentTask_Content(id,**kwargs):
    session = Session()
    res = session.query(AgentTask).filter(AgentTask.is_first == True,AgentTask.id==id).one_or_none()
    if res:
        task_id = res.task_id
    tasks = session.query(AgentTask).filter(AgentTask.task_id==task_id).order_by(asc(AgentTask.create_time)).all()

    # for task in tasks:
    #     print(f"ID: {task.id}, qes: {task.problem},ans:{task.answer}")
    session.close()

    return  tasks

def query_AgentTask_Search_Content(**kwargs):
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

    if title_keyword=="":
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

def query_AgentTask_Search_First(agent_id, task_id):
    session = Session()

    # 查找特定 agent_id 和 task_id 且 is_first 为 True 的记录
    first_task = session.query(AgentTask) \
        .filter(AgentTask.agent_id == agent_id, AgentTask.task_id == task_id, AgentTask.is_first == True) \
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
    borndate = Column(DateTime, default=datetime.now, doc="出生日期")
    borncontry = Column(String(100), doc="")
    language = Column(String(100), doc="")
    gender = Column(Integer, doc="")
    joinfederation = Column(Boolean, default=False, doc="")
    syncfederation = Column(Boolean, default=False, doc="")
    federationid = Column(String(150), doc="")
    specialization = Column(Text, doc="")
    plugins = Column(String(500), doc="")
    kms = Column(String(500), doc="")
    prompt = Column(Text, doc="")
    snsaccount = Column(String(100), doc="")
    snsnickname = Column(String(100), doc="")
    islimittotalmessage =  Column(Boolean, default=True, doc="")
    islimitmessagepp =  Column(Boolean, default=True, doc="")
    totalmessages =  Column(Integer, doc="")
    ppmessages = Column(Integer, doc="")
    readfile = Column(Boolean, default=True, doc="")
    writefile = Column(Boolean, default=True, doc="")
    deletefile = Column(Boolean, default=True, doc="")
    execfile = Column(Boolean, default=True, doc="")
    autorunrounds = Column(Integer, doc="")
    position = Column(Integer,default=9999, doc="")
    is_show = Column(Boolean, default=True, doc="是否显示")
    is_delete = Column(Boolean, default=False, doc="软删除")
    create_time = Column(DateTime, default=datetime.now, doc="创建时间")

def add_AgentCfg(user_id,name,memo,borndate ,borncontry,language,gender,joinfederation,syncfederation,federationid,specialization,plugins,kms,prompt,snsaccount,snsnickname,islimittotalmessage,islimitmessagepp,totalmessages,ppmessages,readfile,writefile,deletefile,execfile,autorunrounds):
    session = Session()
    agentcfg = AgentCfg(user_id=user_id,name=name,memo=memo,borndate=borndate,borncontry=borncontry,language=language,gender=gender,joinfederation=joinfederation,syncfederation=syncfederation,federationid=federationid,specialization=specialization,plugins=plugins,kms=kms,prompt=prompt,snsaccount=snsaccount,snsnickname=snsnickname,islimittotalmessage=islimittotalmessage,islimitmessagepp=islimitmessagepp,totalmessages=totalmessages,ppmessages=ppmessages,readfile=readfile,writefile=writefile,deletefile=deletefile,execfile=execfile,autorunrounds=autorunrounds)
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
    owner =  Column(String(100), doc="该内容的发送者")
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
    is_first =Column(Boolean, default=False, doc="是否第一句对话")

def add_AgentTaskMulti(task_id,topic,content, owner, group_id,is_first=True,attachment_list="",document_content="",image_json="",model_name="",agent_id=""):
    session = Session()
    new_task = AgentTaskMulti(task_id=task_id,topic=topic,content=content, owner=owner,group_id=group_id,is_first=is_first,attachment_list=attachment_list,document_content=document_content,image_json=image_json,model_name=model_name,agent_id=agent_id)
    session.add(new_task)
    session.flush()
    record_id =  new_task.id
    session.refresh(new_task)
    try:
        session.commit()
    except Exception as e:
        print(e)

    session.close()
    return(record_id)

def query_AgentTaskMulti(**kwargs):
    session = Session()
    try:
        # 构建过滤条件
        filter_expr = []
        for key, value in kwargs.items():
            filter_expr.append(getattr(AgentTaskMulti, key) == value)

        # 查询并过滤记录
        tasks = session.query(AgentTaskMulti).filter(*filter_expr).order_by(desc(AgentTaskMulti.create_time)).limit(500).all()
        # for task in tasks:
        #     print(f"ID: {task.id}, Name: {task.content}")
    except Exception as e:
        print(e)
        tasks = []
    session.close()
    return tasks


def query_AgentTaskMulti_Content(id,**kwargs):
    session = Session()
    res = session.query(AgentTaskMulti).filter(AgentTaskMulti.is_first == True,AgentTaskMulti.id==id).one_or_none()
    if res:
        task_id = res.task_id
    tasks = session.query(AgentTaskMulti).filter(AgentTaskMulti.task_id==task_id).order_by(asc(AgentTaskMulti.create_time)).all()
    #
    # for task in tasks:
    #     print(f"ID: {task.id}, content: {task.content}")
    session.close()

    return  tasks

def update_AgentTaskMulti(id, **kwargs):
    session = Session()
    task = session.query(AgentTaskMulti).filter_by(id=id).first()
    if task:
        for key, value in kwargs.items():
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


    islimittotalmessage =  Column(Boolean, default=True, doc="")
    islimitmessagepp =  Column(Boolean, default=True, doc="")
    totalmessages =  Column(Integer, doc="")
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

def add_MutiAgentCfg(group_id,name,memo,agents,agentcommander,specialization,plugins,kms,prompt,islimittotalmessage,islimitmessagepp,totalmessages,ppmessages,readfile,writefile,deletefile,execfile,autorunrounds):
    session = Session()
    mutiAgentCfg = MutiAgentCfg(group_id = group_id,name = name,memo = memo,agents = agents,agentcommander = agentcommander,specialization = specialization,plugins = plugins,kms = kms,prompt = prompt,islimittotalmessage = islimittotalmessage,islimitmessagepp = islimitmessagepp,totalmessages = totalmessages,ppmessages = ppmessages,readfile = readfile,writefile = writefile,deletefile = deletefile,execfile = execfile,autorunrounds = autorunrounds)
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
    city = Column(String(100), doc="城市")
    address = Column(String(200), doc="地址")
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
    agreeallfriendrequest = Column(Boolean, default=True, doc="同意所有联系人请求")

    position = Column(Integer,default=9999, doc="")
    is_show = Column(Boolean, default=True, doc="是否显示")
    is_delete = Column(Boolean, default=False, doc="软删除")
    create_time = Column(DateTime, default=datetime.now, doc="创建时间")

def add_AiChatCfg(user_id,account,password,nickname,sign,status,humantakeover,name,borndate,gender,area,city,address,mail,imaccount,phone,organization,title,orgposition,memo,serveraddress,port,ssl,resource,proxyused,proxyaddress,proxyport,proxyssl,savepasswordlocal,autoconnect,sendreceipt,sendreadflag,sendchatstatus,sendgroupchatstatus,agreeallfriendrequest):
    session = Session()
    aichatCfg = AiChatCfg(user_id = user_id,account = account,password = password,nickname = nickname,sign = sign,status = status,humantakeover = humantakeover,name = name,borndate = borndate,gender = gender,area = area,city = city,address = address,mail = mail,imaccount = imaccount,phone = phone,organization = organization,title = title,orgposition = orgposition,memo = memo,serveraddress = serveraddress,port = port,ssl = ssl,resource = resource,proxyused = proxyused,proxyaddress = proxyaddress,proxyport = proxyport,proxyssl = proxyssl,savepasswordlocal = savepasswordlocal,autoconnect = autoconnect,sendreceipt = sendreceipt,sendreadflag = sendreadflag,sendchatstatus = sendchatstatus,sendgroupchatstatus = sendgroupchatstatus,agreeallfriendrequest = agreeallfriendrequest)
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
    return (record_id)



def query_AiChatCfg_All(**kwargs):
    session = Session()
    records = session.query(AiChatCfg).filter_by(**kwargs).order_by(asc(AiChatCfg.position)).all()
    # for record in records:
    #     print(f"ID: {record.id}, Name: {record.nickname}, Memo: {record.memo}")
    session.close()
    return records

def query_AiChatCfg(**kwargs):
    session = Session()
    record = session.query(AiChatCfg).filter_by(**kwargs).first()
    session.close()
    return record

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


def add_HumanChatCfg(user_id, account, password, nickname, sign, status, name, borndate, gender, area, city, address, mail, imaccount, phone, organization, title, orgposition, memo, serveraddress, port, ssl, resource, proxyused, proxyaddress, proxyport, proxyssl,  savepasswordlocal, autoconnect, sendreceipt, sendreadflag, sendchatstatus, sendgroupchatstatus,autoaway,autona, agreeallfriendrequest):
    session = Session()
    humanChatCfg = HumanChatCfg(user_id=user_id, account=account, password=password, nickname=nickname, sign=sign, status=status, name=name, borndate=borndate, gender=gender, area=area, city=city, address=address, mail=mail, imaccount=imaccount, phone=phone, organization=organization, title=title, orgposition=orgposition, memo=memo, serveraddress=serveraddress, port=port, ssl=ssl, resource=resource, proxyused=proxyused, proxyaddress=proxyaddress, proxyport=proxyport, proxyssl=proxyssl, savepasswordlocal=savepasswordlocal, autoconnect=autoconnect, sendreceipt=sendreceipt, sendreadflag=sendreadflag, sendchatstatus=sendchatstatus, sendgroupchatstatus=sendgroupchatstatus,autoaway=autoaway,autona=autona, agreeallfriendrequest=agreeallfriendrequest)
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
    kmtype = Column(String(100), doc="")
    vectortype = Column(String(150), doc="")
    embeddingmodel  = Column(String(150), doc="")

    textblocklength =  Column(Integer, doc="单段文本最大长度")
    overlaplength = Column(Integer, doc="相邻文本重合长度")
    titleaugment = Column(Boolean, default=True, doc="是否开启中文标题加强")

    position = Column(Integer, default=9999, doc="")
    is_show = Column(Boolean, default=True, doc="是否显示")

    is_delete = Column(Boolean, default=False, doc="软删除")
    create_time = Column(DateTime, default=datetime.now, doc="创建时间")

def add_KMCfg(km_id,name,memo,label ,kmpath,vectorization,kmtype,vectortype,embeddingmodel,textblocklength,overlaplength,titleaugment):
    session = Session()
    kmCfg = KMCfg(km_id=km_id,name=name,memo=memo,label=label,kmpath=kmpath,kmtype=kmtype,vectorization=vectorization,vectortype=vectortype,embeddingmodel=embeddingmodel,textblocklength=textblocklength,overlaplength=overlaplength,titleaugment=titleaugment)
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

    textblocklength =  Column(Integer, default=1, doc="单段文本最大长度")
    overlaplength = Column(Integer, default=1, doc="相邻文本重合长度")

    is_delete = Column(Boolean, default=False, doc="软删除")
    create_time = Column(DateTime, default=datetime.now, doc="创建时间")

def add_KMData(km_id,filename,filenum,textblocklength,overlaplength):
    session = Session()
    kmData = KMData(km_id=km_id,filename=filename,filenum=filenum,textblocklength=textblocklength,overlaplength=overlaplength)
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
    instruction = Column(Text, doc="调用该插件的指令")


    runtime_main = Column(String(200), doc="运行时主程序")
    runtime_test = Column(String(200), doc="运行时测试程序")
    description = Column(Text, doc="功能描述")

    plugin_directory = Column(String(100), doc="插件目录")
    plugin_type = Column(String(100), doc="插件类型")
    plugin_api_type = Column(String(100), doc="插件api类型")
    plugin_event = Column(String(100), doc="插件事件")
    plugin_event_description = Column(Text, doc="插件事件描述")
    detail = Column(Text, doc="详细信息")


    creator = Column(String(100), doc="创建人")


    is_delete = Column(Boolean, default=False, doc="软删除")
    create_time = Column(DateTime, default=datetime.now, doc="创建时间")

def add_PluginMng(plugin_id,company,company_abbr,name,version,alias_name,filename,runtime_main,runtime_test,description,plugin_directory,plugin_type,plugin_api_type,plugin_event,plugin_event_description,detail,creator,run_mode="",run_scope="",instruction=""):
    session = Session()
    pluginMng = PluginMng(plugin_id=plugin_id,company=company,company_abbr=company_abbr,name=name,version=version,alias_name=alias_name,filename=filename,run_mode=run_mode,run_scope=run_scope,instruction=instruction,runtime_main=runtime_main,runtime_test=runtime_test,description=description,plugin_directory=plugin_directory,plugin_type=plugin_type,plugin_api_type=plugin_api_type,plugin_event=plugin_event,plugin_event_description=plugin_event_description,detail=detail,creator=creator)
    session.add(pluginMng)
    session.commit()
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
        plugin_types=["Tool_Headless","Tool_Gui"]

        # 如果提供了文件名列表，添加过滤条件
        if plugin_types:
            query = query.filter(or_(PluginMng.plugin_type == plugin_type for plugin_type in plugin_types))

        # 添加其他过滤条件
        if kwargs:
            query = query.filter_by(**kwargs)

        records = query.all()  # 执行查询并获取所有记录
    finally:
        session.close()  # 确保会话被关闭

    return records  # 返回查询结果

def query_PluginMng_All(**kwargs):
    session = Session()
    records = session.query(PluginMng).filter_by(**kwargs).all()
    # for record in records:
    #     print(f"ID: {record.id}, filename: {record.filename}, plugin_id: {record.plugin_id}")
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

def delete_PluginMng(id):
    session = Session()
    record = session.query(PluginMng).filter_by(id=id).first()
    if record:
        session.delete(record)
        session.commit()
    session.close()


# functionmng
# FunctionMng
class FunctionMng(Base):
    __tablename__ = 'function_mng'

    # 主键
    id = Column(Integer, primary_key=True, autoincrement=True)

    # 表字段
    function_id = Column(String(100), doc="功能ID")
    name = Column(String(100), doc="名称")
    file_path = Column(String(200), doc="文件路径")
    requirement = Column(Text, doc="需求")
    parameter = Column(Text, doc="参数")
    description = Column(String(100), doc="简介")
    detail = Column(Text, doc="描述")
    function_type = Column(String(100), doc="功能类型")
    function_event = Column(String(100), doc="功能事件")
    creator = Column(String(100), doc="创建人")
    is_delete = Column(Boolean, default=False, doc="软删除")
    create_time = Column(DateTime, default=datetime.now, doc="创建时间")

def add_function_mng(function_id,  name, file_path, requirement, parameter,
                     description,detail, function_type, function_event,  creator):
    """添加功能管理记录"""
    session = Session()
    new_function = FunctionMng(
        function_id=function_id,  name=name, file_path=file_path,
        requirement=requirement, parameter=parameter, description=description,detail=detail,
        function_type=function_type, function_event=function_event,creator=creator
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


def delete_function_mng(**kwargs):
    """删除功能管理记录"""
    session = Session()
    record = session.query(FunctionMng).filter_by(**kwargs).first()  # 查询记录
    if record:
        session.delete(record)  # 删除记录
        session.commit()  # 提交事务
    session.close()  # 关闭会话

#workflow
# 定义 Workflow 数据模型
class WorkflowMng(Base):
    __tablename__ = 'workflow_mng'

    # 定义表的字段
    id = Column(Integer, primary_key=True, autoincrement=True, doc="主键ID")
    workflow_id = Column(String(100), doc="工作流ID")
    title = Column(String(100), doc="标题")
    description = Column(Text, doc="描述")
    workflow_tags = Column(String(100), doc="工作流类型")
    workflow_event = Column(String(100), doc="工作流事件")
    detail = Column(Text, doc="详细信息")
    creator = Column(String(100), doc="创建人")
    is_delete = Column(Boolean, default=False, doc="软删除")
    create_time = Column(DateTime, default=datetime.now, doc="创建时间")


def add_workflow_mng(workflow_id, title, description, workflow_tags,
                      detail):
    """添加新的工作流管理记录"""
    session = Session()
    workflow_mng = WorkflowMng(
            workflow_id=workflow_id,
            title=title,
            description=description,
            workflow_tags=workflow_tags,
            detail=detail
        )
    # 添加并提交到数据库
    session.add(workflow_mng)
    session.flush()
    record_id = workflow_mng.id
    session.refresh(workflow_mng)
    session.commit()
    session.close()  # 关闭会话


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

def copy_workflow(workflow_id,new_workflow_id):
    """根据 workflow_id 拷贝工作流记录"""
    session = Session()
    try:
        # 查找指定的工作流记录
        original_record = session.query(WorkflowMng).filter_by(workflow_id=workflow_id).first()
        if original_record:
            # 创建新的工作流记录，拷贝字段
            new_workflow = WorkflowMng(
                workflow_id=new_workflow_id,  # 新工作流ID可根据需求修改
                title=original_record.title+"-Copy",
                description=original_record.description,
                workflow_tags=original_record.workflow_tags,
                workflow_event=original_record.workflow_event,
                detail=original_record.detail,
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

# NotesMng

class NoteMng(Base):
    __tablename__ = 'note_mng'

    # 主键
    id = Column(Integer, primary_key=True, autoincrement=True)

    # 表字段
    note_id = Column(String(100), doc="功能ID")
    title = Column(String(100), doc="名称")
    file_name  = Column(String(200), doc="文件名称")
    content = Column(Text, doc="内容")
    km_id = Column(String(100), doc="功能ID")
    tag_1 =  Column(String(100), doc="tag")
    tag_2 =  Column(String(100), doc="tag")
    tag_3 = Column(String(100), doc="tag")
    creator = Column(String(100), doc="创建人")
    is_delete = Column(Boolean, default=False, doc="软删除")
    create_time = Column(DateTime, default=datetime.now, doc="创建时间")

def add_note_mng(note_id,  title,file_name, content,km_id, tag_1, tag_2,
                     tag_3):
    """添加功能管理记录"""
    session = Session()
    new_note = NoteMng(
        note_id=note_id,  title=title,file_name=file_name, content=content,km_id=km_id,
        tag_1=tag_1, tag_2=tag_2, tag_3=tag_3
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




def query_note_mng_all(count,**kwargs):
    """查询所有功能管理记录"""
    session = Session()
    if count==-1:
        records = session.query(NoteMng).filter_by(**kwargs).order_by(desc(NoteMng.create_time)).all()  # 查询所有符合条件的记录
    else:
        records = session.query(NoteMng).filter_by(**kwargs).order_by(desc(NoteMng.create_time)).limit(count).all()  # 查询所有符合条件的记录
    session.close()  # 关闭会话
    return records


def query_note_mng(**kwargs):
    """查询单个功能管理记录"""
    session = Session()
    record = session.query(NoteMng).filter_by(**kwargs).first()  # 查询第一个符合条件的记录
    session.close()  # 关闭会话
    return record


def update_note_mng(note_id, **kwargs):
    """更新功能管理记录"""
    session = Session()
    record = session.query(NoteMng).filter_by(note_id=note_id).first()  # 查询记录
    if record:
        for key, value in kwargs.items():
            setattr(record, key, value)  # 更新字段
        session.commit()  # 提交事务
    session.close()  # 关闭会话

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


def query_Note_Search_Content(**kwargs):
    session = Session()


    # 搜索关键词
    title_keyword = kwargs.get('title', None)
    content_keyword = kwargs.get('content', None)

    # 构建初始查询
    query = session.query(NoteMng)



    # 添加搜索条件
    search_terms = []
    if title_keyword:
        search_terms.append(NoteMng.title.contains(title_keyword))
    if content_keyword:
        search_terms.append(NoteMng.content.contains(content_keyword))


    if search_terms:
        query = query.filter(or_(*search_terms))

    # 获取结果
    records = query.order_by(desc(NoteMng.create_time)).limit(50000).all()

    session.close()
    return records


# System Cfg
class SystemCfg(Base):
    __tablename__ = 'system_cfg'
    id = Column(Integer, primary_key=True, autoincrement=True)

    autorun = Column(Boolean, default=False, doc="开机自动运行")
    showtaskbar = Column(Boolean, default=False, doc="在任务栏显示")
    updateinfo =  Column(Boolean, default=False, doc="有更新时提醒升级")
    closebuttontype = Column(String(100), doc="点击关闭按钮:隐藏窗口，关闭程序")
    style = Column(String(500), doc="风格：亮色，暗色")

    showinfo =  Column(Boolean, default=True, doc="显示通知")
    showinfoicon =  Column(Boolean, default=True, doc="通知区域显示图标")
    infosound = Column(Boolean, default=True, doc="通知时播放声音")

    is_delete = Column(Boolean, default=False, doc="软删除")
    create_time = Column(DateTime, default=datetime.now, doc="创建时间")

def add_SystemCfg(autorun,showtaskbar,updateinfo,closebuttontype,style,showinfo,showinfoicon,infosound):
    session = Session()
    systemCfg = SystemCfg(autorun=autorun,showtaskbar=showtaskbar,updateinfo=updateinfo,closebuttontype=closebuttontype,style=style,showinfo=showinfo,showinfoicon=showinfoicon,infosound=infosound)
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

def add_LogsMng(logs_id,content,type):
    session = Session()
    logsMng = LogsMng(logs_id=logs_id,content=content,type=type)
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

def update_config_lang(lang,**kwargs):
    session = Session()
    record = session.query(SysConfig).filter_by(**kwargs).first()
    record.lang=lang
    session.commit()
    session.close()
    return lang

# Prompt
class Prompt(Base):
    __tablename__ = 'prompts'
    id = Column(Integer, primary_key=True, autoincrement=True)
    title = Column(String)  # 新增的 title 字段
    content = Column(String)
    question = Column(String)
    tags = Column(String)  # Storing tags as comma-separated values

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
    return prompt.content if prompt else None


# 定义 KeyValue 表
class KeyValue(Base):
    __tablename__ = 'key_value'

    id = Column(Integer, primary_key=True, autoincrement=True)
    key = Column(String, nullable=False)
    value = Column(String, nullable=False)


# 增加一条记录
def add_key_value(key: str, value: str):
    """增加一条 key-value 记录"""
    new_entry = KeyValue(key=key, value=value)
    session.add(new_entry)
    session.commit()


# 查询记录
def get_key_value(key: str):
    """根据 key 查询 value"""
    result = session.query(KeyValue).filter_by(key=key).first()
    return result.value if result else None

# 查询多条记录
def get_all_key_values() -> list:
    """获取所有 key-value 记录"""
    records = session.query(KeyValue).all()
    return records

# 模糊查询
def search_key_values(search_text: str) -> list:
    """根据传入的文本对 key 进行模糊搜索"""
    records = session.query(KeyValue).filter(KeyValue.key.like(f'%{search_text}%')).all()
    return records

# 更新记录
def update_key_value(key: str, new_value: str):
    """根据 key 更新对应的 value"""
    entry = session.query(KeyValue).filter_by(key=key).first()
    if entry:
        entry.value = new_value
        session.commit()


# 删除记录
def delete_key_value(key: str):
    """根据 key 删除对应的记录"""
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
    agent=query_AgentCfg(id=1)
    # print(f"ID: {agent.id}, Name: {agent.name}, Memo: {agent.memo}")


    # update_AgentCfg(1,user_id="0012",name="i am chen12")
