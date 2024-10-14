# filename: pyqt5_text_editor.py
import sys
from PyQt5.QtWidgets import QApplication, QTextEdit, QMainWindow
from PyQt5.QtCore import Qt

class TextEditor(QMainWindow):
    def __init__(self):
        super().__init__()
        self.initUI()

    def initUI(self):
        self.text_edit = QTextEdit(self)
        self.setCentralWidget(self.text_edit)
        self.setWindowTitle('Multi-line Text Editor')
        self.resize(800, 600)

    def keyPressEvent(self, event):
        if event.key() == Qt.Key_F11:  # Use Qt.Key_F11 for better readability
            if self.isFullScreen():
                self.setWindowState(self.windowState() & ~Qt.WindowFullScreen)
            else:
                self.setWindowState(self.windowState() | Qt.WindowFullScreen)

if __name__ == '__main__':
    app = QApplication(sys.argv)
    editor = TextEditor()
    editor.show()
    sys.exit(app.exec_())