from sqlalchemy.orm import Session
from crud.base import CRUDBase
from models.model import PrivateModel
from models.task_model import TaskTrainRecord
from models.dataset_model import Dataset
from schemas.private_model import PrivateModelCreate, PrivateModelUpdate
from sqlalchemy import or_
from fastapi.exceptions import HTTPException
from core.utils import _skip
from core.utils import ResponseData


class CRUDItem(CRUDBase[PrivateModel, PrivateModelCreate, PrivateModelUpdate]):

    def get_private_model(self, db: Session, id, user_id):
        instance = db.query(self.model).filter(self.model.id == id, self.model.user_id == user_id).first()
        if not instance:
            raise HTTPException(status_code=404, detail="model不存在")
        task_data = db.query(TaskTrainRecord).filter(TaskTrainRecord.id == instance.task_id,
                                                     TaskTrainRecord.user_id == user_id).first()
        if not task_data:
            raise HTTPException(status_code=404, detail="task不存在")
        dataset = db.query(Dataset).filter(Dataset.id == task_data.dataset, Dataset.user_id == user_id).first()
        if not dataset:
            raise HTTPException(status_code=404, detail="dataset不存在")
        return {
            "id": instance.id,
            "model_name": instance.model_name,
            "task_name": instance.task_name,
            "dataset_name": dataset.name,
            "capacity": instance.capacity,
            "create_time": instance.create_time,
            "advanced_parameter": task_data.advanced_parameter
        }

    def remove_private_model(self, db: Session, id: int, user_id):

        instance = db.query(self.model).filter(self.model.id == id, self.model.user_id == user_id).one_or_none()
        if not instance:
            raise HTTPException(status_code=404, detail="记录不存在")
        from db.write_queue import db_write
        _model = self.model
        _inst_id = instance.id
        def _do(session):
            rec = session.query(_model).filter(_model.id == _inst_id).first()
            if rec:
                session.delete(rec)
            return rec
        return db_write(_do, description="crud_remove_private_model")
        # 构建分页查询函数

    def list_params(self, db: Session,
                    skip: int = 0,
                    limit: int = 10,
                    **kwargs):
        # 构建查询基础
        query = db.query(self.model)

        # 动态构建查询条件
        filters = []
        filter_user = kwargs.pop("user_id")
        for field, value in kwargs.items():
            if value is not None:
                filters.append(getattr(self.model, field).like(f"%{value}%"))
        if filter_user:
            query = query.filter(self.model.user_id == filter_user)
        if filters:
            query = query.filter(*filters)
        total_data = query.count()
        # 执行查询并返回结果
        result = query.offset(_skip(skip, limit)).limit(limit).all()
        return ResponseData(page=skip,
                            size=limit,
                            total_data=total_data,
                            count=total_data,
                            data=result)


CrudPrivateModel = CRUDItem(PrivateModel)
