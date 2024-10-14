# filename: qtoolbox_example.py
import sys
from PyQt5.QtWidgets import QApplication, QToolBox, QWidget, QLabel, QVBoxLayout

class ToolBoxExample(QToolBox):
    def __init__(self):
        super().__init__()

        self.initUI()

    def initUI(self):
        page1 = QWidget()
        layout1 = QVBoxLayout()
        layout1.addWidget(QLabel("Page 1 content"))
        page1.setLayout(layout1)

        page2 = QWidget()
        layout2 = QVBoxLayout()
        layout2.addWidget(QLabel("Page 2 content"))
        page2.setLayout(layout2)

        self.addItem(page1, "Page 1")
        self.addItem(page2, "Page 2")

        self.setWindowTitle("QToolBox Example")
        self.show()

if __name__ == '__main__':
    app = QApplication(sys.argv)
    ex = ToolBoxExample()
    sys.exit(app.exec_())