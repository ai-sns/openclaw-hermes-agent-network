import json
import os
from datetime import datetime
from PyQt5 import QtCore
from PyQt5.QtWidgets import QTreeWidget, QTreeWidgetItem, QMenu, QAction, QHeaderView, QMessageBox, QInputDialog, \
    QTreeWidgetItemIterator
from PyQt5.QtGui import QIcon, QPixmap
from PyQt5.QtCore import Qt, QPoint

from PyQt5.QtCore import QSettings, QThread, pyqtSignal
import time

from ChatList import ChatList
from db.DBFactory import query_AIChat_Content, query_AIChatMessages_All, query_AgentTask, \
    query_AgentTask_Search_Content, query_AgentTask_Content, query_AgentTask_Search_First, AgentTask, \
    deleteTasksFromDatabase, update_AgentTask, query_AIChatMessages_Search_Content, update_AIChatMessages_stick, \
    update_AIChatMessages, query_AIChatMessages_ById, query_AIChatMessages_Search_First

from util import generate_random_id, add_msg_to_message_window, get_user_ask_msg_title_formatted, \
    get_user_ask_msg_content_formatted, get_agent_reply_msg_title_formatted, get_agent_reply_msg_content_formatted, \
    add_agent_reply_msg_to_message_window, add_msg_to_message_window_with_markdown_and_highlight, \
    get_content_from_attachment_content_list, add_attachment_to_message_window


class ChatListLabel(ChatList):
    """ChatList implements the view in a Tree of the Roster"""

    def __init__(self, parent, agent):

        super(ChatListLabel, self).__init__(parent, agent)

        # self.chat_list = query_AIChatMessages_All(is_first=True, owner_account=self.agent.account,friend_account=self.jid)
        # for record in self.chat_list:
        #     self.addItem(record.title.replace("\n", ""), record.id)

    # --> 加载 数据
    def load_data(self):
        # 用于存储已经创建的分类项
        labels = {}
        self.chat_list = query_AIChatMessages_All(label=True,is_first=True, owner_account=self.agent.account,
                                                  friend_account=self.jid)
        for record in self.chat_list:
            label = record.label
            if label is None or len(label) == 0:
                label = "无标签"
            # 如果分类项不存在，则创建一个新的分类项
            if label not in labels:
                labels[label] = QTreeWidgetItem(self, [label])

            stick_icon = True if record.stick_time is not None else False

            self.addItem(record.title.replace("\n", ""), labels[label], record.id, icon=stick_icon)

    def addItem(self, name, group_item, id, is_top=False, icon=False):
        if is_top == False:
            # print("not top")
            top_item = QTreeWidgetItem(group_item)
            top_item.setText(0, name[0:50])
            if icon == True:
                top_item.setIcon(0, self.stick_icon)  # 设置第一列的图标
            top_item.setToolTip(0, name)
            top_item.setData(0, Qt.UserRole, id)  # Qt.UserRole, id)
            top_item.setTextAlignment(0, 0)
            self.expandAll()

    def reload(self, key_word):
        self.clear()

        self.setHeaderLabel("对话列表")  # 需要设置此处的值，否则缺省值为1
        self.buddies = {}
        self.groups = {}
        self.tree = {}

        self.load_pop_menu()
        self.itemDoubleClicked.connect(self.on_itemDoubleClicked)

        if key_word.startswith('+++'):
            # 获取上一次的搜索结果并过滤
            filtered_chat_list = [
                record for record in self.chat_list
                if key_word[3:] in record.title or key_word[3:] in record.content
            ]
        else:
            # AIChatMessages
            self.chat_list = query_AIChatMessages_Search_Content(
                label = True,is_first=True, owner_account=self.agent.account,
                friend_account=self.jid, title=key_word, content=key_word
            )
            filtered_chat_list = self.chat_list

        # 创建一个集合来存储已经处理过的 first_record 记录
        processed_first_records = set()
        labels = {}
        for record in filtered_chat_list:
            if record.is_first and record.id not in processed_first_records:
                # 处理 first_record
                label = record.label
                if label is None or len(label) == 0:
                    label = "无标签"
                if label not in labels:
                    labels[label] = QTreeWidgetItem(self, [label])
                stick_icon = True if record.stick_time is not None else False
                self.addItem(record.title.replace("\n", ""), labels[label], record.id, icon=stick_icon)
                processed_first_records.add(record.id)
            elif not record.is_first:
                # 查找是否有相同 conversation_id 且 is_first 为 True 的记录
                first_record = query_AIChatMessages_Search_First(agent_id=self.agent_cfg.user_id,
                                                                 conversation_id=record.conversation_id,label=True)
                if first_record and first_record.id not in processed_first_records:
                    # 处理 first_record
                    label = first_record.label
                    if label is None or len(label) == 0:
                        label = "无标签"
                    if label not in labels:
                        labels[label] = QTreeWidgetItem(self, [label])
                    stick_icon = True if record.stick_time is not None else False
                    self.addItem(first_record.title.replace("\n", ""), labels[label], first_record.id, icon=stick_icon)
                    processed_first_records.add(first_record.id)

    def addItemLabel(self, record, labels):
        label = record.label
        if label is None or len(label) == 0:
            label = "无标签"
        if label not in labels:
            labels[label] = QTreeWidgetItem(self, [label])

        stick_icon = True if record.stick_time is not None else False
        self.addItem(record.title.replace("\n", ""), labels[label], record.id, icon=stick_icon)

    # -->  增加标签后刷新,增加 reload调用
    def label_item(self):
        self.label_signal.emit(self.currentItem)
        item = self.current_Item
        oldName=None
        column = 0
        id_value = item.data(column, Qt.UserRole)

        if id_value:
            res = query_AIChatMessages_ById(id_value)
            if res is not None:
                oldName = res.label
            if oldName is None:
                oldName = ""
            newName, ok = QInputDialog.getText(self, "加标签", "新标签:", text=oldName)
            if ok and newName:
                update_AIChatMessages(id_value, label=newName)
                self.reload("")
        else:
            QMessageBox.critical(None, "警告", "分类名不能加标签", QMessageBox.Ok)