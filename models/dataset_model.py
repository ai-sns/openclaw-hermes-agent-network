from db.base_class import Base
from sqlalchemy import Column, Integer, String, DateTime, Text, Boolean


class Dataset(Base):
    __tablename__ = 'dataset'

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(45), nullable=False)
    user_id = Column(String(45), nullable=False)
    introduce = Column(String)
    create_time = Column(DateTime)
    update_time = Column(DateTime)
    train_dataset = Column(Text)
    valid_dataset = Column(Text)
    test_dataset = Column(Text)
    train_dataset_size = Column(Integer, default=0)
    valid_dataset_size = Column(Integer, default=0)
    test_dataset_size = Column(Integer, default=0)
    is_delete = Column(Boolean, default=False, doc="软删除")

    def __init__(self, name, user_id,
                 introduce, create_time,
                 update_time, train_dataset,
                 valid_dataset, test_dataset,
                 train_dataset_size, valid_dataset_size,
                 test_dataset_size):
        self.name = name
        self.user_id = user_id
        self.introduce = introduce
        self.create_time = create_time
        self.update_time = update_time
        self.train_dataset = train_dataset
        self.valid_dataset = valid_dataset
        self.test_dataset = test_dataset
        self.train_dataset_size = train_dataset_size
        self.valid_dataset_size = valid_dataset_size
        self.test_dataset_size = test_dataset_size

    @property
    def size(self):
        return self.test_dataset_size + self.train_dataset_size + self.valid_dataset_size
