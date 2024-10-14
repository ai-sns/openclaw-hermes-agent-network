from PyQt5 import QtWidgets
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QPlainTextEdit
import syntax_pars
import os
import webbrowser

class CodeEditor(QWidget):
    def __init__(self, content=""):
        super().__init__()
        # 初始化用户界面
        self.init_ui(content)

    def init_ui(self, content):
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
        hello_button = QPushButton("Add 'Hello World2'")
        hello_button.clicked.connect(self.add_hello_world)  # 连接按钮点击事件到添加函数
        button_layout.addWidget(hello_button)

        # 创建保存按钮
        save_button = QPushButton("Save")
        save_button.clicked.connect(self.save_file)  # 连接保存事件
        button_layout.addWidget(save_button)

        # 创建预览按钮
        preview_button = QPushButton("Preview")
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

    def add_hello_world(self):
        """向文本编辑器中添加 'Hello World2'"""
        self.editor.appendPlainText("Hello World2")

    def save_file(self):
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

    def preview_file(self):
        """保存文件并在浏览器中打开"""
        self.save_file()  # 先保存文件
        # 获取文件路径
        file_path = os.path.join("coding", "mycode.html")
        webbrowser.open(f"file://{os.path.abspath(file_path)}")  # 使用默认浏览器打开文件

# 主入口
if __name__ == "__main__":
    app = QtWidgets.QApplication([])
    # 创建代码编辑器窗口并设置初始内容
    editor_widget = CodeEditor(content="def cjrok():")
    editor_widget.show()  # 显示窗口
    app.exec_()  # 运行应用程序的事件循环
