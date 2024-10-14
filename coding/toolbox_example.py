# filename: toolbox_example.py

import sys
from PyQt5.QtWidgets import QApplication, QToolBox, QWidget, QVBoxLayout, QLabel, QScrollArea

class ToolboxExample(QWidget):
    def __init__(self):
        super().__init__()
        self.initUI()

    def initUI(self):
        layout = QVBoxLayout()
        toolbox = QToolBox()

        for i in range(10):
            label = QLabel(f'Content for Item {i + 1}')
            toolbox.addItem(label, f'Item {i + 1}')

        # Add toolbox to a scroll area
        scroll = QScrollArea()
        scroll.setWidget(toolbox)
        scroll.setWidgetResizable(True)
        scroll.setFixedHeight(200)
        
        layout.addWidget(scroll)
        self.setLayout(layout)
        
        self.setWindowTitle('QToolBox Example')
        self.show()

def main():
    app = QApplication(sys.argv)
    ex = ToolboxExample()
    sys.exit(app.exec_())

if __name__ == '__main__':
    main()