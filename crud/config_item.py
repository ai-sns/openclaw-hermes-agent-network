from crud.base import CRUDBase
from models.config import ConfigItem
from schemas.config_item import ConfigItemCreate, ConfigItemUpdate
from sqlalchemy.orm import Session


class CRUDItem(CRUDBase[ConfigItem, ConfigItemCreate, ConfigItemUpdate]):
    def update_config_item(self, key, obj_in: ConfigItemUpdate, db: Session):
        from db.write_queue import db_write
        data = obj_in.dict(exclude_unset=True)
        _model = self.model
        def _do(session):
            session.query(_model).filter(_model.key == key).update(data)
        db_write(_do, description="crud_update_config_item")


CrudConfigItem = CRUDItem(ConfigItem)
