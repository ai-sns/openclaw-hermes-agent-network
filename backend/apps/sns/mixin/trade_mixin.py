from sqlalchemy.orm import Session
from backend.database.models.chat import AiChatCfg
from backend.apps.sns.map_task_manager import MapTaskManager
from backend.apps.sns.js_task_manager import JsTaskManager
from backend.apps.sns.xmpp_client import XMPPClientManager
from backend.modules.agent.agent_manager import agent_manager
from backend.shared.websocket_manager import manager as websocket_manager

# *********
import os
import math
# 主要用于发送附件
import asyncio
import zipfile
import shutil
import time

import logging

import re

log = logging.getLogger(__name__)
from db.DBFactory import (query_AgentCfg, add_AIChatMessages, get_prompt_by_title, query_function_mng,
                          add_function_mng, update_map_task, add_map_visit, get_key_value,
                          update_map_trade, add_map_trade, add_map_tool, query_single_map_trade, update_AiChatCfg_by_user_id, update_AiChatCfg_map, query_AiChatCfg_map, add_mcp_mng, query_mcp_mng,
                          delete_map_preset_msg, query_map_preset_msg_all, add_map_preset_msg, query_tool_list, query_single_tool, query_AiChatCfg_map_setting)
from util import (generate_random_id, add_memory_list)
from i18n import lt
from enum import Enum
from typing import List, Dict, Optional
import json
import logging
import requests
import geopy.distance
from geopy.distance import distance
from geopy.point import Point
from geographiclib.geodesic import Geodesic
import random

logger = logging.getLogger(__name__)

class TradeMixin:

    def _parse_trade_payment(self, price_str: str):
        trade_id = ""
        trade_price = "0"

        if price_str and "__AISNS_INT_SEPARATOR__" in price_str:
            price_str = price_str.strip()
            parts = price_str.split("__AISNS_INT_SEPARATOR__", 1)
            trade_id = (parts[0] or "").strip()
            trade_price = (parts[1] or "0").strip()
        else:
            trade_price = (price_str or "0").strip()

        return trade_id, trade_price

    def get_guidance(self):
        user_list_stra = """
        - J宝:是个律师,坐标[116.30375329461533,40.049108567364904],距离7公里\n
        - W宝:是个医生,坐标[116.30690718139134,40.06259235539735],距离8公里\n
                """
        user_list_str = """
暂时没有更多人员
                """
        place_list_str = """
- 北京天安门:很多人在此看升旗。坐标[116.3975,39.9087],距离40公里。\n
- 八达岭长城:著名旅游景点。坐标[116.0204,40.3606],距离60公里。\n
                """

        result = f"""
        您支付了10元费用，获得了如下信息：
        ### 人员列表：
        {user_list_str}
        ### 地址列表：
        {place_list_str}
        """""
        self.aichatcfg_record.money = float(self.aichatcfg_record.money or 0) - 10

        return result

    def set_food_order(self):
        result = ""
        self.aichatcfg_record.energy_point = self.aichatcfg_record.energy_point + 25
        self.aichatcfg_record.move_point = 100 * (self.aichatcfg_record.life_point / 100) * (self.aichatcfg_record.energy_point / 100)
        self.aichatcfg_record.money = self.aichatcfg_record.money - 30
        result = f"你支付了30元购买食物，你的体力值已经恢复为{self.aichatcfg_record.energy_point}%，当前行动力为{self.aichatcfg_record.move_point}%"
        return result

    def set_taxi_order(self, current_position, target_position, target_place):
        point1 = (current_position[1], current_position[0])  # 转换成 (纬度, 经度)
        point2 = (target_position[1], target_position[0])  # 转换成 (纬度, 经度)

        # 使用 geopy 计算距离
        dist = distance(point1, point2).kilometers
        fee = dist * 2.5

        self.aichatcfg_record.money = self.aichatcfg_record.money - fee

        self.aichatcfg_record.last_position = current_position
        self.aichatcfg_record.current_position = target_position
        new_pos = self.aichatcfg_record.current_position
        command = ("move_to_a_place", str(new_pos[0]), str(new_pos[1]))
        self.send_msg_to_map(command)

        result = f"你支付了{fee:.2f}元车费，你已经到达{target_place}，坐标为{target_position}"
        return result

    def call_a_doctor(self):
        result = ""

        self.aichatcfg_record.life_point = self.aichatcfg_record.life_point + 25
        self.aichatcfg_record.move_point = 100 * (self.aichatcfg_record.life_point / 100) * (self.aichatcfg_record.energy_point / 100)
        self.aichatcfg_record.money = self.aichatcfg_record.money - 210
        result = f"你支付了210元远程治疗服务，你的生命值已经恢复为{self.aichatcfg_record.life_point}%，当前行动力为{self.aichatcfg_record.move_point}%"
        return result

    def sell_to_a_people(self, action_str, instrunction):
        human_object = ""
        self.talk_type = "sell"
        self.ask_agent_start_to_sell_to_a_people_sync(action_str, human_object)

    def buy_from_a_people(self, action_str, instrunction):
        human_object = ""
        self.talk_type = "buy"
        self.ask_agent_start_to_buy_from_a_people_sync(action_str, human_object)

    def ask_agent_start_to_sell_to_a_people_sync(self, objective_to_achieve, human_objective_to_achieve=""):
        provided_profile_list = json.dumps(self.get_people_list(), indent=4, ensure_ascii=False)
        objective_to_achieve = f"{human_objective_to_achieve}{objective_to_achieve}"

        role_prompt = get_prompt_by_title("__start_to_sell_to_a_people__")

        content_prompt = get_prompt_by_title("__start_to_sell_to_a_people_content__")
        content_prompt = content_prompt.replace("__action_desc__", objective_to_achieve)
        content_prompt = content_prompt.replace("__people__to__select__", provided_profile_list)

        self.command_status = "ask_agent_start_to_sell_to_a_people"
        asyncio.create_task(self.ask_agent_and_get_instruction(content_prompt, role_prompt))

    def ask_agent_start_to_buy_from_a_people_sync(self, objective_to_achieve, human_objective_to_achieve=""):
        provided_profile_list = json.dumps(self.get_people_list(), indent=4, ensure_ascii=False)
        objective_to_achieve = f"{human_objective_to_achieve}{objective_to_achieve}"

        role_prompt = get_prompt_by_title("__start_to_buy_from_a_people__")

        content_prompt = get_prompt_by_title("__start_to_buy_from_a_people_content__")
        content_prompt = content_prompt.replace("__action_desc__", objective_to_achieve)
        content_prompt = content_prompt.replace("__people__to__select__", provided_profile_list)

        self.command_status = "ask_agent_start_to_buy_from_a_people"
        asyncio.create_task(self.ask_agent_and_get_instruction(content_prompt, role_prompt))

    async def ask_agent_start_to_sell_to_a_people(self, objective_to_achieve, human_objective_to_achieve=""):
        provided_profile_list = json.dumps(self.get_people_list(), indent=4, ensure_ascii=False)
        objective_to_achieve = f"{human_objective_to_achieve}{objective_to_achieve}"

        role_prompt = get_prompt_by_title("__start_to_sell_to_a_people__")

        content_prompt = get_prompt_by_title("__start_to_sell_to_a_people_content__")
        content_prompt = content_prompt.replace("__action_desc__", objective_to_achieve)
        content_prompt = content_prompt.replace("__people__to__select__", provided_profile_list)

        self.command_status = "ask_agent_start_to_sell_to_a_people"
        await  self.ask_agent_and_get_instruction(content_prompt, role_prompt)

    async def ask_agent_start_to_buy_from_a_people(self, objective_to_achieve, human_objective_to_achieve=""):
        provided_profile_list = json.dumps(self.get_people_list(), indent=4, ensure_ascii=False)
        objective_to_achieve = f"{human_objective_to_achieve}{objective_to_achieve}"

        role_prompt = get_prompt_by_title("__start_to_buy_from_a_people__")

        content_prompt = get_prompt_by_title("__start_to_buy_from_a_people_content__")
        content_prompt = content_prompt.replace("__action_desc__", objective_to_achieve)
        content_prompt = content_prompt.replace("__people__to__select__", provided_profile_list)

        self.command_status = "ask_agent_start_to_buy_from_a_people"
        await  self.ask_agent_and_get_instruction(content_prompt, role_prompt)

    def handle_ask_agent_start_to_sell_to_a_people_result(self, content):
        result = json.loads(content)
        if result:
            nation_id = result["nation_id"]
            account = result["account"]
            nick_name = result["nick_name"]
            message = result["message"]
            self.current_talk_people = result

            self.taskmng.current_process["people_communicated_list"].append(nation_id)
            self.taskmng.current_process["rounds_current_person"] = 1
            self.current_talk_history = []
            self.talk_to_a_people(message, nation_id, account, nick_name)

        else:
            description = "我未找到目标人员。"

            asyncio.create_task(self.taskmng.process_task(event="agent_pick_people_list_fail"))

    def handle_ask_agent_start_to_buy_from_a_people_result(self, content):
        result = json.loads(content)
        if result:
            nation_id = result["nation_id"]
            account = result["account"]
            nick_name = result["nick_name"]
            message = result["message"]
            self.current_talk_people = result

            self.taskmng.current_process["people_communicated_list"].append(nation_id)
            self.taskmng.current_process["rounds_current_person"] = 1
            self.current_talk_history = []
            message = "[AISNS_INT_003_INQUIRY]" + message
            self.talk_to_a_people(message, nation_id, account, nick_name)

        else:
            description = "我未找到目标人员。"

            asyncio.create_task(self.taskmng.process_task(event="agent_pick_people_list_fail"))

    async def ask_agent_to_review_conversation_sell(self, conversation_target, messages_history):
        role_prompt = get_prompt_by_title("__review_conversation_sell__")
        role_prompt = role_prompt.replace("__messages_history__", messages_history)
        question = "请严格遵照要求评估，并严格按照格式输出。"
        await  self.ask_agent_and_get_instruction(question, role_prompt)

    async def ask_agent_to_review_conversation_buy(self, conversation_target, messages_history):
        role_prompt = get_prompt_by_title("__review_conversation_buy__")
        role_prompt = role_prompt.replace("__messages_history__", messages_history)
        question = "请严格遵照要求评估，并严格按照格式输出。"
        await  self.ask_agent_and_get_instruction(question, role_prompt)

    def handle_agent_review_conversation_sell_result(self, content):

        self.handle_agent_review_conversation_sell_result_final(content)

    def handle_agent_review_conversation_sell_result_final(self, content):
        content = content.strip()
        result = json.loads(content)
        continue_chat = result["continue_chat"]
        current_chat_summary = result["summary"]
        message = result["next_message"]

        if not continue_chat:
            self.taskmng.add_process_info_to_list(f"和朋友沟通后得到如下情况：{current_chat_summary}")
            self.write_task_process_to_pane(f"和朋友沟通后得到如下情况：{current_chat_summary}\n\n")
            self.taskmng.current_situation = f"和别人沟通后，得到如下情况:{current_chat_summary}"
            asyncio.create_task(self.taskmng.process_task(action="process_activity", ask_content=f"- 当前目标\n{self.taskmng.current_objective}\n- 当前进展\n和别人沟通后，得到如下情况:{current_chat_summary}"))

        else:
            if self.taskmng.current_process["rounds_current_person"] < self.max_rounds_per_person:
                self.taskmng.current_process["rounds_current_person"] = self.taskmng.current_process["rounds_current_person"] + 1
                self.talk_to_a_people(message, self.current_talk_people["nation_id"], self.current_talk_people["account"], self.current_talk_people["nick_name"])
            else:
                self.taskmng.add_process_info_to_list(f"和朋友沟通后得到如下情况：{current_chat_summary}")
                self.taskmng.current_situation = f"和别人沟通后，得到如下情况:{current_chat_summary}"
                asyncio.create_task(self.taskmng.process_task(action="process_activity", ask_content=f"- 当前目标\n{self.taskmng.current_objective}\n- 当前进展\n和别人沟通后，得到如下情况:{current_chat_summary}"))

    def handle_agent_review_conversation_buy_result(self, content):

        self.handle_agent_review_conversation_buy_result_final(content)

    def handle_agent_review_conversation_buy_result_final(self, content):
        content = content.strip()
        result = json.loads(content)
        continue_chat = result["continue_chat"]
        current_chat_summary = result["summary"]
        message = result["next_message"]

        buy_score = result.get("buy_score", False)
        price = result.get("price", 0)

        if buy_score >= 80 and price >= 0:
            self.send_pay(price)
            return

        if not continue_chat:
            self.taskmng.add_process_info_to_list(f"和朋友沟通后得到如下情况：{current_chat_summary}")
            self.write_task_process_to_pane(f"和朋友沟通后得到如下情况：{current_chat_summary}\n\n")
            self.taskmng.current_situation = f"和别人沟通后，得到如下情况:{current_chat_summary}"
            asyncio.create_task(self.taskmng.process_task(action="process_activity", ask_content=f"- 当前目标\n{self.taskmng.current_objective}\n- 当前进展\n和别人沟通后，得到如下情况:{current_chat_summary}"))

        else:
            if not self.taskmng.current_process:
                self.taskmng.current_process = {"rounds_current_person": 0}
            if not self.current_talk_people:
                self.current_talk_people = {
                    "nation_id": "AI123451234567890ABCDEF7894",
                    "account": "yangyang@xabber.de",
                    "location": [
                        116.30690718139134,
                        40.06259235539735
                    ],
                    "nick_name": "W宝",
                    "avatar": "img_woman_hi",
                    "avatar_3d": "smallofficewoman_0_0_0_0_1_0.glb",
                    "profile": "我是个医生",
                    "sns_url": "x.com"
                }

            if self.taskmng.current_process["rounds_current_person"] < self.max_rounds_per_person:
                self.taskmng.current_process["rounds_current_person"] = self.taskmng.current_process["rounds_current_person"] + 1
                self.talk_to_a_people(message, self.current_talk_people["nation_id"], self.current_talk_people["account"], self.current_talk_people["nick_name"])
            else:
                self.taskmng.add_process_info_to_list(f"和朋友沟通后得到如下情况：{current_chat_summary}")
                self.taskmng.current_situation = f"和别人沟通后，得到如下情况:{current_chat_summary}"
                asyncio.create_task(self.taskmng.process_task(action="process_activity", ask_content=f"- 当前目标\n{self.taskmng.current_objective}\n- 当前进展\n和别人沟通后，得到如下情况:{current_chat_summary}"))

    def check_pay_in_received(self, msg):
        """
            从输入字符串中提取 JSON 字符串，位于特定的起始和结束标记之间。

            :param msg: 包含 JSON 字符串的原始输入
            :return: 提取的 JSON 字符串，如果未找到则返回 None
            """
        # 定义正则表达式模式，使用原始字符串以避免转义字符的问题
        pattern = r'AISNS_INT_001_PAY_SEND_START(.*?)AISNS_INT_001_PAY_SEND_END'

        # 使用 re.search 查找符合模式的部分
        match = re.search(pattern, msg, re.DOTALL)  # DOTALL 使 . 可以匹配换行符

        # 检查是否找到匹配，并返回提取的内容
        if match:
            result = match.group(1).strip()  # 提取并去除首尾空白
            return result
        else:
            return None  # 如果没有匹配，返回 None

    def check_good_in_received(self, msg):
        """
            从输入字符串中提取 JSON 字符串，位于特定的起始和结束标记之间。

            :param msg: 包含 JSON 字符串的原始输入
            :return: 提取的 JSON 字符串，如果未找到则返回 None
            """
        # 定义正则表达式模式，使用原始字符串以避免转义字符的问题
        pattern = r'AISNS_INT_002_GOOD_SEND_START(.*?)AISNS_INT_002_GOOD_SEND_END'

        # 使用 re.search 查找符合模式的部分
        match = re.search(pattern, msg, re.DOTALL)  # DOTALL 使 . 可以匹配换行符

        # 检查是否找到匹配，并返回提取的内容
        if match:
            result = match.group(1).strip()  # 提取并去除首尾空白
            return result
        else:
            return None  # 如果没有匹配，返回 None

    def check_buy_in_received(self, msg):
        pattern = '[AISNS_INT_003_INQUIRY]'

        if pattern in msg:
            return True
        else:
            return False

    def send_pay(self, price) -> None:
        trade_id = generate_random_id()
        current_talk_people = self.current_talk_people
        nation_id = current_talk_people["nation_id"]
        account = current_talk_people["account"]
        nick_name = current_talk_people["nick_name"]
        try:
            message = f"AISNS_INT_001_PAY_SEND_START\n{trade_id}__AISNS_INT_SEPARATOR__{price}\nAISNS_INT_001_PAY_SEND_END"

            self.talk_to_a_people(message, nation_id, account, nick_name)

            self.add_money(0 - price)
            trade_type = "B"
            title = f"Trade with {nick_name}"
            detail = "Waiting for goods"
            trade_with_name = nick_name
            trade_with_account = account

            add_map_trade(trade_id=trade_id, trade_type=trade_type, title=title, detail=detail, pay=price, trade_with_name=trade_with_name, trade_with_account=trade_with_account)
        except Exception as e:
            print(f"Tool trade sell error: {str(e)}")

    def handle_pay_received(self, price_str) -> None:
        talk_history_str = json.dumps(self.current_talk_history, ensure_ascii=False)
        trade_id, trade_price = self._parse_trade_payment(price_str)

        try:
            self.current_trade_price = float(trade_price or 0)
        except Exception:
            self.current_trade_price = 0

        try:
            record = query_AiChatCfg_map()
            profession = record.profession
            handle_after_trade = record.handle_after_trade
            handle_content = record.handle_content

            if profession in {"doctor", "driver", "seller"}:
                self.handle_send_goods(handle_content, trade_id)
                return

            if handle_after_trade == "发送消息":
                self.handle_send_goods(handle_content, trade_id)
                return

            tool_name = handle_content
            what_to_do = "## 聊天记录 \n" + talk_history_str
            tool_task = self.run_configured_tool_text_generation_sync(
                tool_name,
                what_to_do,
                conversation_suffix="trade_delivery",
            )

            if isinstance(tool_task, asyncio.Task):
                def _on_tool_done(t: asyncio.Task):
                    try:
                        result_text = t.result()
                    except Exception as e:
                        logger.error(f"ask agent to run tool before send goods failed: {e}", exc_info=True)
                        result_text = f"工具执行失败: {str(e)}"
                    try:
                        self.handle_send_goods(result_text, trade_id)
                    except Exception as e:
                        logger.error(f"handle_send_goods failed after tool execution: {e}", exc_info=True)

                tool_task.add_done_callback(_on_tool_done)
            else:
                self.handle_send_goods(tool_task, trade_id)

        except Exception as e:
            print(f"Tool trade sell error: {str(e)}")

    def handle_send_goods(self, good_str, trade_id):
        current_talk_people = self.current_talk_people
        nation_id = current_talk_people["nation_id"]
        account = current_talk_people["account"]
        nick_name = current_talk_people["nick_name"]
        price = self.current_trade_price

        try:
            if not trade_id:
                trade_id = generate_random_id()

            message = f"AISNS_INT_002_GOOD_SEND_START\n{trade_id}__AISNS_INT_SEPARATOR__{good_str}\nAISNS_INT_002_GOOD_SEND_END"
            self.talk_to_a_people(message, nation_id, account, nick_name)
            trade_type = "S"
            title = f"Trade with {nick_name}"
            detail = good_str
            trade_with_name = nick_name
            trade_with_account = account
            add_map_trade(trade_id=trade_id, trade_type=trade_type, title=title, detail=detail, pay=price, trade_with_name=trade_with_name, trade_with_account=trade_with_account)
            self.add_money(price)

        except Exception as e:
            print(f"Tool trade sell error: {str(e)}")

    def handle_good_received(self, goods_str) -> None:
        trade_id = ""
        current_talk_people = self.current_talk_people
        nation_id = current_talk_people["nation_id"]
        account = current_talk_people["account"]
        nick_name = current_talk_people["nick_name"]

        if "__AISNS_INT_SEPARATOR__" in goods_str:
            goods_str = goods_str.strip()
            trade_id = goods_str.split("__AISNS_INT_SEPARATOR__")[0]
            goods_detail = goods_str.split("__AISNS_INT_SEPARATOR__")[1]

        try:
            update_map_trade(trade_id, detail=goods_detail)
        except Exception as e:
            print(f"Tool trade sell error: {str(e)}")

    def add_money(self, count):
        money = float(self.aichatcfg_record.money or 0) + count
        self.aichatcfg_record.money = money
