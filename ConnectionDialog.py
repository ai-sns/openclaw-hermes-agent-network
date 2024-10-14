from PyQt5.QtWidgets import QDialog
from PyQt5.QtCore import QSettings, QVariant, pyqtSignal, pyqtSlot
from ui.ui_ConnectionDialog import Ui_ConnectionDialog

"""
流程说明：Application.py 的init中，创建并调用该对话框
        # Connection
        connection = ConnectionDialog(self)
        self.actionConnection.triggered.connect(connection.exec_)#actionConnection是ui_mainwindow的菜单项，该项触发ConnectionDialog对象的运行
        self.actionDeconnection.triggered.connect(self.disconnect)
        connection.configured.connect(self.on_configured)

"""

class ConnectionDialog(QDialog, Ui_ConnectionDialog):
    configured = pyqtSignal()
    connectcancel = pyqtSignal()

    def __init__(self, parent=None):
        super(ConnectionDialog, self).__init__(parent)
        self.setupUi(self)
        self.accepted.connect(self.saveSettings)  # 点击确认了之后，将调用saveSettings函数
        self.rejected.connect(self.dialogrejected)

        self.readSettings()

    def readSettings(self):
        settings = QSettings("Trunat", "PyTalk")
        settings.beginGroup("Connection")
        self.userID.setText(settings.value("userID", type=str))
        self.password.setText(settings.value("password", type=str))
        self.server.setText(settings.value("server", type=str))
        self.useSSL.setChecked(settings.value("useSSL", True, type=bool))

        if self.useSSL.isChecked():
            self.port.setText(str(settings.value("port", 5223, type=int)))
        else:
            self.port.setText(str(settings.value("port", 5222, type=int)))

        self.ressource.setText(settings.value("ressource", "PyTalk", type=str))
        settings.endGroup()

    def saveSettings(self):
        settings = QSettings("Trunat", "PyTalk")
        settings.beginGroup("Connection")
        settings.setValue("userID", self.userID.text())
        settings.setValue("password", self.password.text())
        settings.setValue("server", self.server.text())
        settings.setValue("port", int(self.port.text()))
        settings.setValue("ressource", self.ressource.text())
        settings.setValue("useSSL", self.useSSL.isChecked())
        settings.endGroup()
        print("saveing")
        self.configured.emit()  # 保存结束，发送configured信号，该信号已经在上面定义了configured = pyqtSignal()
        print("emit")
        #self.on_configured

    def dialogrejected(self):
        print("reject")
        self.connectcancel.emit()




