import sys
from PyQt5.QtWidgets import QApplication, QLineEdit, QWidget, QVBoxLayout, QLabel
from PyQt5.QtGui import QRegExpValidator
from PyQt5.QtCore import QRegExp

class LimitLineEdit(QWidget):
    def __init__(self):
        super().__init__()
        
        # 创建布局
        self.layout = QVBoxLayout()
        
        # 创建标签
        self.label = QLabel("请输入中文或英文（最多10个汉字或单词）:")
        self.layout.addWidget(self.label)
        
        # 创建QLineEdit
        self.line_edit = QLineEdit(self)
        
        # 设置输入限制
        self.set_input_limit()
        
        self.layout.addWidget(self.line_edit)
        self.setLayout(self.layout)
        
        # 窗口设置
        self.setWindowTitle("QLineEdit 输入限制示例")
        self.setGeometry(100, 100, 300, 100)

    def set_input_limit(self):
        # 正则表达式：限制最多10个汉字或10个单词
        regex = QRegExp(r'(([\u4e00-\u9fa5]{1,10})|(([\w-]+[\s]*){0,10}))')
        validator = QRegExpValidator(regex, self.line_edit)
        
        # 设置验证器到QLineEdit
        self.line_edit.setValidator(validator)

def main():
    app = QApplication(sys.argv)
    window = LimitLineEdit()
    window.show()
    sys.exit(app.exec_())

if __name__ == "__main__":
    main()