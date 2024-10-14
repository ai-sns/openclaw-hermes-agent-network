from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime

from db.base_class import Base


class TaskTrainRecord(Base):
    __tablename__ = 'task_train_record'

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(45), nullable=False)
    model = Column(String(45), nullable=False)
    dataset = Column(Integer, comment='数据集id')
    introduce = Column(Text, comment='介绍')
    train_start_time = Column(DateTime, comment='训练开始时间')
    train_end_time = Column(DateTime, comment='训练结束时间')
    state = Column(String, name='state', comment='训练状态，running，complete')
    user_id = Column(String(45), comment='用户id', nullable=False)
    advanced_parameter = Column(Text, comment='高阶训练参数，json格式')
    log_file_path = Column(Text, comment='日志文件位置')
    report_file_path = Column(Text, comment='报告文件位置')
    model_file_path = Column(Text, comment='模型文件位置')
    experience_address = Column(Text, comment='体验地址')
    progress = Column(Integer, comment='进度')
    model_train_result = relationship("ModelTrainResult", back_populates="task_train_record")

    def __init__(self, name, model, dataset, introduce, train_start_time, train_end_time, state, user_id,
                 advanced_parameter, log_file_path, report_file_path, model_file_path, experience_address, progress):
        self.name = name
        self.model = model
        self.dataset = dataset
        self.introduce = introduce
        self.train_start_time = train_start_time
        self.train_end_time = train_end_time
        self.state = state
        self.user_id = user_id
        self.advanced_parameter = advanced_parameter
        self.log_file_path = log_file_path
        self.report_file_path = report_file_path
        self.model_file_path = model_file_path
        self.experience_address = experience_address
        self.progress = progress


class ArithmeticParameter(Base):
    __tablename__ = 'arithmetic_parameter'

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(45), nullable=False)
    arithmetic = Column(String(45))
    policy = Column(String(45), comment='微调策略')

    def __init__(self, name, arithmetic, policy):
        self.name = name
        self.arithmetic = arithmetic
        self.policy = policy


class ArithmeticParameterItem(Base):
    __tablename__ = 'arithmetic_parameter_item'

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(45), nullable=False, comment='参数名称')
    p_type = Column(String(45), comment='参数类型')
    introduce = Column(Text, comment='参数项说明')
    parameter_id = Column(Integer, comment='参数集id')
    sort = Column(Integer, comment='排序值')

    def __init__(self, name, p_type, introduce, parameter_id, sort):
        self.name = name
        self.p_type = p_type
        self.introduce = introduce
        self.parameter_id = parameter_id
        self.sort = sort


class ModelTrainResult(Base):
    __tablename__ = 'model_train_result'
    id = Column(Integer, primary_key=True, autoincrement=True)
    model_version = Column(String(60), doc="模型版本")
    filename = Column(String(60), doc="模型文件名称")
    create_time = Column(DateTime, default=datetime.now, doc="创建时间")
    status = Column(Integer, doc="状态:已保存(0)/已失效(1)")
    user_id = Column(String(200), doc="用户id")
    task_id = Column(Integer, ForeignKey("task_train_record.id"))
    task_train_record = relationship("TaskTrainRecord", back_populates="model_train_result")
    private_model = relationship("PrivateModel", uselist=False, back_populates="model_train_result")


