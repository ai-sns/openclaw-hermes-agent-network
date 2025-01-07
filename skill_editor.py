import datetime

from PyQt5.QtCore import QSize

from pluginsmanager.plugins_gui.plugin_interface import PluginInterface
from PyQt5.QtWidgets import QTextEdit, QHBoxLayout, QGroupBox, QLineEdit, QRadioButton, QLabel, QDialog, QFormLayout, QComboBox
from pytalk.pluginsmanager.plugins_gui.plugins.code_editor import syntax_pars
from PyQt5 import QtWidgets
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QPushButton, QPlainTextEdit
import os
import webbrowser
from db.DBFactory import query_skill_mng,add_skill_mng,update_skill_mng,query_AgentCfg_All
from pytalk.util import generate_random_id
from TaskPage import TaskPage
from pathlib import Path

from autogen.coding import CodeBlock, LocalCommandLineCodeExecutor
from globals import global_agent_list


class SkillEditor(QWidget,PluginInterface):
    def __init__(self,skill_manager):
        super().__init__()
        self.skill_manager=skill_manager
        self.skill_id = ""
        self.changesSaved=True
        self.is_browser_page_loaded = False
        self.taskpage = None
        self.name = ""
        # 初始化用户界面
        # self.init_ui(content)

    def re_init(self):
        self.filename = ""
        self.changesSaved = True
        self.is_first = False
        self.editor.setPlainText("")
        self.skill_name_input.setText("")
        self.skill_description_input.setText("")
        self.publish_radio.setChecked(False)
        self.detail_text_edit.setPlainText("")

    def create_widget(self, *args, **kwagrs):
        content=kwagrs.get("content","")
        # 创建主布局
        # 创建主布局
        layout = QVBoxLayout()

        # 创建文本编辑器控件
        self.editor = QPlainTextEdit()
        self.editor.setObjectName("skill_editor")
        # 设置文本编辑器样式
        self.editor.setStyleSheet("""QPlainTextEdit{
                    font-family: 'Consolas'; 
                    color: #ccc; 
                    background-color: #2b2b2b;
                }""")

        # 设置语法高亮
        self.highlighter = syntax_pars.PythonHighlighter(self.editor.document())

        # 设置初始内容
        self.editor.setPlainText(content)
        self.editor.textChanged.connect(self.changed)

        # 将编辑器添加到布局
        layout.addWidget(self.editor)

        # 创建 QGroupBox
        group_box = QGroupBox("配置信息")  # 设置 QGroupBox 的标题
        group_layout = QVBoxLayout()  # 创建 GroupBox 的布局

        # 创建水平布局，用于放置函数名输入框和发布单选按钮
        skill_layout = QHBoxLayout()

        # 创建标签（函数名）
        skill_label = QLabel("标题:")
        skill_layout.addWidget(skill_label)

        # 创建单行输入框（函数名）
        self.skill_name_input = QLineEdit()
        self.skill_name_input.setPlaceholderText("请输入名称")

        skill_layout.addWidget(self.skill_name_input)



        skill_description_label = QLabel("简介:")
        skill_layout.addWidget(skill_description_label)

        # 创建单行输入框（函数名）
        self.skill_description_input = QLineEdit()
        self.skill_description_input.setPlaceholderText("简明扼要")
        self.skill_description_input.setMaxLength(350)

        skill_layout.addWidget(self.skill_description_input)


        # # 创建状态标签（状态）
        # status_label = QLabel("状态:")
        # skill_layout.addWidget(status_label)

        # # 创建单选按钮（发布）
        # self.publish_radio = QRadioButton("发布")
        # skill_layout.addWidget(self.publish_radio)
        # # 将函数布局添加到 GroupBox 布局中
        group_layout.addLayout(skill_layout)
        #
        # if self.skill_manager.type_str=="2":
        #     status_label.setHidden(True)
        #     self.publish_radio.setHidden(True)
        detail_layout = QHBoxLayout()
        # 创建多行文本框（描述）
        skill_detail_label = QLabel("详细:")

        self.detail_text_edit = QTextEdit()
        self.detail_text_edit.setPlaceholderText("请输入关于该函数的描述")
        self.detail_text_edit.setFixedHeight(60)  # 设置多行文本框的高度
        detail_layout.addWidget(skill_detail_label)

        detail_layout.addWidget(self.detail_text_edit)

        group_layout.addLayout(detail_layout)
        # 将 GroupBox 的布局应用到 QGroupBox
        group_box.setLayout(group_layout)
        group_box.setFixedHeight(150)  # 限制 QGroupBox 的高度

        # 将 QGroupBox 添加到主布局
        layout.addWidget(group_box)





        # 创建按钮的水平布局
        button_layout = QHBoxLayout()

        # 创建添加按钮
        return_button = QPushButton("关闭")
        return_button.clicked.connect(self.go_back)  # 连接按钮点击事件到添加函数
        button_layout.addWidget(return_button)

        # 创建保存按钮
        save_button = QPushButton("保存")
        save_button.clicked.connect(self.save_file)  # 连接保存事件
        button_layout.addWidget(save_button)

        # 创建预览按钮
        preview_button = QPushButton("运行")
        preview_button.clicked.connect(self.preview_file)  # 连接预览事件
        button_layout.addWidget(preview_button)

        if self.skill_manager.type_str=="2":
            preview_button.setHidden(True)

        # 创建单选按钮（发布）
        # status_label = QLabel("状态:")
        # skill_layout.addWidget(status_label)

        self.publish_radio = QRadioButton("发布")

        # 将函数布局添加到 GroupBox 布局中
        # button_layout.addWidget(status_label)
        button_layout.addWidget(self.publish_radio)

        if self.skill_manager.type_str == "2":
            # status_label.setHidden(True)
            self.publish_radio.setHidden(True)



        # 将按钮布局添加到主布局
        layout.addLayout(button_layout)

        # 设置窗口布局
        self.setLayout(layout)
        # 设置窗口标题
        self.setWindowTitle("Skill Editor")
        # 设置窗口大小
        self.resize(600, 400)

    def go_back(self):

        self.parent().setCurrentWidget(self.skill_manager)

    def changed(self):
        self.changesSaved = False


    def add_hello_world(self, editor=None):
        """向文本编辑器中添加 'Hello World2'"""
        parent = self.parent().parent()
        if parent:
            # 获取并打印父控件的类型
            print(f"按钮的父控件类型是: {type(parent).__name__}")
            current_index = parent.currentIndex()  # 获取当前选中的 Tab 的索引
            if current_index != -1:  # 确保有 Tab 被选中
                parent.removeTab(current_index)  # 移除当前选中的 Tab
        else:
            print("按钮没有父控件。")

        if editor is None:
            # 如果没有传入 editor，则向主编辑器添加
            editor = self.editor
        editor.appendPlainText("Hello World2")




    def save_file(self):
        skill_id=""
        if not self.filename:
            skill_id = generate_random_id()
            name = self.skill_name_input.text()
            self.skill_id = skill_id
            filename = "steps.txt"
            filename = os.path.join(os.getcwd(), "skilllearning", "data", skill_id, filename)
            self.filename=filename

            description = self.skill_description_input.text()
            detail = self.detail_text_edit.toPlainText()
            file_path = name
            requirement = ""
            parameter = ""
            if self.publish_radio.isChecked():
                skill_type = "1"
            else:
                skill_type="0"

            if self.skill_manager.type_str == "2":
                skill_type = "2"
                self.filename = os.path.join(os.getcwd(), "agent", "tools.py")

            skill_event = ""
            creator = ""
            record_id=add_skill_mng(skill_id, name, file_path,requirement,parameter, description,detail, skill_type, skill_event,
                     creator)
            self.is_first = True
        else:
            skill_id = self.skill_id
            name = self.skill_name_input.text()
            description = self.skill_description_input.text()
            detail = self.detail_text_edit.toPlainText()
            requirement = ""
            parameter = ""
            if self.publish_radio.isChecked():
                skill_type = "1"
            else:
                skill_type = "0"

            if self.skill_manager.type_str == "2":
                skill_type = "2"
                self.filename = os.path.join(os.getcwd(), "agent", "tools.py")

            create_time = datetime.datetime.now()
            update_skill_mng(skill_id,name=name,description=description,detail=detail,skill_type=skill_type,create_time=create_time)

        if self.filename:

            with open(self.filename, 'w', encoding='utf-8') as file:
                file.write(self.editor.toPlainText())  # 将文本写入文件

            self.changesSaved = True

        if self.is_first == True:

            self.is_first = False



    def preview_file(self):
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

            # 显示对话框并处理结果
            if transfer_dialog.exec_():
                agent_id = transfer_dialog.comboBox.currentData()
                agent_name = transfer_dialog.comboBox.currentText()
                self.skill_manager.app.ShowAiAssistantStack()

                agent_item = self.skill_manager.app.toolBox_AgentChat.findChild(QWidget, agent_id)

                if agent_item:
                    current_index = self.skill_manager.app.toolBox_AgentChat.indexOf(agent_item)  # 获取当前索引
                    self.skill_manager.app.toolBox_AgentChat.setCurrentIndex(current_index)

                agents = global_agent_list.values()  # 前面已经从数据库中初始化了agent列表，直接使用前面已经初始化的列表获取其agent_cfg即可
                for agent in agents:
                    if agent.name == agent_name:
                        self.skill_manager.app.open_exist_agent_task_chat(agent)

                        agent_chat_window = self.skill_manager.app.agent_chat_window_list[agent_id]
                        taskpage = agent_chat_window.findChild(TaskPage, "TaskPageObject")
                        self.taskpage = taskpage

                        browser_page = taskpage.messageBrowser.page()
                        browser_page.loadFinished.connect(self.onBrowserLoadFinished)  # 第一次可能page没来得及load，所以需要在onload中处理

                        self.is_browser_page_loaded = False
                        if taskpage.is_browser_page_loaded == True:  # page是否已经load了
                            self.is_browser_page_loaded = True

                        if self.is_browser_page_loaded == True:
                            self.onBrowserLoadFinished(True)





                # self.skill_manager.app.conversation_pages.setCurrentIndex(1)  # 首页


    def onBrowserLoadFinished(self, success):
        if success:
            taskpage = self.taskpage
            taskpage.messageEdit.setFocus()

            taskpage.messageEdit.setPlainText(f"给我演示一下:{self.skill_name_input.text()},skill_id:{self.skill_id}")
            taskpage.sendMessage()


    def loadFile(self):

        if not self.changesSaved:

            popup = QtWidgets.QMessageBox()
            popup.setWindowTitle("AI-SNS")

            popup.setIcon(QtWidgets.QMessageBox.Warning)

            popup.setText("The document has been modified")

            popup.setInformativeText("Do you want to save your changes?")

            popup.setStandardButtons(QtWidgets.QMessageBox.Save   |
                                      QtWidgets.QMessageBox.Cancel |
                                      QtWidgets.QMessageBox.Discard)

            popup.setDefaultButton(QtWidgets.QMessageBox.Save)

            answer = popup.exec_()

            if answer == QtWidgets.QMessageBox.Save:
                self.save_file()

        self.re_init()

        skill_id =self.skill_id
        if skill_id=="" and self.skill_manager.type_str != "2":
            return

        elif skill_id=="" and self.skill_manager.type_str == "2":
                filename = os.path.join(os.getcwd(), "agent", "tools.py")

        else:
            record =query_skill_mng(skill_id=skill_id)
            if record:
                filename="steps.txt"
                filename = os.path.join(os.getcwd(), "skilllearning", "data",skill_id, filename)
                if record.skill_type=="2":
                    filename = os.path.join(os.getcwd(), "agent", "tools.py")

                self.filename=filename
                self.skill_id = record.skill_id
                self.name = record.name


                self.skill_name_input.setText(record.name)
                self.skill_description_input.setText(record.description)

                if record.skill_type=="1":
                    self.publish_radio.setChecked(True)
                else:
                    self.publish_radio.setChecked(False)


                self.detail_text_edit.setPlainText(record.detail)

        if filename:
            with open(filename,"rt", encoding='utf-8') as file:
                self.editor.setPlainText(file.read())

        self.changesSaved = True


# 主入口
if __name__ == "__main__":
    app = QtWidgets.QApplication([])
    # 创建代码编辑器窗口并设置初始内容
    editor_widget = SkillEditor(content="def cjrok():")
    editor_widget.create_widget("def cjrok():")
    editor_widget.show()  # 显示窗口
    app.exec_()  # 运行应用程序的事件循环
