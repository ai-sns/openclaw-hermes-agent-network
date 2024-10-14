# plugins/code_editor.py
import sys

from PyQt5.QtCore import QSize
from pluginsmanager.plugins_gui.plugin_interface import PluginInterface
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QTextEdit, QPushButton, QHBoxLayout, QDialog, QInputDialog, QLineEdit, QMessageBox
from PyQt5 import QtWidgets
from pluginsmanager.plugins_gui.plugins import syntax_pars
from PyQt5 import QtWidgets
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QPushButton, QPlainTextEdit
import os
import webbrowser
import autogen
from autogen import AssistantAgent, UserProxyAgent

from pathlib import Path

from autogen.coding import CodeBlock, LocalCommandLineCodeExecutor

from pytalk.db.DBFactory import add_function_mng
from pytalk.util import generate_random_id


class CodeEditor(QWidget,PluginInterface):
    def __init__(self, content=""):
        super().__init__()
        # 初始化用户界面
        # self.init_ui(content)

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

        # 将编辑器添加到布局
        layout.addWidget(self.editor)

        # 创建按钮的水平布局
        button_layout = QHBoxLayout()

        # 创建添加按钮
        hello_button = QPushButton("关闭")
        hello_button.clicked.connect(self.close_tab)  # 连接按钮点击事件到添加函数
        button_layout.addWidget(hello_button)

        # 创建保存按钮
        save_button = QPushButton("保存")
        save_button.clicked.connect(self.save_file)  # 连接保存事件
        button_layout.addWidget(save_button)

        # 存为函数插件
        save_as_function_button = QPushButton("存为函数插件")
        save_as_function_button.clicked.connect(self.save_as_function_plugin)  # 连接保存事件
        button_layout.addWidget(save_as_function_button)

        # 创建预览按钮
        preview_button = QPushButton("运行")
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
        self.file_name=""

    def close_tab(self):
        """向文本编辑器中添加 'Hello World2'"""
        tab = self.parent().parent()
        if tab:
            # 获取并打印父控件的类型
            print(f"父控件类型是: {type(tab).__name__}")
            current_index = tab.currentIndex()  # 获取当前选中的 Tab 的索引
            if current_index != -1:  # 确保有 Tab 被选中
                # 获取当前 Tab 对应的 Widget
                tab_widget = tab.widget(current_index)
                # 使用 deleteLater() 方法安全地删除该 Widget
                tab_widget.deleteLater()
                tab.removeTab(current_index)  # 移除当前选中的 Tab
        else:
            print("没有父控件。")


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

        content = self.editor.toPlainText()
        trimmed_content = content.strip()
        code = trimmed_content
        last_str = code[-7:]
        if last_str.lower() == "</html>":
            type_str = ".html"
        else:
            type_str = ".py"


        # 创建目录
        taskpage = self.parent().parent().parent().parent()  # 获取父级任务页
        task_id = taskpage.task_id  # 获取任务ID
        directory_path = os.path.join('resource', 'attachment', 'chat', task_id)  # 构造目录路径
        os.makedirs(directory_path, exist_ok=True)
        directory=directory_path
        if not self.file_name:
            file_name, ok = QInputDialog.getText(self, "请指定文件名称", "请指定文件名称:", text="")

            if ok and file_name:
                self.file_name=file_name
            else:
                return
        # 保存文件路径
        file_name = self.file_name


        file_path = os.path.join(directory, file_name)

        ext=os.path.splitext(file_path)[1]
        #如果没有指定扩展名
        if not ext:
            file_path=file_path+type_str


        with open(file_path, 'w', encoding='utf-8') as file:
            file.write(self.editor.toPlainText())  # 将文本写入文件

        print(f"File saved: {file_path}")  # 控制台打印信息


    def save_file_to_run(self):
        """将编辑器中的文本保存到 coding/mycode.html"""
        # 创建目录
        directory = "coding"
        if not os.path.exists(directory):
            os.makedirs(directory)  # 如果目录不存在创建它

        # 保存文件路径
        file_path = os.path.join(directory, "mycode.html")
        with open(file_path, 'w', encoding='utf-8') as file:
            file.write(self.editor.toPlainText())  # 将文本写入文件

        print(f"File saved: {file_path}")  # 控制台打印信息

    def save_as_function_plugin(self):
        # Create an input dialog
        content = self.editor.toPlainText()
        trimmed_content = content.strip()
        code = trimmed_content
        last_str = code[-7:]
        if last_str.lower() == "</html>":
            QMessageBox.information(self, "提示", "函数插件仅支持Python！")
            return

        ext = os.path.splitext(self.file_name)[1]
        if ext:
            if ext != ".py":
                QMessageBox.information(self, "提示", "函数插件仅支持Python！")
                return




        name, ok = QInputDialog.getText(self, "请指定函数名称", "请指定函数名称:", text="")

        if ok and name:
            function_id = generate_random_id()
            function_id = function_id
            filename = os.path.join(os.getcwd(),"pluginsmanager","plugins_function",function_id+".py")
            description=""
            file_path = function_id
            requirement = ""
            parameter = ""
            function_type="0"
            function_event = ""
            creator = ""
            record_id=add_function_mng(function_id, name, file_path,requirement,parameter, description, function_type, function_event,
                     creator)

            if filename:
                with open(filename, 'w', encoding='utf-8') as file:
                    file.write(self.editor.toPlainText())  # 将文本写入文件

            QMessageBox.information(self,"提示", "请到:插件工具-函数插件-未发布 进行编辑发布！")


    def preview_filebak(self):
        """保存文件并在浏览器中打开"""
        self.save_file_to_run()  # 先保存文件
        # 获取文件路径
        file_path = os.path.join("coding", "mycode.html")
        webbrowser.open(f"file://{os.path.abspath(file_path)}")  # 使用默认浏览器打开文件
    def preview_file(self):
        """保存文件并在浏览器中打开"""
        content = self.editor.toPlainText()
        trimmed_content = content.strip()
        code = trimmed_content
        last_str =code[-7:]
        if last_str.lower()=="</html>":
            type_str = "html"
        else:
            type_str = "python"



        if type_str=="html":
            self.save_file_to_run()  # 先保存文件
            # 获取文件路径
            file_path = os.path.join("coding", "mycode.html")
            webbrowser.open(f"file://{os.path.abspath(file_path)}")  # 使用默认浏览器打开文件
        else:
            work_dir = Path("coding")
            work_dir.mkdir(exist_ok=True)

            # executor = LocalCommandLineCodeExecutor(work_dir=work_dir, functions=[add_two_numbers, load_data])#使用codebakok这种徐娅有functions
            executor = LocalCommandLineCodeExecutor(work_dir=work_dir)  # 使用code这种直接指明functions文件的就不需要这里写functions这个参数了


            execute_result=executor.execute_code_blocks(
                code_blocks=[
                    CodeBlock(language="python", code=code),
                ]
            )
            print(execute_result)
            print("exit_code",execute_result.exit_code)
            print("output",execute_result.output)
            print("code_file",execute_result.code_file)

            self.console = QDialog()
            self.te = QTextEdit(self.console)
            self.te.append(f"exit_code:\n{execute_result.exit_code}\n")
            self.te.append(f"code_file:\n{execute_result.code_file}\n")
            self.te.append(f"output:\n{execute_result.output}")
            self.te.setReadOnly(True)
            vl = QVBoxLayout()
            vl.addWidget(self.te)
            self.console.setLayout(vl)

            self.console.setWindowTitle("Output Console")
            self.console.resize(QSize(1024, 500))
            self.console.exec_()
            # self.console.raise_()



# 主入口
if __name__ == "__main__":
    app = QtWidgets.QApplication([])
    # 创建代码编辑器窗口并设置初始内容
    editor_widget = CodeEditor(content="def cjrok():")
    editor_widget.create_widget("def cjrok():")
    editor_widget.show()  # 显示窗口
    app.exec_()  # 运行应用程序的事件循环
