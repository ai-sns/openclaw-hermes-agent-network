# plugins/my_plugin.py
from plugin_interface import PluginInterface
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QTextEdit, QPushButton


class MyPlugin(PluginInterface):
    def create_widget(self):
        # 创建一个 QWidget 作为插件的界面
        widget = QWidget()
        layout = QVBoxLayout()

        # 创建 QTextEdit 控件
        text_edit = QTextEdit()
        layout.addWidget(text_edit)

        # 创建按钮控件
        button = QPushButton("Add 'Hello World2'")

        # 使用闭包确保按钮点击事件绑定到当前插件实例
        button.clicked.connect(lambda: self.add_hello_world(text_edit))
        layout.addWidget(button)

        widget.setLayout(layout)
        return widget

    def add_hello_world(self, text_edit):
        # 向 QTextEdit 中添加 "Hello World"
        text_edit.append("Hello World2")
