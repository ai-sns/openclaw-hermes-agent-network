# ORM模型字段缺失修复

## 错误信息
```
ERROR:backend.modules.chat.service:Error getting conversations:
Entity namespace for "ai_chat_messages" has no property "agent_id"
```

## 问题原因

项目中有**两个** `AIChatMessages` 模型定义：

1. **`backend/database/models/chat.py`** - 新的模型定义，包含 `agent_id` 字段 ✅
2. **`db/DBFactory.py`** - 旧的模型定义，**缺少** `agent_id` 字段 ❌

`service.py` 使用的是 `db/DBFactory.py` 中的旧模型（通过导入语句）：
```python
from db.DBFactory import (
    query_AIChatMessages_All as query_AIChatMessages,
    ...
)
```

因此SQLAlchemy无法识别 `agent_id` 字段。

## 修复方案

在 `db/DBFactory.py` 的 `AIChatMessages` 类定义中添加 `agent_id` 字段：

```python
class AIChatMessages(Base):
    __tablename__ = 'ai_chat_messages'
    id = Column(Integer, primary_key=True, autoincrement=True)
    conversation_id = Column(String(50), doc="对话id")
    agent_id = Column(Integer, default=None, doc="Agent ID (多Agent支持)")  # ✅ 添加此行
    flag = Column(Integer, doc="0为发送，1为接收")
    # ... 其他字段
```

## 验证步骤

1. **重启后端服务器**（必须！）
```bash
# 停止当前服务（Ctrl+C）
python3 api_server.py
```

2. **测试API**
```bash
curl "http://localhost:8788/api/chat/conversations?agent_id=1&limit=50"
```

应该返回正确的数据，不再有错误日志。

3. **在Electron应用中测试**
   - 打开Agent页面
   - 点击某个Agent
   - Chat List应该正确显示对话列表

## 技术说明

这个问题说明了维护两套ORM模型定义的风险。长期来看，建议：

1. 统一使用 `backend/database/models/` 下的新模型
2. 逐步迁移 `db/DBFactory.py` 中的查询函数到新的repository层
3. 或者确保两处模型定义保持同步

当前的临时方案是在旧模型中添加缺失的字段，以保持向后兼容。
