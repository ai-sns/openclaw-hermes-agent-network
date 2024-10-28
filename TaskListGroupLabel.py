from PyQt5 import QtCore
from PyQt5.QtWidgets import QTreeWidget, QTreeWidgetItem, QMenu, QAction, QHeaderView, QInputDialog, QMessageBox
from PyQt5.QtGui import QIcon, QPixmap
from PyQt5.QtCore import Qt, QPoint

from PyQt5.QtCore import QSettings, QThread, pyqtSignal
import time
from db.DBFactory import query_AgentTaskMulti, query_AgentTaskMulti_Content, AgentTaskMulti, update_AgentTaskMulti, \
    deleteMultiTasksFromDatabase, query_AgentTask_Search_Content, query_AgentTaskMulti_Search_First, \
    query_AgentTaskMulti_Search_Content, update_AgentTaskMulti_stick, query_AgentTask_ById, query_AgentTaskMulti_ById
from TaskListGroup import TaskListGroup

# from TaskListGroup import TaskList

# import TaskListGroup
from util import generate_random_id, add_msg_to_message_window, get_user_ask_msg_title_formatted, \
    get_user_ask_msg_content_formatted, get_agent_reply_msg_title_formatted, get_agent_reply_msg_content_formatted, \
    add_agent_reply_msg_to_message_window, add_msg_to_message_window_with_markdown_and_highlight


class TaskListGroupLabel(TaskListGroup):
    """TaskListGroup implements the view in a Tree of the Roster"""

    def __init__(self, parent, agentcfg):
        super(TaskListGroupLabel, self).__init__(parent, agentcfg)
        print("TaskListGroup parent", parent)

    # --> 加载 数据
    def load_data(self):
        # 用于存储已经创建的分类项
        labels = {}
        self.tasklist = query_AgentTaskMulti(label=True,is_first=True, group_id=self.agentcfg.group_id)
        # 遍历联系人，按label分类
        for record in self.tasklist:
            label = record.label
            if label is None or len(label) == 0:
                label = "无标签"
            # name = record.name

            # 如果分类项不存在，则创建一个新的分类项
            if label not in labels:
                labels[label] = QTreeWidgetItem(self, [label])

            # 创建联系人项，并添加到对应的分类下
            # contact_item = QTreeWidgetItem(labels[label], [name])
            stick_icon = False
            if record.stick_time is not None:
                stick_icon = True
            self.addItem(record.topic.replace("\n", ""), labels[label], record.id, icon=stick_icon)

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
            filtered_tasklist = [
                record for record in self.tasklist
                if key_word[3:] in record.topic
            ]
        else:
            self.tasklist = query_AgentTaskMulti_Search_Content(label = True,is_first=True,
                                                                group_id=self.agentcfg.group_id, topic=key_word
                                                                )
            filtered_tasklist = self.tasklist

        # 创建一个集合来存储已经处理过的 first_record 记录
        processed_first_records = set()
        labels = {}
        print("label:", len(filtered_tasklist))
        for record in filtered_tasklist:

            if record.is_first and record.id not in processed_first_records:
                # 处理 first_record
                # --> 添加一条 数据
                label = record.label
                if label is None or len(label) == 0:
                    label = "无标签"
                if label not in labels:
                    labels[label] = QTreeWidgetItem(self, [label])
                stick_icon = False
                if record.stick_time is not None:
                    stick_icon = True
                self.addItem(record.topic.replace("\n", ""), labels[label], record.id, icon=stick_icon)

                # lambda: self.addItemLabel(record,labels)
                # self.addItem(record.title.replace("\n", ""), record.id)
                processed_first_records.add(record.id)
            elif not record.is_first:
                # 查找是否有相同 task_id 且 is_first 为 True 的记录
                first_record = query_AgentTaskMulti_Search_First(agent_id=self.agentcfg.group_id,
                                                                 task_id=record.task_id,label=True)
                if first_record and first_record.id not in processed_first_records:
                    # 处理 first_record
                    # --> 添加一条 数据
                    label = first_record.label
                    if label is None or len(label) == 0:
                        label = "无标签"
                    if label not in labels:
                        labels[label] = QTreeWidgetItem(self, [label])
                    stick_icon = False
                    if first_record.stick_time is not None:
                        stick_icon = True
                    self.addItem(first_record.topic.replace("\n", ""), labels[label], first_record.id, icon=stick_icon)

                    # lambda: self.addItemLabel(record, labels)
                    processed_first_records.add(first_record.id)
        # -->内部函数
        # def addItemLabel():
        #     label = record.label
        #     if label is None or len(label) == 0:
        #         label = "无标签"
        #     if label not in labels:
        #         labels[label] = QTreeWidgetItem(self, [label])
        #     stick_icon = False
        #     if record.stick_time is not None:
        #         stick_icon = True
        #     self.addItem(record.title.replace("\n", ""), labels[label], record.id, icon=stick_icon)

    def addItemLabel(self, record, labels):
        label = record.label
        if label is None or len(label) == 0:
            label = "无标签"
        if label not in labels:
            labels[label] = QTreeWidgetItem(self, [label])
        stick_icon = False
        if record.stick_time is not None:
            stick_icon = True
        self.addItem(record.topic.replace("\n", ""), labels[label], record.id, icon=stick_icon)
