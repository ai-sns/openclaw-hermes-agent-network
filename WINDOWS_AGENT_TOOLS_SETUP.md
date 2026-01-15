# Agent工具配置指南 (Windows)

## 问题原因

您遇到的问题是：**Agent 1 没有关联任何工具**

从日志可以看到：
```
INFO:backend.modules.agent.agent_instance:Agent Altman (ID: 1) 已加载 0 个工具
INFO:backend.modules.agent.agent_instance:准备了 0 个工具用于LLM调用
```

## 解决方案

### 方法1: 使用自动化脚本 (推荐)

1. **停止 api_server.py**
   - 关闭运行 api_server.py 的命令行窗口
   - 或按 `Ctrl+C` 停止

2. **运行配置脚本**
   ```cmd
   setup_agent_tools.bat
   ```

3. **重启 api_server.py**
   ```cmd
   python api_server.py
   ```

### 方法2: 手动执行SQL

1. **停止 api_server.py**

2. **执行SQL脚本**
   ```cmd
   sqlite3 db\db.sqlite < add_agent_tools.sql
   ```

3. **重启 api_server.py**

## 已配置的工具

执行配置后，Agent 1 将拥有以下工具：

### 1. 高德地图 MCP (ZP2025061314162230222)
**功能**: 查询地点、规划路线、导航

**测试用例**:
- "查询北京到上海的路线"
- "天安门在哪里？"
- "推荐上海的景点"

### 2. DuckDuckGo 搜索 MCP (LD2025061314404887010)
**功能**: 网络搜索、查询信息

**测试用例**:
- "搜索2024年的重要新闻"
- "查询Python教程"
- "什么是量子计算？"

## 验证配置

配置完成后，重启 api_server.py，您应该看到类似的日志：

```
INFO:backend.modules.agent.agent_instance:Agent Altman (ID: 1) 已加载 2 个工具
INFO:backend.modules.agent.agent_instance:已加载工具: mcp_ZP2025061314162230222_search_poi, mcp_LD2025061314404887010_search
```

## 测试对话

### 测试案例1: 地图查询
```
用户: 查询北京到上海的驾车路线
预期: Agent调用高德地图MCP，返回路线信息
```

### 测试案例2: 网络搜索
```
用户: 搜索一下量子计算的最新进展
预期: Agent调用DuckDuckGo MCP，返回搜索结果
```

### 测试案例3: 普通对话
```
用户: 你好，介绍一下自己
预期: Agent直接回答，不调用工具
```

## 添加更多工具

如果您想添加其他类型的工具，请编辑 `add_agent_tools.sql`：

### 添加Plugin工具
```sql
INSERT INTO agent_tools (agent_id, tool_type, tool_id, enabled, priority)
VALUES (1, 'plugin', 'YOUR_PLUGIN_ID', 1, 8);
```

### 添加Function工具
```sql
INSERT INTO agent_tools (agent_id, tool_type, tool_id, enabled, priority)
VALUES (1, 'function', 'YOUR_FUNCTION_ID', 1, 7);
```

### 添加Skill工具
```sql
INSERT INTO agent_tools (agent_id, tool_type, tool_id, enabled, priority)
VALUES (1, 'skill', 'YOUR_SKILL_ID', 1, 6);
```

## 查看可用工具

### 查看所有Plugin
```cmd
sqlite3 db\db.sqlite "SELECT plugin_id, name, description FROM pluginmng;"
```

### 查看所有MCP
```cmd
sqlite3 db\db.sqlite "SELECT mcp_id, name FROM mcp_mng;"
```

### 查看所有Function
```cmd
sqlite3 db\db.sqlite "SELECT function_id, name FROM function_mng;"
```

### 查看所有Skill
```cmd
sqlite3 db\db.sqlite "SELECT skill_id, name FROM skill_mng;"
```

## 工具优先级说明

`priority` 字段控制工具的优先级（数字越大优先级越高）：

- **10**: 最高优先级（地图查询）
- **9**: 高优先级（搜索）
- **8**: 中优先级
- **5**: 普通优先级
- **1**: 低优先级

## 故障排除

### 问题1: 数据库被锁定
**症状**: `database is locked`
**解决**: 确保 api_server.py 已完全停止

### 问题2: 工具仍然显示0个
**检查**:
1. 确认SQL执行成功
2. 确认已重启 api_server.py
3. 检查数据库路径是否正确（db/db.sqlite）

### 问题3: 工具调用失败
**检查**:
1. 查看api_server.py的日志
2. 确认MCP Server文件存在且可执行
3. 检查工具ID是否正确

## 进阶配置

### 为不同Agent配置不同工具

```sql
-- Agent 1: 通用助手（地图+搜索）
INSERT INTO agent_tools (agent_id, tool_type, tool_id, enabled, priority)
VALUES (1, 'mcp', 'ZP2025061314162230222', 1, 10);

-- Agent 2: 专业搜索助手（只有搜索）
INSERT INTO agent_tools (agent_id, tool_type, tool_id, enabled, priority)
VALUES (2, 'mcp', 'LD2025061314404887010', 1, 10);
```

### 临时禁用工具

```sql
-- 禁用某个工具（不删除配置）
UPDATE agent_tools
SET enabled = 0
WHERE agent_id = 1 AND tool_id = 'ZP2025061314162230222';

-- 重新启用
UPDATE agent_tools
SET enabled = 1
WHERE agent_id = 1 AND tool_id = 'ZP2025061314162230222';
```

## API管理工具

配置完成后，也可以通过API管理工具：

### 获取Agent的工具列表
```bash
curl http://localhost:8788/api/agent/1/tools
```

### 更新Agent的工具配置
```bash
curl -X POST http://localhost:8788/api/agent/1/tools \
  -H "Content-Type: application/json" \
  -d '{
    "tools": [
      {"tool_type": "mcp", "tool_id": "ZP2025061314162230222", "priority": 10},
      {"tool_type": "mcp", "tool_id": "LD2025061314404887010", "priority": 9}
    ]
  }'
```

### 获取所有可用工具
```bash
curl http://localhost:8788/api/agent/1/available-tools
```

## 相关文档

- `AGENT_TOOL_CALLING_INTEGRATION_COMPLETE.md` - 完整的技术实现文档
- `AGENT_INSTANCE_INTEGRATION_PLAN.md` - 集成方案
- `test_agent_tool_calling.py` - 测试脚本

## 技术支持

如遇到问题，请查看：
1. api_server.py 的完整日志
2. 数据库中的工具配置: `SELECT * FROM agent_tools WHERE agent_id = 1;`
3. Agent加载日志中的工具数量

---

**配置完成后，Agent将能够智能地调用工具来完成任务！** 🎉
