import os
import threading

import openai
import shutil
import urllib
from datetime import datetime
import requests
import os
from PyQt5 import QtGui
from PyQt5.QtWidgets import QWidget, QFileDialog, QMessageBox, QDialog, QTreeWidgetItemIterator, QPlainTextEdit
from PyQt5.QtCore import QSettings, Qt, QUrl, QFile, QFileInfo
from PyQt5.QtGui import QIcon, QStandardItemModel, QStandardItem

from langchainhandler import getvectorkm_String
from speaker import Speaker
from ui.ui_TaskPageWidget import Ui_TaskPageWidget
import hashlib
import webbrowser
from db.DBFactory import add_AgentTask
import http.client
import json
from pluginsmanager import PluginEngine, PluginType

import argparse

from pluginsmanager import FileSystem

import urllib.request
import re

import sys

sys.path.append("..")
sys.path.append("../..")
from kmselect import FreezeTableDialog as KmFreezeTableDialog
from pluginselect import FreezeTableDialog as PluginFreezeTableDialog, ComboBoxDelegate, ButtonDelegate
from pluginselect_tool import FreezeTableDialog as PluginFreezeTableDialogTool, ComboBoxDelegate as ComboBoxDelegateTool, ButtonDelegate as ButtonDelegateTool

from db.DBFactory import add_KMCfg, query_KMCfg_All, update_KMCfg, delete_KMCfg, query_KMCfg
from db.DBFactory import add_PluginMng, query_PluginMng_All, update_PluginMng, delete_PluginMng, query_PluginMng,query_PluginMng_All_Tool
from db.DBFactory import update_AgentCfg
from globals import global_plugin_list
from globals import global_buddy_list
import globals
import sys
from PyQt5.QtWidgets import QApplication, QMessageBox
from PyQt5.QtCore import QThread, pyqtSignal
from RPAStocksHandle import StocksHandle
from Agent import Agent, AgentMode
import pyautogui
import pyperclip
import os
import time

from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QLineEdit, QPushButton, QVBoxLayout, QWidget, QMenu, QAction, QHBoxLayout, QShortcut
)
from PyQt5.QtWebEngineWidgets import QWebEngineView
from PyQt5.QtCore import QUrl, Qt
from PyQt5.QtGui import QKeySequence
from pluginsmanager.plugins_gui.tab_plugin import load_plugin
from pluginsmanager.plugins_headless.plugin_mng import load_plugin as load_plugin_headless
pyautogui.PAUSE = 0.5
from pathlib import Path
from util import generate_random_id, add_msg_to_message_window, get_user_ask_msg_title_formatted, get_user_ask_msg_content_formatted, get_agent_reply_msg_title_formatted, get_agent_reply_msg_content_formatted, toggle_msg_loading_status, add_agent_reply_msg_to_message_window, add_msg_to_message_window_with_markdown_and_highlight, add_attachment_to_message_window,image_to_base64,generate_img_tag

current_agent = None



class WorkerThread(QThread):
    finished = pyqtSignal(str, str, int)

    def __init__(self, agent, task_id, is_first, question, messages, pluginname, vector_path, embedding_model_name, modelname, web_browser, speaker, attachment_content_list, plugin_tool_record_selected_list,parent=None):
        super(WorkerThread, self).__init__(parent)
        global current_agent
        self.agent = agent
        current_agent = self.agent
        agent_cfg = agent.agent_cfg
        self.agentcfg = agent_cfg
        self.task_id = task_id
        self.is_first = is_first
        self.agent_name = agent_cfg.name
        self.question = question
        self.messages = messages
        self.pluginname = pluginname
        self.vector_path = vector_path
        self.embedding_model_name = embedding_model_name
        self.modelname = modelname
        self.web_browser = web_browser
        self.browser_page = web_browser.page()
        self.speaker = speaker
        self.attachment_content_list=attachment_content_list
        self.plugin_tool_record_selected_list = plugin_tool_record_selected_list

    def run(self):
        agent = self.agent
        browser_page = self.browser_page
        agent.set_mode(AgentMode.ChatOnly)
        agent.give_it_plugin(self.pluginname)
        agent.give_it_plugin_tool(self.plugin_tool_record_selected_list)
        agent.give_it_attachment_content_list(self.attachment_content_list)
        agent.give_it_km(self.vector_path, self.embedding_model_name)
        agent.give_it_speaker(self.speaker)
        question = self.question
        answer = agent.ask_it(question, self.messages, browser_page,self.task_id)
        attachment_content_list=json.dumps(agent.attachment_content_list, ensure_ascii=False)#km部分已经在agent中进行了处理，添加进去了
        # attachment_doc_content=json.dumps(agent.attachment_doc_content)
        # attachment_image_list=json.dumps(agent.attachment_image_list)
        if agent.chat_mode=="task":
            # question="用户发出了上述指令"
            question = "exit"
        record_id = add_AgentTask(self.task_id, question, question, answer, self.modelname, self.agentcfg.user_id, self.is_first,attachment_content_list)

        agent.remove_all_attachment()
        self.finished.emit(question, answer, record_id)

    def stop(self):
        print("thread stopping....")
        del self.agent
        print("del agent....")

class WorkerThreadGP(QThread):


    def __init__(self):
        super(WorkerThreadGP, self).__init__(None)
        print("ok")


    def run(self):
        stocks_handle = StocksHandle()
        companies = ['google', 'amazon', 'meta', 'apple']
        stocks_handle.get_Stocks(companies)
        print("准备发文件...")
        os.startfile("C:\Program Files (x86)\Tencent\WeChat\WeChat.exe")
        time.sleep(1)
        self.click_image_position("search.png")
        name = '文件传输助手'
        pyperclip.copy(name)
        # 模拟按下和释放Ctr1键和V键
        pyautogui.hotkey('ctrl', 'v')
        pyautogui.press('enter')
        time.sleep(1)  # 避免操作过快
        self.click_image_position("sendfile.png")
        directory = os.path.join(Path(__file__).resolve().parent, "temp", "market")
        NOW = datetime.now()
        PPTX = f'{directory}-{NOW.month}-{NOW.year}.pptx'
        file_path = PPTX
        pyperclip.copy(file_path)
        pyautogui.hotkey('ctrl', 'v')
        pyautogui.press('enter')
        time.sleep(1)
        pyautogui.press('enter')




class TaskPage(QWidget, Ui_TaskPageWidget):
    def __init__(self, application, agent):
        super(TaskPage, self).__init__()
        self.agent = agent
        agent_cfg = agent.agent_cfg
        self.agent_cfg = agent_cfg
        self.name = agent_cfg.name
        self.application = application
        self.task_id = ""
        self.is_first = True
        self.task_type = 'single'
        self.page_index = 0
        self.system_role_prompt = "You are a helpful assistant who provides concise and accurate information."
        # 后面可能会有system提示，这句在这个地方，可能会导致像百川这样不允许多个system的role的提示语，会报错，百度不允许有system这个角色
        self.messages = [{"role": "system", "content": f"{self.system_role_prompt}"}]
        # self.messages = []
        self.task_command=""
        self.is_transfer_to_workflow = False
        self.pre_system_role_prompt = ""
        self.work_flow_title = ""
        self.work_flow_label = ""
        self.work_flow_desc = ""

        self.messages_attachment_list = {}
        self.messages_km_list = {}
        self.messages_attachment_content = {}
        self.messages_km_content = {}
        self.words = ""
        self.words_count = 0


        # 指定历史(指定上下文相关)
        self.selected_history_messages = []
        self.selected_history_index = []
        self.selected_history_id = []

        # 附件信息相关
        self.current_attachment_list = []
        # self.current_attachment_content="___________以下是相关附件信息,供你参考___________"
        # self.current_attachment_content = ""  # 合并后的附件内容
        self.attachment_content_list = []  # 附件内容列表
        self.attachment_labels = []  # 存储所有附件标签

        self.conten_menu_closing=False#是否正在关闭内容菜单，用于给全选按钮做判断条件

        self.setupUi(self)

        # webengineview去掉了
        # self.messageBrowser.setPlainText("")
        # self.messageBrowser.setOpenLinks(False)

        self.messageEdit.setFocus()

        self.sendButton.clicked.connect(self.sendMessage)
        self.stopButton.clicked.connect(self.stopMessage)
        self.plugin_button.clicked.connect(self.opendialog_plugin_tool)
        self.newButton.clicked.connect(self.new_task_by_btn)
        self.attach_button.clicked.connect(self.add_attachment)
        self.kmButton.clicked.connect(self.opendialogkm)
        self.model_select_checkbox.stateChanged.connect(self.toggle_model_select_type)
        self.task_mode_checkbox.stateChanged.connect(self.toggle_chat_mode)
        self.history_mode_checkbox.stateChanged.connect(self.toggle_history_mode)
        self.prompt_combobox.currentIndexChanged.connect(self.set_prompt_string)
        # self.manage_button.clicked.connect(self.on_manage_button_clicked)#由下面这句替代了
        self.manage_button.mousePressEvent=self.manage_button_mousePressEvent



        self.update_prompts_in_combobox()

        self.shortcut = QShortcut(QKeySequence('Ctrl+F'), self)
        self.shortcut.activated.connect(self.toggle_search_box)

        self.tab_plugin=None

        self.kmselectedList = []
        if agent_cfg.kms != "":
            self.kmselectedList = agent_cfg.kms.split(",")
        print(self.kmselectedList)
        self.pluginselectedList = []
        self.pluginselectedList_tool = []
        self.plugin_tool_record_selected_list = []
        self.plugin_tool_loaded_list ={}
        if agent_cfg.plugins != "":
            self.pluginselectedList = agent_cfg.plugins.split(",")
        print(self.pluginselectedList)
        self.set_messagebox_placeholder()

        # self.messageBrowser.anchorClicked.connect(self.openLink)
        print(self.application.cjr)
        self.is_browser_page_loaded = False
        self.messageBrowser.page().loadFinished.connect(self.onLoadFinished)  # 第一次可能page没来得及load，所以需要在onload中处理

    def onLoadFinished(self):
        self.is_browser_page_loaded = True
        self.messageEdit.setFocus()

    def keyPressEvent(self, event):
        # if event.key() == Qt.Key_F and event.modifiers() == Qt.ControlModifier:
        if event.key() == Qt.Key_F1 and event.modifiers() == Qt.ControlModifier:
            print("Ctrl+F detected")
            self.toggle_search_box()

    def increment_page_index(self):
        self.page_index += 1
        return self.page_index

    def set_selected_history_index(self, i, id, status):
        print("set_selected_history_index i:", i)
        print("set_selected_history_index id", id)
        print("set_selected_history_index status", status)
        if status == "checked":
            self.add_selected_history_index(i)
            self.add_selected_history_id(id)
        else:
            self.remove_selected_history_index(i)
            self.remove_selected_history_id(id)
        self.get_selected_history_messages()



    def toggle_content_menu(self,status="checked"):
        if status == "checked":
            self.content_menu_group_box.setVisible(True)

            for i in range(self.hboxlayout.count()):
                item = self.hboxlayout.itemAt(i)
                if item.widget():
                    item.widget().setVisible(False)  # 隐藏每个控件

            for i in range(self.hboxlayout1.count()):
                item = self.hboxlayout1.itemAt(i)
                if item.widget():
                    item.widget().setVisible(False)  # 隐藏每个控件

        else:#由关闭按钮触发
            self.conten_menu_closing = True
            self.content_menu_group_box.setVisible(False)

            for i in range(self.hboxlayout.count()):
                item = self.hboxlayout.itemAt(i)
                if item.widget():
                    item.widget().setVisible(True)  # 隐藏每个控件

            for i in range(self.hboxlayout1.count()):
                item = self.hboxlayout1.itemAt(i)
                if item.widget():
                    item.widget().setVisible(True)  # 隐藏每个控件
            self.stopButton.setVisible(False)

            if self.history_mode_checkbox.isChecked()==False:

                self.task_mode_checkboxa.setChecked(False)
                # self.toggle_page_all_checkboxes_status(0)
                self.messageBrowser.page().runJavaScript("hideCheckboxes()")



    def edit_selected_content(self, code_type, text,file_name=""):
        tabs = self.tabWidget
        if code_type.lower() == "mermaid" or (code_type.lower() == "markdown" and "```mermaid" in text) :

            plugin_cfg=query_PluginMng(plugin_id="EK202405K7170A7T190951")

        elif code_type.lower() == "mindmap" or (code_type.lower() == "markdown" and (("思维导图" in text and "##" in text) or ("mindmap" in text and "##" in text)  or (text.startswith("#") and "##" in text)) ):

            plugin_cfg = query_PluginMng(plugin_id="AK2024Y5Q717U20711095")

        else:

            plugin_cfg = query_PluginMng(plugin_id="TP20230517670237197EF")

        plugin = self.load_plugin_to_tab(plugin_cfg)

        plugin.run(file_name, text)

    def add_selected_history_index(self, i):
        # Check if 'i' is already in 'self.selected_history_index'
        if i not in self.selected_history_index:
            # Insert 'i' into 'self.selected_history_index' in sorted order
            self.selected_history_index.append(i)
            self.selected_history_index.sort()

    def remove_selected_history_index(self, i):
        # Remove the first occurrence of 'i' from 'self.selected_history_index', if it exists
        if i in self.selected_history_index:
            self.selected_history_index.remove(i)

    def add_selected_history_id(self, id):
        # Check if 'i' is already in 'self.selected_history_index'
        if id not in self.selected_history_id:
            # Insert 'i' into 'self.selected_history_index' in sorted order
            self.selected_history_id.append(id)
            self.selected_history_id.sort()

    def remove_selected_history_id(self, id):
        # Remove the first occurrence of 'i' from 'self.selected_history_index', if it exists
        if id in self.selected_history_id:
            self.selected_history_id.remove(id)

    def get_selected_history_messages(self):
        # Clear the selected_history_messages list first
        self.selected_history_messages.clear()
        self.selected_history_messages = [{"role": "system", "content": f"{self.system_role_prompt}"}]
        # Get the messages corresponding to the indices in selected_history_index
        for index in self.selected_history_index:
            if 0 <= index < len(self.messages):
                self.selected_history_messages.append(self.messages[index])

    def new_task(self):
        self.task_id = ""
        self.is_first = True
        # 后面可能会有system提示，这句在这个地方，可能会导致像百川这样不允许多个system的role的提示语，会报错，百度不允许有system这个角色
        # self.messages = [{"role": "system", "content": "You are a helpful assistant who provides concise and accurate information."}]
        self.messages = [{"role": "system", "content": f"{self.system_role_prompt}"}]
        self.task_command = ""
        # self.messages = []
        self.page_index = 0
        self.selected_history_messages = []
        self.selected_history_index = []
        self.selected_history_id = []

        self.messages_attachment_list = {}
        self.messages_km_list = {}
        self.messages_attachment_content = {}
        self.messages_km_content = {}


        # 附件信息相关
        self.current_attachment_list = []
        # self.current_attachment_content="___________以下是相关附件信息,供你参考___________"
        # self.current_attachment_content = ""  # 合并后的附件内容
        self.attachment_content_list = []  # 附件内容列表
        self.attachment_labels = []  # 存储所有附件标签

        #***********todo:附件的界面也要清除掉****************


        self.messageBrowser.page().runJavaScript('re_init()')

    def receiveMessage(self, event):
        message = f"""\n<strong><span style="color: darkblue">{self.name} :</span></strong> {event.getBody()}"""
        self.messageBrowser.append(message)

    def __description(self) -> str:
        return "Create your own anime meta data"

    def __usage(self) -> str:
        return "vrv-meta.py --service vrv"

    def __init_cli(self) -> argparse:
        parser = argparse.ArgumentParser(description=self.__description(), usage=self.__usage())
        parser.add_argument(
            '-l', '--log', default='DEBUG', help="""
            Specify log level which should use. Default will always be DEBUG, choose between the following options
            CRITICAL, ERROR, WARNING, INFO, DEBUG
            """
        )
        parser.add_argument(
            '-d', '--directory', default=f'{FileSystem.get_plugins_directory()}', help="""
            (Optional) Supply a directory where plugins should be loaded from. The default is ./plugins
            """
        )
        return parser

    def __print_program_end(self) -> None:
        print("-----------------------------------")
        print("End of execution")
        print("-----------------------------------")

    def __init_app(self, parameters: dict) -> None:
        return PluginEngine(options=parameters).start()

    def click_image_position(self, img):
        # time.sleep(1)
        image_1 = pyautogui.locateOnScreen(img, grayscale=True, confidence=0.7)
        # time.sleep(1)
        center = pyautogui.center(image_1)
        pyautogui.click(center)

    def sendMessage(self):

        if self.messageEdit.toPlainText():

            __cli_args = self.__init_cli().parse_args()
            print(__cli_args.log)


            if len(self.pluginselectedList) > 0:
                # self.pluginselectedList: [(1, '2', 'ChatGLM连接器: 1.0.0', 'chatglm_connector')]#row index,record id,plugin name,plugin alias
                # pluginname=self.pluginselectedList[0][2]
                # modelname=self.pluginselectedList[0][3]
                pluginname = self.pluginselectedList[0]
                llm = global_plugin_list[pluginname]
                config = llm.get_config()
                modelname = config.get("model", "")
                modelname = pluginname + f"({modelname})"

                # 增加以下语句，如果有选中的插件，则认为是指定了，而不是自动，暂时不要使用checkbox进行指定
                self.agent.model_select_type = 'specify'

            else:
                pluginname = "ChatGLM连接器: 1.0.0"  # 设置缺省连接器
                modelname = "ChatGLM"  # 指定缺省模型
                # 增加以下语句，如果没选中插件，则认为是自动，暂时不要使用checkbox进行指定
                self.agent.model_select_type = 'auto'

            if self.agent.model_select_type == 'auto':
                if "天气" in self.messageEdit.toPlainText():
                    pluginname = "百度文心连接器: 1.0.0"
                    llm = global_plugin_list[pluginname]
                    config = llm.get_config()
                    modelname = "ERNIE-3.5-8K"
                    modelname = pluginname + f"({modelname})"
                elif "编写" in self.messageEdit.toPlainText():
                    pluginname = "通义千问连接器: 1.0.0"
                    llm = global_plugin_list[pluginname]
                    config = llm.get_config()
                    modelname = "qwen-long"
                    modelname = pluginname + f"({modelname})"
                elif "写一个" in self.messageEdit.toPlainText():
                    pluginname = "通义千问连接器: 1.0.0"
                    llm = global_plugin_list[pluginname]
                    config = llm.get_config()
                    modelname = "qwen-long"
                    modelname = pluginname + f"({modelname})"

                elif "算法" in self.messageEdit.toPlainText():
                    pluginname = "通义千问连接器: 1.0.0"
                    llm = global_plugin_list[pluginname]
                    config = llm.get_config()
                    modelname = "qwen-long"
                    modelname = pluginname + f"({modelname})"

                elif "介绍一下" in self.messageEdit.toPlainText():
                    pluginname = "讯飞星火连接器: 1.0.0"
                    llm = global_plugin_list[pluginname]
                    config = llm.get_config()
                    modelname = "general"
                    modelname = pluginname + f"({modelname})"

            promptstr = ""
            print("the km list", self.kmselectedList)
            print("the km list length", len(self.kmselectedList))
            if len(self.kmselectedList) > 0:
                print("self.kmselectedList:")
                print(self.kmselectedList)
                km_name = self.kmselectedList[0]
                km_record = query_KMCfg(name=km_name)
                vector_path = km_record.kmpath
                print("vector_path:", vector_path)
                # vector_path = "vector_store/vector"  # 先写死
                vector_path = os.path.join(os.getcwd(), "km",vector_path,"vector")
                print("vector_path2:", vector_path)
                embedding_model_name = km_record.embeddingmodel
            else:
                vector_path = ""
                embedding_model_name = ""



            question = self.messageEdit.toPlainText()
            self.task_command = question


            speaker = self.speaker

            # 处理插件
            plugin_tool_record_selected_list = self.plugin_tool_record_selected_list
            for record in plugin_tool_record_selected_list:
                if "previous_to_send_b" in record.plugin_event :
                    index_event=record.plugin_event.split(",").index("previous_to_send_b")
                    instruction_list = []
                    instruction = record.instruction
                    instructed_flag = False
                    run_plugin_flag = False
                    if instruction:
                        instruction_list = instruction.split(",")

                    for inst in instruction_list:
                        if inst in question:
                            instructed_flag = True

                    if instructed_flag:
                        run_plugin_flag = True

                    if run_plugin_flag:
                        plugin = self.plugin_tool_loaded_list[record.name]
                        result = plugin.handle_previous_to_send_b(self, question)
                        how_to_handle_executed_result = record.plugin_executed.split(",")[index_event]
                        if how_to_handle_executed_result == "get_output_as_final_result":
                            answer = result
                            return answer
                        else:
                            question = result
                            self.messageEdit.setPlainText(result)


            if self.messageEdit.toPlainText() == "ymcymc":

                print(os.getcwd())
                print(os.path.join(os.getcwd(), "scripts", "index.html"))
                print(urllib.request.pathname2url(os.path.join(os.getcwd(), "index.html")))
                url_string = urllib.request.pathname2url(os.path.join(os.getcwd(), "scripts", "index.html"))
                print("transform")
                print(url_string)
                self.messageBrowser.page().load(QUrl(url_string))
                print("okcjrok")
            elif self.messageEdit.toPlainText() == "szrszr":

                url_string = "https://bridge.yfd.net:1443/"
                print("transform")
                print(url_string)
                self.messageBrowser.page().load(QUrl(url_string))
                print("szrszr")
            elif self.messageEdit.toPlainText() == "zdfzdf":

                self.application.conversation_pages.setCurrentIndex(1)  # 首页
                self.application.ShowAiChatStack()

                if "buddylist" in global_buddy_list:
                    buddylist = global_buddy_list["buddylist"]
                    buddylist.send_message("yangyang@xabber.de", "您好，我自动发")
            elif "to autogen:" in self.messageEdit.toPlainText():
                global current_agent

                current_agent.human_reply = self.messageEdit.toPlainText()[11:]
                message = f"""{current_agent.human_reply}"""
                self.messageBrowser.page().runJavaScript('document.body.innerHTML += "' + message + '<br><br>"')
            elif "*给我画*" in self.messageEdit.toPlainText():
                #废弃掉不通过这个判断走了，现在是在Agent中走
                urls=self.generate_image(self.messageEdit.toPlainText())
                print("给我画url:",urls)



                message = f"""<strong><em><span style='color: darkred;font-size:14px;'>{self.tr("用户")}: </span><span style='color: #c0c0c0; font-size:14px;'>{datetime.now().strftime("%Y-%m-%d %H:%M:%S")}</span></em></strong>"""
                self.messageBrowser.page().runJavaScript('document.getElementById("allcontent").innerHTML += "' + message + '<br>"')
                message = f"""{self.messageEdit.toPlainText()}"""
                self.messageBrowser.page().runJavaScript('document.getElementById("allcontent").innerHTML += "' + message + '<br><br>"')
                modelname="Dall-e-3"
                message = f"""<strong><em><span style='color: darkblue; font-size:14px;'>{self.tr(modelname)}: </span><span style='color: #c0c0c0; font-size:14px;'>{datetime.now().strftime("%Y-%m-%d %H:%M:%S")}</span></em></strong><br>"""
                self.messageBrowser.page().runJavaScript('document.getElementById("allcontent").innerHTML += "' + message + '"')

                # 创建新的附件元素

                img_element=''.join(f"<img src='{url}'>&nbsp;&nbsp;&nbsp;&nbsp;<br>" for url in urls)
                print(img_element)
                # 添加附件元素到页面中
                self.messageBrowser.page().runJavaScript('document.getElementById("allcontent").innerHTML += `' + img_element + '`')
            elif "股票" in self.messageEdit.toPlainText():
                print("股票")

                os.system("C:\\dev\\rpa\\Stocks_RPA_Python\\venv\\Scripts\\python.exe C:/dev/rpa/Stocks_RPA_Python/mainv2.py")

                # stocks_handle = StocksHandle()
                # companies = ['google', 'amazon', 'meta', 'apple']
                # stocks_handle.get_Stocks(companies)

                # self.thread = WorkerThreadGP()
                #
                # self.thread.start()

                # print("准备发文件...")
                # os.startfile("C:\Program Files (x86)\Tencent\WeChat\WeChat.exe")
                # time.sleep(1)
                # self.click_image_position("search.png")
                # name = '文件传输助手'
                # pyperclip.copy(name)
                # # 模拟按下和释放Ctr1键和V键
                # pyautogui.hotkey('ctrl', 'v')
                # pyautogui.press('enter')
                # time.sleep(1)  # 避免操作过快
                # self.click_image_position("sendfile.png")
                # directory = os.path.join(Path(__file__).resolve().parent, "temp", "market")
                # NOW = datetime.now()
                # PPTX = f'{directory}-{NOW.month}-{NOW.year}.pptx'
                # file_path = PPTX
                # pyperclip.copy(file_path)
                # pyautogui.hotkey('ctrl', 'v')
                # pyautogui.press('enter')
                # time.sleep(1)
                # pyautogui.press('enter')

                message = f"""<strong><em><span style='color: darkred;font-size:14px;'>{self.tr("用户")}: </span><span style='color: #c0c0c0; font-size:14px;'>{datetime.now().strftime("%Y-%m-%d %H:%M:%S")}</span></em></strong>"""
                self.messageBrowser.page().runJavaScript('document.body.innerHTML += "' + message + '<br>"')
                message = f"""{self.messageEdit.toPlainText()}"""
                self.messageBrowser.page().runJavaScript('document.body.innerHTML += "' + message + '<br><br>"')

                message = f"""<strong><em><span style='color: darkblue; font-size:14px;'>{self.tr(modelname)}: </span><span style='color: #c0c0c0; font-size:14px;'>{datetime.now().strftime("%Y-%m-%d %H:%M:%S")}</span></em></strong><br>"""
                self.messageBrowser.page().runJavaScript('document.body.innerHTML += "' + message + '"')

                message = f"""处理完毕！"""
                self.messageBrowser.page().runJavaScript('document.body.innerHTML += "' + message + '<br><br>"')

            elif "学习" in self.messageEdit.toPlainText():


                # stocks_handle = StocksHandle()
                # companies = ['google', 'amazon', 'meta', 'apple']
                # stocks_handle.get_Stocks(companies)

                # self.thread = WorkerThreadGP()
                #
                # self.thread.start()

                # print("准备发文件...")
                # os.startfile("C:\Program Files (x86)\Tencent\WeChat\WeChat.exe")
                # time.sleep(1)
                # self.click_image_position("search.png")
                # name = '文件传输助手'
                # pyperclip.copy(name)
                # # 模拟按下和释放Ctr1键和V键
                # pyautogui.hotkey('ctrl', 'v')
                # pyautogui.press('enter')
                # time.sleep(1)  # 避免操作过快
                # self.click_image_position("sendfile.png")
                # directory = os.path.join(Path(__file__).resolve().parent, "temp", "market")
                # NOW = datetime.now()
                # PPTX = f'{directory}-{NOW.month}-{NOW.year}.pptx'
                # file_path = PPTX
                # pyperclip.copy(file_path)
                # pyautogui.hotkey('ctrl', 'v')
                # pyautogui.press('enter')
                # time.sleep(1)
                # pyautogui.press('enter')

                message = f"""<strong><em><span style='color: darkred;font-size:14px;'>{self.tr("用户")}: </span><span style='color: #c0c0c0; font-size:14px;'>{datetime.now().strftime("%Y-%m-%d %H:%M:%S")}</span></em></strong>"""
                self.messageBrowser.page().runJavaScript('document.body.innerHTML += "' + message + '<br>"')
                message = f"""{self.messageEdit.toPlainText()}"""
                self.messageBrowser.page().runJavaScript('document.body.innerHTML += "' + message + '<br><br>"')

                message = f"""<strong><em><span style='color: darkblue; font-size:14px;'>{self.tr(modelname)}: </span><span style='color: #c0c0c0; font-size:14px;'>{datetime.now().strftime("%Y-%m-%d %H:%M:%S")}</span></em></strong><br>"""
                self.messageBrowser.page().runJavaScript('document.body.innerHTML += "' + message + '"')

                message = f"""好的，记录下每个步骤，并认真学习！"""
                self.messageBrowser.page().runJavaScript('document.body.innerHTML += "' + message + '<br><br>"')

                time.sleep(1)

                print("学习....")
                opr_file_name = self.messageEdit.toPlainText()
                opr_file_name = opr_file_name.replace("学习一下", "")
                opr_file_name = opr_file_name.replace("学习", "")
                os.system(f"python C:/dev/ai-sns/record-and-play-pynput/record-and-play-pynput/record.py {opr_file_name} record-all")


            elif "演示" in self.messageEdit.toPlainText():
                print("演示....")

                # os.system("C:\\dev\\ai-sns\\record-and-play-pynput\\record-and-play-pynput\\venv\\Scripts\\python.exe C:/dev/ai-sns/record-and-play-pynput/record-and-play-pynput/play.py test001 1")
                print("演示....")
                opr_file_name = self.messageEdit.toPlainText()
                opr_file_name = opr_file_name.replace("演示一下", "")
                opr_file_name = opr_file_name.replace("演示", "")
                os.system(f"python C:/dev/ai-sns/record-and-play-pynput/record-and-play-pynput/play.py {opr_file_name} 1")

                # stocks_handle = StocksHandle()
                # companies = ['google', 'amazon', 'meta', 'apple']
                # stocks_handle.get_Stocks(companies)

                # self.thread = WorkerThreadGP()
                #
                # self.thread.start()

                # print("准备发文件...")
                # os.startfile("C:\Program Files (x86)\Tencent\WeChat\WeChat.exe")
                # time.sleep(1)
                # self.click_image_position("search.png")
                # name = '文件传输助手'
                # pyperclip.copy(name)
                # # 模拟按下和释放Ctr1键和V键
                # pyautogui.hotkey('ctrl', 'v')
                # pyautogui.press('enter')
                # time.sleep(1)  # 避免操作过快
                # self.click_image_position("sendfile.png")
                # directory = os.path.join(Path(__file__).resolve().parent, "temp", "market")
                # NOW = datetime.now()
                # PPTX = f'{directory}-{NOW.month}-{NOW.year}.pptx'
                # file_path = PPTX
                # pyperclip.copy(file_path)
                # pyautogui.hotkey('ctrl', 'v')
                # pyautogui.press('enter')
                # time.sleep(1)
                # pyautogui.press('enter')

                message = f"""<strong><em><span style='color: darkred;font-size:14px;'>{self.tr("用户")}: </span><span style='color: #c0c0c0; font-size:14px;'>{datetime.now().strftime("%Y-%m-%d %H:%M:%S")}</span></em></strong>"""
                self.messageBrowser.page().runJavaScript('document.body.innerHTML += "' + message + '<br>"')
                message = f"""{self.messageEdit.toPlainText()}"""
                self.messageBrowser.page().runJavaScript('document.body.innerHTML += "' + message + '<br><br>"')

                message = f"""<strong><em><span style='color: darkblue; font-size:14px;'>{self.tr(modelname)}: </span><span style='color: #c0c0c0; font-size:14px;'>{datetime.now().strftime("%Y-%m-%d %H:%M:%S")}</span></em></strong><br>"""
                self.messageBrowser.page().runJavaScript('document.body.innerHTML += "' + message + '"')

                message = f"""好的，这是我演示的内容，请多指教！"""
                self.messageBrowser.page().runJavaScript('document.body.innerHTML += "' + message + '<br><br>"')


            elif "//中国象棋" in self.messageEdit.toPlainText():
                tabs = self.tabWidget
                load_plugin(tabs, "中国象棋", "chinese_chess", "ChineseChess", content="red")
                if not self.output_checkbox.isChecked():
                    self.output_checkbox.setChecked(True)
                    self.toggle_output_checkbox(self.output_checkbox.checkState())
            elif "//国际象棋bak" in self.messageEdit.toPlainText():
                tabs = self.tabWidget
                move_str=self.messageEdit.toPlainText().replace("//国际象棋","")
                chess_view = tabs.findChild(QWebEngineView, "chess")
                if chess_view is None:
                    self.tab_plugin=load_plugin(tabs, "国际象棋", "chess", "Chess", content=move_str)

                    # 设置定时器，5秒后调用 my_function
                    # timer = threading.Timer(1, self.tab_plugin.handle_send_message(self, move_str))
                    #
                    # # 启动定时器
                    # timer.start()
                    return_msg=self.tab_plugin.handle_send_message(self, move_str)
                    # self.messageEdit.setPlainText(return_msg)
                    # self.sendMessage()
                else:
                    # chess_view.page().runJavaScript(f"document.getElementById('allcontent').innerHTML = `{svg}`")
                    return_msg = self.tab_plugin.handle_send_message(self, move_str)
                    self.messageEdit.setPlainText(return_msg)
                    self.sendMessage()

                if not self.output_checkbox.isChecked():
                    self.output_checkbox.setChecked(True)
                    self.toggle_output_checkbox(self.output_checkbox.checkState())

                # return False

            elif "//数字人" in self.messageEdit.toPlainText():
                tabs = self.tabWidget
                move_str=self.messageEdit.toPlainText().replace("//数字人","")
                digital_human_view = tabs.findChild(QWebEngineView, "digital_human")
                if digital_human_view is None:
                    self.tab_plugin=load_plugin(tabs, "数字人", "digital_human", "DigitalHuman", content=move_str)

                    # 设置定时器，5秒后调用 my_function
                    # timer = threading.Timer(1, self.tab_plugin.handle_send_message(self, move_str))
                    #
                    # # 启动定时器
                    # timer.start()
                    return_msg=self.tab_plugin.handle_send_message(self, move_str)
                    # self.messageEdit.setPlainText(return_msg)
                    # self.sendMessage()
                else:
                    # chess_view.page().runJavaScript(f"document.getElementById('allcontent').innerHTML = `{svg}`")
                    return_msg = self.tab_plugin.handle_send_message(self, move_str)
                    self.messageEdit.setPlainText(return_msg)
                    self.sendMessage()

                if not self.output_checkbox.isChecked():
                    self.output_checkbox.setChecked(True)
                    self.toggle_output_checkbox(self.output_checkbox.checkState())

                # return False


            elif self.speaker.status == "wait_for_feedback":
                 self.speaker.human_feedback=self.messageEdit.toPlainText()

                 page_index = self.increment_page_index()
                 message = get_user_ask_msg_title_formatted(page_index)
                 add_msg_to_message_window(self.messageBrowser.page(), message, 1)

                 message = get_user_ask_msg_content_formatted(question)
                 add_msg_to_message_window(self.messageBrowser.page(), message, 2)
                 self.messageBrowser.page().runJavaScript("window.scrollTo(0, document.body.scrollHeight);")

                 page_index = self.increment_page_index()
                 message = get_agent_reply_msg_title_formatted(modelname, page_index)
                 add_msg_to_message_window(self.messageBrowser.page(), message, 1)


            else:
                task_id = self.task_id
                if task_id == "":
                    task_id = generate_random_id()
                    self.task_id = task_id
                    self.is_first = True

                if len(self.current_attachment_list)>0:
                    directory_path = os.path.join('resource', 'attachment', 'chat', task_id)
                    os.makedirs(directory_path, exist_ok=True)

                for file_path in self.current_attachment_list:
                    try:
                        shutil.copy(file_path, directory_path)
                    except Exception as e:
                        print(f"Error copying file {file_path}: {e}")

                page_index = self.increment_page_index()
                if self.history_mode_checkbox.isChecked()==True:
                    message = get_user_ask_msg_title_formatted(page_index,show_checkbox="inline-block",checked="checked")
                    self.set_selected_history_index(page_index,"id_t99999_a","checked")#cjr error
                else:
                    message = get_user_ask_msg_title_formatted(page_index)
                add_msg_to_message_window(self.messageBrowser.page(), message, 1)

                message = get_user_ask_msg_content_formatted(question)
                add_msg_to_message_window(self.messageBrowser.page(), message, 2)
                self.messageBrowser.page().runJavaScript("window.scrollTo(0, document.body.scrollHeight);")


                #处理附件
                if len(self.current_attachment_list) > 0:
                    add_attachment_to_message_window(self.messageBrowser.page(),directory_path, self.current_attachment_list, 2)

                if self.messages[0]["role"] != "system":
                    self.messages.insert(0, {"role": "system", "content": f"{self.system_role_prompt}"})
                elif self.messages[0]["role"] == "system":
                    self.messages[0]["content"] = self.system_role_prompt

                if "百度" in modelname:
                    if self.messages[0]["role"] == "system":
                        self.messages = self.messages[1:]

                self.messages.append({"role": "user", "content": self.messageEdit.toPlainText()})

                page_index = self.increment_page_index()

                if self.history_mode_checkbox.isChecked()==True:

                    message = get_agent_reply_msg_title_formatted(modelname, page_index,show_checkbox="inline-block",checked="checked")

                else:
                    message = get_agent_reply_msg_title_formatted(modelname, page_index)


                add_msg_to_message_window(self.messageBrowser.page(), message, 1)


                #挪到顶部了
                # message_handler = self.message_handler
                # web_browser = self.messageBrowser
                # speaker = Speaker(message_handler, web_browser)
                # self.speaker =speaker

                if self.agent.history_mode == 'specify':
                    messages = [{"role": "system", "content": f"{self.system_role_prompt}"}]+self.selected_history_messages
                    messages.append({"role": "user", "content": self.messageEdit.toPlainText()})
                else:
                    messages = self.messages[:]

                attachment_content_list=self.attachment_content_list

                self.thread = WorkerThread(self.agent, task_id, self.is_first,question, messages, pluginname, vector_path, embedding_model_name, modelname, self.messageBrowser, speaker,attachment_content_list,plugin_tool_record_selected_list)
                self.thread.finished.connect(self.onTaskFinished)
                self.thread.start()

                # ***************????????????

            self.messageEdit.clear()
            self.messageEdit.setAcceptRichText(False)
            self.messageEdit.setTextColor(QtGui.QColor(0, 0, 0))
            self.messageEdit.setPlainText("")
            self.messageEdit.setStyleSheet("""
                        QTextEdit {
                            border-radius: 2px; /* 设置圆角 */
                            border: 1px solid #c0c0c0; /* 设置边框 */
                            background: transparent; 
                            color: black;
                        }
                        QTextEdit:focus {
                            border-color: #61addf; /* 设置焦点时的边框颜色 */
                        }
                    """)
            # self.messageEdit.setAcceptRichText(True)
            # if self.agent.chat_mode == 'chat':
            #     self.stopButton.setVisible(True)
            #     self.sendButton.setVisible(False)
            self.modelname=modelname
            self.messageEdit.setFocus()

    def stopMessage(self):
        self.thread.stop()

        del self.thread
        print("after deling2")
        self.speaker.stop_speaker=True
        self.stopButton.setVisible(False)
        self.sendButton.setVisible(True)

    def onTaskFinished(self, question, content, record_id):
        if self.is_first == True:
            application = self.application
            agent_cfg = self.agent_cfg
            taskList = application.tasklist_list[agent_cfg.user_id]
            taskList.deselect_all_items()
            taskList.addItem(question.replace("\n", "")[:50], record_id, True)
            # new_item=taskList.addItem(question.replace("\n", "")[:50], record_id, True)
            # new_item.setSelected(True)
            first_toplevel_item = taskList.topLevelItem(0)
            first_subitem = first_toplevel_item.child(0)
            first_subitem.setSelected(True)

        self.is_first = False
        toggle_msg_loading_status(self.messageBrowser.page())
        browser_page = self.messageBrowser.page()
        # add_agent_reply_msg_to_message_window(browser_page,content)已经在agent中处理了
        self.messages.append({"role": "assistant", "content": content})
        if self.tab_plugin:
            self.tab_plugin.handle_received_message(self, content)

        # 处理插件
        plugin_tool_record_selected_list = self.plugin_tool_record_selected_list
        for record in plugin_tool_record_selected_list:
            if "after_send_b" in record.plugin_event:
                index_event = record.plugin_event.split(",").index("after_send_b")
                instruction_list = []
                instruction = record.instruction
                instructed_flag = False
                run_plugin_flag = False
                if instruction:
                    instruction_list = instruction.split(",")

                for inst in instruction_list:
                    if inst in question:
                        instructed_flag = True

                if instructed_flag:
                    run_plugin_flag = True

                run_plugin_flag=True
                if run_plugin_flag:
                    plugin = self.plugin_tool_loaded_list[record.name]
                    result = plugin.handle_after_send_b(self, content)
                    how_to_handle_executed_result = record.plugin_executed.split(",")[index_event]
                    if how_to_handle_executed_result == "get_output_as_final_result":
                        answer = result
                        return answer
                    else:
                        answer = result


        #1.将附件列表添加到相应的附件列表全局变量中 2.将附件内容加入相应的问题附件内容 3.将附件全部清理掉
        # 4.将相关的知识召回列表添加到全局变量中 5.将相关的知识召回内容添加到全局变量中 6.清理此次相关的知识召回的信息
        self.messages_attachment_list[self.page_index-1] = self.current_attachment_list
        # self.messages_attachment_content[self.page_index-1] = self.current_attachment_content
        if self.history_mode_checkbox.isChecked()==True:
            self.set_selected_history_index(self.page_index,"id_" + str(record_id)+"_r", "checked")

        self.remove_all_attachments()

        question_div_id_old = f"msg_div_{self.page_index - 1}"
        answer_div_id_old = f"msg_div_{self.page_index}"
        question_div_id = "id_"+str(record_id)+"_a"
        answer_div_id = "id_" + str(record_id)+"_r"

        browser_page.runJavaScript('oldId=`' + question_div_id_old + '`')
        browser_page.runJavaScript('newId=`' + question_div_id + '`')
        browser_page.runJavaScript('setDivId(oldId,newId)')

        browser_page.runJavaScript('oldId=`' + answer_div_id_old + '`')
        browser_page.runJavaScript('newId=`' + answer_div_id + '`')
        browser_page.runJavaScript('setDivId(oldId,newId)')


        question_div_id_old = f"msg_checkbox_{self.page_index - 1}"
        answer_div_id_old = f"msg_checkbox_{self.page_index}"
        question_div_id = "id_"+str(record_id)+"_a"
        answer_div_id = "id_" + str(record_id)+"_r"

        browser_page.runJavaScript('oldId=`' + question_div_id_old + '`')
        browser_page.runJavaScript('newId=`' + question_div_id + '`')
        browser_page.runJavaScript('setCheckBoxId(oldId,newId)')

        browser_page.runJavaScript('oldId=`' + answer_div_id_old + '`')
        browser_page.runJavaScript('newId=`' + answer_div_id + '`')
        browser_page.runJavaScript('setCheckBoxId(oldId,newId)')


        if self.is_transfer_to_workflow:
            self.transfer_message_to_workflow(content)


        self.stopButton.setVisible(False)
        self.sendButton.setVisible(True)


    def setOpenFileName(self):
        openFileNameLabel = ""
        options = QFileDialog.Options()
        native = True
        if not native:
            options |= QFileDialog.DontUseNativeDialog
        fileName, _ = QFileDialog.getOpenFileName(self,
                                                  "QFileDialog.getOpenFileName()", openFileNameLabel,
                                                  "All Files (*);;Text Files (*.txt)", options=options)
        if fileName:
            openFileNameLabel = fileName
        print(openFileNameLabel)
        return openFileNameLabel

    def new_task_by_btn(self):
        application=self.application
        application.create_new_task_chat(self.agent)

    def add_attachment(self):
        openFilesPath = ""
        openFileNamesLabel = ""
        options = QFileDialog.Options()
        native = True
        filter_extensions = ("Text and Document Files (*.txt *.docx *.csv *.xlsx *.xls *.pptx *.pdf *.md *.html *.htm *.js);;"
                             "Image Files (*.png *.jpg *.bmp *.jpeg *.gif);;"
                             "Text Files (*.txt);;"
                             "Microsoft Word (*.docx);;"
                             "CSV Files (*.csv);;"
                             "Excel Files (*.xlsx);;"
                             "Excel 97-2003 (*.xls);;"
                             "PowerPoint Files (*.pptx);;"
                             "PDF Files (*.pdf);;"
                             "Markdown Files (*.md);;"
                             "HTML Files (*.html *.htm);;"
                             "SQL Files (*.sql);;"
                             "Markdown Files (*.md)")
        if not native:
            options |= QFileDialog.DontUseNativeDialog
        files, _ = QFileDialog.getOpenFileNames(self,
                                                "QFileDialog.getOpenFileNames()", openFilesPath,
                                                filter_extensions, options=options)

        self.add_attachment_area(files)


    def opendialog_plugin_tool(self):
        pluginselectedList_tool = self.pluginselectedList_tool
        selected_items = []
        unselected_items = []

        agents = query_PluginMng_All_Tool(is_delete=0)

        model = QStandardItemModel()
        header = ["", "plugin_id", "名称", "运行模式", "版本", "功能描述", "插件调用指令", "操作"]
        model.setHorizontalHeaderLabels(header)

        def create_item(text, editable=False):
            item = QStandardItem(text)
            if not editable:
                item.setFlags(item.flags() & ~Qt.ItemIsEditable)
            return item

        agent_dict = {f"{agent.plugin_id}": agent for agent in agents}

        # Process selected items first according to the order in pluginselectedList
        for selected in pluginselectedList_tool:
            if selected in agent_dict:
                agent = agent_dict.pop(selected)
                row_data = [
                    create_item(agent.plugin_id),
                    create_item(agent.name),
                    create_item({"back_end": "后台运行", "show_by_ai_call": "AI调用时显示插件", "show_when_activate": "启用时显示插件"}.get(agent.run_mode, "后台运行")),
                    create_item(agent.version),
                    create_item(agent.description),
                    create_item(agent.instruction),
                    create_item("操作")
                ]
                checkbox_item = QStandardItem()
                checkbox_item.setCheckable(True)
                checkbox_item.setCheckState(Qt.Checked)
                row_data.insert(0, checkbox_item)

                selected_items.append((agent, row_data))

        # Process the rest of the items
        for agent in agent_dict.values():
            row_data = [
                create_item(agent.plugin_id),
                create_item(agent.name),
                create_item({"back_end": "后台运行", "show_by_ai_call": "AI调用时显示插件", "show_when_activate": "启用时显示插件"}.get(agent.run_mode, "后台运行")),
                create_item(agent.version),
                create_item(agent.description),
                create_item(agent.instruction),
                create_item("操作")
            ]
            checkbox_item = QStandardItem()
            checkbox_item.setCheckable(True)
            row_data.insert(0, checkbox_item)
            unselected_items.append((agent, row_data))

        # Combine selected and unselected items
        all_items = selected_items + unselected_items

        # Add items to the model
        for row, (agent, item_row) in enumerate(all_items):
            for col, item in enumerate(item_row):
                model.setItem(row, col, item)


            # Placeholder for button, actual button will be inserted by delegate
            model.setItem(row, 7, QStandardItem())

        # Generate items_per_row based on the order of all_items
        items_per_row = {}
        for i, (agent, _) in enumerate(all_items):
            detail_json = json.loads(agent.detail)
            items_per_row[i] = detail_json.get("model_type", [])

        dialog = PluginFreezeTableDialogTool(model, items_per_row)

        button_delegate = ButtonDelegateTool(dialog.tableView, dialog)
        dialog.tableView.setItemDelegateForColumn(7, button_delegate)

        if dialog.exec_() == QDialog.Accepted:
            self.pluginselectedList_tool = dialog.getResult()
            print("self.pluginselectedList:", self.pluginselectedList_tool)
            print("self.pluginselectedListjoin:", ",".join(self.pluginselectedList_tool))
            self.plugin_tool_record_selected_list.clear()
            if self.pluginselectedList_tool:
                for plugin_id in self.pluginselectedList_tool:
                    record = query_PluginMng(plugin_id=plugin_id)
                    self.plugin_tool_record_selected_list.append(record)
                    if record.run_mode=="show_when_activate":
                        self.load_plugin_to_tab(record)

    def opendialogplugin(self):
        pluginselectedList = self.pluginselectedList
        selected_items = []
        unselected_items = []

        agents = query_PluginMng_All(is_delete=0,plugin_type="LLM_Connector")
        model = QStandardItemModel()
        header = ["", "plugin_id", "名称", "简称", "型号", "版本", "功能描述", "操作"]
        model.setHorizontalHeaderLabels(header)

        def create_item(text, editable=False):
            item = QStandardItem(text)
            if not editable:
                item.setFlags(item.flags() & ~Qt.ItemIsEditable)
            return item

        agent_dict = {f"{agent.name}: {agent.version}": agent for agent in agents}

        # Process selected items first according to the order in pluginselectedList
        for selected in pluginselectedList:
            if selected in agent_dict:
                agent = agent_dict.pop(selected)
                row_data = [
                    create_item(agent.plugin_id),
                    create_item(agent.name),
                    create_item(agent.alias_name),
                    create_item(json.dumps(agent.detail)),  # Convert JSON to string
                    create_item(agent.version),
                    create_item(agent.description),
                    create_item("操作")
                ]
                checkbox_item = QStandardItem()
                checkbox_item.setCheckable(True)
                checkbox_item.setCheckState(Qt.Checked)
                row_data.insert(0, checkbox_item)

                selected_items.append((agent, row_data))

        # Process the rest of the items
        for agent in agent_dict.values():
            row_data = [
                create_item(agent.plugin_id),
                create_item(agent.name),
                create_item(agent.alias_name),
                create_item(json.dumps(agent.detail)),  # Convert JSON to string
                create_item(agent.version),
                create_item(agent.description),
                create_item("操作")
            ]
            checkbox_item = QStandardItem()
            checkbox_item.setCheckable(True)
            row_data.insert(0, checkbox_item)
            unselected_items.append((agent, row_data))

        # Combine selected and unselected items
        all_items = selected_items + unselected_items

        # Add items to the model
        for row, (agent, item_row) in enumerate(all_items):
            for col, item in enumerate(item_row):
                model.setItem(row, col, item)

            # Create a combo box for '型号'
            combo_item = QStandardItem("gpt-3.5-turbo")
            model.setItem(row, 4, combo_item)

            # Placeholder for button, actual button will be inserted by delegate
            model.setItem(row, 7, QStandardItem())

        # Generate items_per_row based on the order of all_items
        items_per_row = {}
        for i, (agent, _) in enumerate(all_items):
            detail_json = json.loads(agent.detail)
            items_per_row[i] = detail_json.get("model_type", [])

        dialog = PluginFreezeTableDialog(model, items_per_row)

        combo_delegate = ComboBoxDelegate(items_per_row, dialog.tableView)
        dialog.tableView.setItemDelegateForColumn(4, combo_delegate)
        button_delegate = ButtonDelegate(dialog.tableView, dialog)
        dialog.tableView.setItemDelegateForColumn(7, button_delegate)

        if dialog.exec_() == QDialog.Accepted:
            self.pluginselectedList = dialog.getResult()
            print("self.pluginselectedList:", self.pluginselectedList)
            print("self.pluginselectedListjoin:", ",".join(self.pluginselectedList))
            update_AgentCfg(self.agent_cfg.id, plugins=",".join(self.pluginselectedList))
            self.agent.reset_cfg_plugin_llm()
            tech_list = self.application.techlist_list[self.agent_cfg.user_id]
            tech_list.reload()
            self.set_messagebox_placeholder()


    def opendialogkm(self):
        kmselectedList = self.kmselectedList
        print(kmselectedList)
        selected_items = []
        unselected_items = []

        agents = query_KMCfg_All(is_delete=0,vectorization=1)
        model = QStandardItemModel()
        header = ["", "km_id", "名称", "简介", "标签", "路径"]
        model.setHorizontalHeaderLabels(header)

        def create_item(text, editable=False):
            item = QStandardItem(text)
            if not editable:
                item.setFlags(item.flags() & ~Qt.ItemIsEditable)
            return item

        agent_dict = {agent.name: agent for agent in agents}

        # Process selected items first according to the order in kmselectedList
        for selected in kmselectedList:
            if selected in agent_dict:
                agent = agent_dict.pop(selected)
                row_data = [
                    create_item(agent.km_id),
                    create_item(agent.name),
                    create_item(agent.memo),
                    create_item(agent.label),
                    create_item(agent.kmpath)
                ]
                checkbox_item = QStandardItem()
                checkbox_item.setCheckable(True)
                checkbox_item.setCheckState(Qt.Checked)
                row_data.insert(0, checkbox_item)
                selected_items.append(row_data)

        # Process the rest of the items
        for agent in agent_dict.values():
            row_data = [
                create_item(agent.km_id),
                create_item(agent.name),
                create_item(agent.memo),
                create_item(agent.label),
                create_item(agent.kmpath)
            ]
            checkbox_item = QStandardItem()
            checkbox_item.setCheckable(True)
            row_data.insert(0, checkbox_item)
            unselected_items.append(row_data)

        # Add selected items to model first
        row = 0
        for item_row in selected_items + unselected_items:
            for col, item in enumerate(item_row):
                model.setItem(row, col, item)
            row += 1

        dialog = KmFreezeTableDialog(model)
        if dialog.exec_() == QDialog.Accepted:
            self.kmselectedList = dialog.getResult()
            print("self.kmselectedList", self.kmselectedList)
            print("self.kmselectedList:", ",".join(self.kmselectedList))
            update_AgentCfg(self.agent_cfg.id, kms=",".join(self.kmselectedList))
            self.agent.reload_agent_cfg()
            tech_list = self.application.techlist_list[self.agent_cfg.user_id]
            tech_list.reload()

    def openLink(self, url):
        webbrowser.open(url.toString())


    def generate_imagebak(self,prompt, model="dall-e-3", n=1, size="1024x1024"):
        url = "https://api.openai.com/v1/images/generations"
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer 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"  # 确保你已设置环境变量 OPENAI_API_KEY
        }
        data = {
            "model": model,
            "prompt": prompt,
            "n": n,
            "size": size
        }

        response = requests.post(url, headers=headers, json=data)

        if response.status_code == 200:
            response_json = response.json()
            # 提取 URL 列表
            urls = [item['url'] for item in response_json.get('data', [])]
            return urls  # 返回生成的图像 URL 列表
        else:
            response.raise_for_status()  # 抛出错误以便调试



    def generate_image(self, prompt, model="dall-e-3", n=1, size="1024x1024"):
        #***dall-e-3的n必须是1
        openai.api_key = "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"
        response = openai.images.generate(
            model=model,
            prompt=prompt,
            n=n,
            size=size,
            response_format="url",
        )

        # 提取 URL 列表
        # urls = [data['url'] for data in response['data']]
        urls = [datum.url for datum in response.data]
        return urls  # 返回生成的图像 URL 列表


    def set_messagebox_placeholder(self):
        if len(self.pluginselectedList) > 0:
            pluginname = self.pluginselectedList[0]
            llm = global_plugin_list[pluginname]
            config = llm.get_config()
            modelname = config.get("model", "")
            modelname = pluginname + f"({modelname})"
            # self.messageEdit.setPlaceholderText("Powered by " + modelname)
            # self.model_label.setText("Powered by " + modelname)
            self.model_label.setText(modelname)

    def save_task_output(self,output):
        print("cjrok the task output:",output)
        question=self.task_command
        answer=output
        attachment_content_list = json.dumps(self.attachment_content_list, ensure_ascii=False)  # km部分已经在agent中进行了处理，添加进去了

        record_id=add_AgentTask(self.task_id, question, question, answer, self.modelname, self.agent_cfg.user_id, self.is_first, attachment_content_list)
        self.onTaskFinished(question, answer, record_id)

        browser_page = self.messageBrowser.page()
        browser_page.runJavaScript('toggleOperatorDisplay()')

    def load_plugin_to_tab(self,plugin_cfg, *args, **kwagrs):
        if not plugin_cfg.name in self.plugin_tool_loaded_list:
            plugin = load_plugin(self, plugin_cfg, *args, **kwagrs)
            self.plugin_tool_loaded_list[plugin_cfg.name]=plugin
        else:
            plugin = self.plugin_tool_loaded_list[plugin_cfg.name]

        if not self.output_checkbox.isChecked():
            self.output_checkbox.setChecked(True)
            self.toggle_output_checkbox(self.output_checkbox.checkState())

        return plugin

    def on_message_from_message_handler(self,word):
        """
            处理传入的单词并更新显示内容。

            :param word: 字符串，表示需要处理的单词。
            """

        plugin_tool_record_selected_list = self.plugin_tool_record_selected_list
        for record in plugin_tool_record_selected_list:
            if "replying_a" in record.plugin_event:
                index_event = record.plugin_event.split(",").index("replying_a")
                instruction_list = []
                instruction = record.instruction
                instructed_flag = False
                run_plugin_flag = False
                if instruction:
                    instruction_list = instruction.split(",")

                for inst in instruction_list:
                    if inst in question:
                        instructed_flag = True

                if instructed_flag:
                    run_plugin_flag = True

                run_plugin_flag = True

                if run_plugin_flag:
                    plugin = self.plugin_tool_loaded_list[record.name]
                    result = plugin.handle_replying_a(self, word)
                    how_to_handle_executed_result = record.plugin_executed.split(",")[index_event]
                    if how_to_handle_executed_result == "get_output_as_final_result":
                        answer = result
                        return answer
                    else:
                        # question = result
                        # self.messageEdit.setPlainText(result)
                        pass

        words =self.words
        k = self.words_count

        # 检查单词是否为结束标志
        if word != "__end_speak__":
            # 将单词添加到已有的单词集合中
            words += word

            # 增加计数器
            k += 1

            # 每当计数器为1或是6的倍数时，渲染下一个单词
            if k == 1 or k % 6 == 0:
                self.handle_next_word(words)

        else:
            # 如果单词为结束标志，则渲染剩余的单词
            self.handle_next_word(words)
            self.words=""
            self.words_count=0

    def handle_next_word(self,words):
        print("handlingword:",words)

