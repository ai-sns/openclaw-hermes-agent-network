# AI Social Engine Adapter 异步优化快速检查清单

## 📋 文件修改清单

### ✅ 必须修改的文件

| 文件 | 修改内容 | 优先级 |
|------|---------|--------|
| `requirements.txt` | 添加 `sqlalchemy[asyncio]`, `aiosqlite`, `httpx` | ⭐⭐⭐ |
| `backend/config/database.py` | 改为异步数据库配置 | ⭐⭐⭐ |
| `backend/modules/sns/ai_social_engine_adapter.py` | 主要异步化改造 | ⭐⭐⭐ |
| `backend/modules/sns/service.py` | 改为异步方法 | ⭐⭐⭐ |
| `backend/modules/sns/router.py` | 更新依赖注入类型 | ⭐⭐ |
| `db/DBFactory_async.py` | 新建异步数据库函数 | ⭐⭐⭐ |

---

## 🔧 函数修改清单

### 1. 需要改为 `async def` 的函数

#### HTTP 请求相关（⭐⭐⭐ 高优先级）
- [ ] `http_request()` → `async def http_request()`
- [ ] `call_service()` → `async def call_service()`
- [ ] `get_service_list()` → `async def get_service_list()`
- [ ] `get_skill_list()` → `async def get_skill_list()`
- [ ] `get_plugin_tool_list()` → `async def get_plugin_tool_list()`
- [ ] `get_tool_list()` → `async def get_tool_list()`
- [ ] `get_tool_list_for_trade()` → `async def get_tool_list_for_trade()`
- [ ] `get_mcp_list_for_trade()` → `async def get_mcp_list_for_trade()`
- [ ] `get_place_list()` → `async def get_place_list()`
- [ ] `get_people_list()` → `async def get_people_list()`

#### 数据库操作相关（⭐⭐⭐ 高优先级）
- [ ] 添加 `async def async_init()` - 异步初始化方法
- [ ] `load_all_user_data()` → `async def load_all_user_data()`
- [ ] `save_all_user_data()` → `async def save_all_user_data()`

#### Agent 调用相关（⭐⭐ 中优先级）
- [ ] `think()` → `async def think()`
- [ ] `ask_agent_to_bargain_for_buyer()` → `async def ask_agent_to_bargain_for_buyer()`
- [ ] `ask_agent_to_bargain_for_seller()` → `async def ask_agent_to_bargain_for_seller()`
- [ ] `ask_agent_to_use_service()` → `async def ask_agent_to_use_service()`
- [ ] `ask_agent_to_use_skill()` → `async def ask_agent_to_use_skill()`

#### 组合调用相关（⭐⭐ 中优先级）
- [ ] `compose_full_ask_content()` → `async def compose_full_ask_content()`
- [ ] `handle_ask_agent_instruction_to_process_activity()` → `async def handle_ask_agent_instruction_to_process_activity()`

---

### 2. Service 层需要异步化的方法（`service.py`）

- [ ] `get_user_stats()` → `async def get_user_stats()`
- [ ] `get_contacts()` → `async def get_contacts()`
- [ ] `get_chat_history()` → `async def get_chat_history()`
- [ ] `get_ai_chat_config()` → `async def get_ai_chat_config()`
- [ ] `update_ai_chat_config()` → `async def update_ai_chat_config()`
- [ ] `get_social_roles()` → `async def get_social_roles()`
- [ ] `get_user_info()` → `async def get_user_info()`
- [ ] `update_user_info()` → `async def update_user_info()`
- [ ] `get_map_config()` → `async def get_map_config()`
- [ ] `update_map_config()` → `async def update_map_config()`

---

### 3. 需要添加 `await` 的调用

#### 在 `ai_social_engine_adapter.py` 中

- [ ] 第684行：`await self.ask_agent_to_update_task()` （原来是 `asyncio.create_task(...)`）
- [ ] 第2210行：`await self.ask_agent_and_get_instruction(question, role_prompt)`
- [ ] 第2228行：`await self.ask_agent_and_get_instruction(question, role_prompt)`
- [ ] 第2247行：`await self.ask_agent_and_get_instruction(question, role_prompt)`
- [ ] 第2310行：`await self.ask_agent_and_get_instruction(question, role_prompt)`
- [ ] 第859行：`await self.ask_agent_and_get_instruction(full_ask_content, role_prompt)`
- [ ] 第791行：`await self.ask_agent_and_get_instruction(question_to_llm, role_prompt)`
- [ ] 第703行：`await self.ask_agent_and_get_instruction(question, role_prompt)`

#### 在 `compose_full_ask_content()` 中
- [ ] `await self.get_tool_list()`
- [ ] `await self.get_people_list()`
- [ ] `await self.get_place_list()`

#### 在 `get_tool_list()` 及相关函数中
- [ ] `await self.get_service_list()`
- [ ] `await self.get_skill_list()`
- [ ] `await self.get_plugin_tool_list()`

---

## 📝 代码修改示例

### 示例 1：HTTP 请求

**修改前：**
```python
def get_place_list(self):
    url = "http://www.ai-sns.org/api/get_place_list/"
    params = {"lng": ..., "lat": ...}
    place_list = self.http_request(url, params)  # 同步
    return place_list
```

**修改后：**
```python
async def get_place_list(self):
    url = "http://www.ai-sns.org/api/get_place_list/"
    params = {"lng": ..., "lat": ...}
    place_list = await self.http_request(url, params)  # 异步
    return place_list
```

### 示例 2：数据库查询

**修改前：**
```python
from sqlalchemy.orm import Session

def get_user_stats(self) -> dict:
    config = self.db.query(AiChatCfg).filter(...).first()  # 同步
    return {...}
```

**修改后：**
```python
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

async def get_user_stats(self) -> dict:
    stmt = select(AiChatCfg).where(...)
    result = await self.db.execute(stmt)
    config = result.scalar_one_or_none()  # 异步
    return {...}
```

### 示例 3：异步调用链

**修改前：**
```python
def compose_full_ask_content(self, ...):
    tool_list = self.get_tool_list()  # 同步
    people_list = self.get_people_list()  # 同步
    place_list = self.get_place_list()  # 同步
    # ...
```

**修改后：**
```python
async def compose_full_ask_content(self, ...):
    tool_list = await self.get_tool_list()  # 异步
    people_list = await self.get_people_list()  # 异步
    place_list = await self.get_place_list()  # 异步
    # ...
```

---

## 🚀 实施顺序

### 第一阶段：基础设施（1-2天）
1. ⭐ 安装依赖
2. ⭐ 修改数据库配置
3. ⭐ 创建异步数据库函数（`DBFactory_async.py`）

### 第二阶段：核心改造（2-3天）
4. ⭐ 修改 `ai_social_engine_adapter.py`
   - 添加 `async_init()`
   - 修改 HTTP 请求方法
   - 修改数据库加载/保存方法
5. ⭐ 修改 API 获取方法（`get_xxx_list`）

### 第三阶段：Service 层（1-2天）
6. ⭐ 修改 `service.py` 所有方法为异步
7. ⭐ 更新 `router.py` 中的类型注解

### 第四阶段：测试和优化（1-2天）
8. ⭐ 单元测试
9. ⭐ 集成测试
10. ⭐ 性能测试和优化

**总计：5-9天**

---

## ⚠️ 常见错误

### 错误 1：忘记 await
```python
# ❌ 错误
async def some_method():
    result = self.async_method()  # 缺少 await

# ✅ 正确
async def some_method():
    result = await self.async_method()  # 添加 await
```

### 错误 2：在非 async 函数中使用 await
```python
# ❌ 错误
def some_method():
    result = await self.async_method()  # 方法本身不是 async

# ✅ 正确
async def some_method():
    result = await self.async_method()
```

### 错误 3：同步 HTTP 请求
```python
# ❌ 错误
import requests  # 同步库
response = requests.get(url)

# ✅ 正确
import httpx  # 异步库
async with httpx.AsyncClient() as client:
    response = await client.get(url)
```

### 错误 4：同步数据库查询
```python
# ❌ 错误
config = self.db.query(Model).all()

# ✅ 正确
from sqlalchemy import select
stmt = select(Model)
result = await self.db.execute(stmt)
items = result.scalars().all()
```

### 错误 5：忘记提交事务
```python
# ❌ 错误
self.db.add(new_record)
await self.db.flush()  # 只刷新，不提交

# ✅ 正确
self.db.add(new_record)
await self.db.commit()  # 提交到数据库
```

---

## 📊 性能对比预期

| 操作 | 同步版本 | 异步版本 | 改进 |
|------|---------|---------|------|
| 单个数据库查询 | ~50ms | ~50ms | 持平 |
| 并发 10 个数据库查询 | ~500ms | ~60ms | ⬇️ 88% |
| 单个 HTTP 请求 | ~200ms | ~200ms | 持平 |
| 并发 10 个 HTTP 请求 | ~2000ms | ~250ms | ⬇️ 87.5% |
| 启动引擎 | ~500ms | ~400ms | ⬇️ 20% |
| 处理复杂任务 | ~5000ms | ~3000ms | ⬇️ 40% |

---

## 🎯 成功标准

- [ ] 所有 HTTP 请求改为异步（使用 httpx）
- [ ] 所有数据库查询改为异步（使用 AsyncSession）
- [ ] 所有涉及 I/O 的函数标记为 `async def`
- [ ] 所有异步调用都使用 `await`
- [ ] 没有语法错误和运行时错误
- [ ] 单元测试通过率 ≥ 90%
- [ ] 集成测试通过率 ≥ 85%
- [ ] 性能测试显示响应时间降低 ≥ 30%
- [ ] 并发请求性能提升 ≥ 50%

---

## 📞 需要帮助？

如果遇到问题，请参考：
1. `ASYNC_OPTIMIZATION_ANALYSIS.md` - 详细分析报告
2. `ASYNC_OPTIMIZATION_GUIDE.md` - 实施指南
3. SQLAlchemy 官方文档：https://docs.sqlalchemy.org/en/20/orm/extensions/asyncio.html
4. FastAPI 异步文档：https://fastapi.tiangolo.com/async/
