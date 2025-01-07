import os
import urllib
from datetime import datetime

from PyQt5.QtWidgets import QWidget, QFileDialog, QMessageBox, QDialog
from PyQt5.QtCore import QSettings, Qt, QUrl, QFile, QFileInfo
from PyQt5.QtGui import QIcon, QStandardItemModel, QStandardItem

import autogen
from autogen.agentchat.conversable_agent import ConversableAgent

from autogen.agentchat.groupchat import GroupChatManager, GroupChat
from autogen.cache import Cache
from autogen.io.base import IOStream
from autogen.logger.logger_utils import get_current_ts
from autogen.oai.openai_utils import OAI_PRICE1K, get_key, is_valid_api_key
from autogen.runtime_logging import log_chat_completion, log_new_client, log_new_wrapper, logging_enabled
from autogen.token_count_utils import count_token
from Agent import Agent, AgentCommander
# IOStream处理
from autogen.io.base import IOStream

from db.DBFactory import query_MutiAgentCfg, query_AgentCfg

from langchainhandler import getvectorkm_String
from pytalk.agent.io import AISNSIOStream
from ui.ui_TaskPageWidget import Ui_TaskPageWidget
import hashlib
import webbrowser
from db.DBFactory import add_AgentTask
import http.client
import json
from pluginsmanager import PluginEngine

import argparse

from pluginsmanager import FileSystem

import urllib.request
import re

import sys

sys.path.append("../..")
sys.path.append("../../..")
from kmselect import FreezeTableDialog as KmFreezeTableDialog
from pluginselect_llm import FreezeTableDialog as PluginFreezeTableDialog
from db.DBFactory import add_KMCfg, query_KMCfg_All, update_KMCfg, delete_KMCfg, query_KMCfg
from db.DBFactory import add_PluginMng, query_PluginMng_All, update_PluginMng, delete_PluginMng, query_PluginMng
from globals import global_plugin_list
import sys
from PyQt5.QtWidgets import QApplication, QMessageBox
from PyQt5.QtCore import QTimer
from util import format_string_for_run_javascript


class AgentGroup:
    def __init__(self, agent_group_cfg):
        self.agent_group_cfg = agent_group_cfg
        self.name = agent_group_cfg.name
        self.plugin_name = ""
        self.km_path = ""
        self.embedding_model_name = ""
        self.agent_commander_id = agent_group_cfg.agentcommander
        self.agent_id_list = agent_group_cfg.agents.split(",") if agent_group_cfg.agents else None
        self.agent_list_to_run_task = {}
        self.task_list_to_run = []
        self.speaker = None

    def give_it_plugin(self, plugin_name):
        self.plugin_name = plugin_name

    def give_it_km(self, km_path, embedding_model_name):
        self.km_path = km_path
        self.embedding_model_name = embedding_model_name

    def ask_her_to_assign_task(self, messages, agent_list_to_run_task, browser_page=None):

        self.agent_list_to_run_task = agent_list_to_run_task

        if self.plugin_name != "":
            thinking_engine_name = self.plugin_name
        else:
            thinking_engine_name = "ChatGLM"

        brain = global_plugin_list[thinking_engine_name]

        back_ground_knowledge = ""
        if self.km_path != "":
            vector_path = self.km_path
            persist_directory = vector_path
            embedding_model_name = self.embedding_model_name
            docs = getvectorkm_String(messages[-1]["content"], persist_directory, embedding_model_name)
            print(docs)
            print(docs[0].page_content)
            back_ground_knowledge = docs[0].page_content

        messages[-1]["content"] = f"{messages}，请罗列一下任务列表。每项内容只需要标题，不需要详细内容，任务用逗号分隔开形成一个字符串。"

        if back_ground_knowledge != "":
            messages = f'请根据后面提供的背景内容回答问题，回答只能限制在背景内容的范围内，问题是：{messages};供参考的背景内容是：{back_ground_knowledge}'
            answer = brain(command=messages)
        else:
            # answer = brain(command=task_content)
            generator = brain(command=messages)
            chunks = ""
            total_output = []
            for chunk in generator:
                # print("the chunk",chunk)
                # print(chunk, end='', flush=True)  # 实时打印流式输出
                # print("the scripts:",'show_response_msg("""' + chunk + '""")')

                # chunk=chunk.replace("`","\`")
                # chunk = chunk.replace("\n", "\\n")
                total_output.append(chunk)  # 未处理过的
                chunks += chunk
                tchunks = format_string_for_run_javascript(chunks)

                if browser_page != None:
                    browser_page.runJavaScript('tchunks=`' + tchunks + '`')
                    browser_page.runJavaScript('show_response_msg(tchunks)')

                # total_output.append(chunk)

            if browser_page != None:
                browser_page.runJavaScript('updatemaincontent()')

            print("\n最终输出:")
            print(''.join(total_output))
            answer = ''.join(total_output)

        # 分割字符串为行，并去除每行前的序号
        task_list = [line.split('. ', 1)[-1] for line in answer.strip().split('\n') if line]

        print("task assign return", task_list)
        agent_altman = agent_list_to_run_task["Sam Altman"]
        agent_musk = agent_list_to_run_task["Elon Musk"]
        i = 0
        for messages in task_list:
            print("task", messages)
            if i % 2 == 0:
                task_id = "T" + str(i)
                agent_altman.assign_task(task_id, messages)
                task = (agent_altman.name, task_id, messages)
            else:
                task_id = "T" + str(i)
                agent_musk.assign_task(task_id, messages)
                task = (agent_musk.name, task_id, messages)
            self.task_list_to_run.append(task)
            i += 1

        add_AgentTask(messages, answer, 1, 1, 1, 1, 1)

        return answer

    def give_it_speaker(self, speaker):
        self.speaker = speaker

    def ask_it_to_assign_task(self, messages, agent_list_to_run_task, browser_page=None):
        speaker = self.speaker
        IOStream.set_global_default(AISNSIOStream(speaker))
        llm_config = {
            "cache_seed": None,
            "temperature": 0,
            "config_list": [{"model": "gpt-4o-mini", "stream": True, "api_key": "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"}],
            "timeout": 120,
        }

        agent_id_list = self.agent_id_list
        agent_list = []
        agent_dict = {}

        agent_commander_cfg = query_AgentCfg(user_id=self.agent_commander_id)

        for agent_id in agent_id_list:
            agent_cfg = query_AgentCfg(user_id=agent_id)
            agent = Agent(agent_cfg, chat_in_group=True)
            print("agent member name:", agent.name)
            agent_list.append(agent)
            agent_dict[agent_id] = agent

        # *1.Admin 使用内置的*****
        user_proxy = Agent(
            agent_cfg=None,
            chat_in_group=True,
            name="Admin",
            human_input_mode="ALWAYS",
            system_message="You are a human administrator. Your role is to review all code written by the Engineer before execution. Ensure that the code meets the required standards and conforms to the approved plan.",
            code_execution_config=False,
            description="An attentive HUMAN user who can answer questions about the task and perform tasks such as running Python code or inputting command line commands at a Linux terminal and reporting back the execution results."
        )

        agent_list.append(user_proxy)

        # 2.资深工程师
        engineer = Agent(
            agent_cfg=None,
            name="Engineer",
            llm_config=llm_config,
            system_message="""You are the Engineer. Follow the approved plan and write python/shell code to solve tasks. After writing the code, submit it for review by the Admin. Ensure that your code is wrapped in a code block specifying the script type. The user must not modify your code, so do not suggest incomplete code. If there are errors, fix them before resubmitting for review. If the task is not resolved after successful execution, analyze the issue and propose a new solution.
            """,
        )

        # 3.scientist 或者使用通用助手，可以扮演不同的角色
        scientist = Agent(
            agent_cfg=None,
            name="Scientist",
            llm_config=llm_config,
            system_message="""You are the Scientist. Follow the approved plan and categorize papers based on their abstracts. You do not write code.""",
        )
        # 4.任务规划师
        planner = Agent(
            agent_cfg=None,
            name="Planner",
            system_message="""You are the Planner. Suggest a plan and revise it based on feedback from the Admin and Critic until you get approval. Explain the plan clearly, distinguishing between tasks performed by the Engineer and the Scientist.
            """,
            llm_config=llm_config,
        )
        # *5.代码执行器，使用一个内置的就行了，不用使用专门的Agent对象*********
        executor = Agent(
            agent_cfg=None,
            chat_in_group=True,
            name="Executor",
            system_message="You are the Executor. Execute the code provided by the Engineer only after Admin approval and report the results.",
            human_input_mode="NEVER",
            code_execution_config={"executor": autogen.coding.LocalCommandLineCodeExecutor(work_dir="coding")},
        )

        agent_list.append(executor)

        # 6.评审师
        critic = Agent(
            agent_cfg=None,
            name="Critic",
            system_message="You are the Critic. Review the plan, claims, and code from other agents, providing constructive feedback and ensuring that verifiable information is included.",
            llm_config=llm_config,
        )

        groupchat = autogen.GroupChat(
            # agents=[user_proxy, engineer, scientist, planner, executor, critic],
            agents=agent_list,
            messages=[],
            max_round=50
        )
        # 7.使用群主的大模型，后面再考虑，manager就是选择下一用户的管理者，是由它背后的大模型来决定的，使用群主的llm配置以及界面上的大模型切换
        manager = AgentCommander(
            agent_commander_cfg=agent_commander_cfg,
            agent_group_cfg=self.agent_group_cfg,
            groupchat=groupchat,
            llm_config=llm_config
        )

        message = messages[-1]["content"]
        user_proxy.initiate_chat(
            manager,
            message=message,
        )

        answer = "The task is done."
        return answer

    def ask_it_to_assign_taskbak(self, messages, agent_list_to_run_task, browser_page=None):
        speaker = self.speaker
        IOStream.set_global_default(AISNSIOStream(speaker))
        llm_config = {
            "cache_seed": None,
            "temperature": 0,
            "config_list": [{"model": "gpt-4o-mini", "stream": True, "api_key": "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"}],
            "timeout": 120,
        }
        agent_dict = {}
        agent_list = []
        for selected_agent_user_id in agent_list_to_run_task:
            selected_agent_cfg = query_AgentCfg(user_id=selected_agent_user_id)
            agent = Agent(selected_agent_cfg)
            agent_list.append(agent)
            agent_dict[selected_agent_user_id] = agent

        # 1.Admin 使用内置的*****
        user_proxy = Agent(
            agent_cfg=None,
            name="Admin",
            human_input_mode="ALWAYS",
            system_message="You are a human administrator. Your role is to review all code written by the Engineer before execution. Ensure that the code meets the required standards and conforms to the approved plan.",
            code_execution_config=False,
            description="An attentive HUMAN user who can answer questions about the task and perform tasks such as running Python code or inputting command line commands at a Linux terminal and reporting back the execution results."
        )

        # 2.资深工程师
        engineer = Agent(
            agent_cfg=None,
            name="Engineer",
            llm_config=llm_config,
            system_message="""You are the Engineer. Follow the approved plan and write python/shell code to solve tasks. After writing the code, submit it for review by the Admin. Ensure that your code is wrapped in a code block specifying the script type. The user must not modify your code, so do not suggest incomplete code. If there are errors, fix them before resubmitting for review. If the task is not resolved after successful execution, analyze the issue and propose a new solution.
            """,
        )

        # 3.scientist 或者使用通用助手，可以扮演不同的角色
        scientist = Agent(
            agent_cfg=None,
            name="Scientist",
            llm_config=llm_config,
            system_message="""You are the Scientist. Follow the approved plan and categorize papers based on their abstracts. You do not write code.""",
        )
        # 4.任务规划师
        planner = Agent(
            agent_cfg=None,
            name="Planner",
            system_message="""You are the Planner. Suggest a plan and revise it based on feedback from the Admin and Critic until you get approval. Explain the plan clearly, distinguishing between tasks performed by the Engineer and the Scientist.
            """,
            llm_config=llm_config,
        )
        # 5.代码执行器，使用一个内置的就行了，不用使用专门的Agent对象*********
        executor = Agent(
            agent_cfg=None,
            name="Executor",
            system_message="You are the Executor. Execute the code provided by the Engineer only after Admin approval and report the results.",
            human_input_mode="NEVER",
            code_execution_config={"executor": autogen.coding.LocalCommandLineCodeExecutor(work_dir="coding")},
        )
        # 6.评审师
        critic = Agent(
            agent_cfg=None,
            name="Critic",
            system_message="You are the Critic. Review the plan, claims, and code from other agents, providing constructive feedback and ensuring that verifiable information is included.",
            llm_config=llm_config,
        )

        groupchat = autogen.GroupChat(
            agents=[user_proxy, engineer, scientist, planner, executor, critic],
            messages=[],
            max_round=50
        )
        # 7.使用群主的大模型，后面再考虑，manager就是选择下一用户的管理者，是由它背后的大模型来决定的，使用群主的llm配置以及界面上的大模型切换
        manager = AgentCommander(
            agent_commander_cfg=agent,
            groupchat=groupchat,
            llm_config=llm_config
        )

        message = messages[-1]["content"]
        user_proxy.initiate_chat(
            manager,
            message=message,
        )

        answer = "The task is done."
        return answer

    def ask_it(self, question):

        if self.plugin_name != "":
            thinking_engine_name = self.plugin_name
        else:
            thinking_engine_name = "ChatGLM"

        brain = global_plugin_list[thinking_engine_name]

        back_ground_knowledge = ""
        if self.km_path != "":
            vector_path = self.km_path
            question = question
            persist_directory = vector_path
            embedding_model_name = self.embedding_model_name
            docs = getvectorkm_String(question, persist_directory, embedding_model_name)
            print(docs)
            print(docs[0].page_content)
            back_ground_knowledge = docs[0].page_content

        if back_ground_knowledge != "":
            question = f'请根据后面提供的背景内容回答问题，回答只能限制在背景内容的范围内，问题是：{question};供参考的背景内容是：{back_ground_knowledge}'
            answer = brain(command=question)
        else:
            answer = brain(command=question)

        add_AgentTask(question, answer, 1, 1, 1, 1, 1)

        return answer
