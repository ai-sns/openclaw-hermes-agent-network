from crud.base import CRUDBase
from models.config import ConfigItem
from schemas.config_item import ConfigItemCreate, ConfigItemUpdate
from sqlalchemy.orm import Session


class CRUDItem(CRUDBase[ConfigItem, ConfigItemCreate, ConfigItemUpdate]):
    def update_config_item(self, key, obj_in: ConfigItemUpdate, db: Session):
        data = obj_in.dict(exclude_unset=True)
        db.query(self.model).filter(self.model.key == key).update(data)
        db.commit()


CrudConfigItem = CRUDItem(ConfigItem)
