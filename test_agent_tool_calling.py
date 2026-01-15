# -*- coding: utf-8 -*-
"""
测试Agent工具调用完整流程
"""
import asyncio
import sys
import os

# 添加项目路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from backend.modules.agent.agent_instance import AgentInstance


async def test_agent_with_tools():
    """测试Agent工具调用"""

    print("=" * 60)
    print("Agent工具调用系统测试")
    print("=" * 60)

    # 1. 创建Agent实例
    print("\n[1] 创建Agent实例...")
    agent = AgentInstance(
        agent_id=1,
        name="测试Agent",
        description="用于测试工具调用的Agent",
        llm_config={
            "api_endpoint": "https://api.openai.com/v1",
            "api_key": "your-api-key-here",  # 需要替换为真实API key
            "model_name": "gpt-4o-mini",
            "temperature": 0.7,
            "max_tokens": 2048
        },
        role_config={
            "system_prompt": "你是一个智能助手，可以使用各种工具来帮助用户解决问题。"
        }
    )
    print(f"✓ Agent实例已创建: {agent.name} (ID: {agent.agent_id})")

    # 2. 加载工具
    print("\n[2] 从数据库加载工具...")
    await agent.load_tools_from_db()

    if agent.db_tools:
        print(f"✓ 已加载 {len(agent.db_tools)} 个工具:")
        for tool in agent.db_tools:
            tool_name = tool['function']['name']
            tool_desc = tool['function']['description']
            print(f"  - {tool_name}: {tool_desc[:80]}...")
    else:
        print("⚠️  没有找到关联的工具")
        print("\n提示：请先使用以下SQL为Agent添加工具：")
        print("""
        INSERT INTO agent_tools (agent_id, tool_type, tool_id, enabled, priority)
        VALUES (1, 'plugin', 'PL2026011510474128484', 1, 10);

        INSERT INTO agent_tools (agent_id, tool_type, tool_id, enabled, priority)
        VALUES (1, 'mcp', 'MC2026011511561554068', 1, 5);
        """)

    # 3. 测试场景
    print("\n[3] 测试工具调用场景...")

    test_cases = [
        ("计算1+89等于多少", "测试Plugin Calculator"),
        ("查询上海的天气", "测试MCP Weather Server"),
        ("你好，介绍一下自己", "测试普通对话（不调用工具）")
    ]

    for i, (message, description) in enumerate(test_cases, 1):
        print(f"\n--- 测试用例 {i}: {description} ---")
        print(f"用户: {message}")

        # 检查API key
        if not agent.client:
            print("❌ LLM客户端未配置，请在llm_config中设置有效的API key")
            continue

        if agent.llm_config.get("api_key") == "your-api-key-here":
            print("⚠️  需要配置真实的API key才能进行实际测试")
            continue

        try:
            # 调用Agent
            response = await agent.chat(message, conversation_id=f"test_{i}")
            print(f"Agent: {response}")
            print("✓ 测试通过")
        except Exception as e:
            print(f"❌ 测试失败: {e}")

    # 4. 显示Agent信息
    print("\n" + "=" * 60)
    print("Agent信息:")
    print("=" * 60)
    agent_info = agent.to_dict()
    for key, value in agent_info.items():
        print(f"{key}: {value}")

    print("\n" + "=" * 60)
    print("测试完成!")
    print("=" * 60)


async def test_tool_converter():
    """测试工具转换器"""
    print("\n" + "=" * 60)
    print("测试工具转换器")
    print("=" * 60)

    from backend.modules.agent.tool_converter import ToolConverter
    from backend.modules.agent.service import AgentService

    print("\n[1] 从数据库获取Agent 1的工具...")
    tools_data = AgentService.get_agent_tools(1)
    print(f"✓ 获取到 {len(tools_data)} 个工具")

    if not tools_data:
        print("⚠️  Agent 1 没有关联的工具")
        return

    print("\n[2] 转换为OpenAI格式...")
    openai_tools = ToolConverter.convert_tools(tools_data)
    print(f"✓ 转换完成，得到 {len(openai_tools)} 个OpenAI格式工具")

    print("\n[3] 工具详情:")
    for i, tool in enumerate(openai_tools, 1):
        print(f"\n工具 {i}:")
        print(f"  类型: {tool['type']}")
        print(f"  名称: {tool['function']['name']}")
        print(f"  描述: {tool['function']['description'][:100]}...")
        print(f"  参数: {list(tool['function']['parameters'].get('properties', {}).keys())}")


async def test_tool_router():
    """测试工具路由器"""
    print("\n" + "=" * 60)
    print("测试工具路由器")
    print("=" * 60)

    from backend.modules.agent.tool_router import ToolRouter
    from backend.modules.tools.tool_executor import get_tool_executor

    print("\n[1] 初始化工具路由器...")
    tool_router = ToolRouter(get_tool_executor())
    print("✓ 工具路由器已初始化")

    # 测试用例
    test_cases = [
        {
            "name": "测试Plugin工具",
            "function_name": "plugin_PL2026011510474128484",
            "arguments": {"expression": "1+89"}
        },
        # MCP测试需要真实的MCP服务器运行
        # {
        #     "name": "测试MCP工具",
        #     "function_name": "mcp_MC2026011511561554068_get_weather",
        #     "arguments": {"city": "Shanghai", "unit": "celsius"}
        # }
    ]

    for i, test_case in enumerate(test_cases, 1):
        print(f"\n[{i+1}] {test_case['name']}...")
        print(f"  Function: {test_case['function_name']}")
        print(f"  Arguments: {test_case['arguments']}")

        try:
            result = await tool_router.execute_tool(
                test_case['function_name'],
                test_case['arguments']
            )
            print(f"  结果: {result}")
            print("  ✓ 执行成功")
        except Exception as e:
            print(f"  ❌ 执行失败: {e}")


async def main():
    """主测试函数"""
    print("\n" + "=" * 70)
    print(" Agent工具调用系统 - 完整测试套件 ".center(70, "="))
    print("=" * 70)

    # 测试1: 工具转换器
    await test_tool_converter()

    # 测试2: 工具路由器
    await test_tool_router()

    # 测试3: Agent完整流程
    print("\n\n")
    await test_agent_with_tools()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\n测试被用户中断")
    except Exception as e:
        print(f"\n\n测试失败: {e}")
        import traceback
        traceback.print_exc()
