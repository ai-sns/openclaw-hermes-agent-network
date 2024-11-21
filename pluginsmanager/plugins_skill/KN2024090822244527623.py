# plugins/code_editor.py
import datetime
import sys


from pluginsmanager.plugins_gui.plugin_interface import PluginInterface
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QTextEdit, QPushButton, QHBoxLayout, QGroupBox, QLineEdit, QRadioButton, QLabel
from PyQt5 import QtWidgets
from pluginsmanager.plugins_gui.plugins import syntax_pars
from PyQt5 import QtWidgets
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QPushButton, QPlainTextEdit
import os
import webbrowser
from db.DBFactory import query_function_mng,add_function_mng,update_function_mng
from pytalk.util import generate_random_id


class CodeEditor(QWidget,PluginInterface):
    def __init__(self,function_manager):
        super().__init__()
        self.function_manager=function_manager
        self.function_id = ""
        self.changesSaved=True
        # 初始化用户界面
        # self.init_ui(content)

    def re_init(self):
        self.filename = ""
        self.changesSaved = True
        self.is_first = False
        self.editor.setPlainText("")
        self.function_name_input.setText("")
        self.publish_radio.setChecked(False)
        self.description_text_edit.setPlainText("")

    def create_widget(self, *args, **kwagrs):
        content=kwagrs.get("content","")
        # 创建主布局
        # 创建主布局
        layout = QVBoxLayout()

        # 创建文本编辑器控件
        self.editor = QPlainTextEdit()
        self.editor.setObjectName("code_editor")
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
        function_layout = QHBoxLayout()

        # 创建标签（函数名）
        function_label = QLabel("标题:")
        function_layout.addWidget(function_label)

        # 创建单行输入框（函数名）
        self.function_name_input = QLineEdit()
        self.function_name_input.setPlaceholderText("请输入名称")

        function_layout.addWidget(self.function_name_input)

        # 创建状态标签（状态）
        status_label = QLabel("状态:")
        function_layout.addWidget(status_label)

        # 创建单选按钮（发布）
        self.publish_radio = QRadioButton("发布")
        function_layout.addWidget(self.publish_radio)
        # 将函数布局添加到 GroupBox 布局中
        group_layout.addLayout(function_layout)

        # 创建多行文本框（描述）
        self.description_text_edit = QTextEdit()
        self.description_text_edit.setPlaceholderText("请输入关于该函数的描述")
        self.description_text_edit.setFixedHeight(60)  # 设置多行文本框的高度
        group_layout.addWidget(self.description_text_edit)

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
        preview_button = QPushButton("预览")
        preview_button.clicked.connect(self.preview_file)  # 连接预览事件
        button_layout.addWidget(preview_button)

        # 将按钮布局添加到主布局
        layout.addLayout(button_layout)

        # 设置窗口布局
        self.setLayout(layout)
        # 设置窗口标题
        self.setWindowTitle("Code Editor")
        # 设置窗口大小
        self.resize(600, 400)

    def go_back(self):

        self.parent().setCurrentWidget(self.function_manager)

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
        function_id=""
        if not self.filename:
            function_id = generate_random_id()
            self.function_id = function_id
            self.filename = os.path.join(os.getcwd(),"pluginsmanager","plugins_function",function_id+".py")
            description=self.description_text_edit.toPlainText()
            name = self.function_name_input.text()
            file_path = function_id
            requirement = ""
            parameter = ""
            if self.publish_radio.isChecked():
                function_type = "1"
            else:
                function_type="0"
            function_event = ""
            creator = ""
            record_id=add_function_mng(function_id, name, file_path,requirement,parameter, description, function_type, function_event,
                     creator)
            self.is_first = True
        else:
            function_id = self.function_id
            description = self.description_text_edit.toPlainText()
            name = self.function_name_input.text()
            requirement = ""
            parameter = ""
            if self.publish_radio.isChecked():
                function_type = "1"
            else:
                function_type = "0"
            create_time = datetime.datetime.now()
            update_function_mng(function_id,name=name,description=description,function_type=function_type,create_time=create_time)

        if self.filename:

            with open(self.filename, 'w', encoding='utf-8') as file:
                file.write(self.editor.toPlainText())  # 将文本写入文件

            self.changesSaved = True

        if self.is_first == True:

            self.is_first = False


    def preview_file(self):
        """保存文件并在浏览器中打开"""
        self.save_file()  # 先保存文件
        # 获取文件路径
        file_path = os.path.join("coding", "mycode.html")
        webbrowser.open(f"file://{os.path.abspath(file_path)}")  # 使用默认浏览器打开文件

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

        function_id =self.function_id
        if function_id=="":
            return
        else:
            record =query_function_mng(function_id=function_id)
            if record:
                filename=record.file_path
                filename =os.path.join(os.getcwd(),"pluginsmanager","plugins_function",filename+".py")
                self.filename=filename
                self.function_id = record.function_id


                self.function_name_input.setText(record.name)

                if record.function_type=="1":
                    self.publish_radio.setChecked(True)
                else:
                    self.publish_radio.setChecked(False)


                self.description_text_edit.setPlainText(record.description)



            if self.filename:
                with open(self.filename,"rt") as file:
                    self.editor.setPlainText(file.read())

        self.changesSaved = True


# 主入口
if __name__ == "__main__":
    app = QtWidgets.QApplication([])
    # 创建代码编辑器窗口并设置初始内容
    editor_widget = CodeEditor(content="def cjrok():")
    editor_widget.create_widget("def cjrok():")
    editor_widget.show()  # 显示窗口
    app.exec_()  # 运行应用程序的事件循环
