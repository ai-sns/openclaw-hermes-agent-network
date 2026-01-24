#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
测试异步路由是否正常工作
"""
import asyncio
import aiohttp
import sys

BASE_URL = "http://localhost:8788"

async def test_routes():
    """测试所有路由"""
    routes = [
        ("健康检查", f"{BASE_URL}/health"),
        ("用户统计", f"{BASE_URL}/api/sns/user-stats"),
        ("联系人列表", f"{BASE_URL}/api/sns/contacts"),
        ("地图配置", f"{BASE_URL}/api/sns/map-config"),
        ("交易列表", f"{BASE_URL}/api/map/trades"),
    ]

    async with aiohttp.ClientSession() as session:
        print("\n" + "="*60)
        print("开始测试异步路由")
        print("="*60 + "\n")

        for name, url in routes:
            try:
                print(f"测试 {name}: {url}")
                async with session.get(url, timeout=aiohttp.ClientTimeout(total=5)) as resp:
                    status = resp.status
                    print(f"  ✓ 状态码: {status}")
                    if status == 200:
                        data = await resp.json()
                        print(f"  ✓ 返回数据成功")
                    elif status == 404:
                        print(f"  ⚠ 路由不存在（正常，可能是可选功能）")
                    elif status == 500:
                        print(f"  ✗ 服务器内部错误")
                        text = await resp.text()
                        print(f"  错误信息: {text[:200]}")
                    else:
                        print(f"  ⚠ 状态码: {status}")
            except asyncio.TimeoutError:
                print(f"  ✗ 请求超时")
            except aiohttp.ClientError as e:
                print(f"  ✗ 连接错误: {e}")
            except Exception as e:
                print(f"  ✗ 未知错误: {e}")
            print()

        print("="*60)
        print("测试完成")
        print("="*60 + "\n")

if __name__ == "__main__":
    print("确保服务器正在运行: python api_server.py")
    print("按 Enter 开始测试...")
    input()

    try:
        asyncio.run(test_routes())
    except KeyboardInterrupt:
        print("\n测试已取消")
    except Exception as e:
        print(f"测试失败: {e}")
        sys.exit(1)
