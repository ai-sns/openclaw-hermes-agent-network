from fastapi.exceptions import HTTPException
from sqlalchemy.orm import Session
from crud.base import CRUDBase
from models.model import ModelExperience
from schemas.model_experience import ModelExperienceCreate, ModelExperienceUpdate
from datetime import datetime
from core import utils


class CRUDItem(CRUDBase[ModelExperience, ModelExperienceCreate, ModelExperienceUpdate]):
    def read_model_experience(self, db: Session, user_id, model_id, uuid, task_id):
        query = db.query(self.model). \
            order_by(self.model.create_time.asc()). \
            filter(self.model.user_id == user_id,
                   self.model.uuid == uuid,
                   self.model.is_delete == False)
        if model_id is not None and model_id != "":
            query = query.filter(self.model.model_id == model_id)
        elif task_id is not None and task_id != "":
            query = query.filter(self.model.task_id == task_id)
        instance = query.all()
        for item in instance:
            item.create_time = utils.strftime(item.create_time)
        # result = []
        # current_chunk = []
        # for item in instance:
        #     item.create_time = utils.strftime(item.create_time)
        #     current_chunk.append(item)
        #     if item.exceeds_limit:
        #         result.append(current_chunk)
        #         current_chunk = []
        # if current_chunk:
        #     result.append(current_chunk)
        return instance

    def save_conversation(
            self, obj_in: ModelExperienceCreate, db: Session, **kwargs
    ):
        data = obj_in.dict(exclude_unset=True)
        query = db.query(self.model).filter(self.model.uuid == kwargs.get("uuid"))
        uuid_list = query.all()
        db_model = self.model(**data, **kwargs)
        if len(uuid_list) < 1:
            problem = data.get("problem")[:15]
            db_model = self.model(**data, label=problem, **kwargs)
        db.add(db_model)
        instance = query.order_by(
            self.model.create_time).first()
        if instance and instance.label is None:
            instance.label = instance.problem
        db.commit()
        db.refresh(db_model)
        return db_model

    def get_history(self, db: Session, user_id, model_id, task_id):
        query = db.query(self.model).filter(self.model.user_id == user_id, self.model.is_delete == False)
        if model_id is not None and model_id != "":
            query = query.filter(self.model.model_id == model_id)
        elif task_id is not None and task_id != "":
            query = query.filter(self.model.task_id == task_id)
        instance = query.distinct(self.model.uuid).group_by(
            self.model.uuid).order_by(
            self.model.create_time).all()
        create_time_list = set([datetime.strftime(i.create_time, "%Y-%m-%d") for i in instance])
        history_data = []
        for time in create_time_list:
            data = [
                {
                    "id": i.id,
                    "label": i.label,
                    "uuid": i.uuid,
                    "create_time": i.create_time
                } for i in instance if datetime.strftime(i.create_time, "%Y-%m-%d") == time
            ]
            history_data.append({
                "create_time": time,
                "data": sorted(data, key=lambda x: x["create_time"], reverse=True)
            })
        return sorted(history_data, key=lambda x: x["create_time"], reverse=True)

    def delete_history(self, db: Session, user_id, model_id, uuid, task_id):
        query = db.query(self.model).filter(self.model.user_id == user_id,
                                            self.model.uuid == uuid)
        if model_id is not None and model_id != "":
            query = query.filter(self.model.model_id == model_id)
        elif task_id is not None and task_id != "":
            query = query.filter(self.model.task_id == task_id)
        instance = query.all()
        if instance:
            for i in instance:
                i.is_delete = True
            db.commit()

    def update_label(self, db: Session, id, user_id, label):
        instance = db.query(self.model).filter(self.model.id == id, self.model.user_id == user_id).one_or_none()
        if not instance:
            raise HTTPException(status_code=404, detail="该记录不存在")
        instance.label = label
        db.commit()
        db.refresh(instance)

        return {
            "id": instance.id,
            "uuid": instance.uuid,
            "label": instance.label,
            "create_time": instance.create_time
        }


CrudModelExperience = CRUDItem(ModelExperience)
