# Electron Agent 聊天历史管理 - 使用指南

## 📋 功能概述

实现了类似 OpenAI ChatGPT 的聊天历史管理功能：
- ✅ 自动保存聊天内容到数据库
- ✅ Chat List 从数据库加载历史记录
- ✅ 点击历史记录可以重新打开对话
- ✅ 支持新建对话和多对话切换

## 🚀 快速开始

### 1. 启动后端服务器

```bash
# 使用 Python 3
python3 api_server.py

# 或
python api_server.py
```

服务器将在 http://localhost:8788 启动

### 2. 启动 Electron 应用

```bash
npm start
```

### 3. 使用聊天功能

1. **发送消息**: 在输入框输入消息，按 Enter 或点击发送按钮
2. **查看历史**: 左侧 Chat List 显示所有对话
3. **切换对话**: 点击任意历史对话即可加载
4. **新建对话**: 点击 "New Chat" 按钮

## 🔍 如何验证

### 方法1: 通过界面测试

1. 打开 Agent 页面
2. 发送一条消息（例如："你好"）
3. 等待 AI 回复完成
4. 刷新页面
5. 检查左侧 Chat List 是否显示新对话
6. 点击该对话，验证是否正确加载

### 方法2: 查看数据库

```bash
sqlite3 db/db.sqlite

# 查看最近的聊天记录
SELECT
    conversation_id,
    flag,
    substr(content, 1, 50) as content,
    create_time
FROM ai_chat_messages
ORDER BY create_time DESC
LIMIT 10;

# 查看对话列表
SELECT DISTINCT
    conversation_id,
    title,
    create_time
FROM ai_chat_messages
WHERE is_first = 1
ORDER BY create_time DESC;
```

### 方法3: 测试 API

```bash
# 获取对话列表
curl http://localhost:8788/api/chat/conversations

# 获取特定对话的消息
curl http://localhost:8788/api/chat/conversations/{conversation_id}
```

## 📊 数据结构

### Conversation ID 格式
```
conv_{timestamp}_{random_string}
例如: conv_1705012345678_a3b4c5d6e
```

### 数据库表: ai_chat_messages

| 字段 | 类型 | 说明 |
|------|------|------|
| id | INTEGER | 主键 |
| conversation_id | VARCHAR(50) | 对话ID |
| flag | INTEGER | 0=用户消息, 1=AI消息 |
| title | TEXT | 对话标题（仅第一条消息） |
| content | TEXT | 消息内容 |
| role | VARCHAR(20) | user/assistant |
| create_time | DATETIME | 创建时间 |
| is_first | BOOLEAN | 是否为对话首条消息 |

## 🔧 修改的文件

### 后端 (Python)
1. `backend/modules/chat/schemas.py` - 添加 conversation_id
2. `backend/modules/chat/streaming.py` - 保存消息到数据库
3. `backend/modules/chat/service.py` - 添加查询方法
4. `backend/modules/chat/router.py` - 添加新API端点

### 前端 (JavaScript)
1. `renderer/js/modules/agent/agentState.js` - 对话ID管理
2. `renderer/js/modules/agent/agentApi.js` - API调用
3. `renderer/js/modules/agent/agentHandlers.js` - 业务逻辑

## 🆕 新增 API

### 1. 获取对话列表
```
GET /api/chat/conversations?limit=50
```

**响应**:
```json
{
  "success": true,
  "data": [
    {
      "conversation_id": "conv_1705012345678_abc",
      "title": "你好，我想了解...",
      "last_message_time": "2024-01-11 20:30:00",
      "first_message": "你好，我想了解一下..."
    }
  ]
}
```

### 2. 获取对话消息
```
GET /api/chat/conversations/{conversation_id}
```

**响应**:
```json
{
  "success": true,
  "data": [
    {
      "id": 1,
      "role": "user",
      "content": "你好",
      "create_time": "2024-01-11 20:30:00"
    },
    {
      "id": 2,
      "role": "assistant",
      "content": "你好！我是AI助手...",
      "create_time": "2024-01-11 20:30:05"
    }
  ]
}
```

## 💡 工作流程

```
用户发送消息
    ↓
前端生成/获取 conversation_id
    ↓
调用 POST /api/chat/stream
    ↓
后端流式响应 + 累积内容
    ↓
流式结束后自动保存到数据库
    ↓
前端刷新对话列表
    ↓
用户可点击查看历史对话
```

## 🐛 故障排查

### 问题1: 对话列表不显示
- 检查后端服务器是否运行
- 检查数据库是否有记录
- 查看浏览器控制台错误

### 问题2: 点击对话无法加载
- 检查 conversation_id 是否正确
- 验证 API `/api/chat/conversations/{id}` 是否返回数据
- 查看控制台日志

### 问题3: 消息未保存到数据库
- 确认流式聊天完整结束
- 检查 conversation_id 是否传递
- 查看后端日志

## 📝 注意事项

1. **数据库位置**: 确保 `db/db.sqlite` 文件存在且有写权限
2. **Python版本**: 需要 Python 3.7+
3. **对话ID**: 每次新建对话自动生成，不需要手动管理
4. **性能**: 默认加载最近50个对话，可调整

## 🎉 完成状态

- ✅ 后端API实现
- ✅ 前端状态管理
- ✅ 数据库保存
- ✅ 对话列表加载
- ✅ 历史对话查看
- ✅ 新建对话功能
- ✅ 语法错误修复

## 📞 支持

如有问题，请检查：
1. 后端日志输出
2. 浏览器控制台
3. 数据库内容
4. API响应

Happy Chatting! 🚀
