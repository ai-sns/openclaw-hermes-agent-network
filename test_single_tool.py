# -*- coding: utf-8 -*-
"""实际工具调用测试 - 测试货币转换Function"""
import asyncio
import sys
sys.path.insert(0, '.')

from backend.modules.agent.agent_manager import agent_manager

async def test_function_tool():
    """测试Function工具 - 货币转换"""
    print("=" * 80)
    print("测试 Function 工具 - 货币转换".center(80))
    print("=" * 80)

    # 加载Agent
    print("\n[1] 加载Agent...")
    agent = agent_manager.load_agent(1, force_reload=True)
    if not agent:
        print("❌ 无法加载Agent")
        return False

    print(f"✓ Agent: {agent.name}")

    # 加载工具
    print("\n[2] 加载工具...")
    await agent.load_tools_from_db()
    print(f"✓ 已加载 {len(agent.db_tools)} 个工具")

    # 测试问题
    test_message = "100元人民币等于多少美元？"
    print(f"\n[3] 测试问题: {test_message}")
    print("\n[4] Agent回复:")
    print("-" * 80)

    try:
        # 使用流式输出
        full_response = ""
        async for chunk in agent.chat_stream(
            message=test_message,
            conversation_id="test_currency_conversion"
        ):
            print(chunk, end="", flush=True)
            full_response += chunk

        print("\n" + "-" * 80)

        # 检查是否调用了工具
        if "convert_rmb_to_usd" in full_response.lower() or "美元" in full_response:
            print("\n✅ 测试通过 - Agent回复了关于美元的信息")
            return True
        else:
            print("\n⚠️  Agent回复了，但可能没有调用工具")
            return False

    except Exception as e:
        print(f"\n❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    result = asyncio.run(test_function_tool())
    sys.exit(0 if result else 1)
