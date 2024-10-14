from sqlalchemy.orm import Session
from crud.base import CRUDBase
from models.task_model import ModelTrainResult
from models.model import PrivateModel
from schemas.model_train_result import ModelTrainResultCreate, ModelTrainResultUpdate
from utils.enum_config import ModelSaveStatus
from api.service import model_train_result
from fastapi.exceptions import HTTPException


class CRUDItem(CRUDBase[ModelTrainResult, ModelTrainResultCreate, ModelTrainResultUpdate]):
    def save_model(self, db: Session, id):
        instance = db.query(self.model).filter(self.model.id == id).one_or_none()
        if not instance:
            raise HTTPException(status_code=404, detail="该记录不存在")
        size = model_train_result.save_model(task_id=instance.task_id, filename=instance.filename)
        private_model_dict = {
            "user_id": instance.user_id,
            "model_name": instance.model_version,
            "task_id": instance.task_id,
            "task_name": instance.task_train_record.name,
            "capacity": size
        }
        db_private_model = PrivateModel(**private_model_dict)
        instance.private_model = db_private_model
        instance.status = ModelSaveStatus.saved.value
        db.commit()
        db.refresh(instance)

        return instance


CrudModelTrainResult = CRUDItem(ModelTrainResult)
