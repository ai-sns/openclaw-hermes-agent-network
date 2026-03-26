from sqlalchemy import distinct
from sqlalchemy.orm import Session
from sqlalchemy.orm import joinedload
from sqlalchemy import and_
from crud.base import CRUDBase
from models.model import Prompt, Role
from schemas.prompt import PromptCreate, PromptUpdate
from fastapi.exceptions import HTTPException


class CRUDItem(CRUDBase[Prompt, PromptCreate, PromptUpdate]):
    def create_role(self, db: Session, name, obj_in: PromptCreate):
        db_model = Role(name=name)
        if obj_in:
            for i in obj_in:
                db_model.prompt.append(self.model(**i.dict(exclude_unset=True)))
        from db.write_queue import db_write
        _obj_list = [i.dict(exclude_unset=True) for i in obj_in] if obj_in else []
        def _do(session):
            from models.model import Role as _Role
            r = _Role(name=name)
            for item_data in _obj_list:
                r.prompt.append(Prompt(**item_data))
            session.add(r)
            session.flush()
            session.refresh(r)
            return r
        return db_write(_do, description="crud_create_role")

    def list_role(self, db: Session):
        return db.query(Role).all()

    def list_prompt(self, db: Session, **kwargs):
        name = kwargs.get("name")
        type = kwargs.get("type")
        search = kwargs.get("search")
        query = db.query(Role).options(joinedload(Role.prompt))
        if name is not None and name != "":
            query = query.filter(Role.name == name)
        instance = query.all()
        for role in instance:
            if type is not None and type != "":
                prompt = [prompt for prompt in role.prompt if prompt.type == type]
                if search is not None and search != "":
                    prompt = [p for p in prompt if search in p.problem or search in str(p.answer)]
                role.prompt = prompt
            else:
                if search is not None and search != "":
                    prompt = [prompt for prompt in role.prompt if
                              search in prompt.problem or search in str(prompt.answer)]
                    role.prompt = prompt
        return instance

    def list_type(self, db: Session, name):
        if name is not None and name != "":
            instance = db.query(Role).options(joinedload(Role.prompt)).filter(Role.name == name).one_or_none()
            type = []
            if instance:
                instance = instance.prompt
                type = set([i.type for i in instance])
        else:
            prompt_type = db.query(self.model.type).distinct().all()
            type = [i[0] for i in prompt_type]

        return type


CrudPrompt = CRUDItem(Prompt)
