# ✅ 工具加载问题已修复

## 问题摘要

Agent原本应该加载10个工具,但只能加载0个或7个。经过调试,发现并修复了3个关键问题。

## 修复的问题

### 问题1: 数据库路径不匹配
**症状**: Agent加载0个工具
**原因**: 后端配置使用 `data/db.sqlite`,但工具配置在 `db/db.sqlite`
**修复**: 将 `db/db.sqlite` (包含10个工具配置) 复制到 `data/db.sqlite`

```bash
cp db/db.sqlite data/db.sqlite
```

### 问题2: Repository查询方法错误
**症状**: AgentService无法找到工具记录
**原因**: `get_by_id()` 查询主键 `id`,但应该查询自定义ID字段如 `mcp_id`, `plugin_id` 等
**文件**: `backend/modules/agent/service.py`
**修复**: 改用 `get_one()` 方法并传入正确的字段名

```python
# 修复前:
tool_obj = plugin_repo.get_by_id(tool_id)  # ❌ 错误

# 修复后:
tool_obj = plugin_repo.get_one(plugin_id=tool_id)  # ✅ 正确
```

同样修复了 `mcp_repo.get_one(mcp_id=...)`, `function_repo.get_one(function_id=...)`, `skill_repo.get_one(skill_id=...)`

### 问题3: Repository没有to_dict()方法
**症状**: `AttributeError: 'PluginMngRepository' object has no attribute 'to_dict'`
**原因**: 调用了不存在的方法
**文件**: `backend/modules/agent/service.py`
**修复**: 使用SQLAlchemy的列遍历手动转换为字典

```python
# 修复前:
tool_detail = plugin_repo.to_dict(tool_obj)  # ❌ 方法不存在

# 修复后:
tool_detail = {c.name: getattr(tool_obj, c.name) for c in tool_obj.__table__.columns}  # ✅ 正确
```

### 问题4: MCP工具没有tools列表
**症状**: MCP工具无法被ToolConverter转换
**原因**: ToolConverter期望MCP有 `tools` 字段,但数据库记录没有
**文件**: `backend/modules/agent/tool_converter.py`
**修复**: 当MCP没有tools列表时,创建一个通用的execute工具

```python
# 修复后的逻辑:
if isinstance(mcp_tools, list) and len(mcp_tools) > 0:
    for mcp_tool in mcp_tools:
        openai_tools.append(cls.mcp_to_openai(tool, mcp_tool))
else:
    # 创建通用工具
    generic_tool = {
        "name": "execute",
        "description": f"Execute {mcp_name} MCP tool",
        "inputSchema": {...}
    }
    openai_tools.append(cls.mcp_to_openai(tool, generic_tool))
```

## 验证结果

```
✅ Agent: Altman
✅ Tools loaded: 10/10

 1. mcp_ZP2025061314162230222_execute     - 高德地图stdio
 2. mcp_LD2025061314404887010_execute     - duckduckgo
 3. mcp_BK2025061220454036750_execute     - mcp001
 4. function_GT2654780435432639652        - get_weather
 5. function_KL2024091719363863671        - convert_rmb_to_usd_v2
 6. function_SK2025022722375473913        - getUserName
 7. plugin_AK2024Y5Q717U20711095          - Mindmap
 8. plugin_EK202405K7170A7T190951         - Flowchart
 9. plugin_14                             - Control the Chrome
10. skill_CN2024090916031485895           - cjrok-python-skill
```

## 修改的文件

1. **data/db.sqlite** - 替换为包含10个工具配置的版本
2. **backend/modules/agent/service.py** - 修复Repository查询和to_dict转换
3. **backend/modules/agent/tool_converter.py** - 添加MCP通用工具支持

## 下一步: 实际测试

现在所有10个工具都能加载,下一步需要:
1. 运行 `test_all_tools_live.py` 进行真实AI对话测试
2. 验证每种工具类型都能被正确调用
3. 确认工具执行结果正确返回

## 测试命令

```bash
python3 test_all_tools_live.py
```

测试脚本会:
- 测试所有10个工具
- 通过真实AI对话触发工具调用
- 记录测试结果到 `/tmp/agent_tools_test_report.json`

---

修复时间: 2026-01-15
修复者: Claude Code
状态: ✅ 工具加载已完成,等待实际调用测试
