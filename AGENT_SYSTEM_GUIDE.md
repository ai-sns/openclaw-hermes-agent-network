# Agent对象化系统 - 使用指南

## 概述

Agent对象化系统将每个Agent抽象成独立的对象实例，每个Agent拥有：
- 独立的AI大模型配置（API endpoint、API key、model name、temperature等）
- 独立的角色配置（system prompt、greeting message等）
- 独立的工具集（function calling）
- 独立的代码执行能力
- 独立的知识库访问
- 独立的对话记忆（memory）

## 系统架构

### 后端模块

```
backend/modules/agent/
├── agent_instance.py      # Agent实例类（核心）
├── agent_manager.py       # Agent管理器（单例）
├── chat_router.py         # Agent问答API路由
├── tool_executor.py       # 工具执行器
├── code_executor.py       # 代码执行器
├── router.py              # Agent CRUD API
├── service.py             # Agent业务逻辑
├── llm_router.py          # LLM配置管理
├── llm_service.py
├── role_router.py         # 角色配置管理
└── role_service.py
```

### API接口

#### 1. Agent问答接口

**非流式问答（按ID）**
```http
POST /api/agent/{agent_id}/chat
Content-Type: application/json

{
  "message": "你好",
  "conversation_id": "conv_123",  // 可选，用于区分不同对话
  "use_memory": true,              // 是否使用对话记忆
  "use_knowledge_base": true       // 是否使用知识库
}

Response:
{
  "success": true,
  "data": {
    "reply": "你好！我能帮你什么？",
    "conversation_id": "conv_123",
    "agent_id": 1,
    "agent_name": "Balabala"
  }
}
```

**流式问答（按ID）**
```http
POST /api/agent/{agent_id}/chat/stream
Content-Type: application/json
Accept: text/event-stream

{
  "message": "你好",
  "conversation_id": "conv_123",
  "use_memory": true,
  "use_knowledge_base": true
}

Response: (SSE Stream)
data: {"content": "你"}
data: {"content": "好"}
data: {"content": "！"}
data: {"done": true}
```

**按名称问答**
```http
POST /api/agent/name/{agent_name}/chat
POST /api/agent/name/{agent_name}/chat/stream
```

#### 2. Agent Memory管理

**获取记忆**
```http
GET /api/agent/{agent_id}/memory?conversation_id=conv_123
```

**清除记忆**
```http
DELETE /api/agent/{agent_id}/memory?conversation_id=conv_123
```

#### 3. Agent管理

**获取Agent信息**
```http
GET /api/agent/{agent_id}/info
```

**重新加载Agent（刷新配置）**
```http
POST /api/agent/{agent_id}/reload
```

**获取已缓存的Agent列表**
```http
GET /api/agent/cached
```

## 使用示例

### Python示例

```python
import requests

# 1. 非流式问答
response = requests.post(
    'http://localhost:8788/api/agent/1/chat',
    json={
        'message': '介绍一下Python',
        'conversation_id': 'conv_001',
        'use_memory': True,
        'use_knowledge_base': True
    }
)
result = response.json()
print(result['data']['reply'])

# 2. 流式问答
import sseclient

response = requests.post(
    'http://localhost:8788/api/agent/1/chat/stream',
    json={'message': '写一个快速排序算法'},
    stream=True,
    headers={'Accept': 'text/event-stream'}
)

client = sseclient.SSEClient(response)
for event in client.events():
    data = json.loads(event.data)
    if 'content' in data:
        print(data['content'], end='', flush=True)
    elif 'done' in data:
        print('\n完成')
        break
```

### JavaScript示例

```javascript
import agentApi from './renderer/js/modules/agent/agentApi.js';

// 1. 非流式问答
const result = await agentApi.agentChat(
    1,  // agent_id
    '你好',  // message
    'conv_001',  // conversation_id
    {
        use_memory: true,
        use_knowledge_base: true
    }
);
console.log(result.data.reply);

// 2. 流式问答
await agentApi.agentChatStream(
    1,  // agent_id
    '介绍一下JavaScript',  // message
    'conv_001',  // conversation_id
    {
        onData: (content) => {
            console.log(content);
        },
        onEnd: () => {
            console.log('完成');
        },
        onError: (error) => {
            console.error('错误:', error);
        }
    },
    {
        use_memory: true,
        use_knowledge_base: true
    }
);

// 3. 按名称问答
const result2 = await agentApi.agentChatByName(
    'Balabala',  // agent_name
    '你好'
);

// 4. 清除记忆
await agentApi.clearAgentMemory(1, 'conv_001');

// 5. 获取Agent信息
const info = await agentApi.getAgentInfo(1);
console.log(info.data);
```

## 配置Agent

### 1. 创建LLM配置

```http
POST /api/agent/llm-configs
Content-Type: application/json

{
  "name": "GPT-4 Turbo",
  "provider": "openai",
  "api_endpoint": "https://api.openai.com/v1",
  "api_key": "sk-xxx",
  "model_name": "gpt-4-turbo-preview",
  "temperature": 0.7,
  "max_tokens": 4096
}
```

### 2. 创建角色配置

```http
POST /api/agent/roles
Content-Type: application/json

{
  "name": "senior_developer",
  "display_name": "资深开发工程师",
  "system_prompt": "你是一个资深的软件开发工程师，精通多种编程语言和框架...",
  "greeting_message": "你好！我是资深开发工程师，很高兴为你提供技术支持。",
  "category": "development"
}
```

### 3. 创建Agent

```http
POST /api/agent
Content-Type: application/json

{
  "name": "DevAssistant",
  "description": "开发助手Agent",
  "model_config_id": "llm_abc123",  // LLM配置ID
  "role_id": "role_xyz789",         // 角色配置ID
  "plugins": "tool1,tool2",          // 工具ID列表（逗号分隔）
  "kms": "kb1,kb2",                  // 知识库ID列表（逗号分隔）
  "execfile": true,                  // 启用代码执行
  "is_active": true
}
```

## 工具调用

Agent支持OpenAI Function Calling格式的工具调用。

### 1. 在agent/tools.py中定义工具

```python
# agent/tools.py

def get_weather_sbi(city: str) -> str:
    """
    获取城市天气
    city: 城市名称
    """
    return f"The weather in {city} is sunny."

def calculate_tool(a: int, b: int, operator: str) -> int:
    """
    计算器工具
    """
    if operator == "+":
        return a + b
    elif operator == "-":
        return a - b
    # ...
```

### 2. 配置Agent使用工具

在数据库的`agent_cfg`表中，将工具函数名添加到`plugins`字段（逗号分隔）。

系统会自动：
1. 从agent/tools.py加载工具函数
2. 生成OpenAI function calling schema
3. 在LLM调用时提供工具定义
4. 自动执行工具并返回结果

## 代码执行

如果Agent配置了`execfile=True`，则可以执行代码：

```python
# Agent会自动识别代码并执行
user: "写一个Python程序计算1到100的和并执行"
agent: "好的，我来写一个程序：
```python
total = sum(range(1, 101))
print(f"1到100的和是: {total}")
```

执行结果：
```
1到100的和是: 5050
```
"
```

代码执行特性：
- 沙箱隔离（临时目录）
- 超时控制（默认30秒）
- 输出大小限制
- 支持Python和Shell命令

## 知识库集成

Agent可以访问配置的知识库进行RAG检索。

系统在回答问题前会：
1. 从用户问题提取关键词
2. 从关联的知识库检索相关信息
3. 将检索结果添加到system prompt
4. LLM基于检索内容生成回复

## 对话记忆（Memory）

每个Agent实例维护自己的对话记忆：

- 按`conversation_id`区分不同对话
- 自动保留最近50条消息
- 支持多轮对话上下文
- 可手动清除记忆

```javascript
// 同一个conversation_id的对话会保持上下文
await agentApi.agentChat(1, '我叫张三', 'conv_001');
await agentApi.agentChat(1, '我叫什么名字？', 'conv_001');
// Agent会回复：你叫张三

// 不同conversation_id互不影响
await agentApi.agentChat(1, '我叫李四', 'conv_002');
await agentApi.agentChat(1, '我叫什么名字？', 'conv_002');
// Agent会回复：你叫李四
```

## 缓存机制

AgentManager使用缓存机制提高性能：

- 首次调用时从数据库加载Agent配置
- 创建Agent实例并缓存
- 后续调用直接使用缓存实例
- 更新配置后可调用`/api/agent/{agent_id}/reload`刷新

## 最佳实践

1. **配置隔离**：每个Agent使用独立的LLM和角色配置，避免互相影响
2. **对话管理**：使用有意义的conversation_id区分不同对话场景
3. **记忆清理**：长对话时定期清除记忆，避免token超限
4. **工具设计**：工具函数应该是无状态的、幂等的
5. **错误处理**：流式响应要处理断线重连
6. **性能优化**：频繁使用的Agent会被缓存，性能更好

## 故障排查

### Agent加载失败

```
检查项：
1. Agent配置是否存在且未删除（is_delete=False）
2. LLM配置ID是否正确
3. 角色配置ID是否正确
4. API key是否配置
```

### 工具调用失败

```
检查项：
1. 工具函数是否在agent/tools.py中定义
2. 工具名称是否正确
3. 工具参数是否匹配函数签名
4. 工具函数是否抛出异常
```

### 知识库检索无结果

```
检查项：
1. 知识库ID是否正确
2. 知识库是否有内容
3. langchainhandler是否正确配置
4. 向量数据库是否可用
```

## 技术栈

- **后端**: FastAPI, SQLAlchemy, OpenAI SDK
- **前端**: Vanilla JS, Electron
- **LLM**: OpenAI API（兼容格式）
- **工具**: Python Function
- **知识库**: LangChain + Vector DB
- **流式**: Server-Sent Events (SSE)

## 扩展

### 添加新的工具

1. 在`agent/tools.py`中定义函数
2. 在Agent配置的`plugins`字段中添加函数名
3. 重新加载Agent

### 集成新的LLM Provider

1. 修改`AgentInstance._init_llm_client()`支持新provider
2. 或使用OpenAI兼容格式的API endpoint

### 添加新的代码执行语言

1. 在`CodeExecutor`中添加新的执行方法
2. 在`AgentInstance._execute_tool()`中处理新语言的工具调用

## 许可证

查看项目根目录的LICENSE文件。
