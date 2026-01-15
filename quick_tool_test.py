# -*- coding: utf-8 -*-
"""快速工具测试 - 验证所有10个工具能被Agent加载"""
import asyncio
import sys
sys.path.insert(0, '.')

from backend.modules.agent.agent_manager import agent_manager

async def main():
    print("=" * 80)
    print("快速工具测试".center(80))
    print("=" * 80)

    # 加载Agent
    print("\n[1] 加载Agent...")
    agent = agent_manager.load_agent(1, force_reload=True)
    if not agent:
        print("❌ 无法加载Agent 1")
        return False

    print(f"✓ Agent已加载: {agent.name} (ID: {agent.agent_id})")

    # 加载工具
    print("\n[2] 加载工具...")
    await agent.load_tools_from_db()

    tool_count = len(agent.db_tools)
    print(f"✓ 已加载 {tool_count} 个工具")

    # 显示工具列表
    if tool_count > 0:
        print("\n[3] 工具列表:")
        print("-" * 80)

        # 按类型分组
        mcp_tools = []
        function_tools = []
        plugin_tools = []
        skill_tools = []

        for tool in agent.db_tools:
            tool_name = tool['function']['name']
            tool_desc = tool['function']['description'][:50]

            if tool_name.startswith('mcp_'):
                mcp_tools.append((tool_name, tool_desc))
            elif tool_name.startswith('function_'):
                function_tools.append((tool_name, tool_desc))
            elif tool_name.startswith('plugin_'):
                plugin_tools.append((tool_name, tool_desc))
            elif tool_name.startswith('skill_'):
                skill_tools.append((tool_name, tool_desc))

        if mcp_tools:
            print(f"\n  MCP工具 ({len(mcp_tools)}个):")
            for name, desc in mcp_tools:
                print(f"    • {name:45s} - {desc}")

        if function_tools:
            print(f"\n  Function工具 ({len(function_tools)}个):")
            for name, desc in function_tools:
                print(f"    • {name:45s} - {desc}")

        if plugin_tools:
            print(f"\n  Plugin工具 ({len(plugin_tools)}个):")
            for name, desc in plugin_tools:
                print(f"    • {name:45s} - {desc}")

        if skill_tools:
            print(f"\n  Skill工具 ({len(skill_tools)}个):")
            for name, desc in skill_tools:
                print(f"    • {name:45s} - {desc}")

    # 结果
    print("\n" + "=" * 80)
    if tool_count == 10:
        print("✅ 成功! 所有10个工具已加载".center(80))
        print("=" * 80)
        print("\n下一步测试:")
        print("  • 在Windows上重启 api_server.py")
        print("  • 在Electron界面测试工具调用")
        print("  • 参考 WINDOWS_QUICK_TEST.md 中的测试用例")
        return True
    else:
        print(f"⚠️  警告: 预期10个工具，实际加载 {tool_count} 个".center(80))
        print("=" * 80)
        return False

if __name__ == "__main__":
    try:
        result = asyncio.run(main())
        sys.exit(0 if result else 1)
    except Exception as e:
        print(f"\n❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
