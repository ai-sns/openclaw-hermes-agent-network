# plugins/code_editor.py
import sys


from pluginsmanager.plugins_gui.plugin_interface import PluginInterface
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QTextEdit, QPushButton, QHBoxLayout, QInputDialog
from PyQt5 import QtWidgets
from pluginsmanager.plugins_gui.plugins.mindmap import syntax_pars
from PyQt5 import QtWidgets
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QPushButton, QPlainTextEdit
import os
import webbrowser

class Main(QWidget, PluginInterface):
    def __init__(self, parent, plugin_cfg, content=""):
        super().__init__()

        self.parent = parent
        self.plugin_cfg = plugin_cfg


    def create_widget(self, *args, **kwagrs):
        content=kwagrs.get("content","")
        # 创建主布局
        # 创建主布局
        layout = QVBoxLayout()

        # 创建文本编辑器控件
        self.editor = QPlainTextEdit()
        self.editor.setObjectName("mindmap_editor")
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
        self.file_name = ""

    def run(self, *args, **kwagrs):
            file_name = args[0]
            text = args[1]
            editor = self.editor
            editor.setPlainText(text)
            self.file_name = file_name
            tabs = self.parent.tabWidget

            for index in range(tabs.count()):
                if tabs.tabText(index) == self.plugin_cfg.plugin_title:
                    tabs.setCurrentIndex(index)  # 根据索引激活标签页
                    break  # 找到后退出循环


    def close_tab(self):
        """向文本编辑器中添加 'Hello World2'"""
        # tab = self.parent().parent()
        tab = self.parent.tabWidget
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
                self.parent.plugin_tool_loaded_list.pop(self.plugin_cfg.name, None)
        else:
            print("没有父控件。")



    def save_filebak(self):
        """将编辑器中的文本保存到 coding/mindmap.md"""
        # 创建目录
        directory = "coding"
        if not os.path.exists(directory):
            os.makedirs(directory)  # 如果目录不存在创建它

        # 保存文件路径
        file_path = os.path.join(directory, "mindmap.md")
        with open(file_path, 'w', encoding='utf-8') as file:
            file.write(self.editor.toPlainText())  # 将文本写入文件

        print(f"File saved: {file_path}")  # 控制台打印信息

    def save_file(self):
        """将编辑器中的文本保存到 coding/mycode.html"""
        # 创建目录
        # taskpage = self.parent().parent().parent().parent()  # 获取父级任务页
        taskpage = self.parent
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

        ext = os.path.splitext(file_path)[1]
        # 如果没有指定扩展名
        if not ext:
            file_path = file_path + ".mindmap"


        with open(file_path, 'w', encoding='utf-8') as file:
            file.write(self.editor.toPlainText())  # 将文本写入文件

        print(f"File saved: {file_path}")  # 控制台打印信息

    def preview_file(self):
        """保存文件并在浏览器中打开"""
        # 创建目录
        directory = "coding"
        if not os.path.exists(directory):
            os.makedirs(directory)  # 如果目录不存在创建它

        # 保存文件路径
        file_path = os.path.join(directory, "mindmap.html")
        html_txt_head="""
        <!DOCTYPE html><html lang="en"><head><meta charset="UTF-8"/><meta http-equiv="X-UA-Compatible"content="IE=edge"/><meta name="viewport"content="width=device-width, initial-scale=1.0"/><title>Markmap</title><style>svg.markmap{width:100%;height:100vh}</style><script src="https://cdn.jsdelivr.net/npm/markmap-autoloader@0.16"></script></head><body><div class="markmap"><script type="text/template">
        """
        html_txt_tail="""
        </script></div></body></html>
        """
        html_file_content=html_txt_head+self.editor.toPlainText()+html_txt_tail

        with open(file_path, 'w', encoding='utf-8') as file:
            file.write(html_file_content)  # 将文本写入文件


        webbrowser.open(f"file://{os.path.abspath(file_path)}")  # 使用默认浏览器打开文件
