# 🎯 Agent全工具类型测试指南

## 📊 已配置工具清单

Agent 1 (Altman) 现已配置 **10个工具**，覆盖所有4种类型：

### 🔵 1. MCP工具 (3个) - 优先级 20-18

| ID | 工具名称 | 工具ID | 优先级 | 功能描述 |
|----|---------|--------|--------|----------|
| 4 | 高德地图stdio | ZP2025061314162230222 | 20 | 查询地点、规划路线、导航 |
| 5 | DuckDuckGo | LD2025061314404887010 | 19 | 网络搜索、实时信息查询 |
| 6 | mcp001 | BK2025061220454036750 | 18 | 通用MCP工具 |

### 🟢 2. Function工具 (3个) - 优先级 17-15

| ID | 工具名称 | 工具ID | 优先级 | 功能描述 |
|----|---------|--------|--------|----------|
| 7 | get_weather | GT2654780435432639652 | 17 | 获取指定城市天气 |
| 8 | convert_rmb_to_usd_v2 | KL2024091719363863671 | 16 | 人民币转美元 |
| 9 | getUserName | SK2025022722375473913 | 15 | 获取用户名称 |

### 🟡 3. Plugin工具 (3个) - 优先级 14-12

| ID | 工具名称 | 工具ID | 优先级 | 功能描述 |
|----|---------|--------|--------|----------|
| 10 | Mindmap | AK2024Y5Q717U20711095 | 14 | 创建思维导图 |
| 11 | Flowchart | EK202405K7170A7T190951 | 13 | 创建流程图 |
| 12 | Control the Chrome | 14 | 12 | 控制Chrome浏览器 |

### 🔴 4. Skill工具 (Computer Use) (1个) - 优先级 11

| ID | 工具名称 | 工具ID | 优先级 | 功能描述 |
|----|---------|--------|--------|----------|
| 13 | cjrok-python-skill | CN2024090916031485895 | 11 | Python代码执行技能 |

---

## 🚀 操作步骤

### 1. 在Windows上重启服务

```cmd
# 1. 停止当前的 api_server.py (Ctrl+C)

# 2. 从Linux同步数据库到Windows
#    数据库路径: db/db.sqlite

# 3. 重启服务
python api_server.py
```

### 2. 观察启动日志

应该看到：
```
INFO:backend.modules.agent.agent_instance:Agent Altman (ID: 1) 已加载 10 个工具
INFO:backend.modules.agent.agent_instance:已加载工具: mcp_ZP2025061314162230222_..., ...
```

---

## 🧪 测试用例（按类型）

### 测试1: MCP工具 - 地图查询 ⭐⭐⭐

**输入**:
```
帮我查一下从北京到上海的驾车路线
```

**预期行为**:
- Agent识别需要路线规划
- 调用工具: `mcp_ZP2025061314162230222_search_route`
- 返回: 路线信息（距离、时间、途经城市）

**日志关键词**:
```
[AgentInstance] 调用工具: mcp_ZP2025061314162230222_...
[ToolRouter] Executing mcp tool: ZP2025061314162230222/...
```

---

### 测试2: MCP工具 - 搜索 ⭐⭐⭐

**输入**:
```
搜索一下上海今天的天气怎么样
```

**预期行为**:
- Agent识别需要搜索天气
- 调用工具: `mcp_LD2025061314404887010_search`
- 返回: 搜索结果（天气信息）

**日志关键词**:
```
[AgentInstance] 调用工具: mcp_LD2025061314404887010_search
[ToolRouter] Executing mcp tool: LD2025061314404887010/search
```

---

### 测试3: Function工具 - 天气查询 ⭐⭐

**输入**:
```
查询一下北京的天气
```

**预期行为**:
- Agent识别需要查询天气
- 调用工具: `function_GT2654780435432639652`
- 返回: 天气数据

**日志关键词**:
```
[AgentInstance] 调用工具: function_GT2654780435432639652
[ToolRouter] Executing function: GT2654780435432639652
```

---

### 测试4: Function工具 - 货币转换 ⭐⭐

**输入**:
```
帮我把100元人民币换算成美元
```

**预期行为**:
- Agent识别需要货币转换
- 调用工具: `function_KL2024091719363863671`
- 参数: `{"amount": 100, "from": "RMB", "to": "USD"}`
- 返回: 美元金额

**日志关键词**:
```
[AgentInstance] 调用工具: function_KL2024091719363863671, 参数: {"amount": 100}
[ToolRouter] Executing function: KL2024091719363863671
```

---

### 测试5: Function工具 - 获取用户名 ⭐

**输入**:
```
我的用户名是什么？
```

**预期行为**:
- Agent识别需要获取用户信息
- 调用工具: `function_SK2025022722375473913`
- 返回: 用户名

**日志关键词**:
```
[AgentInstance] 调用工具: function_SK2025022722375473913
[ToolRouter] Executing function: SK2025022722375473913
```

---

### 测试6: Plugin工具 - 思维导图 ⭐⭐

**输入**:
```
帮我创建一个关于AI发展的思维导图
```

**预期行为**:
- Agent识别需要创建思维导图
- 调用工具: `plugin_AK2024Y5Q717U20711095`
- 返回: 思维导图文件或路径

**日志关键词**:
```
[AgentInstance] 调用工具: plugin_AK2024Y5Q717U20711095
[ToolRouter] Executing plugin: AK2024Y5Q717U20711095
```

---

### 测试7: Plugin工具 - 流程图 ⭐⭐

**输入**:
```
画一个登录流程的流程图
```

**预期行为**:
- Agent识别需要创建流程图
- 调用工具: `plugin_EK202405K7170A7T190951`
- 返回: 流程图文件

**日志关键词**:
```
[AgentInstance] 调用工具: plugin_EK202405K7170A7T190951
[ToolRouter] Executing plugin: EK202405K7170A7T190951
```

---

### 测试8: Plugin工具 - 控制浏览器 ⭐

**输入**:
```
帮我打开Chrome浏览器并访问百度
```

**预期行为**:
- Agent识别需要控制浏览器
- 调用工具: `plugin_14`
- 参数: `{"url": "https://www.baidu.com"}`
- 执行: 打开Chrome并导航到百度

**日志关键词**:
```
[AgentInstance] 调用工具: plugin_14
[ToolRouter] Executing plugin: 14
```

---

### 测试9: Skill工具 - Python代码执行 ⭐⭐⭐

**输入**:
```
帮我用Python计算1到100的和
```

**预期行为**:
- Agent识别需要执行Python代码
- 调用工具: `skill_CN2024090916031485895`
- 参数: `{"code": "print(sum(range(1, 101)))"}`
- 返回: 5050

**日志关键词**:
```
[AgentInstance] 调用工具: skill_CN2024090916031485895
[ToolRouter] Executing skill: CN2024090916031485895
```

---

### 测试10: 普通对话 (不调用工具) ⭐

**输入**:
```
你好，介绍一下自己
```

**预期行为**:
- Agent直接回答，不调用任何工具
- 日志中显示: `准备了 10 个工具用于LLM调用`
- 但不会有工具调用日志

---

## 📝 测试记录表

请在测试时填写：

| 测试编号 | 工具类型 | 输入内容 | 是否调用工具 | 调用的工具 | 返回结果 | 状态 |
|---------|---------|---------|------------|-----------|---------|------|
| 1 | MCP | 北京到上海路线 | ☐ | | | ☐ |
| 2 | MCP | 搜索天气 | ☐ | | | ☐ |
| 3 | Function | 查询天气 | ☐ | | | ☐ |
| 4 | Function | 货币转换 | ☐ | | | ☐ |
| 5 | Function | 获取用户名 | ☐ | | | ☐ |
| 6 | Plugin | 思维导图 | ☐ | | | ☐ |
| 7 | Plugin | 流程图 | ☐ | | | ☐ |
| 8 | Plugin | 控制Chrome | ☐ | | | ☐ |
| 9 | Skill | Python代码 | ☐ | | | ☐ |
| 10 | 无 | 普通对话 | ☐ | | | ☐ |

---

## 🔍 故障排除

### 问题1: 仍显示0个工具

**检查**:
```cmd
# 确认数据库中有工具配置
sqlite3 db\db.sqlite "SELECT COUNT(*) FROM agent_tools WHERE agent_id = 1;"
# 应该返回: 10
```

**解决**:
- 确保已从Linux复制了最新的数据库
- 重启 api_server.py

### 问题2: 工具调用失败

**查看日志**:
```
ERROR:backend.modules.agent.tool_router:[ToolRouter] ... execution failed
```

**可能原因**:
1. **MCP工具**: MCP Server文件不存在或无法执行
2. **Function工具**: Function代码文件缺失
3. **Plugin工具**: Plugin文件路径错误
4. **Skill工具**: Skill配置或代码问题

**解决方法**:
- 查看完整的错误日志
- 检查对应工具在数据库中的配置
- 验证工具文件是否存在

### 问题3: LLM不调用工具

**可能原因**:
- 提问不明确，LLM认为不需要工具
- 工具描述不清楚，LLM不知道该用哪个

**解决方法**:
- 使用更明确的提问（如测试用例中的示例）
- 检查工具的description字段是否清晰

---

## 📊 预期日志示例

### 成功调用MCP工具:
```
INFO:backend.modules.agent.agent_instance:Agent Altman (ID: 1) 已加载 10 个工具
INFO:backend.modules.agent.agent_instance:准备了 10 个工具用于LLM调用
INFO:backend.modules.agent.agent_instance:[AgentInstance] 调用工具: mcp_LD2025061314404887010_search, 参数: {"query": "上海天气"}
INFO:backend.modules.agent.tool_router:[ToolRouter] Executing mcp tool: LD2025061314404887010/search
INFO:backend.modules.tools.tool_executor:[ToolExecutor] Executing MCP tool: search
INFO:httpx:HTTP Request: POST https://api.chatanywhere.tech/v1/chat/completions "HTTP/1.1 200 OK"
```

### 成功调用Function工具:
```
INFO:backend.modules.agent.agent_instance:[AgentInstance] 调用工具: function_GT2654780435432639652, 参数: {"city": "Beijing"}
INFO:backend.modules.agent.tool_router:[ToolRouter] Executing function: GT2654780435432639652
INFO:backend.modules.tools.tool_executor:[ToolExecutor] Executing function: get_weather
```

### 成功调用Plugin工具:
```
INFO:backend.modules.agent.agent_instance:[AgentInstance] 调用工具: plugin_AK2024Y5Q717U20711095, 参数: {"topic": "AI发展"}
INFO:backend.modules.agent.tool_router:[ToolRouter] Executing plugin: AK2024Y5Q717U20711095
INFO:backend.modules.tools.tool_executor:[ToolExecutor] Executing plugin: Mindmap
```

### 成功调用Skill工具:
```
INFO:backend.modules.agent.agent_instance:[AgentInstance] 调用工具: skill_CN2024090916031485895, 参数: {"code": "print(sum(range(1,101)))"}
INFO:backend.modules.agent.tool_router:[ToolRouter] Executing skill: CN2024090916031485895
INFO:backend.modules.tools.tool_executor:[ToolExecutor] Executing skill: cjrok-python-skill
```

---

## 🎯 测试目标

- ✅ 验证所有4种工具类型都能被正确识别
- ✅ 验证LLM能根据问题选择正确的工具
- ✅ 验证工具执行流程正常（转换→路由→执行）
- ✅ 验证工具返回结果能被LLM正确处理
- ✅ 验证优先级系统是否生效

---

## 📚 相关文档

- `AGENT_TOOL_CALLING_INTEGRATION_COMPLETE.md` - 技术实现详解
- `AGENT_TOOLS_CONFIGURED.md` - 配置说明
- `test_agent_tool_calling.py` - 自动化测试脚本

---

**🎉 配置完成！现在重启 api_server.py 开始测试吧！**

请在测试后反馈结果，特别是：
1. 哪些工具类型成功调用了
2. 哪些工具调用失败了（附上日志）
3. LLM是否能正确选择合适的工具
