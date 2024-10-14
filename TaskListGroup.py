from PyQt5 import QtCore
from PyQt5.QtWidgets import QTreeWidget, QTreeWidgetItem, QMenu, QAction, QHeaderView, QInputDialog, QMessageBox
from PyQt5.QtGui import QIcon
from PyQt5.QtCore import Qt, QPoint


from PyQt5.QtCore import QSettings, QThread, pyqtSignal
import time
from db.DBFactory import query_AgentTaskMulti, query_AgentTaskMulti_Content,AgentTaskMulti,update_AgentTaskMulti,deleteMultiTasksFromDatabase
from TaskPageGroup import TaskPageGroup
from util import generate_random_id,add_msg_to_message_window,get_user_ask_msg_title_formatted,get_user_ask_msg_content_formatted,get_agent_reply_msg_title_formatted,get_agent_reply_msg_content_formatted,add_agent_reply_msg_to_message_window,add_msg_to_message_window_with_markdown_and_highlight
class TaskListGroup(QTreeWidget):
    """TaskListGroup implements the view in a Tree of the Roster"""
    rename_signal = pyqtSignal(object)
    def __init__(self, parent, agentcfg):

        super(TaskListGroup, self).__init__(parent)
        print("TaskListGroup parent",parent)
        self.connection = None
        self.mainwindow=parent
        self.agentcfg = agentcfg
        self.current_task_id = ""
        self.tasks_history = None
        self.browser_page = None
        self.is_browser_page_loaded=False

        self.setHeaderLabel("对话列表")#需要设置此处的值，否则缺省值为1
        # self.setSortingEnabled(True)#排序
        # self.sortItems(0, Qt.AscendingOrder)#排序
        self.buddies = {}
        self.groups = {}
        self.tree = {}

        self.setContextMenuPolicy(Qt.CustomContextMenu)
        self.menu = QMenu()
        self.rename_action = QAction(QIcon("images/rename.png"), "重命名", self)
        self.rename_action.triggered.connect(self.rename)
        self.menu.addAction(self.rename_action)

        self.delete_action = QAction(QIcon("images/delete.png"), "删除", self)
        self.delete_action.triggered.connect(self.delete_item)
        self.menu.addAction(self.delete_action)

        self.customContextMenuRequested.connect(self.context)
        self.itemDoubleClicked.connect(self.on_itemDoubleClicked)

        self.offline = True
        self.away = False
        print("agentcfg:",agentcfg)
        class_type =type(agentcfg).__name__
        print("class_type",class_type)
        self.tasklist = query_AgentTaskMulti(is_first = True,group_id=agentcfg.group_id)
        for record in self.tasklist:
            self.addItem(record.topic, record.id)
            # print(f"ID: {record.id}, filename: {record.filename}, filenum: {record.filenum}")


    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Delete:
            item = self.currentItem()
            if item:
                reply = QMessageBox.question(self, '删除确定',
                                             f"您确定要删除 '{item.text(0)}'?",
                                             QMessageBox.Yes | QMessageBox.No, QMessageBox.Yes)
                if reply == QMessageBox.Yes:
                    column = 0
                    id_value = item.data(column, Qt.UserRole)
                    # 从数据库中删除所有task_id相同的记录
                    deleteMultiTasksFromDatabase(id_value)

                    index = self.indexOfTopLevelItem(item)
                    if index != -1:
                        self.takeTopLevelItem(index)
                    else:
                        parent = item.parent()
                        parent.removeChild(item)
        else:
            super(TaskListGroup, self).keyPressEvent(event)


    def scrollContentsBy(self, dx, dy):
        # 调用父类方法处理滚动
        super().scrollContentsBy(dx, dy)

        # 判断是否滚动到底部
        if self.verticalScrollBar().value() == self.verticalScrollBar().maximum():
            print("Reached bottom!")


    def addItem(self, name, id,is_top=False):
        item_count = self.topLevelItemCount()

        if item_count==0:
            group_item = QTreeWidgetItem(self)
            group_item.setText(0, "所有")
        else:
            group_item = self.topLevelItem(0)
        # print("adding item:",name)

        # top_item = QTreeWidgetItem(group_item)
        top_item = QTreeWidgetItem()
        top_item.setText(0, name[0:50])
        top_item.setToolTip(0, name)
        top_item.setData(0, Qt.UserRole, id)  # Qt.UserRole, id)
        if is_top == False:
            # print("not top")
            group_item.addChild(top_item)
        else:
            print("im toppppppppp....")
            group_item.insertChild(0, top_item)
        top_item.setTextAlignment(0, 0)

        self.expandAll()

    def context(self, pos):
        item = self.itemAt(pos)
        self.current_Item = item
        self.menu.popup(self.mapToGlobal(pos))

    def rename(self):
        self.rename_signal.emit(self.currentItem)
        item = self.current_Item

        column = 0
        id_value = item.data(column, Qt.UserRole)

        if id_value:

            oldName = item.text(0)
            newName, ok = QInputDialog.getText(self, "重命名", "新名称:", text=oldName)
            if ok and newName:
                item.setText(0, newName)
                column = 0
                id_value = item.data(column, Qt.UserRole)
                update_AgentTaskMulti(id_value, topic=newName)
        else:
            QMessageBox.critical(None, "警告", "分类名不能重命名", QMessageBox.Ok)


    def delete_item(self):


        item = self.current_Item
        column = 0
        id_value = item.data(column, Qt.UserRole)
        print("id_value",id_value)

        if id_value:

            if item:
                reply = QMessageBox.question(self, '删除确定',
                                         f"您确定要删除 '{item.text(0)}'?",
                                         QMessageBox.Yes | QMessageBox.No, QMessageBox.Yes)
            if reply == QMessageBox.Yes:

                # 从数据库中删除所有task_id相同的记录
                deleteMultiTasksFromDatabase(id_value)

                index = self.indexOfTopLevelItem(item)
                if index != -1:
                    self.takeTopLevelItem(index)
                else:
                    parent = item.parent()
                    parent.removeChild(item)
        else:

            QMessageBox.critical(None, "警告", "分类不能删除", QMessageBox.Ok)


    def getInfo(self):
        pass

    def onLoadFinished(self, success):
        if success:
            browser_page = self.browser_page
            records = self.tasks_history
            for record in records:
                self.format_text(browser_page, record.content, record.owner, record.create_time)
            self.is_browser_page_loaded = True


    def on_itemDoubleClicked(self, item, column):
        print("双击了：", item.text(column))
        print(column)
        id_value = item.data(column, Qt.UserRole)
        print("双击了：", id_value)
        if id_value==None:
            return(False)

        records = query_AgentTaskMulti_Content(id=id_value)

        agentcfg = self.agentcfg
        task_id = ""
        if records:
            task_id = records[0].task_id
        self.mainwindow.open_multi_agent_task_chat(agentcfg)
        agent_chat_window = self.mainwindow.multi_agent_chat_window_list[agentcfg.group_id]
        taskpage = agent_chat_window.findChild(TaskPageGroup, "TaskPageGroupObject")
        taskpage.task_id = task_id
        taskpage.is_first = False
        browser_page = taskpage.messageBrowser.page()
        browser_page.loadFinished.connect(self.onLoadFinished)#第一次可能page没来得及load，所以需要在onload中处理
        self.browser_page = browser_page
        self.tasks_history = records

        if taskpage.is_browser_page_loaded==True:#page是否已经load了
                 self.is_browser_page_loaded = True

        if self.is_browser_page_loaded==True:
            self.onLoadFinished(True)


    def format_text(self, browser_page, content, owner, create_time):

        message = get_agent_reply_msg_title_formatted(owner,1, create_time, False)
        add_msg_to_message_window(browser_page, message, 1)
        # add_agent_reply_msg_to_message_window(browser_page, content)
        add_msg_to_message_window_with_markdown_and_highlight(browser_page, content, 2)


