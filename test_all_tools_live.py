# -*- coding: utf-8 -*-
"""
Agent工具调用实战测试
通过真实的LLM对话测试所有10个工具
"""
import asyncio
import json
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from backend.modules.agent.agent_manager import agent_manager


# 10个测试用例
TEST_CASES = [
    {
        "id": 1,
        "type": "MCP",
        "name": "地图路线查询",
        "message": "帮我规划一下从北京到上海的驾车路线，需要多长时间？",
        "expected_tool_prefix": "mcp_ZP2025061314162230222"
    },
    {
        "id": 2,
        "type": "MCP",
        "name": "DuckDuckGo搜索",
        "message": "搜索一下2024年人工智能的重要突破",
        "expected_tool_prefix": "mcp_LD2025061314404887010"
    },
    {
        "id": 3,
        "type": "MCP",
        "name": "mcp001通用工具",
        "message": "使用mcp001查询一些信息",
        "expected_tool_prefix": "mcp_BK2025061220454036750"
    },
    {
        "id": 4,
        "type": "Function",
        "name": "获取天气",
        "message": "北京现在的天气怎么样？",
        "expected_tool_prefix": "function_GT2654780435432639652"
    },
    {
        "id": 5,
        "type": "Function",
        "name": "货币转换",
        "message": "100元人民币可以换多少美元？",
        "expected_tool_prefix": "function_KL2024091719363863671"
    },
    {
        "id": 6,
        "type": "Function",
        "name": "获取用户名",
        "message": "我的用户名是什么？",
        "expected_tool_prefix": "function_SK2025022722375473913"
    },
    {
        "id": 7,
        "type": "Plugin",
        "name": "思维导图",
        "message": "帮我创建一个关于机器学习的思维导图",
        "expected_tool_prefix": "plugin_AK2024Y5Q717U20711095"
    },
    {
        "id": 8,
        "type": "Plugin",
        "name": "流程图",
        "message": "画一个用户登录的流程图",
        "expected_tool_prefix": "plugin_EK202405K7170A7T190951"
    },
    {
        "id": 9,
        "type": "Plugin",
        "name": "控制Chrome",
        "message": "帮我打开Chrome浏览器访问百度网站",
        "expected_tool_prefix": "plugin_14"
    },
    {
        "id": 10,
        "type": "Skill",
        "name": "Python执行",
        "message": "用Python帮我计算从1加到100的总和",
        "expected_tool_prefix": "skill_CN2024090916031485895"
    }
]


async def test_single_tool(agent, test_case):
    """测试单个工具"""
    print("\n" + "=" * 80)
    print(f"测试 {test_case['id']}: {test_case['name']} ({test_case['type']})")
    print("=" * 80)
    print(f"\n用户输入: {test_case['message']}")
    print(f"预期工具: {test_case['expected_tool_prefix']}")
    print("\n正在调用Agent...")

    try:
        # 使用流式聊天
        full_response = ""
        tool_called = False
        tool_name = None

        async for chunk in agent.chat_stream(
            message=test_case['message'],
            conversation_id=f"test_{test_case['id']}"
        ):
            full_response += chunk
            # 实时输出
            print(chunk, end="", flush=True)

        print("\n")
        print("-" * 80)
        print(f"✓ 测试 {test_case['id']} 完成")
        print(f"回复长度: {len(full_response)} 字符")

        # TODO: 从日志中检查是否调用了正确的工具
        # 这里需要查看agent内部的工具调用记录

        return {
            "test_id": test_case['id'],
            "type": test_case['type'],
            "name": test_case['name'],
            "success": True,
            "response": full_response,
            "tool_called": tool_called,
            "tool_name": tool_name
        }

    except Exception as e:
        print(f"\n✗ 测试失败: {e}")
        import traceback
        traceback.print_exc()

        return {
            "test_id": test_case['id'],
            "type": test_case['type'],
            "name": test_case['name'],
            "success": False,
            "error": str(e)
        }


async def main():
    """主测试函数"""
    print("\n" + "=" * 80)
    print(" Agent工具调用 - 实战测试 ".center(80, "="))
    print("=" * 80)
    print("\n测试说明:")
    print("  • 将测试所有10个工具类型")
    print("  • 使用真实的LLM进行对话")
    print("  • 观察工具调用过程和结果")
    print("  • 每个测试之间有间隔，便于观察")

    # 获取Agent实例
    print("\n[初始化] 加载Agent...")
    agent = agent_manager.load_agent(1)

    if not agent:
        print("✗ 错误: 无法加载Agent 1")
        return

    print(f"✓ Agent已加载: {agent.name} (ID: {agent.agent_id})")

    # 加载工具
    if not agent.tools_loaded:
        await agent.load_tools_from_db()

    print(f"✓ 已加载 {len(agent.db_tools)} 个工具")

    if len(agent.db_tools) != 10:
        print(f"\n⚠️  警告: 预期10个工具，实际加载了 {len(agent.db_tools)} 个")
        print("请确认数据库配置是否正确")

    # 运行所有测试
    results = []

    for i, test_case in enumerate(TEST_CASES, 1):
        print(f"\n\n{'#' * 80}")
        print(f" 进度: {i}/10 ".center(80, '#'))
        print('#' * 80)

        result = await test_single_tool(agent, test_case)
        results.append(result)

        # 测试之间暂停2秒
        if i < len(TEST_CASES):
            print("\n等待2秒后继续下一个测试...")
            await asyncio.sleep(2)

    # 输出测试总结
    print("\n\n" + "=" * 80)
    print(" 测试总结 ".center(80, "="))
    print("=" * 80)

    success_count = sum(1 for r in results if r['success'])
    total_count = len(results)

    print(f"\n总体结果: {success_count}/{total_count} 个测试成功")

    # 按类型统计
    print("\n按工具类型统计:")
    for tool_type in ["MCP", "Function", "Plugin", "Skill"]:
        type_results = [r for r in results if r['type'] == tool_type]
        type_success = sum(1 for r in type_results if r['success'])
        if type_results:
            print(f"  {tool_type:12s}: {type_success}/{len(type_results)} 成功")

    # 详细结果
    print("\n测试详情:")
    for result in results:
        status = "✓" if result['success'] else "✗"
        print(f"  {status} 测试{result['test_id']:2d} - {result['name']:20s} ({result['type']:8s})")
        if not result['success']:
            print(f"           错误: {result.get('error', 'Unknown')}")

    # 生成报告文件
    report_file = "/tmp/agent_tools_test_report.json"
    with open(report_file, 'w', encoding='utf-8') as f:
        json.dump({
            "test_time": "2026-01-15",
            "agent_id": 1,
            "agent_name": agent.name,
            "tools_loaded": len(agent.db_tools),
            "total_tests": total_count,
            "success_tests": success_count,
            "results": results
        }, f, ensure_ascii=False, indent=2)

    print(f"\n详细报告已保存到: {report_file}")

    print("\n" + "=" * 80)
    print(" 测试完成！ ".center(80, "="))
    print("=" * 80)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\n测试被用户中断")
    except Exception as e:
        print(f"\n\n测试失败: {e}")
        import traceback
        traceback.print_exc()
