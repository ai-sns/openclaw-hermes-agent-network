from crud.base import CRUDBase
from models.model import LangchainParameter
from schemas.langchain import LangchainParameterCreate, LangchainParameterUpdate
from sqlalchemy.orm import Session


class CRUDItem(CRUDBase[LangchainParameter, LangchainParameterCreate, LangchainParameterUpdate]):
    def param_list(self, db: Session, model_id):
        query = db.query(self.model).filter(self.model.model_id == model_id).all()
        return query

    def update_param(self, id, obj_in: LangchainParameterUpdate, db: Session):
        data = obj_in.dict(exclude_unset=True)
        db.query(self.model).filter(self.model.id == id).update(data)
        db.commit()


CrudLangchainParameter = CRUDItem(LangchainParameter)
