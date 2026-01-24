# AI Social Engine Adapter 异步优化分析报告

## 概述

本文档详细分析了 `backend/modules/sns/ai_social_engine_adapter.py` 文件中需要异步优化的函数和调用。

---

## 一、核心问题分析

### 1. 数据库操作问题

**当前状态：**
- 使用同步的 SQLAlchemy Session（第5行：`from sqlalchemy.orm import Session`）
- 所有数据库查询都是同步的：`self.db.query()`
- 数据库操作阻塞事件循环

**问题位置：**

#### 1.1 `__init__` 方法中的同步查询（第72-74行）
```python
def __init__(self, db: Session):
    self.db = db
    # ...
    self.config = self.db.query(AiChatCfg).filter(
        AiChatCfg.is_delete == False
    ).first()
```

#### 1.2 `load_all_user_data()` 方法（第3534-3559行）
```python
def load_all_user_data(self):
    record = query_AiChatCfg_map()  # 同步数据库查询
    self.current_place = record.current_place
    # ... 更多属性赋值
```

#### 1.3 `save_all_user_data()` 方法（第3518-3532行）
```python
def save_all_user_data(self):
    data = {...}
    update_AiChatCfg_map(**data)  # 同步数据库更新
```

---

### 2. HTTP 请求问题

**当前状态：**
- 使用同步的 `requests` 库进行 HTTP 请求
- 阻塞网络 I/O 操作

**问题位置：**

#### 2.1 `http_request()` 方法（第3495-3516行）
```python
def http_request(self, url, params=None, method="GET", data=None):
    # ... 错误处理代码 ...
    if method == "GET":
        response = requests.get(url, params=params)
    elif method == "POST":
        response = requests.post(url, data=params)
    # ... 同步等待响应 ...
    return response.json()
```

#### 2.2 `call_service()` 方法（第2274-2291行）
```python
def call_service(self, url, method, **params):
    try:
        if method == "get":
            response = requests.get(url, params=params)
        elif method == "post":
            response = requests.post(url, data=params)
        # ... 同步等待响应 ...
        self.handle_service_called_result(response.json())
```

#### 2.3 API 调用方法（第1486-1552行）
```python
def get_service_list(self):
    url = "http://www.ai-sns.org/api/get_service_list/"
    params = {...}
    service_list = self.http_request(url, params)  # 同步 HTTP 请求
    return service_list

def get_place_list(self):
    url = "http://www.ai-sns.org/api/get_place_list/"
    params = {...}
    place_list = self.http_request(url, params)  # 同步 HTTP 请求
    return place_list

def get_people_list(self):
    url = "http://www.ai-sns.org/api/get_people_list/"
    params = {...}
    data = self.http_request(url, params)  # 同步 HTTP 请求
    return people_list
```

---

### 3. 异步函数调用问题

**当前状态：**
- 某些函数调用了异步函数但没有使用 `await`
- 使用 `asyncio.create_task()` 但没有等待结果

**问题位置：**

#### 3.1 `think()` 方法（第681-692行）
```python
def think(self, **kwargs):
    event = kwargs.get("event", "")
    current_chat_summary = kwargs.get("current_chat_summary", "")
    asyncio.create_task(self.ask_agent_to_update_task())  # 创建任务但不等待
    # ... 其他代码 ...
```

#### 3.2 `ask_agent_to_bargain_for_buyer()` 方法（第2202-2210行）
```python
def ask_agent_to_bargain_for_buyer(self, tool_list):
    # ... 准备数据 ...
    await self.ask_agent_and_get_instruction(question, role_prompt)  # 方法本身不是异步
```

**问题：** 该方法不是 `async def`，但内部使用了 `await`。这会导致语法错误。

---

### 4. Service 层异步不一致问题

**当前状态：**
- Router 层的端点都是异步的
- Service 层某些方法是异步的，某些是同步的
- 数据库操作都是同步的

**问题位置：**

#### 4.1 `service.py` 中的同步方法（被异步路由调用）

```python
# router.py 第26-29行
@router.get("/user-stats", response_model=UserStatsResponse)
async def get_user_stats(db: Session = Depends(get_db)):
    service = SNSService(db)
    return service.get_user_stats()  # service 方法是同步的

# service.py 第34-77行
def get_user_stats(self) -> dict:  # 同步方法
    config = self.db.query(AiChatCfg).filter(...).first()  # 同步查询
    # ...
```

#### 4.2 同步数据库操作被异步路由调用

```python
# service.py 第79-101行
def get_contacts(self) -> List[AIFriend]:  # 同步方法
    config = self.db.query(AiChatCfg).filter(...).first()  # 同步
    contacts = self.db.query(AIFriend).filter(...).all()  # 同步
    return contacts

# router.py 第32-36行
@router.get("/contacts", response_model=List[ContactResponse])
async def get_contacts(db: Session = Depends(get_db)):
    service = SNSService(db)
    return service.get_contacts()  # 同步方法在异步路由中调用
```

---

## 二、需要优化的函数清单

### 1. 必须改为 async 的函数（涉及 I/O 操作）

#### 1.1 数据库相关
- `__init__()` - 改为 `async def __init__()`
- `load_all_user_data()` → `async def load_all_user_data()`
- `save_all_user_data()` → `async def save_all_user_data()`

#### 1.2 HTTP 请求相关
- `http_request()` → `async def http_request()`
- `get_service_list()` → `async def get_service_list()`
- `get_skill_list()` → `async def get_skill_list()`
- `get_plugin_tool_list()` → `async def get_plugin_tool_list()`
- `get_tool_list()` → `async def get_tool_list()`
- `get_place_list()` → `async def get_place_list()`
- `get_people_list()` → `async def get_people_list()`
- `call_service()` → `async def call_service()`

#### 1.3 调用了上述函数的方法
- `get_tool_list_for_trade()` → `async def get_tool_list_for_trade()`
- `get_mcp_list_for_trade()` → `async def get_mcp_list_for_trade()`
- `compose_full_ask_content()` → 需要异步调用 get_xxx_list() 方法

#### 1.4 需要添加 await 的异步调用
- `think()` → `async def think()` 或添加 `await asyncio.create_task(...)`
- `ask_agent_to_bargain_for_buyer()` → `async def ask_agent_to_bargain_for_buyer()`
- `ask_agent_to_bargain_for_seller()` → `async def ask_agent_to_bargain_for_seller()`
- `ask_agent_to_use_service()` → `async def ask_agent_to_use_service()`
- `ask_agent_to_use_skill()` → `async def ask_agent_to_use_skill()`

---

### 2. Service 层需要异步化的方法

#### 2.1 `service.py` 中的同步方法
```python
# 改为异步：
async def get_user_stats(self) -> dict:
async def get_contacts(self) -> List[AIFriend]:
async def get_chat_history(self, friend_account: str, limit: int = 50) -> List[AIChatMessages]:
async def get_ai_chat_config(self, user_id: str = None):
async def update_ai_chat_config(self, user_id: str = None, data: dict = None):
async def get_social_roles(self):
async def get_user_info(self):
async def update_user_info(self, data: dict):
async def get_map_config(self):
async def update_map_config(self, data: dict):
```

---

## 三、优化建议

### 方案一：使用 AsyncSession（推荐）

#### 1. 安装依赖
```bash
pip install sqlalchemy[asyncio] aiosqlite httpx
```

#### 2. 修改数据库配置

**`backend/config/database.py`：**
```python
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.orm import declarative_base

# 使用异步引擎
SQLALCHEMY_DATABASE_URL = f"sqlite+aiosqlite:///{settings.database.full_path}"

engine = create_async_engine(
    SQLALCHEMY_DATABASE_URL,
    echo=settings.debug
)

AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False
)

async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with AsyncSessionLocal() as session:
        yield session
```

#### 3. 修改 `ai_social_engine_adapter.py`

**初始化改为异步：**
```python
class AISocialEngine:
    def __init__(self, db: AsyncSession):  # 使用 AsyncSession
        self.db = db
        # ... 其他初始化代码 ...

    async def async_init(self):  # 异步初始化方法
        """异步初始化，用于加载数据库数据"""
        from sqlalchemy import select
        stmt = select(AiChatCfg).where(AiChatCfg.is_delete == False)
        result = await self.db.execute(stmt)
        self.config = result.scalar_one_or_none()
        # ... 其他异步数据库操作 ...
```

**HTTP 请求改为异步：**
```python
import httpx

async def http_request(self, url, params=None, method="GET", data=None):
    """异步 HTTP 请求"""
    async with httpx.AsyncClient() as client:
        if method == "GET":
            response = await client.get(url, params=params)
        elif method == "POST":
            response = await client.post(url, data=params)
        elif method == "PUT":
            response = await client.put(url, data=params)
        # ... 其他方法 ...
        response.raise_for_status()
        return response.json()
```

**数据库查询改为异步：**
```python
async def load_all_user_data(self):
    """异步加载用户数据"""
    from sqlalchemy import select
    from db.DBFactory import query_AiChatCfg_map_async  # 需要创建异步版本

    record = await query_AiChatCfg_map_async()  # 异步查询
    self.current_place = record.current_place
    # ... 其他赋值 ...
```

#### 4. 修改 `service.py`

```python
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

class SNSService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_user_stats(self) -> dict:
        """异步获取用户统计"""
        stmt = select(AiChatCfg).where(AiChatCfg.is_delete == False)
        result = await self.db.execute(stmt)
        config = result.scalar_one_or_none()

        if not config:
            return {...}  # 默认值

        return {
            "level": config.level or 3,
            "credit": config.credit or 100,
            # ... 其他字段
        }

    async def get_contacts(self) -> List[AIFriend]:
        """异步获取联系人列表"""
        # 先获取 owner account
        stmt_config = select(AiChatCfg).where(AiChatCfg.is_delete == False)
        result_config = await self.db.execute(stmt_config)
        config = result_config.scalar_one_or_none()

        if not config:
            return []

        # 获取联系人
        stmt_contacts = select(AIFriend).where(
            AIFriend.is_delete == False,
            AIFriend.owner_sns_account == config.account
        ).order_by(AIFriend.nick_name)
        result_contacts = await self.db.execute(stmt_contacts)
        contacts = result_contacts.scalars().all()

        return contacts
```

---

### 方案二：在同步函数中运行异步操作（临时方案）

如果暂时不想全面改造成异步，可以使用 `asyncio.run()` 包装：

```python
import asyncio

def http_request(self, url, params=None, method="GET", data=None):
    """在同步函数中运行异步 HTTP 请求"""
    async def _async_request():
        async with httpx.AsyncClient() as client:
            if method == "GET":
                response = await client.get(url, params=params)
            elif method == "POST":
                response = await client.post(url, data=params)
            response.raise_for_status()
            return response.json()

    return asyncio.run(_async_request())
```

**注意：** 这种方案不推荐用于长期使用，因为它会阻塞事件循环。

---

## 四、具体修改代码示例

### 1. 修改 `__init__` 和添加 `async_init`

```python
class AISocialEngine:
    def __init__(self, db: AsyncSession):
        self.db = db
        # ... 同步初始化的属性 ...

    async def async_init(self):
        """异步初始化 - 必须在创建实例后调用"""
        from sqlalchemy import select

        stmt = select(AiChatCfg).where(AiChatCfg.is_delete == False)
        result = await self.db.execute(stmt)
        self.config = result.scalar_one_or_none()
        self.ai_chat_cfg = self.config

        # 初始化 AiChatCfgManager
        self.aichatcfg_record = AiChatCfgManager()
        self.aichatcfg_record.connect(self.handle_aichatcfg_property_updated)

        # 异步加载数据
        await self.load_all_user_data()
```

**在 `service.py` 中使用：**
```python
async def start_social_engine(self) -> dict:
    from backend.modules.sns.ai_social_engine_adapter import AISocialEngine

    if _social_engine_instance is None:
        _social_engine_instance = AISocialEngine(self.db)
        await _social_engine_instance.async_init()  # 异步初始化

    await _social_engine_instance.start()
    # ...
```

### 2. 修改 HTTP 请求方法

```python
import httpx

async def http_request(self, url, params=None, method="GET", data=None):
    """
    异步 HTTP 请求

    Args:
        url: 请求的 URL
        params: GET 请求参数
        method: HTTP 方法（GET, POST, PUT, DELETE, PATCH）
        data: POST/PUT 请求体

    Returns:
        JSON 响应数据
    """
    try:
        async with httpx.AsyncClient() as client:
            if method == "GET":
                response = await client.get(url, params=params, timeout=30.0)
            elif method == "POST":
                response = await client.post(url, data=data, timeout=30.0)
            elif method == "PUT":
                response = await client.put(url, data=data, timeout=30.0)
            elif method == "DELETE":
                response = await client.delete(url, params=params, timeout=30.0)
            elif method == "PATCH":
                response = await client.patch(url, data=data, timeout=30.0)
            else:
                raise ValueError(f"不支持的请求方法: {method}")

            response.raise_for_status()
            return response.json()

    except httpx.HTTPStatusError as http_err:
        print(f"HTTP错误发生: {http_err}")
    except httpx.RequestError as req_err:
        print(f"请求错误发生: {req_err}")
    except ValueError as json_err:
        print(f"JSON解析错误: {json_err}")

    return None
```

### 3. 修改 API 调用方法

```python
async def get_service_list(self):
    """异步获取服务列表"""
    url = "http://www.ai-sns.org/api/get_service_list/"
    pos = self.aichatcfg_record.current_position
    params = {
        "lng": pos[0],
        "lat": pos[1]
    }
    service_list = await self.http_request(url, params)
    return service_list

async def get_place_list(self):
    """异步获取地点列表"""
    url = "http://www.ai-sns.org/api/get_place_list/"
    params = {
        "lng": self.aichatcfg_record.current_position[0],
        "lat": self.aichatcfg_record.current_position[1]
    }
    place_list = await self.http_request(url, params)
    return place_list

async def get_people_list(self):
    """异步获取人员列表"""
    url = "http://www.ai-sns.org/api/get_people_list/"
    params = {
        "lng": self.aichatcfg_record.current_position[0],
        "lat": self.aichatcfg_record.current_position[1]
    }
    data = await self.http_request(url, params)

    remove_id = self.user_map_setting.get("nationid", "")
    people_list = [item for item in data if item["nation_id"] != remove_id]
    return people_list

async def get_tool_list(self):
    """异步获取工具列表"""
    service_list = await self.get_service_list()
    skill_list = await self.get_skill_list()
    plugin_tool_list = await self.get_plugin_tool_list()
    tool_list = service_list + skill_list + plugin_tool_list
    return tool_list
```

### 4. 修改 `think()` 方法

```python
async def think(self, **kwargs):
    """异步思考方法"""
    event = kwargs.get("event", "")
    current_chat_summary = kwargs.get("current_chat_summary", "")

    # 使用 await 而不是 create_task
    await self.ask_agent_to_update_task()

    if event == "after_conversation":
        self.taskmng.js_task_manager.show_information(
            lt("I'm thinking after conversation.", "正在思考对话内容。")
        )
        self.taskmng.set_command_status("ask_agent_to_think_after_conversation")
        self.ask_agent_to_think_after_conversation(current_chat_summary)
```

### 5. 修改 `ask_agent_to_bargain_for_buyer()` 方法

```python
async def ask_agent_to_bargain_for_buyer(self, tool_list):
    """异步要求代理为买家议价"""
    messages_history = json.dumps(self.current_talk_history, ensure_ascii=False)
    conversation_target = self.taskmng.current_objective
    role_prompt = get_prompt_by_title("__buyer_bargain_content__")
    role_prompt = role_prompt.replace("__conversation_target__", conversation_target)
    role_prompt = role_prompt.replace("__messages_history__", messages_history)
    role_prompt = role_prompt.replace("__tool_list__", tool_list)
    question = "请严格遵照要求评估，并严格按照格式输出。"
    await self.ask_agent_and_get_instruction(question, role_prompt)
```

### 6. 修改 `compose_full_ask_content()` 方法

```python
async def compose_full_ask_content(self, task_description, ability_list, question_to_llm):
    """异步构建完整的请求内容"""
    if self.temp_index > 7:
        self.decline_life()

    if self.temp_index_2 > 3:
        self.decline_energy()

    current_status = f"""
* 资金值: {self.money:.2f}元
* 生命值: {self.life_point}%
* 体力值: {self.energy_point}%
* 行动力: {self.move_point}%
    """
    question_to_llm = question_to_llm.replace("下一行动", "执行行动")
    question_to_llm = question_to_llm.replace("### 游戏攻略", "### 相关思考")
    question_to_llm = question_to_llm.replace("### 当前状况回顾", "### 行动前状况")

    prompt = get_prompt_by_title("__current_execute_status__")
    prompt = prompt.replace(f"__task_description__", task_description)
    prompt = prompt.replace(f"__last_instruction__", question_to_llm)
    prompt = prompt.replace(f"__action_result__", self.action_result)
    prompt = prompt.replace(f"__current_status__", current_status)

    # 异步获取列表
    tool_list = await self.get_tool_list()
    people_list = await self.get_people_list()
    place_list = await self.get_place_list()

    prompt = prompt.replace(f"__tool_list__", json.dumps(tool_list, indent=4, ensure_ascii=False))
    prompt = prompt.replace(f"__people_list__", json.dumps(people_list, indent=4, ensure_ascii=False))
    prompt = prompt.replace(f"__place_list__", json.dumps(place_list, indent=4, ensure_ascii=False))
    prompt = prompt.replace(f"__question_to_llm__", question_to_llm)
    return prompt.strip()
```

---

## 五、修改调用处

### 1. 在 `handle_ask_agent_instruction_to_process_activity()` 中

```python
async def handle_ask_agent_instruction_to_process_activity(self, ask_content):
    """异步处理代理指令"""
    self.show_status_on_map("thinking")
    if not self.started_flag:
        return

    role_prompt = get_prompt_by_title("__main_control__")
    process_info_list_str = "\n".join(f"{index + 1}. {info}" for index, info in enumerate(self.taskmng.process_info_list))
    ability_list = self.get_ability_list()

    # 异步调用 compose_full_ask_content
    full_ask_content = await self.compose_full_ask_content(
        process_info_list_str, ability_list, ask_content
    )
    await self.ask_agent_and_get_instruction(full_ask_content, role_prompt)
```

### 2. 在 MapTaskManager 中调用时

```python
# 在 map_task_manager.py 中，所有调用 parent.get_xxx_list() 的地方
# 改为：
tool_list = await parent.get_tool_list()
people_list = await parent.get_people_list()
place_list = await parent.get_place_list()
```

---

## 六、注意事项

### 1. 向后兼容性
- 在过渡期，可以保留同步版本的函数作为 `_sync_xxx()` 的后备实现
- 使用装饰器标记异步/同步版本

### 2. 错误处理
- 异步操作需要适当的错误处理
- 使用 `try-except` 捕获 `asyncio.CancelledError` 等异步异常

### 3. 资源管理
- 使用 `async with` 管理异步资源（如 HTTP 客户端、数据库会话）
- 确保在异常情况下正确关闭资源

### 4. 性能考虑
- 批量异步请求使用 `asyncio.gather()`
- 合理设置超时时间
- 避免过多的并发连接

---

## 七、测试建议

### 1. 单元测试
```python
import pytest
from httpx import AsyncMock

@pytest.mark.asyncio
async def test_get_service_list():
    engine = AISocialEngine(mock_db)
    service_list = await engine.get_service_list()
    assert isinstance(service_list, list)
```

### 2. 集成测试
- 测试异步数据库操作
- 测试异步 HTTP 请求
- 测试异步函数调用链

### 3. 性能测试
- 对比异步/同步版本的响应时间
- 测试并发请求的性能

---

## 八、总结

### 主要优化点：
1. ✅ 数据库操作改为异步（使用 AsyncSession）
2. ✅ HTTP 请求改为异步（使用 httpx）
3. ✅ 涉及 I/O 的函数改为 async
4. ✅ 添加必要的 await 调用
5. ✅ 统一 service 层的异步/同步接口

### 优先级：
1. **高优先级**：数据库查询、HTTP 请求（阻塞最严重）
2. **中优先级**：调用高优先级方法的函数
3. **低优先级**：纯计算函数（不需要异步）

### 预期效果：
- 提高并发处理能力
- 降低响应延迟
- 更好地利用系统资源
- 符合 FastAPI 异步最佳实践
