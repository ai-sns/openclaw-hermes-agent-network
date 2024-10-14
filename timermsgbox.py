import sys
from PyQt5.QtWidgets import QApplication, QMessageBox
from PyQt5.QtCore import QTimer

class AutoCloseMessageBox(QMessageBox):
    def __init__(self, timeout=3, parent=None):
        super(AutoCloseMessageBox, self).__init__(parent)
        self.setWindowTitle("自动关闭对话框")
        self.setText("这个对话框会在3秒后自动关闭，并且不显示任何按钮。")
        self.setStandardButtons(QMessageBox.NoButton)  # 不显示任何标准按钮
        self.timeout = timeout
        self.setAutoClose(True)

    def setAutoClose(self, autoClose):
        if autoClose:
            self.timer = QTimer(self)
            self.timer.setInterval(self.timeout * 1000)  # 将秒转换为毫秒
            self.timer.setSingleShot(True)  # 设置为单次触发
            self.timer.timeout.connect(self.accept)  # 超时则接受对话框，导致对话框关闭
            self.timer.start()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    messageBox = AutoCloseMessageBox()
    messageBox.exec_()
    sys.exit(app.exec_())
