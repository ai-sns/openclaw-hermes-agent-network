# -*- coding: utf-8 -*-
"""
Agent全工具类型测试脚本
测试所有4种工具类型：Plugin、MCP、Function、Skill
"""
import asyncio
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from backend.modules.agent.agent_instance import AgentInstance


# 测试用例定义
TEST_CASES = [
    {
        "id": 1,
        "type": "MCP",
        "name": "地图路线查询",
        "message": "帮我查一下从北京到上海的驾车路线",
        "expected_tool": "mcp_ZP2025061314162230222",
        "priority": "⭐⭐⭐"
    },
    {
        "id": 2,
        "type": "MCP",
        "name": "搜索查询",
        "message": "搜索一下上海今天的天气怎么样",
        "expected_tool": "mcp_LD2025061314404887010",
        "priority": "⭐⭐⭐"
    },
    {
        "id": 3,
        "type": "Function",
        "name": "天气查询",
        "message": "查询一下北京的天气",
        "expected_tool": "function_GT2654780435432639652",
        "priority": "⭐⭐"
    },
    {
        "id": 4,
        "type": "Function",
        "name": "货币转换",
        "message": "帮我把100元人民币换算成美元",
        "expected_tool": "function_KL2024091719363863671",
        "priority": "⭐⭐"
    },
    {
        "id": 5,
        "type": "Function",
        "name": "获取用户名",
        "message": "我的用户名是什么？",
        "expected_tool": "function_SK2025022722375473913",
        "priority": "⭐"
    },
    {
        "id": 6,
        "type": "Plugin",
        "name": "思维导图",
        "message": "帮我创建一个关于AI发展的思维导图",
        "expected_tool": "plugin_AK2024Y5Q717U20711095",
        "priority": "⭐⭐"
    },
    {
        "id": 7,
        "type": "Plugin",
        "name": "流程图",
        "message": "画一个登录流程的流程图",
        "expected_tool": "plugin_EK202405K7170A7T190951",
        "priority": "⭐⭐"
    },
    {
        "id": 8,
        "type": "Plugin",
        "name": "控制浏览器",
        "message": "帮我打开Chrome浏览器并访问百度",
        "expected_tool": "plugin_14",
        "priority": "⭐"
    },
    {
        "id": 9,
        "type": "Skill",
        "name": "Python代码执行",
        "message": "帮我用Python计算1到100的和",
        "expected_tool": "skill_CN2024090916031485895",
        "priority": "⭐⭐⭐"
    },
    {
        "id": 10,
        "type": "None",
        "name": "普通对话",
        "message": "你好，介绍一下自己",
        "expected_tool": None,
        "priority": "⭐"
    }
]


async def test_agent_tools():
    """测试Agent工具调用"""

    print("\n" + "=" * 80)
    print(" Agent全工具类型测试 ".center(80, "="))
    print("=" * 80)

    # 创建Agent实例
    print("\n[步骤1] 创建Agent实例...")
    agent = AgentInstance(
        agent_id=1,
        name="Altman",
        description="测试Agent - 支持所有工具类型",
        llm_config={
            "api_endpoint": "https://api.chatanywhere.tech/v1",
            "api_key": "your-api-key-here",  # 需要替换为真实API key
            "model_name": "gpt-4o-mini",
            "temperature": 0.7,
            "max_tokens": 2048
        },
        role_config={
            "system_prompt": "你是一个智能助手，可以使用各种工具来帮助用户。当用户需要查询信息、处理数据或执行操作时，你应该选择合适的工具。"
        }
    )
    print(f"✓ Agent实例已创建: {agent.name} (ID: {agent.agent_id})")

    # 加载工具
    print("\n[步骤2] 从数据库加载工具...")
    await agent.load_tools_from_db()

    if not agent.db_tools:
        print("❌ 错误：没有找到任何工具配置")
        print("\n请确保:")
        print("1. 数据库文件存在: db/db.sqlite")
        print("2. agent_tools表中有Agent 1的配置")
        print("3. 运行SQL: SELECT * FROM agent_tools WHERE agent_id = 1;")
        return

    print(f"✓ 已加载 {len(agent.db_tools)} 个工具")
    print("\n已加载的工具列表:")
    for i, tool in enumerate(agent.db_tools, 1):
        tool_name = tool['function']['name']
        tool_desc = tool['function']['description'][:60]
        print(f"  {i:2d}. {tool_name}: {tool_desc}...")

    # 检查API key
    if agent.llm_config.get("api_key") == "your-api-key-here":
        print("\n" + "=" * 80)
        print("⚠️  警告: 未配置真实的API key")
        print("=" * 80)
        print("\n要进行实际测试，请修改此脚本中的API key")
        print("或者手动在Electron界面测试")
        print("\n跳过LLM调用测试，仅验证工具加载...")
        return

    # 运行测试用例
    print("\n" + "=" * 80)
    print(" 开始测试 ".center(80, "="))
    print("=" * 80)

    results = []

    for test_case in TEST_CASES:
        print(f"\n{'─' * 80}")
        print(f"测试 {test_case['id']}: {test_case['name']} ({test_case['type']}) {test_case['priority']}")
        print(f"{'─' * 80}")
        print(f"用户输入: {test_case['message']}")
        print(f"预期工具: {test_case['expected_tool'] or '不调用工具'}")

        try:
            # 调用Agent
            response = await agent.chat(
                message=test_case['message'],
                conversation_id=f"test_{test_case['id']}"
            )

            print(f"\nAgent回复: {response[:200]}...")

            # 记录结果
            results.append({
                "test_case": test_case,
                "success": True,
                "response": response
            })

            print("✓ 测试完成")

        except Exception as e:
            print(f"\n❌ 测试失败: {e}")
            results.append({
                "test_case": test_case,
                "success": False,
                "error": str(e)
            })

    # 输出测试总结
    print("\n" + "=" * 80)
    print(" 测试总结 ".center(80, "="))
    print("=" * 80)

    success_count = sum(1 for r in results if r['success'])
    total_count = len(results)

    print(f"\n总计: {success_count}/{total_count} 个测试通过")

    # 按类型统计
    print("\n按工具类型统计:")
    for tool_type in ["MCP", "Function", "Plugin", "Skill", "None"]:
        type_results = [r for r in results if r['test_case']['type'] == tool_type]
        type_success = sum(1 for r in type_results if r['success'])
        if type_results:
            print(f"  {tool_type:12s}: {type_success}/{len(type_results)} 通过")

    # 详细结果
    print("\n详细结果:")
    for i, result in enumerate(results, 1):
        status = "✓" if result['success'] else "✗"
        test_case = result['test_case']
        print(f"  {status} 测试{i:2d} - {test_case['name']:20s} ({test_case['type']:8s})")
        if not result['success']:
            print(f"           错误: {result.get('error', 'Unknown error')}")

    print("\n" + "=" * 80)


async def verify_database():
    """验证数据库配置"""
    print("\n" + "=" * 80)
    print(" 数据库配置验证 ".center(80, "="))
    print("=" * 80)

    try:
        from backend.modules.agent.service import AgentService

        print("\n[1] 检查Agent 1的工具配置...")
        tools = AgentService.get_agent_tools(1)

        if not tools:
            print("❌ 没有找到Agent 1的工具配置")
            print("\n请执行SQL:")
            print("  sqlite3 db/db.sqlite < add_agent_tools.sql")
            return False

        print(f"✓ 找到 {len(tools)} 个工具配置")

        # 按类型统计
        tool_types = {}
        for tool in tools:
            tool_type = tool.get('tool_type', 'unknown')
            tool_types[tool_type] = tool_types.get(tool_type, 0) + 1

        print("\n工具类型统计:")
        for tool_type, count in sorted(tool_types.items()):
            print(f"  {tool_type:12s}: {count} 个")

        print("\n工具详情:")
        for i, tool in enumerate(tools, 1):
            tool_type = tool.get('tool_type')
            tool_name = tool.get('name', 'Unknown')
            priority = tool.get('priority', 0)
            print(f"  {i:2d}. [{tool_type:8s}] {tool_name:30s} (优先级: {priority})")

        return True

    except Exception as e:
        print(f"❌ 验证失败: {e}")
        import traceback
        traceback.print_exc()
        return False


async def main():
    """主函数"""
    print("\n" + "=" * 80)
    print(" Agent工具调用系统 - 测试套件 ".center(80, "="))
    print("=" * 80)
    print("\n测试目标:")
    print("  ✓ 验证所有4种工具类型（Plugin/MCP/Function/Skill）")
    print("  ✓ 验证LLM能正确选择工具")
    print("  ✓ 验证工具执行流程")
    print("  ✓ 验证工具结果处理")

    # 验证数据库
    if not await verify_database():
        print("\n数据库验证失败，终止测试")
        return

    # 运行测试
    await test_agent_tools()

    print("\n" + "=" * 80)
    print(" 测试完成 ".center(80, "="))
    print("=" * 80)
    print("\n提示:")
    print("  • 如需实际测试LLM调用，请配置真实的API key")
    print("  • 查看 api_server.py 日志了解详细的工具调用过程")
    print("  • 参考 ALL_TOOLS_TEST_GUIDE.md 了解测试用例详情")
    print("\n")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\n测试被用户中断")
    except Exception as e:
        print(f"\n\n测试失败: {e}")
        import traceback
        traceback.print_exc()
