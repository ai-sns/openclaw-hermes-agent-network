from PyQt5 import QtWidgets
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QPushButton

import syntax_pars

app = QtWidgets.QApplication([])
# editor = QtWidgets.QPlainTextEdit()
# # editor = QtWidgets.QTextEdit()
# editor.setStyleSheet("""QPlainTextEdit{
# 	font-family:'Consolas';
# 	color: #ccc;
# 	background-color: #2b2b2b;}""")
# highlight = syntax_pars.PythonHighlighter(editor.document())
# editor.show()

# # Load syntax.py into the editor for demo purposes
# infile = open('syntax_pars.py', 'r')
# editor.setPlainText(infile.read())


class CodeEditor(QWidget):
    def create_widget(self, *args, **kwagrs):
        # 创建一个 QWidget 作为插件的界面
        widget = QWidget()
        layout = QVBoxLayout()

        # 创建 QPlainTextEdit 控件
        editor = QtWidgets.QPlainTextEdit()
        editor.setObjectName("code_editor")
        # editor = QtWidgets.QTextEdit()
        editor.setStyleSheet("""QPlainTextEdit{
        	font-family:'Consolas'; 
        	color: #ccc; 
        	background-color: #2b2b2b;}""")
        highlight = syntax_pars.PythonHighlighter(editor.document())
        editor.show()#不要执行此句否则控件会调用缺省窗口


        text=kwagrs.get("content","")
        editor.setPlainText(text)


        layout.addWidget(editor)

        # 创建按钮控件
        button = QPushButton("Add 'Hello World2'")

        # 使用闭包确保按钮点击事件绑定到当前插件实例
        button.clicked.connect(lambda: self.add_hello_world(editor))
        layout.addWidget(button)

        widget.setLayout(layout)
        return widget

    def add_hello_world(self, text_edit):
        # 向 QTextEdit 中添加 "Hello World"
        syntax_pars.PythonHighlighter(text_edit.document())
        text_edit.appendPlainText("Hello World2")


aa=CodeEditor()
bb=aa.create_widget(content="cjrok")
bb.show()
app.exec_()
