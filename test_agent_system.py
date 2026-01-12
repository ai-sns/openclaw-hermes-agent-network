#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Agent System Test Script
测试Agent对象化系统的各项功能
"""

import asyncio
import sys
from pathlib import Path

# 添加项目根目录到sys.path
project_root = Path(__file__).resolve().parent
sys.path.insert(0, str(project_root))

from backend.modules.agent.agent_manager import agent_manager


async def test_agent_system():
    """测试Agent系统"""
    print("=" * 60)
    print("Agent对象化系统测试")
    print("=" * 60)

    # 1. 测试加载Agent
    print("\n[1] 测试加载Agent...")
    agent = agent_manager.get_agent_by_id(1)
    if agent:
        print(f"✓ Agent加载成功: {agent.name} (ID: {agent.agent_id})")
        print(f"  - LLM: {agent.get_model_name()}")
        print(f"  - System Prompt: {agent.get_system_prompt()[:50]}...")
        print(f"  - 工具数量: {len(agent.tools)}")
        print(f"  - 知识库数量: {len(agent.knowledge_bases)}")
        print(f"  - 代码执行: {'启用' if agent.enable_code_execution else '禁用'}")
    else:
        print("✗ Agent加载失败")
        return

    # 2. 测试非流式问答
    print("\n[2] 测试非流式问答...")
    try:
        reply = await agent.chat(
            message="你好，请简单介绍一下你自己",
            conversation_id="test_conv_001",
            use_memory=True,
            use_knowledge_base=False
        )
        print(f"✓ 非流式问答成功")
        print(f"  回复: {reply[:100]}...")
    except Exception as e:
        print(f"✗ 非流式问答失败: {e}")

    # 3. 测试流式问答
    print("\n[3] 测试流式问答...")
    try:
        print("  回复: ", end="", flush=True)
        async for chunk in agent.chat_stream(
            message="用一句话介绍Python语言",
            conversation_id="test_conv_001",
            use_memory=True
        ):
            print(chunk, end="", flush=True)
        print("\n✓ 流式问答成功")
    except Exception as e:
        print(f"\n✗ 流式问答失败: {e}")

    # 4. 测试Memory
    print("\n[4] 测试Memory...")
    memory = agent._get_conversation_memory("test_conv_001")
    print(f"✓ Memory中有 {len(memory)} 条消息")
    if memory:
        print(f"  最新消息: {memory[-1]['role']}: {memory[-1]['content'][:50]}...")

    # 5. 测试清除Memory
    print("\n[5] 测试清除Memory...")
    agent.clear_memory("test_conv_001")
    memory_after = agent._get_conversation_memory("test_conv_001")
    print(f"✓ Memory已清除，剩余 {len(memory_after)} 条消息")

    # 6. 测试工具列表
    print("\n[6] 测试工具系统...")
    from backend.modules.agent.tool_executor import tool_executor
    tools = tool_executor.list_tools()
    print(f"✓ 系统中有 {len(tools)} 个工具")
    if tools:
        print(f"  可用工具: {', '.join(tools[:5])}...")

    # 7. 测试按名称获取Agent
    print("\n[7] 测试按名称获取Agent...")
    agent_by_name = agent_manager.get_agent_by_name(agent.name)
    if agent_by_name:
        print(f"✓ 按名称获取成功: {agent_by_name.name}")
    else:
        print("✗ 按名称获取失败")

    # 8. 测试缓存
    print("\n[8] 测试缓存机制...")
    cached_agents = agent_manager.get_all_cached_agents()
    print(f"✓ 缓存中有 {len(cached_agents)} 个Agent")

    print("\n" + "=" * 60)
    print("测试完成！")
    print("=" * 60)


def main():
    """主函数"""
    try:
        asyncio.run(test_agent_system())
    except KeyboardInterrupt:
        print("\n测试被用户中断")
    except Exception as e:
        print(f"\n测试过程中出错: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
