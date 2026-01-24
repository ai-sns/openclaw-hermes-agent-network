"""
异步数据库操作函数
"""
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, delete
from db.database import AsyncSessionLocal, AiChatCfg, Tool
import logging

logger = logging.getLogger(__name__)


async def query_AiChatCfg_map():
    """异步查询 AiChatCfg 记录"""
    async with AsyncSessionLocal() as session:
        stmt = select(AiChatCfg)
        result = await session.execute(stmt)
        record = result.scalar_one_or_none()
        return record


async def query_AiChatCfg_map_setting(**kwargs):
    """异步查询 AiChatCfg 地图设置"""
    async with AsyncSessionLocal() as session:
        query = select(AiChatCfg)
        if kwargs:
            query = query.filter_by(**kwargs)
        result = await session.execute(query)
        record = result.scalar_one_or_none()

        if record:
            fields = {
                "nick_name": record.nickname,
                "account": record.account,
                "profile": record.sign,
                "profession": record.profession,
                "nationid": record.nationid,
                "nationpassword": record.nationpassword,
                "sns_url": record.sns_url,
                "status": record.status,
                "avatar": record.avatar,
                "avatar3d": record.avatar3d,
                "house3d": record.house3d,
                "map_type": record.map_type,
                "map_api_key": record.map_api_key,
                "map_id": record.map_id,
                "current_position": record.current_position,
                "home_position": record.home_position,
                "positionx": record.positionx,
                "positiony": record.positiony,
                "positionz": record.positionz,
                "route_start": record.route_start,
                "route_end": record.route_end,
                "route_status": record.route_status,
                "route_current_position": record.route_current_position,
                "route": record.route
            }
            return fields
        return None


async def update_AiChatCfg_map(**kwargs):
    """异步更新 AiChatCfg 记录"""
    async with AsyncSessionLocal() as session:
        stmt = select(AiChatCfg)
        result = await session.execute(stmt)
        record = result.scalar_one_or_none()

        if record:
            for key, value in kwargs.items():
                setattr(record, key, value)
            await session.commit()

        return record


async def query_tool_list():
    """异步查询工具列表"""
    async with AsyncSessionLocal() as session:
        stmt = select(Tool)
        result = await session.execute(stmt)
        records = result.scalars().all()
        return records


async def query_single_tool(tool_id):
    """异步查询单个工具"""
    async with AsyncSessionLocal() as session:
        stmt = select(Tool).where(Tool.id == tool_id)
        result = await session.execute(stmt)
        record = result.scalar_one_or_none()
        return record


async def update_map_task(task_id, **kwargs):
    """异步更新地图任务"""
    from db.database import MapTask
    async with AsyncSessionLocal() as session:
        stmt = select(MapTask).where(MapTask.id == task_id)
        result = await session.execute(stmt)
        task = result.scalar_one_or_none()

        if task:
            for key, value in kwargs.items():
                setattr(task, key, value)
            await session.commit()

        return task


async def add_map_visit(**kwargs):
    """异步添加地图访问记录"""
    from db.database import MapVisit
    async with AsyncSessionLocal() as session:
        visit = MapVisit(**kwargs)
        session.add(visit)
        await session.commit()
        await session.refresh(visit)
        return visit


async def add_map_trade(**kwargs):
    """异步添加地图交易记录"""
    from db.database import MapTrade
    async with AsyncSessionLocal() as session:
        trade = MapTrade(**kwargs)
        session.add(trade)
        await session.commit()
        await session.refresh(trade)
        return trade


async def add_map_tool(**kwargs):
    """异步添加地图工具记录"""
    from db.database import MapTool
    async with AsyncSessionLocal() as session:
        tool = MapTool(**kwargs)
        session.add(tool)
        await session.commit()
        await session.refresh(tool)
        return tool


async def query_single_map_trade(trade_id):
    """异步查询单个地图交易"""
    from db.database import MapTrade
    async with AsyncSessionLocal() as session:
        stmt = select(MapTrade).where(MapTrade.trade_id == trade_id)
        result = await session.execute(stmt)
        record = result.scalar_one_or_none()
        return record


async def add_AIChatMessages(**kwargs):
    """异步添加聊天消息"""
    async with AsyncSessionLocal() as session:
        message = AIChatMessages(**kwargs)
        session.add(message)
        await session.commit()
        await session.refresh(message)
        return message


async def query_mcp_mng(name=None):
    """异步查询MCP管理"""
    from db.database import McpMng
    async with AsyncSessionLocal() as session:
        stmt = select(McpMng)
        if name:
            stmt = stmt.where(McpMng.name == name)
        result = await session.execute(stmt)
        records = result.scalars().all()
        return records


async def add_mcp_mng(**kwargs):
    """异步添加MCP管理"""
    from db.database import McpMng
    async with AsyncSessionLocal() as session:
        mcp = McpMng(**kwargs)
        session.add(mcp)
        await session.commit()
        await session.refresh(mcp)
        return mcp


async def delete_map_preset_msg(msg_id):
    """异步删除地图预设消息"""
    from db.database import MapPresetMsg
    async with AsyncSessionLocal() as session:
        stmt = delete(MapPresetMsg).where(MapPresetMsg.id == msg_id)
        result = await session.execute(stmt)
        if result.rowcount > 0:
            await session.commit()


async def query_map_preset_msg_all():
    """异步查询所有地图预设消息"""
    from db.database import MapPresetMsg
    async with AsyncSessionLocal() as session:
        stmt = select(MapPresetMsg)
        result = await session.execute(stmt)
        records = result.scalars().all()
        return records


async def add_map_preset_msg(**kwargs):
    """异步添加地图预设消息"""
    from db.database import MapPresetMsg
    async with AsyncSessionLocal() as session:
        msg = MapPresetMsg(**kwargs)
        session.add(msg)
        await session.commit()
        await session.refresh(msg)
        return msg


async def update_AiChatCfg_by_user_id(user_id, **kwargs):
    """异步根据用户ID更新AiChatCfg"""
    async with AsyncSessionLocal() as session:
        stmt = select(AiChatCfg).where(AiChatCfg.user_id == user_id)
        result = await session.execute(stmt)
        record = result.scalar_one_or_none()

        if record:
            for key, value in kwargs.items():
                setattr(record, key, value)
            await session.commit()

        return record


async def add_function_mng(**kwargs):
    """异步添加函数管理"""
    from db.database import FunctionMng
    async with AsyncSessionLocal() as session:
        func = FunctionMng(**kwargs)
        session.add(func)
        await session.commit()
        await session.refresh(func)
        return func


async def query_function_mng():
    """异步查询函数管理"""
    from db.database import FunctionMng
    async with AsyncSessionLocal() as session:
        stmt = select(FunctionMng)
        result = await session.execute(stmt)
        records = result.scalars().all()
        return records


async def get_key_value(key):
    """异步获取键值"""
    from db.database import KeyValue
    async with AsyncSessionLocal() as session:
        stmt = select(KeyValue).where(KeyValue.key == key)
        result = await session.execute(stmt)
        record = result.scalar_one_or_none()
        return record.value if record else None
