import os

from PyQt5.QtCore import QFileInfo, QUrl, pyqtSignal, pyqtProperty
from PyQt5.QtWidgets import QApplication, QMainWindow, QWidget, QMessageBox
from PyQt5.QtWebEngineWidgets import QWebEngineView
from PyQt5.QtWebChannel import QWebChannel
import sys
from pathlib import Path

class Myshared(QWidget):
    on_message = pyqtSignal(str)
    def __init__(self):
        super().__init__()
        self.theinnervalue = "cjrok"

    def PyQt52WebValue(self):
        return self.theinnervalue

    def Web2PyQt5Value(self, tmpstr):
        self.theinnervalue = self.theinnervalue + tmpstr
        QMessageBox.information(self, "从网页来的信息", tmpstr)

    thevalue = pyqtProperty(str, fget=PyQt52WebValue, fset=Web2PyQt5Value)


def setup_web_channel(window):
    channel = QWebChannel()
    shared = Myshared()
    channel.registerObject("con", shared)
    window.page().setWebChannel(channel)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    main_window = QMainWindow()
    web_view = QWebEngineView(main_window)
    main_window.setCentralWidget(web_view)

    # Load your web content here
    # 加载外部网页
    url = QUrl(QFileInfo("./index3.html").absoluteFilePath())

    file_path = os.path.join(Path(__file__).resolve().parent, "index3.html")
    print(file_path)
    url_string = QUrl.fromLocalFile(file_path)
    web_view.setUrl(url_string)

    # Set up the web channel
    setup_web_channel(web_view)

    main_window.show()
    sys.exit(app.exec_())
