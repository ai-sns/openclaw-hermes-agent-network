import json
import sys
import os
import datetime
import time
import threading

from PyQt5 import QtWidgets
from PyQt5.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QTableWidget,
    QTableWidgetItem, QPushButton, QFileDialog, QMessageBox, QHeaderView, QDialog, QFormLayout, QComboBox, QHBoxLayout
)
from PyQt5.QtCore import Qt, QUrl, pyqtSignal, pyqtSlot, pyqtProperty
from PyQt5.QtWebChannel import QWebChannel
from PyQt5.QtWebEngineWidgets import QWebEnginePage, QWebEngineFullScreenRequest, QWebEngineView, QWebEngineProfile, QWebEngineSettings

from pathlib import Path
from db.DBFactory import query_workflow_mng,add_workflow_mng,update_workflow_mng,query_AgentCfg_All,add_task_schedule_mng,query_task_schedule,update_task_schedule,delete_task_schedule
from globals import global_agent_list
from TaskPage import TaskPage
from util import generate_random_id

class MessageHandler(QWidget):
    on_message_load_workflow = pyqtSignal(str,str,str,str,str,str,str,str,str)
    on_message_save = pyqtSignal(str,str,str,str,str,str,str,str,str)
    on_message_run = pyqtSignal(str,str)
    on_message_set_timer =pyqtSignal()

    def __init__(self):
        super().__init__()
        self.theinnervalue = "cjrok"

    def PyQt52WebValue(self):
        return self.theinnervalue

    @pyqtSlot(str, result=str)
    def Web2PyQt5Value(self, tmpstr):
        self.theinnervalue = self.theinnervalue + tmpstr
        QMessageBox.information(self, "从网页来的信息", tmpstr)

    @pyqtSlot(str,str,str,str,str,str,str, str,str, result=str)
    def save_message(self,workflow_id,workflow_title,workflow_description,workflow_tags,data,timer_desc,timer_cron,run_agent_name,run_agent_id):
        print(data)
        self.on_message_save.emit(workflow_id,workflow_title,workflow_description,workflow_tags,data,timer_desc,timer_cron,run_agent_name,run_agent_id)

    @pyqtSlot(str, str, result=str)
    def run_workflow(self, workflow_id, workflow_title):

        self.on_message_run.emit(workflow_id, workflow_title)

    @pyqtSlot()
    def set_timer(self):
        self.on_message_set_timer.emit()

    @pyqtSlot(str, str, result=str)
    def edit_content_message(self,code_type,text):
        print("codetype:",code_type)
        print("text:",text)
        self.on_edit_content_message.emit(code_type,text)

    @pyqtSlot(str, result=str)
    def file_clicked_message(self,file_path):
        print("file_path:",file_path)
        self.on_message_file_clicked.emit(file_path)

    @pyqtSlot(str, result=str)
    def open_link_message(self, url):
        print("url:", url)
        self.on_message_open_link.emit(url)



    def pass_message(self, messsage,workflow_title,workflow_description,workflow_id,workflow_tags,timer_desc,timer_cron,run_agent_name,run_agent_id):
        print("passmessage")
        self.on_message_load_workflow.emit(messsage,workflow_title,workflow_description,workflow_id,workflow_tags,timer_desc,timer_cron,run_agent_name,run_agent_id)
        print("timer_desc",timer_desc)

    thevalue = pyqtProperty(str, fget=PyQt52WebValue, fset=Web2PyQt5Value)


class WorkFlowDesign(QWidget):
    def __init__(self,workflow_manager,workflow_id,workflow_title):
        super().__init__()
        print(workflow_manager,":",workflow_id,":",workflow_title)

        self.workflow_id = ""
        self.workflow_name = ""
        self.taskpage = None
        self.app = None
        # 设置窗口标题和大小
        self.setWindowTitle("工作流设计器")
        self.setGeometry(100, 100, 800, 400)

        self.vboxlayout = QtWidgets.QVBoxLayout()
        self.vboxlayout.setObjectName("vboxlayout")
        self.vboxlayout.setContentsMargins(0, 0, 0, 0)  # 不留间隙


        self.frame = QtWidgets.QFrame()
        self.frame.setStyleSheet("QFrame { border: 1px solid #c0c0c0;}")
        self.frame_layout = QtWidgets.QVBoxLayout(self.frame)


        file_path = os.path.join(Path(__file__).resolve().parent, "scripts", "workflow_design.html")
        # file_path = os.path.join(Path(__file__).resolve().parent, "coding", "mycode.html")



        self.workflow_manager=workflow_manager

        # self.messageBrowser = QtWidgets.QTextBrowser(TaskWidget)
        self.messageBrowser = QWebEngineView()
        self.messageBrowser.setObjectName("messageBrowser")
        print(file_path)
        url_string = QUrl.fromLocalFile(file_path)
        self.messageBrowser.page().load(url_string)
        self.messageBrowser.page().loadFinished.connect(self.onLoadFinished)  # 第一次可能page没来得及load，所以需要在onload中处理

        global channel
        global message_handler
        channel = QWebChannel()
        message_handler = MessageHandler()
        self.message_handler = message_handler
        self.channel = channel
        channel.registerObject("message_handler", message_handler)

        # self.messageBrowser.page().setWebChannel(channel)
        self.messageBrowser.page().setWebChannel(channel)

        message_handler.on_message_save.connect(self.save_workflow)
        message_handler.on_message_run.connect(self.run_workflow)
        message_handler.on_message_set_timer.connect(self.set_timer)





        # 创建布局和控件
        self.layout = QVBoxLayout()
        self.vboxlayout.addWidget(self.frame)

        self.return_button = QPushButton("返回")

        # 连接按钮的点击事件
        self.return_button.clicked.connect(self.go_back)

        # 将控件添加到布局中
        self.frame_layout.addWidget(self.messageBrowser)
        # self.layout.addLayout(self.frame_layout)
        self.frame_layout.addWidget(self.return_button)


        # 设置主窗口的布局
        self.setLayout(self.vboxlayout)
        self.workflow_id=workflow_id
        self.workflow_title=workflow_title
        self.workflow_description = ""
        self.workflow_tags = ""
        self.timer_desc = ""
        self.timer_cron = ""


    def onLoadFinished(self):
        self.is_browser_page_loaded = True
        # time.sleep(0.5)
        # self.load_workflow()

        # 设置定时器，5秒后调用 my_function
        timer = threading.Timer(1, self.load_workflow)

        # 启动定时器
        timer.start()

    def save_workflow(self,workflow_id,workflow_title,workflow_description,workflow_tags,data,timer_desc,timer_cron,run_agent_name,run_agent_id):

        record=query_workflow_mng(workflow_id=workflow_id)
        if record:
            update_workflow_mng(record.id,title=workflow_title,description=workflow_description,workflow_tags=workflow_tags,detail=data, timer_desc=timer_desc, timer_cron=timer_cron,run_agent_name=run_agent_name,run_agent_id=run_agent_id)
        else:
            add_workflow_mng(workflow_id=workflow_id,title=workflow_title,description=workflow_description,workflow_tags=workflow_tags,detail=data, timer_desc=timer_desc, timer_cron=timer_cron,run_agent_name=run_agent_name,run_agent_id=run_agent_id)

        schedule_record = query_task_schedule(org_id=workflow_id)


        if timer_desc:
            if schedule_record:
                update_task_schedule(schedule_record.id,title=workflow_title, description=workflow_description, timer_desc=timer_desc, timer_cron=timer_cron, run_agent_name=run_agent_name, run_agent_id=run_agent_id)
            else:
                task_type = "workflow"
                task_id = generate_random_id()
                org_id =workflow_id
                parameter = ""
                schedule_time=None
                add_task_schedule_mng(workflow_title, workflow_description, task_type,
                                      task_id, org_id, parameter, schedule_time, timer_desc, timer_cron, run_agent_name, run_agent_id)
        else:
            if schedule_record:
               delete_task_schedule(org_id=workflow_id)

        QMessageBox.information(self, "提示", "保存成功。")

    def load_workflow(self):
        print("loading workflow")
        message=""
        workflow_id = self.workflow_id

        record = query_workflow_mng(workflow_id=workflow_id)
        if record:
            message = record.detail
            self.workflow_title = record.title
            self.workflow_description = record.description
            self.workflow_id = record.workflow_id
            self.workflow_tags = record.workflow_tags
            self.timer_desc =  record.timer_desc
            self.timer_cron = record.timer_cron
            self.run_agent_name = record.run_agent_name
            self.run_agent_id = record.run_agent_id

        print("message",message)
        self.message_handler.pass_message(message,self.workflow_title,self.workflow_description,self.workflow_id,self.workflow_tags,self.timer_desc,self.timer_cron,self.run_agent_name,self.run_agent_id)

    def set_timer(self):
        # 获取未删除的记录
        records = query_AgentCfg_All(is_delete=0)

        # 使用字典推导式将记录转换为所需的格式
        result_dict = {record.name: record.user_id for record in records}

        # 将字典转换为JSON字符串
        result_string = json.dumps(result_dict, ensure_ascii=False)  # ensure_ascii=False可用于保留非ASCII字符

        # 输出结果字符串
        print(result_string)


        self.messageBrowser.page().runJavaScript(f'toggleCronDerper(`{result_string}`)')

    def run_workflow(self,workflow_id,workflow_name):
        self.workflow_id =workflow_id
        self.workflow_name = workflow_name


        # 创建对话框
        transfer_dialog = QDialog()
        transfer_dialog.setWindowTitle("选择Agent")
        transfer_dialog.setMinimumWidth(500)

        # 创建主垂直布局
        main_layout = QVBoxLayout()

        # 创建表单布局
        form_layout = QFormLayout()

        # 创建第一个组合框并填充数据
        transfer_dialog.comboBox = QComboBox()
        transfer_dialog.comboBox.setEditable(False)
        records = query_AgentCfg_All(is_delete=0)

        for record in records:
            transfer_dialog.comboBox.addItem(record.name, record.user_id)

        form_layout.addRow("选择测试运行的Agent：", transfer_dialog.comboBox)

        # 将表单布局添加到主布局
        main_layout.addLayout(form_layout)

        # 创建按钮布局
        button_layout = QHBoxLayout()
        button_layout.addStretch(1)

        # 创建确定和取消按钮
        ok_button = QPushButton("确定")
        cancel_button = QPushButton("取消")

        # 连接按钮事件
        ok_button.clicked.connect(transfer_dialog.accept)
        cancel_button.clicked.connect(transfer_dialog.reject)

        button_layout.addWidget(ok_button)
        button_layout.addWidget(cancel_button)

        # 将按钮布局添加到主布局
        main_layout.addLayout(button_layout)

        # 设置主布局
        transfer_dialog.setLayout(main_layout)

        self.app = self.parent().parent().parent()
        # 显示对话框并处理结果
        if transfer_dialog.exec_():
            agent_id = transfer_dialog.comboBox.currentData()
            agent_name = transfer_dialog.comboBox.currentText()
            self.app.ShowAiAssistantStack()

            agent_item = self.app.toolBox_AgentChat.findChild(QWidget, agent_id)

            if agent_item:
                current_index = self.app.toolBox_AgentChat.indexOf(agent_item)  # 获取当前索引
                self.app.toolBox_AgentChat.setCurrentIndex(current_index)

            agents = global_agent_list.values()  # 前面已经从数据库中初始化了agent列表，直接使用前面已经初始化的列表获取其agent_cfg即可
            for agent in agents:
                if agent.name == agent_name:
                    self.app.open_exist_agent_task_chat(agent)

                    agent_chat_window = self.app.agent_chat_window_list[agent_id]
                    taskpage = agent_chat_window.findChild(TaskPage, "TaskPageObject")
                    self.taskpage = taskpage

                    browser_page = taskpage.messageBrowser.page()
                    browser_page.loadFinished.connect(self.onBrowserLoadFinished)  # 第一次可能page没来得及load，所以需要在onload中处理

                    self.is_browser_page_loaded = False
                    if taskpage.is_browser_page_loaded == True:  # page是否已经load了
                        self.is_browser_page_loaded = True

                    if self.is_browser_page_loaded == True:
                        self.onBrowserLoadFinished(True)

    def onBrowserLoadFinished(self, success):
        if success:
            taskpage = self.taskpage
            taskpage.messageEdit.setFocus()

            taskpage.messageEdit.setPlainText(f"请运行一下工作流:{self.workflow_name},//workflow_id:{self.workflow_id}")
            taskpage.sendMessage()


    def go_back(self):

        self.parent().setCurrentWidget(self.workflow_manager)

    def delete_file(self):
        """删除所选文件"""
        selected_items = self.file_table.selectedItems()
        if not selected_items:
            QMessageBox.warning(self, "警告", "请先选择一个文件进行删除。")
            return

        for item in selected_items:
            row = self.file_table.row(item)
            self.file_table.removeRow(row)

    def open_file(self, item=None):
        """打开所选文件"""
        if item is None:
            selected_items = self.file_table.selectedItems()
            if not selected_items:
                QMessageBox.warning(self, "警告", "请先选择一个文件进行打开。")
                return
            item = selected_items[0]

        row = self.file_table.row(item)
        file_path = self.file_table.item(row, 0).text()  # 获取文件路径
        os.startfile(file_path)  # 在 Windows 上打开文件

    def get_file_info(self, file_path):
        """获取文件的详细信息"""
        try:
            file_name =os.path.basename(file_path)
            file_size = os.path.getsize(file_path)  # 获取文件大小
            file_name = os.path.splitext(file_name)[0]  # 获取文件类型
            modified_time = os.path.getmtime(file_path)  # 获取最后编辑时间
            modified_time_str = datetime.datetime.fromtimestamp(modified_time).strftime('%Y-%m-%d %H:%M:%S')
        except Exception as e:
            # 如果发生异常，提供默认值
            print(f"无法获取文件信息: {file_path}, 错误: {e}")
            file_size = "N/A"
            file_type = "N/A"
            modified_time_str = "N/A"

        # 返回文件信息的列表
        return [file_name,f"{file_size}", modified_time_str,file_path]


if __name__ == "__main__":
    app = QApplication(sys.argv)
    file_manager = WorkFlowDesign()
    file_manager.show()
    sys.exit(app.exec_())
