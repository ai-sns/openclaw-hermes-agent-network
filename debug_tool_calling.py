# -*- coding: utf-8 -*-
"""详细调试工具调用"""
import asyncio
import sys
import json
import logging

sys.path.insert(0, '.')

# 设置详细日志
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

from backend.modules.agent.agent_manager import agent_manager

async def debug_tool_calling():
    """详细调试工具调用流程"""
    print("=" * 80)
    print("工具调用详细调试".center(80))
    print("=" * 80)

    # 加载Agent
    print("\n[步骤1] 加载Agent...")
    agent = agent_manager.load_agent(1, force_reload=True)
    if not agent:
        print("❌ 无法加载Agent")
        return

    print(f"✓ Agent: {agent.name}")
    print(f"✓ LLM Config: {agent.llm_config.get('api_endpoint')} / {agent.llm_config.get('model_name')}")

    # 检查system prompt
    print(f"\n[步骤2] System Prompt:")
    print("-" * 80)
    system_prompt = agent.role_config.get('system_prompt', 'None')
    print(system_prompt[:200])
    if "工具" not in system_prompt and "tool" not in system_prompt.lower():
        print("\n⚠️  警告: System prompt中没有提到工具使用!")

    # 加载工具
    print(f"\n[步骤3] 加载工具...")
    await agent.load_tools_from_db()
    print(f"✓ 已加载 {len(agent.db_tools)} 个工具")

    # 显示前3个工具
    print("\n前3个工具:")
    for i, tool in enumerate(agent.db_tools[:3], 1):
        name = tool['function']['name']
        desc = tool['function']['description'][:50]
        print(f"  {i}. {name} - {desc}")

    # 测试货币转换
    print(f"\n[步骤4] 测试货币转换Function工具")
    print("-" * 80)
    test_message = "请帮我计算100元人民币等于多少美元"

    print(f"用户问题: {test_message}")
    print("\n调用Agent...")

    try:
        # 准备消息
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": test_message}
        ]

        # 调用LLM (不使用chat方法，直接调用以便看到原始响应)
        from openai import OpenAI

        client = OpenAI(
            api_key=agent.llm_config.get('api_key'),
            base_url=agent.llm_config.get('api_endpoint')
        )

        print("\n发送到LLM的tools数量:", len(agent.db_tools))

        response = client.chat.completions.create(
            model=agent.llm_config.get('model_name'),
            messages=messages,
            tools=agent.db_tools,
            temperature=agent.llm_config.get('temperature', 0.7),
            max_tokens=agent.llm_config.get('max_tokens', 2048)
        )

        print("\n[步骤5] LLM响应分析")
        print("-" * 80)

        # 检查是否有tool_calls
        if response.choices[0].message.tool_calls:
            print("✅ LLM决定调用工具!")
            for tool_call in response.choices[0].message.tool_calls:
                print(f"\n  工具名称: {tool_call.function.name}")
                print(f"  参数: {tool_call.function.arguments}")

                # 尝试执行工具
                try:
                    result = await agent._execute_tool(
                        tool_call.function.name,
                        json.loads(tool_call.function.arguments)
                    )
                    print(f"  执行结果: {result[:100] if isinstance(result, str) else result}")
                except Exception as e:
                    print(f"  ❌ 执行失败: {e}")
        else:
            print("❌ LLM没有调用工具，直接回复:")
            print(response.choices[0].message.content)

            print("\n可能的原因:")
            print("  1. System prompt没有提示使用工具")
            print("  2. 工具描述不够吸引人")
            print("  3. LLM认为不需要工具就能回答")

    except Exception as e:
        print(f"\n❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(debug_tool_calling())
