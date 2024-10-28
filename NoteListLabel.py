import json
import os
from datetime import datetime
from PyQt5 import QtCore
from PyQt5.QtWidgets import QTreeWidget, QTreeWidgetItem, QMenu, QAction, QHeaderView, QMessageBox, QInputDialog, \
    QTreeWidgetItemIterator
from PyQt5.QtGui import QIcon, QPixmap
from PyQt5.QtCore import Qt, QPoint

from PyQt5.QtCore import QSettings, QThread, pyqtSignal

from NoteList import NoteList
from db.DBFactory import query_AgentTask, query_AgentTask_Search_Content, update_note_mng_by_recordid, \
    query_AgentTask_Search_First, AgentTask, delete_note_mng, update_AgentTask, update_note_mng_stick, update_note_mng, \
    query_note_mng_ById, query_Note_mng_Search_Content
from db.DBFactory import query_note_mng_all, delete_note_mng, query_note_mng
from TaskPage import TaskPage
from util import generate_random_id, add_msg_to_message_window, get_user_ask_msg_title_formatted, \
    get_user_ask_msg_content_formatted, get_agent_reply_msg_title_formatted, get_agent_reply_msg_content_formatted, \
    add_agent_reply_msg_to_message_window, add_msg_to_message_window_with_markdown_and_highlight, \
    get_content_from_attachment_content_list, add_attachment_to_message_window
from langchainhandler import savevector, delete_vector


class NoteListLabel(NoteList):
    """TaskList implements the view in a Tree of the Roster"""
    rename_signal = pyqtSignal(object)
    label_signal = pyqtSignal(object)

    def __init__(self, parent, km_cfg, type_str):

        super(NoteListLabel, self).__init__(parent, km_cfg, type_str)

    # --> 加载 数据
    def load_data(self):
        # 用于存储已经创建的分类项
        labels = {}
        if self.type_str == "recent":
            self.tasklist = query_note_mng_all(10, label=True,km_id=self.km_cfg.km_id)
        else:
            self.tasklist = query_note_mng_all(-1, label=True,km_id=self.km_cfg.km_id)
        for record in self.tasklist:
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

    def reload(self, key_word=""):
        self.clear()

        self.setHeaderLabel("笔记列表")  # 需要设置此处的值，否则缺省值为1
        self.buddies = {}
        self.groups = {}
        self.tree = {}

        self.load_pop_menu()
        self.itemDoubleClicked.connect(self.on_itemDoubleClicked)

        if key_word.startswith('+++'):
            # 获取上一次的搜索结果并过滤
            filtered_tasklist = [
                record for record in self.tasklist
                if key_word[3:] in record.title or key_word[3:] in record.content
            ]
        else:
            if self.type_str == "recent":
                self.tasklist = query_Note_mng_Search_Content(
                    10,  label = True,title=key_word, content=key_word, km_id=self.km_cfg.km_id
                )
            else:
                self.tasklist = query_Note_mng_Search_Content(
                    -1,  label = True,title=key_word, content=key_word, km_id=self.km_cfg.km_id
                )

            filtered_tasklist = self.tasklist

        labels = {}
        for record in filtered_tasklist:
            label = record.label
            if label is None or len(label) == 0:
                label = "无标签"
            if label not in labels:
                labels[label] = QTreeWidgetItem(self, [label])
            stick_icon = True if record.stick_time is not None else False
            self.addItem(record.title.replace("\n", ""), labels[label], record.id, icon=stick_icon)
            # self.addItem(record.title.replace("\n", ""), record.id,
            #              icon=True if record.stick_time is not None else False)

    def addItemLabel(self, record, labels):
        label = record.label
        if label is None or len(label) == 0:
            label = "无标签"
        if label not in labels:
            labels[label] = QTreeWidgetItem(self, [label])

        stick_icon = True if record.stick_time is not None else False
        self.addItem(record.title.replace("\n", ""), labels[label], record.id, icon=stick_icon)

