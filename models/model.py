from db.base_class import Base
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Boolean, Text, Float
from sqlalchemy.orm import relationship
from utils.enum_config import ModelType
from datetime import datetime
from utils.enum_config import PromptType


class Model(Base):
    __tablename__ = 'model'
    id = Column(Integer, primary_key=True, autoincrement=True)
    model_name = Column(String(45), doc="模型名称")
    langchain_name = Column(String(45), doc="载入langchain模型名称")
    description = Column(String(200), doc="描述")
    label = Column(String(200), doc="标签")
    introduction = Column(String(200), doc="介绍")
    company = Column(String(100), doc="公司名称")
    page_view = Column(Integer, default=0, doc="浏览量")
    type = Column(Integer, default=ModelType.public_model.value, doc="模型类型:公共模型(0)/基础模型(1)/应用案例(2)")
    version_category = Column(String(45), doc="版本类别")
    industry = Column(String(45), doc="行业")
    filename = Column(String(40), doc="图片名")
    create_time = Column(DateTime, default=datetime.now, doc="创建时间")
    update_time = Column(DateTime, onupdate=datetime.now, doc="更新时间")
    release = Column(Boolean, default=False, doc="是否发版")
    is_langchain = Column(Boolean, default=False, doc="是否支持langchain")
    model_experience = relationship("ModelExperience", back_populates="model")
    langchain_parameter = relationship("LangchainParameter", back_populates="model")


class PrivateModel(Base):
    __tablename__ = 'private_model'
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(String(200), doc="用户id")
    model_name = Column(String(45), doc="模型名称")
    file_path = Column(String(100), doc="文件路径")
    task_id = Column(Integer)
    task_name = Column(String(45), doc="任务名称")
    capacity = Column(Integer, doc="容量")
    create_time = Column(DateTime, default=datetime.now, doc="创建时间")
    update_time = Column(DateTime, default=datetime.now, onupdate=datetime.now, doc="更新时间")
    result_id = Column(Integer, ForeignKey('model_train_result.id'))
    model_train_result = relationship("ModelTrainResult", back_populates="private_model")


class ModelExperience(Base):
    __tablename__ = 'model_experience'
    id = Column(Integer, primary_key=True, autoincrement=True)
    problem = Column(Text, doc="问题")
    answer = Column(Text, doc="回答")
    create_time = Column(DateTime, default=datetime.now, doc="创建时间")
    user_id = Column(String(200), doc="用户id")
    uuid = Column(String(500), index=True, doc="uuid,用于进行用户对话分组")
    label = Column(String(500), default=None, doc="标签")
    is_delete = Column(Boolean, default=False, doc="软删除")
    exceeds_limit = Column(Boolean, default=False, doc="是否超出限制")
    task_id = Column(Integer, doc="任务id")
    model_id = Column(Integer, ForeignKey('model.id'))
    model = relationship("Model", back_populates="model_experience")


class Role(Base):
    __tablename__ = 'role'
    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(200), doc="职位名称")
    create_time = Column(DateTime, default=datetime.now, doc="创建时间")
    update_time = Column(DateTime, default=datetime.now, onupdate=datetime.now, doc="更新时间")
    prompt = relationship("Prompt", back_populates="role")


class Prompt(Base):
    __tablename__ = 'prompt'
    id = Column(Integer, primary_key=True, autoincrement=True)
    type = Column(String(50), index=True, doc="提示词类型")
    title = Column(String(50), doc="标题")
    problem = Column(Text, doc="问题")
    answer = Column(Text, doc="回答")
    create_time = Column(DateTime, default=datetime.now, doc="创建时间")
    update_time = Column(DateTime, default=datetime.now, onupdate=datetime.now, doc="更新时间")
    role_id = Column(Integer, ForeignKey('role.id'))
    role = relationship("Role", back_populates="prompt")


class LangchainParameter(Base):
    __tablename__ = 'langchain_parameter'
    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(45), doc='参数名称')
    introduce = Column(Text, doc='参数项说明')
    max_value = Column(Float, doc='最大值')
    min_value = Column(Float, doc='最小值')
    default_value = Column(Float, doc="默认值")
    model_id = Column(Integer, ForeignKey('model.id'))
    model = relationship("Model", back_populates="langchain_parameter")
