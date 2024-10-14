from sqlalchemy.orm import Session
from crud.base import CRUDBase
from models.model import Model
from schemas.model import ModelCreate, ModelUpdate
from utils.enum_config import ModelType
from core.utils import _skip
from core.utils import ResponseData
from sqlalchemy import or_, and_
from core.conf import settings
from core.utils import strftime


class CRUDItem(CRUDBase[Model, ModelCreate, ModelUpdate]):

    def get_version_technology_industry(self, type, db: Session):
        instance = db.query(self.model).filter(self.model.type == type).all()
        vesion = []
        label = []
        industry = []
        for i in instance:
            if i.label and i.label != "":
                label.append(i.label)
            if type == ModelType.base_model.value and i.version_category and i.version_category != "":
                vesion.append(i.version_category)
            if type == ModelType.case.value and i.industry and i.industry != "":
                industry.append(i.industry)
        # 初始化一个空列表来存储分割后的内容
        technology = []
        # 遍历原始数据
        for item in label:
            # 使用逗号分割每个字符串，并去掉首尾的空格
            sub_items = [x.strip() for x in item.split(',')]
            # 将分割后的子项添加到结果列表，去重复
            for sub_item in sub_items:
                if sub_item not in technology:
                    technology.append(sub_item)
        return {
            "vesion": set(vesion),
            "technology": technology,
            "industry": set(industry),
        }

    def list_params(self, db: Session,
                    skip: int = 0,
                    limit: int = 10,
                    **kwargs):
        # 构建查询基础
        query = db.query(self.model)
        type = kwargs.pop("type")
        # 动态构建查询条件
        filters = []
        for field, value in kwargs.items():
            if value is not None and value != "":
                filters.append(getattr(self.model, field).like(f"%{value}%"))
        if filters:
            query = query.filter(and_(*filters))
        if type is not None:
            query = query.filter(self.model.type == type)
        total_data = query.count()
        # 执行查询并返回结果
        result = query.offset(_skip(skip, limit)).limit(limit).all()
        # pic_url = settings.PIC_URL
        for i in result:
            i.pic_url = f"/static/images/maas/{str(i.filename)}"
            i.create_time = strftime(i.create_time)
            i.update_time = strftime(i.update_time)
        return ResponseData(page=skip,
                            size=limit,
                            total_data=total_data,
                            count=total_data,
                            data=result)

    def update_model(self, id, type, obj_in: ModelUpdate, db: Session):
        if obj_in:
            data = obj_in.dict(exclude_unset=True)
            db.query(self.model).filter(self.model.id == id, self.model.type == type).update(data)
            db.commit()

    def delete_model(self, id, type, db: Session):
        db.query(self.model).filter(self.model.id == id, self.model.type == type).delete()
        db.commit()


CrudModel = CRUDItem(Model)
