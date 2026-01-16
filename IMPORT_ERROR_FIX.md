# 导入错误修复

## 错误信息
```
ERROR:backend.modules.chat.service:Error getting conversations: name 'query_AIChatMessages_All' is not defined
```

## 问题原因

在 `backend/modules/chat/service.py` 的导入语句中，使用了别名：

```python
from db.DBFactory import (
    query_AIChatMessages_All as query_AIChatMessages,  # ✅ 使用别名
    ...
)
```

但在代码中错误地使用了原始名称 `query_AIChatMessages_All`，而应该使用别名 `query_AIChatMessages`。

## 修复内容

修改了 `backend/modules/chat/service.py` 的三处调用：

1. **第199行** - `get_conversations()` 方法
2. **第167行** - `get_chat_history()` 方法
3. **第241行** - `get_conversation_messages()` 方法

所有调用都改为使用正确的别名，并添加 `limit` 参数：

```python
# 修复前：
conversations = query_AIChatMessages_All(limit=limit, **query_params)  # ❌ 函数名错误

# 修复后：
conversations = query_AIChatMessages(limit=limit, **query_params)  # ✅ 使用别名
```

## 验证

重启后端服务器后，API应该正常工作：

```bash
# 重启服务
python3 api_server.py

# 测试API
curl "http://localhost:8788/api/chat/conversations?agent_id=1&limit=50"
```

应该返回正确的数据，不再有错误日志。
