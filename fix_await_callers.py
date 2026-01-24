#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
自动修复 ai_social_engine_adapter.py 中所有调用 async 函数但没有 await 的问题
"""

import re
import sys

def fix_async_callers(file_path):
    """
    修复所有在非 async 函数中调用 async 函数但没有 await 的问题
    """
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()

    # 需要修复的函数列表
    functions_to_fix = {
        'handle_event_after_decistion': 'ask_agent_to_run_a_tool',
        'handle_event_receive_msg': 'ask_agent_to_run_a_tool',
        'handle_event_before_send_msg': 'ask_agent_to_run_a_tool',
        'sell_to_a_people': 'ask_agent_start_to_sell_to_a_people',
        'buy_from_a_people': 'ask_agent_start_to_buy_from_a_people',
        'parse_agent_instruction_for_process_human_instruction': 'ask_agent_to_pick_people_list',
        'parse_agent_instruction_for_process_human_instruction_2': 'ask_agent_to_pick_place_list',
        'parse_agent_instruction_for_process_human_instruction_3': 'ask_agent_to_pick_a_tool',
        'call_tool': 'ask_agent_to_run_a_tool',
        'handle_pay_received': 'ask_agent_to_run_a_tool',
        'tool_trade_bargain_for_buyer': 'ask_agent_to_bargain_for_buyer',
        'tool_trade_bargain_for_seller': 'ask_agent_to_bargain_for_seller',
    }

    # 已修复的函数（跳过）
    fixed_functions = {
        'handle_event_before_decistion',  # 已在 async def
        'communicate_with_a_people',  # 已在 async def
    }

    # 逐个修复
    for caller, called_func in functions_to_fix.items():
        if caller in fixed_functions:
            continue

        # 简单替换：找到 def 并在前面添加 async
        old_def = f'    def {caller}('
        new_def = f'    async def {caller}('

        # 查找所有匹配并替换
        count = 0
        while old_def in content:
            # 替换这个调用者定义
            content = content.replace(old_def, new_def, 1)
            count += 1

            # 添加 await 到函数内的调用
            # 找到函数结束（下一个函数定义或文件末尾）
            lines = content.split('\n')
            for i in range(len(lines)):
                if old_def in lines[i]:
                    # 找到函数体
                    for j in range(i + 1, min(i + 20, len(lines))):
                        if lines[j].startswith('self.(' + called_func + '(') and 'await ' not in lines[j]:
                            lines[j] = lines[j].replace('self.(' + called_func + '(', 'await self.(' + called_func + '(')
                            break
                    content = '\n'.join(lines)
                    break

            if count > 0:
                print(f"✅ 修复: {caller} -> async def + await {called_func}")

    # 写回文件
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(content)

    print(f"\n✅ 修复完成！共修复了 {count} 处")

if __name__ == '__main__':
    file_path = 'backend/modules/sns/ai_social_engine_adapter.py'
    print(f"正在修复文件: {file_path}")
    print("="*60)
    fix_async_callers(file_path)
    print("="*60)
    print(f"\n请运行以下命令验证语法:")
    print(f"python -m py_compile {file_path}")
