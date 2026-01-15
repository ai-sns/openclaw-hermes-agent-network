# AgentInstance工具调用集成 - 实现方案

## 需要的修改

### 1. 添加导入

```python
from .tool_router import ToolRouter
from .tool_converter import ToolConverter
from backend.modules.tools.tool_executor import get_tool_executor
```

### 2. 修改__init__方法

```python
def __init__(self, ...):
    # ... existing code ...

    # 初始化工具路由器
    from backend.modules.tools.tool_executor import get_tool_executor
    self.tool_router = ToolRouter(get_tool_executor())

    # 加载工具配置（异步）
    # 注意：这里不能直接await，需要在外部调用
    self.tools_loaded = False

    logger.info(f"Agent实例已创建: {self.name} (ID: {self.agent_id})")
```

### 3. 添加load_tools_from_db方法

```python
async def load_tools_from_db(self):
    """从数据库加载工具并转换为OpenAI格式"""
    try:
        from backend.modules.agent.service import AgentService

        # 获取Agent的工具列表
        tools_data = AgentService.get_agent_tools(self.agent_id)

        # 转换为OpenAI格式
        self.tools = ToolConverter.convert_tools(tools_data)

        self.tools_loaded = True
        logger.info(f"Agent {self.name} loaded {len(self.tools)} tools")

    except Exception as e:
        logger.error(f"Failed to load tools for agent {self.name}: {e}")
        self.tools = []
        self.tools_loaded = True
```

### 4. 修改chat方法

在chat方法中，调用LLM时添加tools参数：

```python
async def chat(self, message: str, conversation_id: Optional[str] = None, ...):
    """Chat with tool calling support"""

    # 确保工具已加载
    if not self.tools_loaded:
        await self.load_tools_from_db()

    # ... build messages ...

    # 调用LLM with tools
    response = await self.client.chat.completions.create(
        model=self.get_model_name(),
        messages=messages,
        temperature=self.get_temperature(),
        max_tokens=self.get_max_tokens(),
        tools=self.tools if self.tools else None,  # ← Add tools
        tool_choice="auto" if self.tools else None
    )

    # 处理tool_calls
    if response.choices[0].message.tool_calls:
        # 执行工具调用
        for tool_call in response.choices[0].message.tool_calls:
            function_name = tool_call.function.name
            arguments = json.loads(tool_call.function.arguments)

            logger.info(f"Calling tool: {function_name} with args: {arguments}")

            # 执行工具
            tool_result = await self.tool_router.execute_tool(function_name, arguments)

            # 添加tool message到对话
            messages.append({
                "role": "assistant",
                "content": None,
                "tool_calls": [tool_call.model_dump()]
            })

            messages.append({
                "role": "tool",
                "tool_call_id": tool_call.id,
                "content": json.dumps(tool_result, ensure_ascii=False)
            })

        # 再次调用LLM with tool results
        final_response = await self.client.chat.completions.create(
            model=self.get_model_name(),
            messages=messages,
            temperature=self.get_temperature(),
            max_tokens=self.get_max_tokens()
        )

        assistant_message = final_response.choices[0].message.content

    else:
        # 没有tool_calls，直接使用响应
        assistant_message = response.choices[0].message.content

    # ... save to memory ...

    return assistant_message
```

### 5. 修改chat_stream方法

类似的修改，但需要处理流式响应：

```python
async def chat_stream(self, message: str, ...) -> AsyncIterator[str]:
    """Chat with streaming and tool calling support"""

    # 确保工具已加载
    if not self.tools_loaded:
        await self.load_tools_from_db()

    # ... build messages ...

    # 调用LLM with tools (streaming)
    stream = await self.client.chat.completions.create(
        model=self.get_model_name(),
        messages=messages,
        temperature=self.get_temperature(),
        max_tokens=self.get_max_tokens(),
        tools=self.tools if self.tools else None,
        tool_choice="auto" if self.tools else None,
        stream=True
    )

    # 收集streaming响应
    collected_messages = []
    tool_calls = []

    async for chunk in stream:
        delta = chunk.choices[0].delta

        # 收集tool_calls
        if delta.tool_calls:
            # 处理tool_calls streaming
            for tc_chunk in delta.tool_calls:
                # ... collect tool call data ...
                pass

        # 输出content
        if delta.content:
            collected_messages.append(delta.content)
            yield delta.content

    # 如果有tool_calls，执行它们
    if tool_calls:
        # ... execute tools and call LLM again ...
        pass
```

## 实现顺序

1. ✅ 添加导入
2. ✅ 修改__init__
3. ✅ 添加load_tools_from_db
4. ✅ 修改chat方法
5. ⏳ 修改chat_stream方法（可选，先实现基本chat）

## 测试计划

```python
# 1. 创建测试脚本
# test_agent_tools.py

import asyncio
from backend.modules.agent.agent_instance import AgentInstance

async def test_agent_with_tools():
    # 创建Agent实例
    agent = AgentInstance(
        agent_id=1,
        name="Test Agent",
        llm_config={
            "api_endpoint": "https://api.openai.com/v1",
            "api_key": "sk-...",
            "model_name": "gpt-4o-mini",
            "temperature": 0.7,
            "max_tokens": 2048
        }
    )

    # 加载工具
    await agent.load_tools_from_db()

    # 测试对话
    response = await agent.chat("查询上海的天气")
    print(f"Response: {response}")

if __name__ == "__main__":
    asyncio.run(test_agent_with_tools())
```
