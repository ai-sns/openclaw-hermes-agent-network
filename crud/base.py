from typing import Any, Dict, Generic, List, Optional, Type, TypeVar, Union

from fastapi.encoders import jsonable_encoder
from pydantic import BaseModel
from sqlalchemy.orm import Session
from sqlalchemy import and_
from sqlalchemy.orm import joinedload
from db.base_class import Base
from core.utils import _skip
from core.utils import ResponseData

ModelType = TypeVar("ModelType", bound=Base)
CreateSchemaType = TypeVar("CreateSchemaType", bound=BaseModel)
UpdateSchemaType = TypeVar("UpdateSchemaType", bound=BaseModel)


class CRUDBase(Generic[ModelType, CreateSchemaType, UpdateSchemaType]):
    def __init__(self, model: Type[ModelType]):
        """
        CRUD object with default methods to Create, Read, Update, Delete (CRUD).

        **Parameters**

        * `model`: A SQLAlchemy model class
        * `schema`: A Pydantic model (schema) class
        """
        self.model = model

    def get(self, db: Session, id: Any) -> Optional[ModelType]:
        return db.query(self.model).filter(self.model.id == id).first()

    def get_multi(
            self, db: Session, *, skip: int = 0, limit: int = 100
    ) -> List[ModelType]:
        return db.query(self.model).offset(skip).limit(limit).all()

    def create(self, db: Session, *, obj_in: CreateSchemaType) -> ModelType:
        from db.write_queue import db_write
        obj_in_data = jsonable_encoder(obj_in)
        _model = self.model
        def _do(session):
            db_obj = _model(**obj_in_data)
            session.add(db_obj)
            session.flush()
            session.refresh(db_obj)
            return db_obj
        return db_write(_do, description=f"crud_create_{self.model.__tablename__}")

    def update(
            self,
            db: Session,
            *,
            db_obj: ModelType,
            obj_in: Union[UpdateSchemaType, Dict[str, Any]]
    ) -> ModelType:
        obj_data = jsonable_encoder(db_obj)
        if isinstance(obj_in, dict):
            update_data = obj_in
        else:
            update_data = obj_in.dict(exclude_unset=True)
        from db.write_queue import db_write
        _model = self.model
        _obj_id = db_obj.id
        def _do(session):
            rec = session.query(_model).filter(_model.id == _obj_id).first()
            if rec:
                for field in obj_data:
                    if field in update_data:
                        setattr(rec, field, update_data[field])
                session.flush()
                session.refresh(rec)
            return rec
        return db_write(_do, description=f"crud_update_{self.model.__tablename__}")

    def remove(self, db: Session, id: int) -> ModelType:
        from db.write_queue import db_write
        _model = self.model
        def _do(session):
            obj = session.query(_model).get(id)
            if obj:
                session.delete(obj)
            return obj
        return db_write(_do, description=f"crud_remove_{self.model.__tablename__}")

    def create_multi(
            self, obj_in: CreateSchemaType, db: Session, **kwargs
    ):
        from db.write_queue import db_write
        _model = self.model
        _items = [data.dict(exclude_unset=True) for data in obj_in]
        def _do(session):
            for item_data in _items:
                db_model = _model(**item_data, **kwargs)
                session.add(db_model)
        db_write(_do, description=f"crud_create_multi_{self.model.__tablename__}")
        return obj_in

    def list_params(self, db: Session,
                    skip: int = 0,
                    limit: int = 10,
                    **kwargs):
        # 构建查询基础
        query = db.query(self.model)

        # 动态构建查询条件
        filters = []
        for field, value in kwargs.items():
            if value is not None:
                filters.append(getattr(self.model, field) == value)
        if filters:
            query = query.filter(and_(*filters))
        total_data = query.count()
        # 执行查询并返回结果
        result = query.offset(_skip(skip, limit)).limit(limit).all()
        return total_data, result
