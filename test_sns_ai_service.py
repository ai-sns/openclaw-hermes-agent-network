#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试SNS AI服务
"""
import asyncio
import sys
import os

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from backend.modules.sns.ai_service import SNSAIService


async def test_ai_service():
    """测试AI服务"""
    print("=" * 60)
    print("测试SNS AI服务")
    print("=" * 60)

    # 测试1: AI模式
    print("\n测试1: AI模式")
    print("-" * 60)
    reply = await SNSAIService.chat_with_agent(
        agent_identifier="1",
        message="你好，请介绍一下你自己",
        mode="ai"
    )
    print(f"用户: 你好，请介绍一下你自己")
    print(f"AI回复: {reply}")

    # 测试2: Friends模式
    print("\n测试2: Friends模式")
    print("-" * 60)
    reply = await SNSAIService.chat_with_agent(
        agent_identifier="1",
        message="你好，请介绍一下你自己",
        mode="friends"
    )
    print(f"用户: 你好，请介绍一下你自己")
    print(f"Friends回复: {reply}")

    # 测试3: 使用Agent名称
    print("\n测试3: 使用Agent名称")
    print("-" * 60)
    reply = await SNSAIService.chat_with_agent(
        agent_identifier="Altman",
        message="你是谁？",
        mode="ai"
    )
    print(f"用户: 你是谁？")
    print(f"AI回复: {reply}")

    print("\n" + "=" * 60)
    print("测试完成")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(test_ai_service())
