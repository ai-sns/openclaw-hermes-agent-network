# Agent工具调用集成 - 实现进度报告

**开始时间**: 2026-01-15 13:00
**当前时间**: 2026-01-15 13:45
**总体进度**: 40% (Phase 1 完成)

---

## ✅ 已完成

### Phase 1: 数据库和基础架构 (100%)

#### 1. 数据库Schema ✅
**文件**: `backend/database/migrations/add_agent_tools_table.py`
**状态**: 已创建并执行

创建了 `agent_tools` 表：
```sql
CREATE TABLE agent_tools (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    agent_id INTEGER NOT NULL,
    tool_type TEXT NOT NULL,  -- 'plugin', 'mcp', 'function', 'skill'
    tool_id TEXT NOT NULL,
    enabled INTEGER DEFAULT 1,
    priority INTEGER DEFAULT 0,
    create_time DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (agent_id) REFERENCES agent_cfg(id)
);
```

索引已创建：
- `idx_agent_tools_agent` on agent_id
- `idx_agent_tools_type` on (tool_type, tool_id)

#### 2. ToolConverter ✅
**文件**: `backend/modules/agent/tool_converter.py`
**状态**: 已创建并测试

实现了 4 种工具格式到 OpenAI Function Calling 格式的转换：
- `plugin_to_openai()` - Plugin → OpenAI格式
- `mcp_to_openai()` - MCP工具 → OpenAI格式
- `function_to_openai()` - Function → OpenAI格式
- `skill_to_openai()` - Skill → OpenAI格式

辅助方法：
- `convert_tools()` - 批量转换
- `parse_function_name()` - 解析function名称回tool信息

**测试结果**: ✅ 通过

```json
{
  "type": "function",
  "function": {
    "name": "plugin_PL2026011510474128484",
    "description": "Real Calculator: Perform arithmetic calculations...",
    "parameters": {...}
  }
}
```

#### 3. ToolRouter ✅
**文件**: `backend/modules/agent/tool_router.py`
**状态**: 已创建

实现了工具执行路由：
- `execute_tool()` - 统一入口
- `_execute_plugin()` - 路由到Plugin执行
- `_execute_mcp()` - 路由到MCP执行
- `_execute_function()` - 路由到Function执行
- `_execute_skill()` - 路由到Skill执行

支持的function_name格式：
- `plugin_{plugin_id}`
- `mcp_{mcp_id}_{tool_name}`
- `function_{function_id}`
- `skill_{skill_id}`

#### 4. ToolExecutor扩展 ✅
**文件**: `backend/modules/tools/tool_executor.py`
**状态**: 已扩展

新增方法 `execute_mcp_tool()`：
- 连接MCP Server
- 执行指定工具
- 返回执行结果

与现有 `_test_mcp_server()` 的区别：
- `_test_mcp_server()`: 测试服务器，返回工具列表 + 第一个工具调用结果
- `execute_mcp_tool()`: 执行特定工具，仅返回该工具结果

#### 5. AgentToolsRepository ✅
**文件**: `backend/database/repositories/agent_tools_repository.py`
**状态**: 已创建

实现了 agent_tools 表的CRUD操作：
- `get_agent_tools()` - 获取Agent关联的工具
- `add_agent_tool()` - 添加工具关联
- `remove_agent_tool()` - 删除工具关联
- `clear_agent_tools()` - 清空Agent所有工具
- `update_tool_priority()` - 更新优先级
- `toggle_tool_enabled()` - 启用/禁用工具

---

## 🚧 进行中

### Phase 2: 后端API (0%)

需要实现以下API端点：

#### 1. GET /api/agent/{agent_id}/tools
获取Agent关联的所有工具（含详细信息）

**响应格式**:
```json
{
  "agent_id": 1,
  "tools": [
    {
      "tool_type": "plugin",
      "tool_id": "PL2026011510474128484",
      "name": "Real Calculator",
      "description": "...",
      "enabled": true,
      "priority": 10
    },
    {
      "tool_type": "mcp",
      "tool_id": "MC2026011511561554068",
      "name": "✓ Real Weather MCP Server",
      "tools": [
        {"name": "get_weather", "description": "..."},
        {"name": "get_current_time", "description": "..."}
      ],
      "enabled": true,
      "priority": 5
    }
  ]
}
```

#### 2. POST /api/agent/{agent_id}/tools
更新Agent关联的工具

**请求格式**:
```json
{
  "tools": [
    {"tool_type": "plugin", "tool_id": "PL...", "priority": 10},
    {"tool_type": "mcp", "tool_id": "MC...", "priority": 5}
  ]
}
```

#### 3. GET /api/agent/{agent_id}/available-tools
获取所有可用工具（用于前端选择器）

**响应格式**:
```json
{
  "plugins": [
    {
      "plugin_id": "PL...",
      "name": "Real Calculator",
      "description": "...",
      "associated": true  // 是否已关联到该Agent
    }
  ],
  "mcps": [...],
  "functions": [...],
  "skills": [...]
}
```

---

## 📋 待实现

### Phase 2: 后端API (续)

#### 4. 修改 AgentInstance
**文件**: `backend/modules/agent/agent_instance.py`

需要修改：
1. `__init__()` - 添加 tool_router 初始化
2. `load_tools_from_db()` - 从数据库加载工具配置
3. `chat()` - 支持 tool_calls 处理
4. `chat_stream()` - 支持流式 tool_calls

#### 5. 集成到 AgentManager
**文件**: `backend/modules/agent/agent_manager.py`

确保 AgentInstance 创建时加载工具配置。

### Phase 3: 前端集成

#### 6. Agent设置界面
**文件**: `renderer/js/modules/agent/AgentSettingsDialog.js`

添加"工具配置"选项卡：
- 工具列表（按类型分组）
- Checkbox选择工具
- 优先级设置
- 保存按钮

#### 7. 聊天界面工具调用显示
**文件**: `renderer/js/modules/agent/AgentPage.js`

显示工具调用过程：
- 工具名称
- 参数
- 执行结果
- 可折叠展开

#### 8. API客户端
**文件**: `renderer/js/modules/agent/agentApi.js`

添加API方法：
- `getAgentTools(agentId)`
- `updateAgentTools(agentId, tools)`
- `getAvailableTools(agentId)`

### Phase 4: 测试

#### 9. 单元测试
- ToolConverter测试 ✅
- ToolRouter测试
- AgentToolsRepository测试

#### 10. 集成测试
- Plugin调用测试
- MCP调用测试
- Function调用测试
- Skill调用测试

#### 11. 端到端测试
- 配置Agent工具
- 聊天触发工具调用
- 验证结果显示

---

## 🎯 下一步计划

### 立即执行：

1. **实现 Agent Tools API** (30分钟)
   - 在 `backend/modules/agent/router.py` 添加3个端点
   - 使用 AgentToolsRepository + SystemRepository

2. **修改 AgentInstance** (45分钟)
   - 添加 `load_tools_from_db()`
   - 修改 `chat()` 支持 tool_calls
   - 修改 `chat_stream()` 支持流式 tool_calls

3. **简单测试** (15分钟)
   - 手动添加工具关联到数据库
   - 测试API返回
   - 测试Agent调用工具

4. **前端集成** (1小时)
   - Agent设置界面（工具选择）
   - 聊天界面（工具调用显示）

5. **完整测试** (30分钟)
   - 所有工具类型
   - 错误处理
   - 边界情况

---

## 📊 文件清单

### 已创建文件：
1. ✅ `AGENT_TOOL_CALLING_DESIGN.md` - 设计文档
2. ✅ `backend/database/migrations/add_agent_tools_table.py` - 数据库迁移
3. ✅ `backend/modules/agent/tool_converter.py` - 工具格式转换
4. ✅ `backend/modules/agent/tool_router.py` - 工具执行路由
5. ✅ `backend/database/repositories/agent_tools_repository.py` - 数据访问层

### 已修改文件：
1. ✅ `backend/modules/tools/tool_executor.py` - 添加 `execute_mcp_tool()`
2. ✅ `data/db.sqlite` - 添加 `agent_tools` 表

### 待创建/修改文件：
1. ⏳ `backend/modules/agent/router.py` - 添加工具管理API
2. ⏳ `backend/modules/agent/agent_instance.py` - 支持工具调用
3. ⏳ `backend/modules/agent/agent_manager.py` - 集成工具加载
4. ⏳ `renderer/js/modules/agent/AgentSettingsDialog.js` - 工具配置UI
5. ⏳ `renderer/js/modules/agent/AgentPage.js` - 工具调用显示
6. ⏳ `renderer/js/modules/agent/agentApi.js` - API客户端方法

---

## 💡 关键技术要点

### 1. 工具命名规范
```
plugin_{plugin_id}                    # Plugin
mcp_{mcp_id}_{tool_name}             # MCP工具
function_{function_id}                # Function
skill_{skill_id}                     # Skill
```

### 2. OpenAI Function Calling流程
```
User message → LLM (with tools) → tool_calls → ToolRouter → Execute
  → tool_result → LLM (with result) → Final response
```

### 3. 数据流
```
agent_tools (DB) → AgentToolsRepository → ToolConverter → OpenAI Format
  → AgentInstance.tools → LLM → tool_calls → ToolRouter → ToolExecutor
```

---

## ⚠️ 注意事项

1. **API服务器状态**: 当前已停止（需要重启进行测试）
2. **数据库锁定**: 操作数据库时注意停止API服务器
3. **MCP连接**: 每次工具调用都会启动新的MCP Server连接
4. **错误处理**: 所有执行器都应返回统一格式的错误
5. **超时控制**: 需要为工具执行设置超时时间

---

## 🔧 测试命令

```bash
# 验证数据库表
sqlite3 data/db.sqlite "SELECT * FROM agent_tools;"

# 测试ToolConverter
python3 backend/modules/agent/tool_converter.py

# 重启API服务器
python3 api_server.py >> /tmp/api_server.log 2>&1 &

# 测试API
curl -X GET http://localhost:8788/api/agent/1/tools
curl -X GET http://localhost:8788/api/agent/1/available-tools
```

---

**下一步**: 实现 Agent Tools API 端点
