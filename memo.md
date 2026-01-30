我会先在代码里定位 `POST /api/sns/start-engine` 这个路由的注册位置（你提到的 `api_server.py`/`backend`），然后顺着调用链把“从 HTTP 入口到最终启动引擎”的每一层：路由函数 -> service/manager -> DB/任务队列/子进程等全部展开，列出涉及的**文件路径、函数名、关键参数/返回**，并把逻辑画成一条可追踪的调用树。  
我先用全仓搜索把路由入口和相关 handler 找出来。


我已经定位到后端 `backend/modules/sns/router.py` 里有 `@router.post("/start-engine")`，它会创建 `SNSService(db)` 并调用 `start_social_engine()`，再进入 `AISocialEngine.start()` 启动后台任务循环。接下来我会把与该请求相关的**路由挂载（/api/sns 前缀来自哪）**、`get_db/get_db_sync`（SQLite 连接）以及 `AISocialEngine` 内部启动的 `_run_task_loop()` 等函数逐一打开，完整列出“哪些文件/哪些函数被调用”。我现在开始读取这些关键文件。
我已经确认 `POST /api/sns/start-engine` 的具体入口在 [backend/modules/sns/router.py::start_social_engine()](cci:1://file:///c:/dev/agi-ev/ai-sns-el/backend/modules/sns/router.py:84:0-95:9)，并且它会走到 [SNSService.start_social_engine()](cci:1://file:///c:/dev/agi-ev/ai-sns-el/backend/modules/sns/service_async.py:236:4-272:13) 里创建/初始化 [AISocialEngine](cci:2://file:///c:/dev/agi-ev/ai-sns-el/backend/modules/sns/ai_social_engine_adapter.py:52:0-936:126)，最后 [AISocialEngine.start()](cci:1://file:///c:/dev/agi-ev/ai-sns-el/backend/modules/sns/ai_social_engine_adapter.py:235:4-299:17) 会 `asyncio.create_task(self._run_task_loop())` 启动后台循环。下一步我会补齐两块关键信息：`/api/sns` 前缀在 [api_server.py](cci:7://file:///c:/dev/agi-ev/ai-sns-el/api_server.py:0:0-0:0) 的路由挂载位置，以及 [_run_task_loop()](cci:1://file:///c:/dev/agi-ev/ai-sns-el/backend/modules/sns/ai_social_engine_adapter.py:325:4-343:67) 的具体实现与它会继续调用哪些函数（以及其中涉及到的 DBFactory/SQLite 访问函数）。我现在继续把这些文件/函数读全并展开调用树。

我接下来会把 [AISocialEngine.start()](cci:1://file:///c:/dev/agi-ev/ai-sns-el/backend/modules/sns/ai_social_engine_adapter.py:235:4-299:17) 启动后的后台循环 [_run_task_loop()](cci:1://file:///c:/dev/agi-ev/ai-sns-el/backend/modules/sns/ai_social_engine_adapter.py:325:4-343:67) 展开：它每 5 秒会调用一次 [start_task()](cci:1://file:///c:/dev/agi-ev/ai-sns-el/backend/modules/sns/ai_social_engine_adapter.py:356:4-424:93)，而 [start_task()](cci:1://file:///c:/dev/agi-ev/ai-sns-el/backend/modules/sns/ai_social_engine_adapter.py:356:4-424:93) 会进入 `MapTaskManager` 的流程（`add_process()` / `process_task()` 等）。同时我会把 [AISocialEngine.__init__()](cci:1://file:///c:/dev/agi-ev/ai-sns-el/backend/modules/sns/ai_social_engine_adapter.py:68:4-162:33) / [async_init()](cci:1://file:///c:/dev/agi-ev/ai-sns-el/backend/modules/sns/ai_social_engine_adapter.py:164:4-233:41) 阶段的初始化（尤其是 `load_all_user_data()`、`AiChatCfg` 读取、DBFactory 对 SQLite 的访问）也纳入调用链，整理成一棵“入口->下游”调用树。现在先把 `MapTaskManager`、`JsTaskManager`、`load_all_user_data` 相关实现读出来并继续追踪。

我已经把 HTTP 入口、[SNSService.start_social_engine()](cci:1://file:///c:/dev/agi-ev/ai-sns-el/backend/modules/sns/service_async.py:236:4-272:13)、以及 [AISocialEngine.start()](cci:1://file:///c:/dev/agi-ev/ai-sns-el/backend/modules/sns/ai_social_engine_adapter.py:235:4-299:17) 启动后台循环的主干链路确认了。接下来为了把“所有会调用到的函数”完整理出来，我需要继续把 `AISocialEngine.load_all_user_data()`、[AiChatCfgManager](cci:2://file:///c:/dev/agi-ev/ai-sns-el/backend/modules/sns/ai_social_engine_adapter.py:939:0-1156:17)、以及 [MapTaskManager.process_task()](cci:1://file:///c:/dev/agi-ev/ai-sns-el/backend/modules/sns/map_task_manager.py:433:4-799:33) 等真正开始跑任务时会触发的函数展开，同时把这些函数背后调用到的 [db/DBFactory.py](cci:7://file:///c:/dev/agi-ev/ai-sns-el/db/DBFactory.py:0:0-0:0)（SQLite 访问）函数也一并列出并串到调用树里。我现在继续定位这些函数定义并读取对应文件。

我还差两块才能把 `POST /api/sns/start-engine` 的“所有会调用到的函数”完整列出来：  
1) `AISocialEngine.load_all_user_data()`（以及它内部会触发哪些 DBFactory 查询）到底在哪里定义、调用了什么；  
2) [AISocialEngine.start_task()](cci:1://file:///c:/dev/agi-ev/ai-sns-el/backend/modules/sns/ai_social_engine_adapter.py:356:4-424:93) 进入 [MapTaskManager.process_task()](cci:1://file:///c:/dev/agi-ev/ai-sns-el/backend/modules/sns/map_task_manager.py:433:4-799:33) 后，会继续触发哪些 [AISocialEngine](cci:2://file:///c:/dev/agi-ev/ai-sns-el/backend/modules/sns/ai_social_engine_adapter.py:52:0-936:126) 方法（比如 `ask_agent_*`、`send_msg_to_map`、XMPP/WebSocket 等）。  
我现在继续在 [ai_social_engine_adapter.py](cci:7://file:///c:/dev/agi-ev/ai-sns-el/backend/modules/sns/ai_social_engine_adapter.py:0:0-0:0) 里把 `load_all_user_data`/`send_msg_to_map`/[AiChatCfgManager](cci:2://file:///c:/dev/agi-ev/ai-sns-el/backend/modules/sns/ai_social_engine_adapter.py:939:0-1156:17) 等定义定位出来，并补齐相关依赖文件。

我会继续把 [AISocialEngine](cci:2://file:///c:/dev/agi-ev/ai-sns-el/backend/modules/sns/ai_social_engine_adapter.py:52:0-936:126) 通过多继承 mixin 组合起来的关键方法补齐：尤其是 `load_all_user_data()`（在 `data_query_mixin.py / resource_management_mixin.py` 里）、以及 `send_msg_to_map()/show_*` 这类把状态推送到前端的函数（在 [ui_display_mixin.py](cci:7://file:///c:/dev/agi-ev/ai-sns-el/backend/modules/sns/ui_display_mixin.py:0:0-0:0) 等）。读完这些后，我会给你一份**从 `/api/sns/start-engine` 入口开始**的完整调用树，并把每个节点标注到具体文件与函数名；同时指出有哪些是“循环中可能被触发的分支调用”（例如根据 LLM 指令进入 `move_ahead()/use_tools()/communicate_with_a_people()`）。

下面把你这次请求 `POST /api/sns/start-engine HTTP/1.1` 返回 `200 OK` 时，**后端实际“跑了哪些文件 / 调了哪些函数”**，按**从 HTTP 入口一路追到引擎后台循环**的方式，给你把**完整逻辑关系（调用树）**理出来。  
（我按你仓库当前实现精确到文件路径 + 函数名；另外会把“循环里可能触发的分支函数”也列出来，因为这些在引擎启动后就会被后台任务按条件调用。）

---

# 0. 路由挂载：为什么是 `/api/sns/start-engine`

## 0.1 应用入口与 router 挂载
- **文件**：[api_server.py](cci:7://file:///c:/dev/agi-ev/ai-sns-el/api_server.py:0:0-0:0)
- **关键代码**：
  - 导入 SNS router：`from backend.modules.sns.router import router as sns_router`
  - 挂载前缀：`app.include_router(sns_router, prefix="/api/sns", tags=["SNS"])`

所以：
- 你打的 `POST /api/sns/start-engine`
- 实际命中的是 SNS router 里路径 `"/start-engine"` 的 handler。

---

# 1. HTTP 调用树（入口到返回 200 的同步链路）

## 1.1 FastAPI handler
- **文件**：[backend/modules/sns/router.py](cci:7://file:///c:/dev/agi-ev/ai-sns-el/backend/modules/sns/router.py:0:0-0:0)
- **函数**：[start_social_engine(db: AsyncSession = Depends(get_db))](cci:1://file:///c:/dev/agi-ev/ai-sns-el/backend/modules/sns/router.py:84:0-95:9)

调用链：
1. `Depends(get_db)` 注入 DB（异步 session）
2. `service = SNSService(db)`
3. [result = await service.start_social_engine()](cci:1://file:///c:/dev/agi-ev/ai-sns-el/backend/modules/sns/router.py:84:0-95:9)
4. `return result`

> 你看到 `200 OK` 的时候，至少说明上面这条链路执行完成并返回了 dict。

---

## 1.2 DB 依赖注入（AsyncSession）
- **文件**：[backend/config/database.py](cci:7://file:///c:/dev/agi-ev/ai-sns-el/backend/config/database.py:0:0-0:0)
- **函数**：[get_db()](cci:1://file:///c:/dev/agi-ev/ai-sns-el/backend/config/database.py:53:0-64:21)（最终别名指向 [get_db_async_depends](cci:1://file:///c:/dev/agi-ev/ai-sns-el/backend/config/database.py:114:0-125:21)）
- **内部行为**：
  - `async with AsyncSessionLocal() as session: yield session`
- **连接串**：
  - `sqlite+aiosqlite:///{settings.database.full_path}`

> 注意：SNS 引擎本身**不是用这个 AsyncSession**跑逻辑，而是在下一步转成了同步 Session。

---

## 1.3 SNSService 启动引擎（核心）
- **文件**：[backend/modules/sns/service_async.py](cci:7://file:///c:/dev/agi-ev/ai-sns-el/backend/modules/sns/service_async.py:0:0-0:0)
- **类**：[SNSService](cci:2://file:///c:/dev/agi-ev/ai-sns-el/backend/modules/sns/service_async.py:28:0-776:63)
- **函数**：[start_social_engine(self)](cci:1://file:///c:/dev/agi-ev/ai-sns-el/backend/modules/sns/router.py:84:0-95:9)

调用链（按代码顺序）：
1. 检查全局状态：
   - `_social_engine_running`（bool）
   - `_social_engine_instance`（单例对象）
2. `from backend.modules.sns.ai_social_engine_adapter import AISocialEngine`
3. 若 `_social_engine_instance is None`：
   - **创建同步 DB Session**
     - **文件**：[backend/config/database.py](cci:7://file:///c:/dev/agi-ev/ai-sns-el/backend/config/database.py:0:0-0:0)
     - **函数**：[get_db_sync() -> Session](cci:1://file:///c:/dev/agi-ev/ai-sns-el/backend/config/database.py:67:0-79:25)
     - 连接串：`sqlite:///{settings.database.full_path}`
   - `_social_engine_instance = AISocialEngine(db_sync)`
   - [await _social_engine_instance.async_init()](cci:1://file:///c:/dev/agi-ev/ai-sns-el/backend/modules/sns/ai_social_engine_adapter.py:164:4-233:41)
4. [await _social_engine_instance.start()](cci:1://file:///c:/dev/agi-ev/ai-sns-el/backend/modules/sns/ai_social_engine_adapter.py:235:4-299:17)
5. `_social_engine_running = True`
6. 返回：
   - `{"success": True, "message": "...", "running": True}`

因此 `200 OK` 的“最后一步”通常就是这份 dict 被 FastAPI 返回。

---

# 2. [AISocialEngine](cci:2://file:///c:/dev/agi-ev/ai-sns-el/backend/modules/sns/ai_social_engine_adapter.py:52:0-936:126) 构造与初始化：启动引擎时“实际运行了哪些文件/函数”

从 [SNSService.start_social_engine()](cci:1://file:///c:/dev/agi-ev/ai-sns-el/backend/modules/sns/service_async.py:236:4-272:13) 开始，真正的“引擎启动”发生在：

## 2.1 创建引擎对象：[AISocialEngine.__init__](cci:1://file:///c:/dev/agi-ev/ai-sns-el/backend/modules/sns/ai_social_engine_adapter.py:68:4-162:33)
- **文件**：[backend/modules/sns/ai_social_engine_adapter.py](cci:7://file:///c:/dev/agi-ev/ai-sns-el/backend/modules/sns/ai_social_engine_adapter.py:0:0-0:0)
- **类**：[AISocialEngine](cci:2://file:///c:/dev/agi-ev/ai-sns-el/backend/modules/sns/ai_social_engine_adapter.py:52:0-936:126)
- **函数**：[__init__(self, db: Session)](cci:1://file:///c:/dev/agi-ev/ai-sns-el/backend/modules/sns/service_async.py:31:4-32:20)

它本身是一个**多继承组合类**：

- [XmppMixin](cci:2://file:///c:/dev/agi-ev/ai-sns-el/backend/modules/sns/xmpp_mixin.py:43:0-340:71) -> [backend/modules/sns/xmpp_mixin.py](cci:7://file:///c:/dev/agi-ev/ai-sns-el/backend/modules/sns/xmpp_mixin.py:0:0-0:0)
- [ToolsMixin](cci:2://file:///c:/dev/agi-ev/ai-sns-el/backend/modules/sns/tools_mixin.py:42:0-421:106) -> [backend/modules/sns/tools_mixin.py](cci:7://file:///c:/dev/agi-ev/ai-sns-el/backend/modules/sns/tools_mixin.py:0:0-0:0)
- [MapMovementMixin](cci:2://file:///c:/dev/agi-ev/ai-sns-el/backend/modules/sns/map_movement_mixin.py:42:0-388:37) -> [backend/modules/sns/map_movement_mixin.py](cci:7://file:///c:/dev/agi-ev/ai-sns-el/backend/modules/sns/map_movement_mixin.py:0:0-0:0)
- [CommunicationMixin](cci:2://file:///c:/dev/agi-ev/ai-sns-el/backend/modules/sns/communication_mixin.py:42:0-311:21) -> [backend/modules/sns/communication_mixin.py](cci:7://file:///c:/dev/agi-ev/ai-sns-el/backend/modules/sns/communication_mixin.py:0:0-0:0)
- [AgentInteractionMixin](cci:2://file:///c:/dev/agi-ev/ai-sns-el/backend/modules/sns/agent_interaction_mixin.py:15:0-199:41) -> [backend/modules/sns/agent_interaction_mixin.py](cci:7://file:///c:/dev/agi-ev/ai-sns-el/backend/modules/sns/agent_interaction_mixin.py:0:0-0:0)
- `TradeMixin` -> [backend/modules/sns/trade_mixin.py](cci:7://file:///c:/dev/agi-ev/ai-sns-el/backend/modules/sns/trade_mixin.py:0:0-0:0)（你仓库存在且被 grep 到）
- `EventHandlerMixin` -> [backend/modules/sns/event_handler_mixin.py](cci:7://file:///c:/dev/agi-ev/ai-sns-el/backend/modules/sns/event_handler_mixin.py:0:0-0:0)（存在）
- [DataQueryMixin](cci:2://file:///c:/dev/agi-ev/ai-sns-el/backend/modules/sns/data_query_mixin.py:41:0-238:83) -> [backend/modules/sns/data_query_mixin.py](cci:7://file:///c:/dev/agi-ev/ai-sns-el/backend/modules/sns/data_query_mixin.py:0:0-0:0)
- [UIDisplayMixin](cci:2://file:///c:/dev/agi-ev/ai-sns-el/backend/modules/sns/ui_display_mixin.py:41:0-541:61) -> [backend/modules/sns/ui_display_mixin.py](cci:7://file:///c:/dev/agi-ev/ai-sns-el/backend/modules/sns/ui_display_mixin.py:0:0-0:0)

> 这意味着：**引擎运行过程中会调用到这些 mixin 文件里的函数**（后面我会在“循环调用树”里完整列出来）。

### [__init__](cci:1://file:///c:/dev/agi-ev/ai-sns-el/backend/modules/sns/service_async.py:31:4-32:20) 内部关键调用/副作用
按代码可见的直接调用/构造（都是“启动时就会发生”的）：

- **创建任务管理器**
  - [JsTaskManager(self)](cci:2://file:///c:/dev/agi-ev/ai-sns-el/backend/modules/sns/js_task_manager.py:4:0-186:67)
    - **文件**：[backend/modules/sns/js_task_manager.py](cci:7://file:///c:/dev/agi-ev/ai-sns-el/backend/modules/sns/js_task_manager.py:0:0-0:0)
    - **类/函数**：[JsTaskManager.__init__](cci:1://file:///c:/dev/agi-ev/ai-sns-el/backend/modules/sns/js_task_manager.py:5:4-13:39)
  - [MapTaskManager(self)](cci:2://file:///c:/dev/agi-ev/ai-sns-el/backend/modules/sns/map_task_manager.py:8:0-900:19)
    - **文件**：[backend/modules/sns/map_task_manager.py](cci:7://file:///c:/dev/agi-ev/ai-sns-el/backend/modules/sns/map_task_manager.py:0:0-0:0)
    - **类/函数**：[MapTaskManager.__init__](cci:1://file:///c:/dev/agi-ev/ai-sns-el/backend/modules/sns/map_task_manager.py:9:4-37:28)
    - 内部会调用：[MapTaskManager.init_task_mng()](cci:1://file:///c:/dev/agi-ev/ai-sns-el/backend/modules/sns/map_task_manager.py:39:4-64:28)
      - [query_single_map_task(status=1)](cci:1://file:///c:/dev/agi-ev/ai-sns-el/db/DBFactory.py:3171:0-3182:23)（DBFactory）
- **初始化 XMPP 管理器**
  - `XMPPClientManager.get_instance()`
    - **文件**：[backend/modules/sns/xmpp_client.py](cci:7://file:///c:/dev/agi-ev/ai-sns-el/backend/modules/sns/xmpp_client.py:0:0-0:0)（你仓库存在且 service_async 引用）
- **读取 SQLAlchemy 模型方式的配置**
  - `self.db.query(AiChatCfg).filter(...).first()`
    - **模型文件**：`backend/database/models/chat.py`（AiChatCfg 定义在该模块）
- **创建配置代理对象**
  - `self.aichatcfg_record = AiChatCfgManager()`
    - [AiChatCfgManager.connect(self.handle_aichatcfg_property_updated)](cci:1://file:///c:/dev/agi-ev/ai-sns-el/backend/modules/sns/ai_social_engine_adapter.py:957:4-965:44)
    - [AiChatCfgManager._load_record()](cci:1://file:///c:/dev/agi-ev/ai-sns-el/backend/modules/sns/ai_social_engine_adapter.py:990:4-995:48)
      - [query_AiChatCfg_map()](cci:1://file:///c:/dev/agi-ev/ai-sns-el/db/DBFactory.py:1299:0-1303:17) 或 [query_AiChatCfg_map_setting()](cci:1://file:///c:/dev/agi-ev/ai-sns-el/db/DBFactory.py:1313:0-1351:19)（DBFactory）

- **重要：启动时直接加载用户数据**
  - [self.load_all_user_data()](cci:1://file:///c:/dev/agi-ev/ai-sns-el/backend/modules/sns/data_query_mixin.py:154:4-183:32)
  - 这个方法实际来自 mixin（见下一节 2.3）

---

## 2.2 异步初始化：[AISocialEngine.async_init](cci:1://file:///c:/dev/agi-ev/ai-sns-el/backend/modules/sns/ai_social_engine_adapter.py:164:4-233:41)
- **文件**：[backend/modules/sns/ai_social_engine_adapter.py](cci:7://file:///c:/dev/agi-ev/ai-sns-el/backend/modules/sns/ai_social_engine_adapter.py:0:0-0:0)
- **函数**：[async_init(self)](cci:1://file:///c:/dev/agi-ev/ai-sns-el/backend/modules/sns/ai_social_engine_adapter.py:164:4-233:41)

这里会做大量字段初始化，并且再次构造：
- [JsTaskManager(self)](cci:2://file:///c:/dev/agi-ev/ai-sns-el/backend/modules/sns/js_task_manager.py:4:0-186:67)
- [MapTaskManager(self)](cci:2://file:///c:/dev/agi-ev/ai-sns-el/backend/modules/sns/map_task_manager.py:8:0-900:19)
并且会再次调用：
- [self.load_all_user_data()](cci:1://file:///c:/dev/agi-ev/ai-sns-el/backend/modules/sns/data_query_mixin.py:154:4-183:32)

---

## 2.3 [load_all_user_data()](cci:1://file:///c:/dev/agi-ev/ai-sns-el/backend/modules/sns/data_query_mixin.py:154:4-183:32) 实际落在哪个文件？
由于 [AISocialEngine](cci:2://file:///c:/dev/agi-ev/ai-sns-el/backend/modules/sns/ai_social_engine_adapter.py:52:0-936:126) 多继承，[load_all_user_data()](cci:1://file:///c:/dev/agi-ev/ai-sns-el/backend/modules/sns/data_query_mixin.py:154:4-183:32) 的解析顺序取决于继承顺序。

你当前 [AISocialEngine](cci:2://file:///c:/dev/agi-ev/ai-sns-el/backend/modules/sns/ai_social_engine_adapter.py:52:0-936:126) 继承顺序里是：
`... EventHandlerMixin, DataQueryMixin, UIDisplayMixin`

因此真正生效的 [load_all_user_data()](cci:1://file:///c:/dev/agi-ev/ai-sns-el/backend/modules/sns/data_query_mixin.py:154:4-183:32) 是：

- **文件**：[backend/modules/sns/data_query_mixin.py](cci:7://file:///c:/dev/agi-ev/ai-sns-el/backend/modules/sns/data_query_mixin.py:0:0-0:0)
- **类**：[DataQueryMixin](cci:2://file:///c:/dev/agi-ev/ai-sns-el/backend/modules/sns/data_query_mixin.py:41:0-238:83)
- **函数**：[load_all_user_data(self)](cci:1://file:///c:/dev/agi-ev/ai-sns-el/backend/modules/sns/data_query_mixin.py:154:4-183:32)

该函数内部调用链（非常关键，因为涉及 SQLite）：

1. `record = query_AiChatCfg_map()`
   - **文件**：[db/DBFactory.py](cci:7://file:///c:/dev/agi-ev/ai-sns-el/db/DBFactory.py:0:0-0:0)
   - **函数**：[query_AiChatCfg_map](cci:1://file:///c:/dev/agi-ev/ai-sns-el/db/DBFactory.py:1299:0-1303:17)（定义在 DBFactory 后半段，你的文件很长；但已被 mixin 引用）
2. 解析位置数据：
   - [self._parse_position_data(record.current_position)](cci:1://file:///c:/dev/agi-ev/ai-sns-el/backend/modules/sns/data_query_mixin.py:185:4-226:17)
   - [self._parse_position_data(record.last_position)](cci:1://file:///c:/dev/agi-ev/ai-sns-el/backend/modules/sns/data_query_mixin.py:185:4-226:17)
   - [_parse_position_data](cci:1://file:///c:/dev/agi-ev/ai-sns-el/backend/modules/sns/data_query_mixin.py:185:4-226:17) 也在 [data_query_mixin.py](cci:7://file:///c:/dev/agi-ev/ai-sns-el/backend/modules/sns/data_query_mixin.py:0:0-0:0)
3. 加载资源字段：
   - `life_point/energy_point/move_point/exp_point/iq_point/money/credit/level`
4. route 状态：
   - `if record.route_status == "playing": self.move_by_route_flag = True`
5. `user_map_setting = query_AiChatCfg_map_setting()`
   - **文件**：[db/DBFactory.py](cci:7://file:///c:/dev/agi-ev/ai-sns-el/db/DBFactory.py:0:0-0:0)
   - **函数**：[query_AiChatCfg_map_setting](cci:1://file:///c:/dev/agi-ev/ai-sns-el/db/DBFactory.py:1313:0-1351:19)
6. 刷新前端显示（WebSocket 广播）：
   - [self.update_resource_display()](cci:1://file:///c:/dev/agi-ev/ai-sns-el/backend/modules/sns/ui_display_mixin.py:169:4-183:82)  -> [backend/modules/sns/ui_display_mixin.py](cci:7://file:///c:/dev/agi-ev/ai-sns-el/backend/modules/sns/ui_display_mixin.py:0:0-0:0)
     - 内部会调用：
       - [self.get_tool_list()](cci:1://file:///c:/dev/agi-ev/ai-sns-el/util.py:623:0-634:20) -> [backend/modules/sns/tools_mixin.py](cci:7://file:///c:/dev/agi-ev/ai-sns-el/backend/modules/sns/tools_mixin.py:0:0-0:0)
       - [self.get_people_list()](cci:1://file:///c:/dev/agi-ev/ai-sns-el/backend/modules/sns/data_query_mixin.py:52:4-64:26) / [self.get_place_list()](cci:1://file:///c:/dev/agi-ev/ai-sns-el/backend/modules/sns/data_query_mixin.py:43:4-50:25) -> [backend/modules/sns/data_query_mixin.py](cci:7://file:///c:/dev/agi-ev/ai-sns-el/backend/modules/sns/data_query_mixin.py:0:0-0:0)（HTTP 请求 ai-sns.org）
       - `asyncio.create_task(self._send_to_frontend('resource', ...))`
         - [_send_to_frontend](cci:1://file:///c:/dev/agi-ev/ai-sns-el/backend/modules/sns/ui_display_mixin.py:96:4-117:60) -> [websocket_manager.broadcast(...)](cci:1://file:///c:/dev/agi-ev/ai-sns-el/backend/shared/websocket_manager.py:99:4-127:38)
         - **文件**：[backend/shared/websocket_manager.py](cci:7://file:///c:/dev/agi-ev/ai-sns-el/backend/shared/websocket_manager.py:0:0-0:0)
         - **函数**：[ConnectionManager.broadcast](cci:1://file:///c:/dev/agi-ev/ai-sns-el/backend/shared/websocket_manager.py:99:4-127:38)
   - [self.update_map_charts()](cci:1://file:///c:/dev/agi-ev/ai-sns-el/backend/modules/sns/ui_display_mixin.py:476:4-524:77) -> [backend/modules/sns/ui_display_mixin.py](cci:7://file:///c:/dev/agi-ev/ai-sns-el/backend/modules/sns/ui_display_mixin.py:0:0-0:0)
     - `asyncio.create_task(self._send_chart_update(user_stats))`
     - [_send_chart_update](cci:1://file:///c:/dev/agi-ev/ai-sns-el/backend/modules/sns/ui_display_mixin.py:526:4-541:61) -> [websocket_manager.broadcast(...)](cci:1://file:///c:/dev/agi-ev/ai-sns-el/backend/shared/websocket_manager.py:99:4-127:38)

> 所以：只要你启动引擎，它不仅仅“起了个后台循环”，还会读取 SQLite、并且尝试通过 WebSocket 广播资源/图表数据给前端。

---

# 3. SQLite（db/db.sqlite）到底走的是哪套 DB 代码？

这里有两套 DB 访问路径同时存在：

## 3.1 后端“标准”SQLAlchemy（backend/config/database.py）
- Async：`sqlite+aiosqlite:///...`
- Sync：`sqlite:///...`
- 主要给 FastAPI 模块化后端 models 用（`backend/database/models/*`）

## 3.2 老的 DBFactory（你 SNS 引擎大量使用）
- **文件**：[db/DBFactory.py](cci:7://file:///c:/dev/agi-ev/ai-sns-el/db/DBFactory.py:0:0-0:0)
- DBPath：`db/db.sqlite`（`DBPath = os.path.join(Path(__file__).resolve().parent, "db.sqlite")`）
- SQLAlchemy engine：`create_engine("sqlite:///...db.sqlite")`
- Session：`Session = sessionmaker(bind=engine)`

SNS 引擎相关的几个关键模块直接 `from db.DBFactory import ...`，例如：
- [backend/modules/sns/data_query_mixin.py](cci:7://file:///c:/dev/agi-ev/ai-sns-el/backend/modules/sns/data_query_mixin.py:0:0-0:0)
- [backend/modules/sns/ui_display_mixin.py](cci:7://file:///c:/dev/agi-ev/ai-sns-el/backend/modules/sns/ui_display_mixin.py:0:0-0:0)
- [backend/modules/sns/map_task_manager.py](cci:7://file:///c:/dev/agi-ev/ai-sns-el/backend/modules/sns/map_task_manager.py:0:0-0:0)
- [backend/modules/sns/js_task_manager.py](cci:7://file:///c:/dev/agi-ev/ai-sns-el/backend/modules/sns/js_task_manager.py:0:0-0:0)
- [backend/modules/sns/xmpp_mixin.py](cci:7://file:///c:/dev/agi-ev/ai-sns-el/backend/modules/sns/xmpp_mixin.py:0:0-0:0)
- 以及 [ai_social_engine_adapter.py](cci:7://file:///c:/dev/agi-ev/ai-sns-el/backend/modules/sns/ai_social_engine_adapter.py:0:0-0:0) 自身头部 import 的一大坨 DBFactory 函数

> 结论：你这次 `/start-engine` 返回 200，**引擎启动后的主要数据读写实际上更偏向 DBFactory（db/db.sqlite）这条链路**。

---

# 4. 引擎真正“开始跑起来”的后台循环调用树（启动后会持续触发）

[SNSService.start_social_engine()](cci:1://file:///c:/dev/agi-ev/ai-sns-el/backend/modules/sns/service_async.py:236:4-272:13) 里执行了：

- [await _social_engine_instance.start()](cci:1://file:///c:/dev/agi-ev/ai-sns-el/backend/modules/sns/ai_social_engine_adapter.py:235:4-299:17)

对应：

## 4.1 [AISocialEngine.start()](cci:1://file:///c:/dev/agi-ev/ai-sns-el/backend/modules/sns/ai_social_engine_adapter.py:235:4-299:17)
- **文件**：[backend/modules/sns/ai_social_engine_adapter.py](cci:7://file:///c:/dev/agi-ev/ai-sns-el/backend/modules/sns/ai_social_engine_adapter.py:0:0-0:0)
- **函数**：[start(self)](cci:1://file:///c:/dev/agi-ev/ai-sns-el/backend/modules/sns/ai_social_engine_adapter.py:235:4-299:17)

内部关键动作：
1. `self.started_flag = True`
2. `self.map_task_status = ""`
3. 初始化 `self.ability_list`（用于后续 agent 决策）
4. 启动后台任务：
   - `self.task_runner = asyncio.create_task(self._run_task_loop())`

---

## 4.2 后台循环：[AISocialEngine._run_task_loop()](cci:1://file:///c:/dev/agi-ev/ai-sns-el/backend/modules/sns/ai_social_engine_adapter.py:325:4-343:67)
- **文件**：[backend/modules/sns/ai_social_engine_adapter.py](cci:7://file:///c:/dev/agi-ev/ai-sns-el/backend/modules/sns/ai_social_engine_adapter.py:0:0-0:0)
- **函数**：[_run_task_loop(self)](cci:1://file:///c:/dev/agi-ev/ai-sns-el/backend/modules/sns/ai_social_engine_adapter.py:325:4-343:67)

循环逻辑：
- `while self.started_flag:`
  - [self.start_task()](cci:1://file:///c:/dev/agi-ev/ai-sns-el/backend/modules/sns/ai_social_engine_adapter.py:356:4-424:93)
  - `await asyncio.sleep(5)`

这意味着：启动后每 5 秒都会执行一次 [start_task()](cci:1://file:///c:/dev/agi-ev/ai-sns-el/backend/modules/sns/ai_social_engine_adapter.py:356:4-424:93)。

---

## 4.3 每轮循环调用：[AISocialEngine.start_task()](cci:1://file:///c:/dev/agi-ev/ai-sns-el/backend/modules/sns/ai_social_engine_adapter.py:356:4-424:93)
- **文件**：[backend/modules/sns/ai_social_engine_adapter.py](cci:7://file:///c:/dev/agi-ev/ai-sns-el/backend/modules/sns/ai_social_engine_adapter.py:0:0-0:0)
- **函数**：[start_task(self)](cci:1://file:///c:/dev/agi-ev/ai-sns-el/backend/modules/sns/ai_social_engine_adapter.py:356:4-424:93)

首次进入（`map_task_status == ""`）时：
1. `self.map_task_status = "started"`
2. `self.taskmng.reviewing_task = True`
3. `self.process_list = []`
4. `self.taskmng.current_process = None`
5. [self.taskmng.add_process(...)](cci:1://file:///c:/dev/agi-ev/ai-sns-el/backend/modules/sns/map_task_manager.py:162:4-183:26)
   - **文件**：[backend/modules/sns/map_task_manager.py](cci:7://file:///c:/dev/agi-ev/ai-sns-el/backend/modules/sns/map_task_manager.py:0:0-0:0)
   - **函数**：[MapTaskManager.add_process](cci:1://file:///c:/dev/agi-ev/ai-sns-el/backend/modules/sns/map_task_manager.py:162:4-183:26)
6. `self.taskmng.current_situation = "准备开始执行任务"`
7. 重置 `self.ability_list`
8. 调用任务处理主入口：
   - [self.taskmng.process_task(action="process_activity")](cci:1://file:///c:/dev/agi-ev/ai-sns-el/backend/modules/sns/map_task_manager.py:433:4-799:33)

---

# 5. 任务引擎：[MapTaskManager.process_task()](cci:1://file:///c:/dev/agi-ev/ai-sns-el/backend/modules/sns/map_task_manager.py:433:4-799:33) 之后会调用哪些函数（非常多）

- **文件**：[backend/modules/sns/map_task_manager.py](cci:7://file:///c:/dev/agi-ev/ai-sns-el/backend/modules/sns/map_task_manager.py:0:0-0:0)
- **函数**：[process_task(self, **kwargs)](cci:1://file:///c:/dev/agi-ev/ai-sns-el/backend/modules/sns/map_task_manager.py:433:4-799:33)

这个函数是一个**状态机/路由器**，会根据 `action` 或 `event` 继续分派回 [AISocialEngine](cci:2://file:///c:/dev/agi-ev/ai-sns-el/backend/modules/sns/ai_social_engine_adapter.py:52:0-936:126) 的各类方法。

启动时走到的关键分支是：

## 5.1 action = `process_activity`
- `asyncio.create_task(self.parent.ask_agent_instruction_to_process_activity(ask_content))`

这里 `parent` 就是 [AISocialEngine](cci:2://file:///c:/dev/agi-ev/ai-sns-el/backend/modules/sns/ai_social_engine_adapter.py:52:0-936:126) 实例，所以继续调用：

- **文件**：[backend/modules/sns/ai_social_engine_adapter.py](cci:7://file:///c:/dev/agi-ev/ai-sns-el/backend/modules/sns/ai_social_engine_adapter.py:0:0-0:0)
- **函数**：[ask_agent_instruction_to_process_activity(self, ask_content)](cci:1://file:///c:/dev/agi-ev/ai-sns-el/backend/modules/sns/ai_social_engine_adapter.py:600:4-607:80)
  - 最终会进入：[handle_ask_agent_instruction_to_process_activity](cci:1://file:///c:/dev/agi-ev/ai-sns-el/backend/modules/sns/ai_social_engine_adapter.py:609:4-620:79)
  - 构造 prompt 后调用：
    - [await self.ask_agent_and_get_instruction(full_ask_content, role_prompt)](cci:1://file:///c:/dev/agi-ev/ai-sns-el/backend/modules/sns/agent_interaction_mixin.py:18:4-89:60)

而 [ask_agent_and_get_instruction](cci:1://file:///c:/dev/agi-ev/ai-sns-el/backend/modules/sns/agent_interaction_mixin.py:18:4-89:60) 来自：

- **文件**：[backend/modules/sns/agent_interaction_mixin.py](cci:7://file:///c:/dev/agi-ev/ai-sns-el/backend/modules/sns/agent_interaction_mixin.py:0:0-0:0)
- **函数**：[AgentInteractionMixin.ask_agent_and_get_instruction(...)](cci:1://file:///c:/dev/agi-ev/ai-sns-el/backend/modules/sns/agent_interaction_mixin.py:18:4-89:60)

它内部关键调用链：
1. `agent_manager.get_agent_by_id(self.ai_chat_cfg.agent_id)`
   - **文件**：`backend/modules/agent/agent_manager.py`（项目里存在）
2. `reply = await agent.chat(...)`
   - **文件**：`agent/*`（你的 agent 框架）
3. [self.on_agent_return_instruction(question, reply)](cci:1://file:///c:/dev/agi-ev/ai-sns-el/backend/modules/sns/agent_interaction_mixin.py:92:4-199:41)

[on_agent_return_instruction](cci:1://file:///c:/dev/agi-ev/ai-sns-el/backend/modules/sns/agent_interaction_mixin.py:92:4-199:41) 会根据 `self.command_status` 分派回 [MapTaskManager.process_task(event=...)](cci:1://file:///c:/dev/agi-ev/ai-sns-el/backend/modules/sns/map_task_manager.py:433:4-799:33)：

- **文件**：[backend/modules/sns/agent_interaction_mixin.py](cci:7://file:///c:/dev/agi-ev/ai-sns-el/backend/modules/sns/agent_interaction_mixin.py:0:0-0:0)
- **函数**：[on_agent_return_instruction(self, question, content)](cci:1://file:///c:/dev/agi-ev/ai-sns-el/backend/modules/sns/agent_interaction_mixin.py:92:4-199:41)
- 典型事件：
  - `event="agent_instruction_to_process_activity_returned"`

回到：

- **文件**：[backend/modules/sns/map_task_manager.py](cci:7://file:///c:/dev/agi-ev/ai-sns-el/backend/modules/sns/map_task_manager.py:0:0-0:0)
- **分支**：`event=="agent_instruction_to_process_activity_returned"`
  - 会调用：
    - [self.parent.parse_agent_instruction_for_process_activity(instruction)](cci:1://file:///c:/dev/agi-ev/ai-sns-el/backend/modules/sns/ai_social_engine_adapter.py:656:4-663:77)

---

# 6. LLM 指令解析后：会触发哪些“分支函数”（这些都属于“启动后会调用到的函数”）

[parse_agent_instruction_for_process_activity](cci:1://file:///c:/dev/agi-ev/ai-sns-el/backend/modules/sns/ai_social_engine_adapter.py:656:4-663:77) 在：

- **文件**：[backend/modules/sns/ai_social_engine_adapter.py](cci:7://file:///c:/dev/agi-ev/ai-sns-el/backend/modules/sns/ai_social_engine_adapter.py:0:0-0:0)
- **函数**：[parse_agent_instruction_for_process_activity(self, instruction)](cci:1://file:///c:/dev/agi-ev/ai-sns-el/backend/modules/sns/ai_social_engine_adapter.py:656:4-663:77)
  - -> [handle_parse_agent_instruction_for_process_activity(self, instruction)](cci:1://file:///c:/dev/agi-ev/ai-sns-el/backend/modules/sns/ai_social_engine_adapter.py:665:4-778:85)

它会解析得到 `action_str`（下一行动），并按关键字进入不同分支。你代码里明确出现的分支包括（每个都对应具体函数/文件）：

## 6.1 移动相关（地图）
- **附近逛逛**
  - [self.go_around()](cci:1://file:///c:/dev/agi-ev/ai-sns-el/backend/modules/sns/map_movement_mixin.py:44:4-108:21)  
    - **文件**：[backend/modules/sns/map_movement_mixin.py](cci:7://file:///c:/dev/agi-ev/ai-sns-el/backend/modules/sns/map_movement_mixin.py:0:0-0:0)
    - **函数**：[go_around](cci:1://file:///c:/dev/agi-ev/ai-sns-el/backend/modules/sns/map_movement_mixin.py:44:4-108:21)
    - 内部会调用：
      - [self.send_msg_to_map(command)](cci:1://file:///c:/dev/agi-ev/ai-sns-el/backend/modules/sns/ui_display_mixin.py:462:4-474:62) -> [backend/modules/sns/ui_display_mixin.py::send_msg_to_map](cci:1://file:///c:/dev/agi-ev/ai-sns-el/backend/modules/sns/ui_display_mixin.py:462:4-474:62)
      - [self.update_after_moving()](cci:1://file:///c:/dev/agi-ev/ai-sns-el/backend/modules/sns/map_movement_mixin.py:373:4-384:23) -> [backend/modules/sns/map_movement_mixin.py::update_after_moving](cci:1://file:///c:/dev/agi-ev/ai-sns-el/backend/modules/sns/map_movement_mixin.py:373:4-384:23)（会 HTTP post 到 `ai-sns.org/api/update-location/`）
- **走路前往**
  - [self.move_ahead(current, target, place)](cci:1://file:///c:/dev/agi-ev/ai-sns-el/backend/modules/sns/map_movement_mixin.py:121:4-188:60)
    - **文件**：[backend/modules/sns/map_movement_mixin.py](cci:7://file:///c:/dev/agi-ev/ai-sns-el/backend/modules/sns/map_movement_mixin.py:0:0-0:0)
    - **函数**：[move_ahead](cci:1://file:///c:/dev/agi-ev/ai-sns-el/backend/modules/sns/map_movement_mixin.py:121:4-188:60)
    - 内部会调用：
      - [send_msg_to_map("move_to_a_place", ...)](cci:1://file:///c:/dev/agi-ev/ai-sns-el/backend/modules/sns/ui_display_mixin.py:462:4-474:62)
      - [update_after_moving()](cci:1://file:///c:/dev/agi-ev/ai-sns-el/backend/modules/sns/map_movement_mixin.py:373:4-384:23)
- **导航服务**
  - `self.get_guidance()`（此函数在 adapter 后续未展开行数内，但属于同一类；如果你需要我可以继续定位它定义位置并展开）
- **按路线移动**
  - [self.move_by_route()](cci:1://file:///c:/dev/agi-ev/ai-sns-el/backend/modules/sns/map_movement_mixin.py:190:4-198:133) -> [backend/modules/sns/map_movement_mixin.py](cci:7://file:///c:/dev/agi-ev/ai-sns-el/backend/modules/sns/map_movement_mixin.py:0:0-0:0)
  - [send_msg_to_map("route_move_action", ...)](cci:1://file:///c:/dev/agi-ev/ai-sns-el/backend/modules/sns/ui_display_mixin.py:462:4-474:62)

## 6.2 沟通/对话相关（XMPP + WebSocket）
- **沟通**
  - [self.communicate_with_a_people(...)](cci:1://file:///c:/dev/agi-ev/ai-sns-el/backend/modules/sns/communication_mixin.py:68:4-73:87) -> [backend/modules/sns/communication_mixin.py](cci:7://file:///c:/dev/agi-ev/ai-sns-el/backend/modules/sns/communication_mixin.py:0:0-0:0)
  - -> [ask_agent_start_to_talk_to_a_people_sync(...)](cci:1://file:///c:/dev/agi-ev/ai-sns-el/backend/modules/sns/communication_mixin.py:90:4-101:92)
  - -> [ask_agent_and_get_instruction(...)](cci:1://file:///c:/dev/agi-ev/ai-sns-el/backend/modules/sns/agent_interaction_mixin.py:18:4-89:60)（AgentInteractionMixin）
  - -> 选人后 [talk_to_a_people(...)](cci:1://file:///c:/dev/agi-ev/ai-sns-el/backend/modules/sns/communication_mixin.py:43:4-66:57)
    - 调用：
      - [send_msg_to_map(("start_talk_to_it", ...))](cci:1://file:///c:/dev/agi-ev/ai-sns-el/backend/modules/sns/ui_display_mixin.py:462:4-474:62) -> UIDisplayMixin
      - [sendMessage(...)](cci:1://file:///c:/dev/agi-ev/ai-sns-el/backend/modules/sns/xmpp_mixin.py:225:4-273:24) -> [backend/modules/sns/xmpp_mixin.py::sendMessage](cci:1://file:///c:/dev/agi-ev/ai-sns-el/backend/modules/sns/xmpp_mixin.py:225:4-273:24)
        - [send_xmpp_message(...)](cci:1://file:///c:/dev/agi-ev/ai-sns-el/backend/modules/sns/xmpp_mixin.py:201:4-223:24) -> XMPPClientManager 客户端
        - [_update_ui_with_sent_message](cci:1://file:///c:/dev/agi-ev/ai-sns-el/backend/modules/sns/xmpp_mixin.py:324:4-340:71) -> [send_talk_message(...)](cci:1://file:///c:/dev/agi-ev/ai-sns-el/backend/modules/sns/ui_display_mixin.py:354:4-398:44) -> websocket broadcast

- **接收 XMPP 消息（引擎启动后，只要 XMPPClientManager 收到消息就会调用）**
  - [XmppMixin.receiveMessage(event)](cci:1://file:///c:/dev/agi-ev/ai-sns-el/backend/modules/sns/xmpp_mixin.py:45:4-80:72) -> [backend/modules/sns/xmpp_mixin.py](cci:7://file:///c:/dev/agi-ev/ai-sns-el/backend/modules/sns/xmpp_mixin.py:0:0-0:0)
  - -> [handle_receiveMessage(content, from_str)](cci:1://file:///c:/dev/agi-ev/ai-sns-el/backend/modules/sns/xmpp_mixin.py:82:4-198:20)
  - -> [send_talk_message(...)](cci:1://file:///c:/dev/agi-ev/ai-sns-el/backend/modules/sns/ui_display_mixin.py:354:4-398:44) -> [backend/modules/sns/ui_display_mixin.py](cci:7://file:///c:/dev/agi-ev/ai-sns-el/backend/modules/sns/ui_display_mixin.py:0:0-0:0)
  - -> [self.taskmng.process_task(event="conversation_message_received", ...)](cci:1://file:///c:/dev/agi-ev/ai-sns-el/backend/modules/sns/map_task_manager.py:433:4-799:33)

## 6.3 工具相关
- **工具**
  - [self.use_tools()](cci:1://file:///c:/dev/agi-ev/ai-sns-el/backend/modules/sns/tools_mixin.py:44:4-48:21) -> [backend/modules/sns/tools_mixin.py::use_tools](cci:1://file:///c:/dev/agi-ev/ai-sns-el/backend/modules/sns/tools_mixin.py:44:4-48:21)

以及更深层的“工具挑选与执行”（由 MapTaskManager 的异常检测/流程触发）：
- [ask_agent_to_pick_a_tool_sync](cci:1://file:///c:/dev/agi-ev/ai-sns-el/backend/modules/sns/tools_mixin.py:188:4-205:86) -> ToolsMixin
- [handle_agent_pick_a_tool_result](cci:1://file:///c:/dev/agi-ev/ai-sns-el/backend/modules/sns/tools_mixin.py:228:4-259:93) -> ToolsMixin
- [call_tool](cci:1://file:///c:/dev/agi-ev/ai-sns-el/backend/modules/sns/tools_mixin.py:261:4-294:31) / [call_built_in_function](cci:1://file:///c:/dev/agi-ev/ai-sns-el/backend/modules/sns/tools_mixin.py:296:4-307:16) / [call_service](cci:1://file:///c:/dev/agi-ev/ai-sns-el/backend/modules/sns/tools_mixin.py:362:4-379:80) 等 -> ToolsMixin

## 6.4 UI 推送相关（WebSocket）
很多动作最终都会走：
- [UIDisplayMixin.send_msg_to_map(...)](cci:1://file:///c:/dev/agi-ev/ai-sns-el/backend/modules/sns/ui_display_mixin.py:462:4-474:62)  （广播 `{"type":"command", ...}`）
- [UIDisplayMixin.show_status_on_map(...)](cci:1://file:///c:/dev/agi-ev/ai-sns-el/backend/modules/sns/ui_display_mixin.py:400:4-427:43)（广播 `{"type":"status_update", ...}`）
- [UIDisplayMixin.show_alert_on_map(...)](cci:1://file:///c:/dev/agi-ev/ai-sns-el/backend/modules/sns/ui_display_mixin.py:429:4-458:43)（广播 `{"type":"alert", ...}`）
- [UIDisplayMixin._send_to_frontend(...)](cci:1://file:///c:/dev/agi-ev/ai-sns-el/backend/modules/sns/ui_display_mixin.py:96:4-117:60)（广播 `{"type":"sns_update", ...}`）
- [UIDisplayMixin.update_map_charts()](cci:1://file:///c:/dev/agi-ev/ai-sns-el/backend/modules/sns/ui_display_mixin.py:476:4-524:77) / [_send_chart_update()](cci:1://file:///c:/dev/agi-ev/ai-sns-el/backend/modules/sns/ui_display_mixin.py:526:4-541:61)

它们最终落到：
- **文件**：[backend/shared/websocket_manager.py](cci:7://file:///c:/dev/agi-ev/ai-sns-el/backend/shared/websocket_manager.py:0:0-0:0)
- **函数**：[ConnectionManager.broadcast(...)](cci:1://file:///c:/dev/agi-ev/ai-sns-el/backend/shared/websocket_manager.py:99:4-127:38)

---

# 7. 总结：你这次请求“后台具体运行了哪些文件/函数”（最小闭环 + 启动后必跑）

## 7.1 一次请求必经的最小闭环（一定执行）
- **[api_server.py](cci:7://file:///c:/dev/agi-ev/ai-sns-el/api_server.py:0:0-0:0)**
  - `app.include_router(sns_router, prefix="/api/sns")`
- **[backend/modules/sns/router.py](cci:7://file:///c:/dev/agi-ev/ai-sns-el/backend/modules/sns/router.py:0:0-0:0)**
  - [start_social_engine()](cci:1://file:///c:/dev/agi-ev/ai-sns-el/backend/modules/sns/router.py:84:0-95:9)
- **[backend/config/database.py](cci:7://file:///c:/dev/agi-ev/ai-sns-el/backend/config/database.py:0:0-0:0)**
  - [get_db()](cci:1://file:///c:/dev/agi-ev/ai-sns-el/backend/config/database.py:53:0-64:21)（Depends 注入）
- **[backend/modules/sns/service_async.py](cci:7://file:///c:/dev/agi-ev/ai-sns-el/backend/modules/sns/service_async.py:0:0-0:0)**
  - [SNSService.__init__](cci:1://file:///c:/dev/agi-ev/ai-sns-el/backend/modules/sns/service_async.py:31:4-32:20)
  - [SNSService.start_social_engine](cci:1://file:///c:/dev/agi-ev/ai-sns-el/backend/modules/sns/service_async.py:236:4-272:13)
  - [get_db_sync()](cci:1://file:///c:/dev/agi-ev/ai-sns-el/backend/config/database.py:67:0-79:25)（创建同步 session）
- **[backend/modules/sns/ai_social_engine_adapter.py](cci:7://file:///c:/dev/agi-ev/ai-sns-el/backend/modules/sns/ai_social_engine_adapter.py:0:0-0:0)**
  - [AISocialEngine.__init__](cci:1://file:///c:/dev/agi-ev/ai-sns-el/backend/modules/sns/ai_social_engine_adapter.py:68:4-162:33)
  - `AiChatCfgManager.__init__ / _load_record / connect`
  - [AISocialEngine.async_init](cci:1://file:///c:/dev/agi-ev/ai-sns-el/backend/modules/sns/ai_social_engine_adapter.py:164:4-233:41)
  - [AISocialEngine.start](cci:1://file:///c:/dev/agi-ev/ai-sns-el/backend/modules/sns/ai_social_engine_adapter.py:235:4-299:17)
  - [AISocialEngine._run_task_loop](cci:1://file:///c:/dev/agi-ev/ai-sns-el/backend/modules/sns/ai_social_engine_adapter.py:325:4-343:67)（被 create_task 启动）
- **[backend/modules/sns/data_query_mixin.py](cci:7://file:///c:/dev/agi-ev/ai-sns-el/backend/modules/sns/data_query_mixin.py:0:0-0:0)**
  - [load_all_user_data](cci:1://file:///c:/dev/agi-ev/ai-sns-el/backend/modules/sns/data_query_mixin.py:154:4-183:32)
  - [_parse_position_data](cci:1://file:///c:/dev/agi-ev/ai-sns-el/backend/modules/sns/data_query_mixin.py:185:4-226:17)
- **[backend/modules/sns/ui_display_mixin.py](cci:7://file:///c:/dev/agi-ev/ai-sns-el/backend/modules/sns/ui_display_mixin.py:0:0-0:0)**
  - [update_resource_display](cci:1://file:///c:/dev/agi-ev/ai-sns-el/backend/modules/sns/ui_display_mixin.py:169:4-183:82)
  - [_send_to_frontend](cci:1://file:///c:/dev/agi-ev/ai-sns-el/backend/modules/sns/ui_display_mixin.py:96:4-117:60)
  - [update_map_charts](cci:1://file:///c:/dev/agi-ev/ai-sns-el/backend/modules/sns/ui_display_mixin.py:476:4-524:77)
  - [_send_chart_update](cci:1://file:///c:/dev/agi-ev/ai-sns-el/backend/modules/sns/ui_display_mixin.py:526:4-541:61)
- **[backend/shared/websocket_manager.py](cci:7://file:///c:/dev/agi-ev/ai-sns-el/backend/shared/websocket_manager.py:0:0-0:0)**
  - [ConnectionManager.broadcast](cci:1://file:///c:/dev/agi-ev/ai-sns-el/backend/shared/websocket_manager.py:99:4-127:38)

## 7.2 启动后会进入循环、并可能触发的大量函数（按你代码的实际路径）
- **循环 tick**
  - [AISocialEngine._run_task_loop -> AISocialEngine.start_task -> MapTaskManager.process_task](cci:1://file:///c:/dev/agi-ev/ai-sns-el/backend/modules/sns/map_task_manager.py:433:4-799:33)
- **Agent 回路**
  - [AISocialEngine.ask_agent_instruction_to_process_activity](cci:1://file:///c:/dev/agi-ev/ai-sns-el/backend/modules/sns/ai_social_engine_adapter.py:600:4-607:80)
  - [AgentInteractionMixin.ask_agent_and_get_instruction](cci:1://file:///c:/dev/agi-ev/ai-sns-el/backend/modules/sns/agent_interaction_mixin.py:18:4-89:60)
  - `agent_manager.get_agent_by_id`
  - `agent.chat`
  - [AgentInteractionMixin.on_agent_return_instruction](cci:1://file:///c:/dev/agi-ev/ai-sns-el/backend/modules/sns/agent_interaction_mixin.py:92:4-199:41)
  - [MapTaskManager.process_task(event=...)](cci:1://file:///c:/dev/agi-ev/ai-sns-el/backend/modules/sns/map_task_manager.py:433:4-799:33)
  - [AISocialEngine.parse_agent_instruction_for_process_activity](cci:1://file:///c:/dev/agi-ev/ai-sns-el/backend/modules/sns/ai_social_engine_adapter.py:656:4-663:77)
- **按指令进入的分支**
  - 地图：`go_around / move_ahead / move_by_route / move_to_a_place / update_after_moving ...`
  - 工具：`use_tools / ask_agent_to_pick_a_tool_sync / call_tool / call_service ...`
  - 沟通：`communicate_with_a_people / talk_to_a_people / sendMessage / send_xmpp_message / receiveMessage ...`
  - UI：`send_msg_to_map / show_status_on_map / show_alert_on_map / _send_to_frontend ...`

---

# 你可能最关心的两个点（我直接点出来）
- **`200 OK` 并不等于引擎真的“开始执行任务并成功跑通”**：它只表示 [start()](cci:1://file:///c:/dev/agi-ev/ai-sns-el/backend/modules/sns/ai_social_engine_adapter.py:235:4-299:17) 成功创建了后台 task（`asyncio.create_task`）并返回成功。后台 loop 里如果报错，HTTP 仍可能是 200。
- 引擎启动后会混用两套 DB：
  - FastAPI 模块化层：[backend/config/database.py](cci:7://file:///c:/dev/agi-ev/ai-sns-el/backend/config/database.py:0:0-0:0)
  - SNS 引擎大量：[db/DBFactory.py](cci:7://file:///c:/dev/agi-ev/ai-sns-el/db/DBFactory.py:0:0-0:0)（`db/db.sqlite`）

---

# 完成状态
- **已完成**：把 `POST /api/sns/start-engine` 从路由入口到引擎后台循环（含 DB、WebSocket、Agent、XMPP 的关键路径）按文件/函数维度梳理出完整调用关系，并列出启动后会触发的分支函数集合。