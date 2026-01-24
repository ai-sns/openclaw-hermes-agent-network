# 异步函数调用者缺少 await 修复指南

## ❌ 问题

```
RuntimeWarning: coroutine 'AISocialEngine.ask_agent_to_run_a_tool' was never awaited
```

## 🔍 问题原因

在非 async 函数中调用了 async def 函数，但没有使用 `await`。

## 📋 需要修复的函数列表

| 行号 | 函数名 | 调用的异步函数 | 需要添加 |
|------|--------|-----------|-----------|----------|
| 1378 | `handle_event_before_decistion` | `ask_agent_to_run_a_tool` | ✅ 已修复 |
| 1065 | `handle_event_after_decistion` | `ask_agent_to_run_a_tool` | 待修复 |
| 1081 | `handle_event_receive_msg` | `ask_agent_to_run_a_tool` | 待修复 |
| 1093 | `handle_event_before_send_msg` | `ask_agent_to_run_a_tool` | 待修复 |
| 1258 | `communicate_with_a_people` | `ask_agent_start_to_talk_to_a_people` | ✅ 已修复 |
| 1265 | `sell_to_a_people` | `ask_agent_start_to_sell_to_a_people` | 待修复 |
| 1270 | `buy_from_a_people` | `ask_agent_start_to_buy_from_a_people` | 待修复 |
| 1748 | `parse_agent_instruction_for_process_human_instruction` | `ask_agent_to_pick_people_list` | 待修复 |
| 1755 | `parse_agent_instruction_for_process_human_instruction` | `ask_agent_to_pick_place_list` | 待修复 |
| 1767 | `parse_agent_instruction_for_process_human_instruction` | `ask_agent_to_pick_a_tool` | 待修复 |
| 1883 | `call_tool` | `ask_agent_to_run_a_tool` | 待修复 |
| 2497 | `handle_pay_received` | `ask_agent_to_run_a_tool` | 待修复 |
| 2615 | `tool_trade_bargain_for_buyer` | `ask_agent_to_bargain_for_buyer` | 待修复 |
| 2619 | `tool_trade_bargain_for_seller` | `ask_agent_to_bargain_for_seller` | 待修复 |

**共 13 个函数需要修复（已修复 2 个）**

## 🔧 修复方法

### 方法 1：将调用者改为 async 函数（推荐）

```python
# 修改前
def handle_event_before_decistion(self, tool_name, ask_content):
    ...
    self.ask_agent_to_run_a_tool(tool_id, tool_name, what_to_do)

# 修改后
async def handle_event_before_decistion(self, tool_name, ask_content):
    ...
    await self.ask_agent_to_run_a_tool(tool_id, tool_name, what_to_do)
```

### 方法 2：使用 asyncio.create_task（如果不需要等待结果）

```python
# 修改前
def handle_event_before_decistion(self, tool_name, ask_content):
    ...
    asyncio.create_task(self.ask_agent_to_run_a_tool(tool_id, tool_name, what_to_do))

# 修改后（不需要改变）
def handle_event_before_decistion(self, tool_name, ask_content):
    ...
    asyncio.create_task(self.ask_agent_to_run_a_tool(tool_id, tool_name, what_to_do))
```

## 📝 批量修复示例

使用搜索替换，例如：

```bash
# 查找所有需要修复的函数
grep -n "def handle_event_before_decistion\|def handle_event_after_decistion\|def handle_event_receive_msg" ai_social_engine_adapter.py

# 手动修改或使用脚本批量替换
```

## 🚀 修复后的验证

### 1. Python 语法检查
```bash
python -m py_compile backend/modules/sns/ai_social_engine_adapter.py
```

### 2. 运行服务器测试
```bash
python api_server.py
```

### 3. 检查日志
```
不应该再有：
RuntimeWarning: coroutine '...' was never awaited
```

## ⚠️ 注意事项

1. **调用链**: 确保所有调用者都已修复
2. **async 上下文**: async 函数必须在 async 上下文中被调用
3. **返回值**: 如果需要返回值，必须使用 `await`
4. **后台任务**: 如果不需要等待，使用 `asyncio.create_task()`

## 📚 相关文档

- `ASYNC_AWAIT_FIX_COMPLETE.md` - 异步函数定义修复
- `ASYNC_INIT_FIX_COMPLETE.md` - async_init 方法添加
- 本文档 - 调用者修复指南

---

**剩余需要修复的函数：11 个**
