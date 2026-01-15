# Agent工具调用集成设计方案

## 📋 需求概述

在Electron的Agent聊天界面，用户输入自然语言后，Agent能够智能选择并调用合适的工具：

| 用户输入 | 调用工具 | 工具类型 |
|---------|---------|---------|
| "查询上海的天气" | MCP: get_weather | MCP Server |
| "计算1+89等于多少" | Plugin: calculator | Plugin |
| "问候一下" | Function: greeting | Function |
| "截个屏" | Skill: screenshot | Computer Use Skill |
| "获取系统信息" | MCP: get_system_info 或 Skill: get_system_info | MCP/Skill |

## 🏗️ 架构设计

### 1. 数据库Schema扩展

#### 新增表：`agent_tools` (Agent与工具关联表)

```sql
CREATE TABLE agent_tools (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    agent_id INTEGER NOT NULL,
    tool_type TEXT NOT NULL,  -- 'plugin', 'mcp', 'function', 'skill'
    tool_id TEXT NOT NULL,    -- 对应的工具ID
    enabled INTEGER DEFAULT 1,
    priority INTEGER DEFAULT 0,  -- 优先级，数字越大优先级越高
    create_time DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (agent_id) REFERENCES agent_cfg(id)
);

CREATE INDEX idx_agent_tools_agent ON agent_tools(agent_id);
CREATE INDEX idx_agent_tools_type ON agent_tools(tool_type, tool_id);
```

### 2. 工具格式转换器

#### 目标：将所有工具类型统一转换为OpenAI Function Calling格式

```python
# backend/modules/agent/tool_converter.py

class ToolConverter:
    """Convert different tool types to OpenAI Function Calling format"""

    @staticmethod
    def plugin_to_openai(plugin: dict) -> dict:
        """
        Plugin格式 → OpenAI Function格式

        Input (Plugin from database):
        {
            "plugin_id": "PL2026011510474128484",
            "name": "Real Calculator",
            "description": "Perform arithmetic calculations",
            "instruction": "Use this for math operations",
            "parameter": "{\"type\":\"object\",\"properties\":{\"expression\":{\"type\":\"string\"}}}"
        }

        Output (OpenAI Function):
        {
            "type": "function",
            "function": {
                "name": "plugin_PL2026011510474128484",
                "description": "Real Calculator: Perform arithmetic calculations. Use this for math operations",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "expression": {"type": "string", "description": "Math expression"}
                    },
                    "required": ["expression"]
                }
            }
        }
        """

    @staticmethod
    def mcp_to_openai(mcp: dict, tool: dict) -> dict:
        """
        MCP工具格式 → OpenAI Function格式

        Input (MCP + Tool):
        {
            "mcp_id": "MC2026011511561554068",
            "name": "✓ Real Weather MCP Server",
            "tools": [
                {
                    "name": "get_weather",
                    "description": "Get current weather information",
                    "inputSchema": {
                        "type": "object",
                        "properties": {
                            "city": {"type": "string"},
                            "unit": {"type": "string", "enum": ["celsius", "fahrenheit"]}
                        },
                        "required": ["city"]
                    }
                }
            ]
        }

        Output:
        {
            "type": "function",
            "function": {
                "name": "mcp_MC2026011511561554068_get_weather",
                "description": "Get current weather information (from ✓ Real Weather MCP Server)",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "city": {"type": "string"},
                        "unit": {"type": "string", "enum": ["celsius", "fahrenheit"]}
                    },
                    "required": ["city"]
                }
            }
        }
        """

    @staticmethod
    def function_to_openai(function: dict) -> dict:
        """Function格式 → OpenAI Function格式"""

    @staticmethod
    def skill_to_openai(skill: dict) -> dict:
        """Skill格式 → OpenAI Function格式"""
```

### 3. 工具执行路由器

#### 目标：根据function_name路由到正确的工具执行器

```python
# backend/modules/agent/tool_router.py

class ToolRouter:
    """Route tool calls to appropriate executors"""

    def __init__(self, tool_executor):
        self.tool_executor = tool_executor

    async def execute_tool(self, function_name: str, arguments: dict) -> dict:
        """
        根据function_name执行对应的工具

        function_name格式：
        - plugin_{plugin_id}
        - mcp_{mcp_id}_{tool_name}
        - function_{function_id}
        - skill_{skill_id}

        Returns:
        {
            "success": true,
            "result": "tool execution result"
        }
        """

        # Parse function name
        parts = function_name.split('_', 2)
        tool_type = parts[0]

        if tool_type == "plugin":
            plugin_id = parts[1]
            return await self._execute_plugin(plugin_id, arguments)

        elif tool_type == "mcp":
            mcp_id = parts[1]
            tool_name = parts[2]
            return await self._execute_mcp(mcp_id, tool_name, arguments)

        elif tool_type == "function":
            function_id = parts[1]
            return await self._execute_function(function_id, arguments)

        elif tool_type == "skill":
            skill_id = parts[1]
            return await self._execute_skill(skill_id, arguments)

        else:
            return {"success": False, "error": f"Unknown tool type: {tool_type}"}

    async def _execute_plugin(self, plugin_id: str, arguments: dict) -> dict:
        """Execute plugin via ToolExecutor"""
        result = await self.tool_executor.execute_plugin(plugin_id, arguments)
        return result

    async def _execute_mcp(self, mcp_id: str, tool_name: str, arguments: dict) -> dict:
        """Execute MCP tool"""
        # Need to implement MCP tool calling (not just testing)
        result = await self.tool_executor.execute_mcp_tool(mcp_id, tool_name, arguments)
        return result

    async def _execute_function(self, function_id: str, arguments: dict) -> dict:
        """Execute function via ToolExecutor"""
        result = await self.tool_executor.execute_function(function_id, arguments)
        return result

    async def _execute_skill(self, skill_id: str, arguments: dict) -> dict:
        """Execute skill via ToolExecutor"""
        result = await self.tool_executor.execute_skill(skill_id, arguments)
        return result
```

### 4. AgentInstance扩展

```python
# backend/modules/agent/agent_instance.py

class AgentInstance:
    def __init__(self, ...):
        # ... existing code ...
        self.tool_router = ToolRouter(tool_executor)

    async def load_tools_from_db(self, agent_id: int):
        """从数据库加载Agent关联的工具"""
        # 1. 查询 agent_tools 表
        # 2. 根据 tool_type 和 tool_id 从各个工具表获取详情
        # 3. 使用 ToolConverter 转换为 OpenAI 格式
        # 4. 设置 self.tools

    async def chat(self, message: str, ...):
        """Chat with tool calling support"""

        # Build messages
        messages = [...]

        # Call LLM with tools
        response = await self.client.chat.completions.create(
            model=self.llm_config["model_name"],
            messages=messages,
            tools=self.tools,  # ← OpenAI function calling
            tool_choice="auto"
        )

        # Handle tool calls
        if response.choices[0].message.tool_calls:
            for tool_call in response.choices[0].message.tool_calls:
                function_name = tool_call.function.name
                arguments = json.loads(tool_call.function.arguments)

                # Execute tool via ToolRouter
                tool_result = await self.tool_router.execute_tool(
                    function_name,
                    arguments
                )

                # Add tool result to messages
                messages.append({
                    "role": "tool",
                    "tool_call_id": tool_call.id,
                    "content": json.dumps(tool_result)
                })

            # Call LLM again with tool results
            final_response = await self.client.chat.completions.create(...)
            return final_response

        return response
```

### 5. 新增API接口

```python
# backend/modules/agent/router.py

@router.get("/api/agent/{agent_id}/tools")
async def get_agent_tools(agent_id: int):
    """获取Agent关联的所有工具"""
    # 1. 查询 agent_tools 表
    # 2. 获取每个工具的详细信息
    # 3. 返回工具列表
    return {
        "agent_id": agent_id,
        "tools": [
            {
                "tool_type": "plugin",
                "tool_id": "PL2026011510474128484",
                "name": "Real Calculator",
                "description": "...",
                "enabled": True
            },
            {
                "tool_type": "mcp",
                "tool_id": "MC2026011511561554068",
                "name": "✓ Real Weather MCP Server",
                "tools": [
                    {"name": "get_weather", "description": "..."},
                    {"name": "get_current_time", "description": "..."}
                ]
            }
        ]
    }

@router.post("/api/agent/{agent_id}/tools")
async def update_agent_tools(agent_id: int, tools: List[dict]):
    """更新Agent关联的工具"""
    # 1. 删除现有关联
    # 2. 插入新关联
    # 3. 重新加载Agent实例的工具
    return {"success": True}

@router.get("/api/agent/{agent_id}/available-tools")
async def get_available_tools(agent_id: int):
    """获取所有可用的工具（用于前端工具选择器）"""
    # 1. 获取所有 Plugin
    # 2. 获取所有 MCP
    # 3. 获取所有 Function
    # 4. 获取所有 Skill
    # 5. 标记哪些已关联到该Agent
    return {
        "plugins": [...],
        "mcps": [...],
        "functions": [...],
        "skills": [...]
    }
```

### 6. ToolExecutor扩展

需要添加MCP工具调用方法（目前只有测试方法）：

```python
# backend/modules/tools/tool_executor.py

async def execute_mcp_tool(self, mcp_id: str, tool_name: str, arguments: dict) -> dict:
    """
    Execute specific MCP tool (not just test)

    Similar to _test_mcp_server(), but:
    - Takes specific tool_name and arguments
    - Only executes that one tool
    - Returns just the tool result
    """
    # 1. Get MCP config from database
    # 2. Connect to MCP server
    # 3. Call specific tool with arguments
    # 4. Return result
```

### 7. Electron前端集成

#### A. Agent设置界面 (AgentSettingsDialog)

添加"工具配置"选项卡：

```html
<!-- renderer/components/AgentSettingsDialog.html -->
<div class="tab-pane" id="tools-tab">
    <h4>关联的工具</h4>

    <!-- 工具列表 -->
    <div id="agent-tools-list">
        <!-- Plugin -->
        <div class="tool-category">
            <h5>Plugins</h5>
            <div id="plugin-tools">
                <label><input type="checkbox" value="PL2026011510474128484"> Real Calculator</label>
                <label><input type="checkbox" value="PL..."> Image Generator</label>
            </div>
        </div>

        <!-- MCP -->
        <div class="tool-category">
            <h5>MCP Servers</h5>
            <div id="mcp-tools">
                <label><input type="checkbox" value="MC2026011511561554068"> ✓ Real Weather MCP Server</label>
            </div>
        </div>

        <!-- Function -->
        <div class="tool-category">
            <h5>Functions</h5>
            <div id="function-tools">
                <label><input type="checkbox" value="FN..."> Greeting Function</label>
            </div>
        </div>

        <!-- Skill -->
        <div class="tool-category">
            <h5>Computer Use Skills</h5>
            <div id="skill-tools">
                <label><input type="checkbox" value="SK..."> Screenshot</label>
            </div>
        </div>
    </div>

    <button id="save-agent-tools">保存工具配置</button>
</div>
```

#### B. 聊天界面工具调用显示

```javascript
// renderer/js/modules/agent/AgentPage.js

function displayToolCall(toolCall) {
    const toolCallDiv = document.createElement('div');
    toolCallDiv.className = 'tool-call-display';
    toolCallDiv.innerHTML = `
        <div class="tool-call-header">
            <span class="tool-icon">🔧</span>
            <span class="tool-name">${toolCall.function.name}</span>
        </div>
        <div class="tool-call-args">
            <pre>${JSON.stringify(toolCall.arguments, null, 2)}</pre>
        </div>
        <div class="tool-call-result">
            <strong>Result:</strong>
            <pre>${JSON.stringify(toolCall.result, null, 2)}</pre>
        </div>
    `;
    chatContainer.appendChild(toolCallDiv);
}
```

## 🔄 完整流程

### 用户输入："查询上海的天气"

```
1. 用户在Electron聊天界面输入消息
   ↓
2. Frontend: POST /api/agent/{agent_id}/chat/stream
   Body: {"message": "查询上海的天气", "conversation_id": "conv123"}
   ↓
3. Backend: chat_router.agent_chat_stream_by_id()
   ↓
4. AgentInstance.chat_stream(message)
   ├─ 加载Agent配置的工具列表 (self.tools)
   ├─ 构建messages (system + history + user message)
   ├─ 调用OpenAI API with tools
   │  {
   │    "model": "gpt-4",
   │    "messages": [...],
   │    "tools": [
   │      {
   │        "type": "function",
   │        "function": {
   │          "name": "mcp_MC2026011511561554068_get_weather",
   │          "description": "Get current weather information",
   │          "parameters": {...}
   │        }
   │      },
   │      {
   │        "type": "function",
   │        "function": {
   │          "name": "plugin_PL2026011510474128484",
   │          "description": "Real Calculator",
   │          "parameters": {...}
   │        }
   │      }
   │    ]
   │  }
   ↓
5. LLM决定调用工具
   Response: {
     "choices": [{
       "message": {
         "tool_calls": [{
           "id": "call_abc123",
           "function": {
             "name": "mcp_MC2026011511561554068_get_weather",
             "arguments": "{\"city\": \"Shanghai\", \"unit\": \"celsius\"}"
           }
         }]
       }
     }]
   }
   ↓
6. AgentInstance处理tool_calls
   ├─ 解析function_name: "mcp_MC2026011511561554068_get_weather"
   ├─ 调用ToolRouter.execute_tool()
   │  ├─ 识别tool_type: "mcp"
   │  ├─ 提取mcp_id: "MC2026011511561554068"
   │  ├─ 提取tool_name: "get_weather"
   │  └─ 调用ToolExecutor.execute_mcp_tool(mcp_id, tool_name, arguments)
   │     ├─ 连接MCP Server
   │     ├─ 调用get_weather工具
   │     └─ 返回结果: "🌤️ Weather in Shanghai: 22°C, Sunny"
   │
   └─ 将工具结果添加到messages
      messages.append({
        "role": "tool",
        "tool_call_id": "call_abc123",
        "content": "🌤️ Weather in Shanghai: 22°C, Sunny"
      })
   ↓
7. 再次调用LLM (with tool results)
   Request: {
     "messages": [
       {...system...},
       {"role": "user", "content": "查询上海的天气"},
       {"role": "assistant", "tool_calls": [...]},
       {"role": "tool", "content": "🌤️ Weather in Shanghai: 22°C, Sunny"}
     ]
   }
   ↓
8. LLM生成最终回复
   Response: "根据实时天气数据，上海目前天气晴朗，温度22°C。"
   ↓
9. Frontend显示最终回复
   - 显示工具调用过程（可折叠）
   - 显示最终回复
```

## 📊 数据流示意图

```
┌───────────────────────────────────────────────────────────┐
│              Electron Frontend (Agent Chat)               │
│  用户输入: "查询上海的天气"                                 │
└─────────────────────┬─────────────────────────────────────┘
                      │ HTTP POST /api/agent/1/chat/stream
                      ▼
┌───────────────────────────────────────────────────────────┐
│                Backend: AgentInstance                      │
│  1. 加载工具配置 (from agent_tools table)                  │
│  2. 转换为OpenAI格式 (ToolConverter)                       │
│  3. 调用LLM with tools                                     │
└─────────────────────┬─────────────────────────────────────┘
                      │
                      ▼
┌───────────────────────────────────────────────────────────┐
│                  OpenAI API (GPT-4)                        │
│  分析: "查询上海的天气" → 需要调用 get_weather 工具         │
│  Decision: tool_call = mcp_MC...get_weather               │
└─────────────────────┬─────────────────────────────────────┘
                      │ tool_calls response
                      ▼
┌───────────────────────────────────────────────────────────┐
│          Backend: ToolRouter.execute_tool()               │
│  function_name: "mcp_MC2026011511561554068_get_weather"   │
│  ├─ Parse: tool_type="mcp"                                │
│  ├─ Parse: mcp_id="MC2026011511561554068"                 │
│  └─ Parse: tool_name="get_weather"                        │
└─────────────────────┬─────────────────────────────────────┘
                      │
                      ▼
┌───────────────────────────────────────────────────────────┐
│    Backend: ToolExecutor.execute_mcp_tool()               │
│  1. 连接MCP Server (stdio)                                 │
│  2. session.call_tool("get_weather", {"city": "Shanghai"})│
│  3. 返回结果                                               │
└─────────────────────┬─────────────────────────────────────┘
                      │ tool_result
                      ▼
┌───────────────────────────────────────────────────────────┐
│              Backend: AgentInstance                        │
│  将tool_result添加到messages，再次调用LLM                   │
└─────────────────────┬─────────────────────────────────────┘
                      │
                      ▼
┌───────────────────────────────────────────────────────────┐
│                  OpenAI API (GPT-4)                        │
│  基于tool_result生成自然语言回复                            │
└─────────────────────┬─────────────────────────────────────┘
                      │ final_response
                      ▼
┌───────────────────────────────────────────────────────────┐
│              Electron Frontend                             │
│  显示: "根据实时天气数据，上海目前天气晴朗，温度22°C。"       │
└───────────────────────────────────────────────────────────┘
```

## 🎯 实现步骤

### Phase 1: 数据库和基础架构
1. ✅ 创建 agent_tools 表
2. ✅ 实现 ToolConverter (工具格式转换)
3. ✅ 实现 ToolRouter (工具执行路由)

### Phase 2: 后端API
4. ✅ 扩展 ToolExecutor.execute_mcp_tool()
5. ✅ 添加 GET /api/agent/{id}/tools API
6. ✅ 添加 POST /api/agent/{id}/tools API
7. ✅ 添加 GET /api/agent/{id}/available-tools API
8. ✅ 修改 AgentInstance.load_tools_from_db()
9. ✅ 修改 AgentInstance.chat() 支持tool calling

### Phase 3: 前端集成
10. ✅ 实现 Agent设置界面的工具配置选项卡
11. ✅ 实现 agentApi.js 的工具相关API调用
12. ✅ 实现 聊天界面的工具调用显示
13. ✅ 实现 工具调用流式显示（SSE）

### Phase 4: 测试
14. ✅ 测试 Plugin 调用
15. ✅ 测试 MCP 调用
16. ✅ 测试 Function 调用
17. ✅ 测试 Skill 调用
18. ✅ 端到端测试

## 📝 注意事项

1. **工具命名规范**：
   - Plugin: `plugin_{plugin_id}`
   - MCP Tool: `mcp_{mcp_id}_{tool_name}`
   - Function: `function_{function_id}`
   - Skill: `skill_{skill_id}`

2. **错误处理**：
   - 工具执行失败时返回错误信息给LLM
   - LLM可以根据错误信息重试或提示用户

3. **权限控制**：
   - 某些工具可能需要用户确认（confirm_needed=1）
   - 前端弹窗确认后再执行

4. **性能优化**：
   - Agent工具列表缓存
   - MCP连接池复用
   - 工具执行超时控制

5. **兼容性**：
   - 保持现有Agent功能不变
   - 工具是可选的，没有配置工具的Agent仍可正常使用

---

**设计完成时间**: 2026-01-15
**预计实现时间**: 2-3小时
**复杂度**: ⭐⭐⭐⭐ (中高)
