# A2A 协议调用测试指南

本文档详细说明如何通过 A2A 协议发现和调用 Agent 的技能。

---

## 概述

A2A (Agent-to-Agent) 协议是 Google 定义的 Agent 间通信标准。本平台完全兼容 A2A v0.3 规范。

### 调用流程

```
1. 发现 Agent → 获取 Agent Card
2. 查看技能 → 了解可用能力
3. 调用技能 → 发送任务请求
4. 获取结果 → 处理响应
```

---

## 第一步：启动 A2A 服务器

在终端中运行：

```bash
cd /root/sharedata3/ai-sns-el
python tests/run_a2a_server.py --port 8000
```

输出应该显示：
```
============================================================
  AI-SNS A2A Protocol Server
============================================================
  Server: http://0.0.0.0:8000
  Agent Card: http://localhost:8000/.well-known/agent.json
  JSON-RPC: http://localhost:8000/a2a/rpc
  REST API: http://localhost:8000/a2a/tasks
============================================================
```

---

## 第二步：发现 Agent（获取 Agent Card）

### 方式 1：使用 curl

```bash
curl http://localhost:8000/.well-known/agent.json
```

### 方式 2：使用 Python

```python
import requests

response = requests.get("http://localhost:8000/.well-known/agent.json")
agent_card = response.json()

print(f"Agent Name: {agent_card['name']}")
print(f"Protocol Version: {agent_card['protocolVersion']}")
print(f"Capabilities: {agent_card['capabilities']}")
```

### Agent Card 返回示例

```json
{
  "name": "AI-SNS Agent Platform",
  "description": "AI Agent Open Platform supporting A2A and MCP protocols",
  "url": "http://localhost:8000/a2a",
  "version": "1.0.0",
  "protocolVersion": "0.3",
  "capabilities": {
    "streaming": true,
    "pushNotifications": true,
    "stateTransitionHistory": false
  },
  "skills": [
    {
      "id": "chat",
      "name": "General Chat",
      "description": "General conversation and Q&A with AI",
      "tags": ["conversation", "qa", "general"],
      "inputModes": ["text"],
      "outputModes": ["text"]
    },
    // ... 更多技能
  ]
}
```

---

## 第三步：查看可用技能

当前平台提供以下技能：

| 技能 ID | 名称 | 描述 | 输入模式 | 输出模式 |
|---------|------|------|----------|----------|
| `chat` | General Chat | 通用对话和问答 | text | text |
| `code-execution` | Code Execution | 安全执行 Python 代码 | text, file | text, file |
| `web-search` | Web Search | 网络信息搜索 | text | text |
| `file-analysis` | File Analysis | 文件分析处理 | text, file | text, file |

### 查看技能示例

```python
import requests

response = requests.get("http://localhost:8000/.well-known/agent.json")
agent_card = response.json()

print("可用技能列表:")
for skill in agent_card['skills']:
    print(f"\n{skill['id']}:")
    print(f"  名称: {skill['name']}")
    print(f"  描述: {skill['description']}")
    print(f"  示例: {skill.get('examples', [])}")
```

---

## 第四步：调用技能

### 方式 1：JSON-RPC 2.0（推荐）

这是 Google A2A 规范的标准方法。

#### 请求格式

```bash
curl -X POST http://localhost:8000/a2a/rpc \
  -H "Content-Type: application/json" \
  -d '{
    "jsonrpc": "2.0",
    "method": "tasks/send",
    "params": {
      "id": "task-001",
      "message": {
        "role": "user",
        "parts": [
          {"type": "text", "text": "你好，介绍一下你有什么技能"}
        ]
      },
      "metadata": {
        "skill_id": "chat"
      }
    },
    "id": 1
  }'
```

#### Python 示例

```python
import requests

# JSON-RPC 请求
rpc_request = {
    "jsonrpc": "2.0",
    "method": "tasks/send",
    "params": {
        "id": "task-001",
        "message": {
            "role": "user",
            "parts": [
                {"type": "text", "text": "你好，介绍一下你有什么技能"}
            ]
        },
        "metadata": {
            "skill_id": "chat"  # 指定使用 chat 技能
        }
    },
    "id": 1
}

response = requests.post(
    "http://localhost:8000/a2a/rpc",
    json=rpc_request
)

result = response.json()
print(result)
```

#### 响应格式

```json
{
  "jsonrpc": "2.0",
  "result": {
    "id": "task-001",
    "sessionId": "",
    "status": {
      "state": "completed",
      "message": "Task completed successfully",
      "timestamp": "2026-01-04T12:00:00"
    },
    "history": [
      {
        "role": "user",
        "parts": [{"type": "text", "text": "你好，介绍一下你有什么技能"}]
      },
      {
        "role": "agent",
        "parts": [{"type": "text", "text": "我是 AI-SNS Agent，具有以下技能：..."}]
      }
    ]
  },
  "id": 1
}
```

### 方式 2：REST API

```bash
curl -X POST http://localhost:8000/a2a/tasks \
  -H "Content-Type: application/json" \
  -d '{
    "messages": [
      {"role": "user", "content": "帮我执行 Python 代码: print(2+2)"}
    ],
    "metadata": {
      "skill_id": "code-execution"
    }
  }'
```

---

## 第五步：获取任务状态

对于长时间运行的任务，可以查询状态：

### JSON-RPC 方式

```bash
curl -X POST http://localhost:8000/a2a/rpc \
  -H "Content-Type: application/json" \
  -d '{
    "jsonrpc": "2.0",
    "method": "tasks/get",
    "params": {
      "id": "task-001"
    },
    "id": 2
  }'
```

### REST API 方式

```bash
curl http://localhost:8000/a2a/tasks/task-001
```

---

## 完整测试脚本

运行交互式测试客户端：

```bash
cd /root/sharedata3/ai-sns-el
python tests/test_a2a_client.py --url http://localhost:8000
```

运行快速测试：

```bash
python tests/test_a2a_client.py --url http://localhost:8000 --quick
```

---

## 支持的 JSON-RPC 方法

| 方法 | 描述 |
|------|------|
| `tasks/send` | 发送任务并等待完成 |
| `tasks/sendSubscribe` | 发送任务并订阅流式更新 |
| `tasks/get` | 获取任务状态 |
| `tasks/cancel` | 取消任务 |
| `tasks/pushNotification/set` | 设置 Webhook 通知 |
| `tasks/pushNotification/get` | 获取 Webhook 配置 |

---

## 错误处理

JSON-RPC 错误代码：

| 代码 | 含义 |
|------|------|
| -32700 | Parse error - 无效的 JSON |
| -32600 | Invalid Request - 无效的请求格式 |
| -32601 | Method not found - 方法不存在 |
| -32602 | Invalid params - 参数无效 |
| -32000 | Task not found - 任务不存在 |

---

## 流程图

```
┌─────────────────┐
│  Client (你)     │
└────────┬────────┘
         │
         │ 1. GET /.well-known/agent.json
         ▼
┌─────────────────┐
│  发现 Agent      │ ─────────────────────────────┐
│  获取 Agent Card │                               │
└────────┬────────┘                               │
         │                                         │
         │ 2. 解析技能列表                          │
         ▼                                         │
┌─────────────────┐                               │
│  查看可用技能    │                               │
│  - chat         │                               │
│  - code-exec    │                               │
│  - web-search   │                               │
│  - file-analysis│                               │
└────────┬────────┘                               │
         │                                         │
         │ 3. POST /a2a/rpc (tasks/send)          │
         ▼                                         │
┌─────────────────┐                               │
│  调用技能        │                               │
│  发送 JSON-RPC   │                               │
└────────┬────────┘                               │
         │                                         │
         │ 4. 获取响应                             │
         ▼                                         │
┌─────────────────┐                               │
│  处理结果        │ ◄────────────────────────────┘
└─────────────────┘
```

---

## 问题排查

1. **服务器无法启动**
   - 检查端口是否被占用: `lsof -i :8000`
   - 杀死占用进程: `fuser -k 8000/tcp`

2. **Agent Card 返回 404**
   - 确认 `static/.well-known/agent.json` 文件存在

3. **JSON-RPC 返回 Method not found**
   - 确认方法名正确，如 `tasks/send` 而非 `task/send`

4. **连接超时**
   - 检查防火墙设置
   - 确认服务器正在运行

---

## 下一步

- 集成到你的 Agent 客户端
- 使用 gRPC 进行流式通信
- 设置 Webhook 接收异步通知
