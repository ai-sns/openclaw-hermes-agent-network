import PyQt5
from PyQt5 import QtWidgets
from PyQt5.QtCore import QDate, QSize, Qt, QRect
from PyQt5.QtGui import QIcon, QPixmap, QPainter, QPen, QPainterPath, QIntValidator
from PyQt5.QtWidgets import (QApplication, QCheckBox, QComboBox, QDateTimeEdit,
                             QDialog, QGridLayout, QGroupBox, QHBoxLayout, QLabel, QLineEdit,
                             QListView, QListWidget, QListWidgetItem, QPushButton, QSpinBox,
                             QStackedWidget, QVBoxLayout, QWidget, QDialogButtonBox, QRadioButton, QFileDialog)
from db.DBFactory import add_SystemCfg,query_SystemCfg,query_SystemCfg_All,update_SystemCfg,delete_SystemCfg

import configdialog_rc
import datetime
import random
import string
# from datetime import datetime

class ConfigDialog(QDialog):
    def __init__(self, parent=None):
        super(ConfigDialog, self).__init__(parent)

        self.contentsWidget = QListWidget()
        self.contentsWidget.setViewMode(QListView.IconMode)
        self.contentsWidget.setIconSize(QSize(96, 84))
        self.contentsWidget.setMovement(QListView.Static)
        self.contentsWidget.setMaximumWidth(128)
        self.contentsWidget.setSpacing(12)

        self.agent = query_SystemCfg()

        self.generalPage=GeneralPage(self.agent)
        self.infoPage=InfoPage(self.agent)




        self.pagesWidget = QStackedWidget()
        self.pagesWidget.addWidget(self.generalPage)
        self.pagesWidget.addWidget(self.infoPage)





        closeButton = QPushButton("Close")

        self.createIcons()
        self.contentsWidget.setCurrentRow(0)

        closeButton.clicked.connect(self.close)

        horizontalLayout = QHBoxLayout()
        horizontalLayout.addWidget(self.contentsWidget)
        horizontalLayout.addWidget(self.pagesWidget, 1)

        buttonsLayout = QHBoxLayout()
        buttonsLayout.addStretch(1)
        buttonsLayout.addWidget(closeButton)

        mainLayout = QVBoxLayout()
        mainLayout.addLayout(horizontalLayout)
        mainLayout.addStretch(1)
        mainLayout.addSpacing(12)
        #mainLayout.addLayout(buttonsLayout)


        # Add OK and Cancel buttons
        button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        ok_button = button_box.button(QDialogButtonBox.Ok)
        ok_button.setText("确定")
        cancel_button = button_box.button(QDialogButtonBox.Cancel)
        cancel_button.setText("取消")
        button_box.accepted.connect(self.accept_close)
        button_box.rejected.connect(self.reject_close)

        mainLayout.addWidget(button_box)



        self.setLayout(mainLayout)

        self.setWindowTitle("系统设置")

    def accept_close(self):
        print("accept")

        # generalpage

        autorun=self.generalPage.autorunCheckBox.isChecked()
        showtaskbar=self.generalPage.showtaskbarCheckBox.isChecked()
        updateinfo=self.generalPage.updateinfoCheckBox.isChecked()
        closebuttontype=self.generalPage.closebuttontypeCombo.currentText()
        style=self.generalPage.styleCombo.currentText()
        showinfo=self.infoPage.showinfoCheckBox.isChecked()
        showinfoicon=self.infoPage.showinfoiconCheckBox.isChecked()
        infosound=self.infoPage.infosoundCheckBox.isChecked()

        if self.agent == None:
            add_SystemCfg(autorun,showtaskbar,updateinfo,closebuttontype,style,showinfo,showinfoicon,infosound)
        else:
            update_SystemCfg(self.agent.id, autorun=autorun, showtaskbar=showtaskbar, updateinfo=updateinfo, closebuttontype=closebuttontype, style=style, showinfo=showinfo, showinfoicon=showinfoicon, infosound=infosound)

        self.accept()
        self.close()

    def reject_close(self):
        print("reject")
        self.close()


    def changePage(self, current, previous):
        if not current:
            current = previous

        self.pagesWidget.setCurrentIndex(self.contentsWidget.row(current))

    def createIcons(self):
        configButton = QListWidgetItem(self.contentsWidget)
        configButton.setIcon(QIcon(':/images/config.png'))
        configButton.setText("常规配置")
        configButton.setTextAlignment(Qt.AlignHCenter)
        configButton.setFlags(Qt.ItemIsSelectable | Qt.ItemIsEnabled)

        techButton = QListWidgetItem(self.contentsWidget)
        techButton.setIcon(QIcon('images/technique.png'))
        techButton.setText("通知配置")
        techButton.setTextAlignment(Qt.AlignHCenter)
        techButton.setFlags(Qt.ItemIsSelectable | Qt.ItemIsEnabled)




        self.contentsWidget.adjustSize()
        self.contentsWidget.setFixedHeight(500)
        self.contentsWidget.currentItemChanged.connect(self.changePage)

    def generate_random_id(self):
        # 生成随机字母ID，使用大写字母
        random_id = ''.join(random.choices(string.ascii_uppercase, k=2))
        # 获取当前时间
        current_time = datetime.datetime.now().strftime('%Y%m%d%H%M%S')
        # 生成随机数
        random_number = ''.join(random.choices(string.digits, k=5))
        # 组合生成的ID
        generated_id = random_id + current_time + random_number
        return generated_id


class GeneralPage(QWidget):
    def __init__(self, agent, parent=None):
        super(GeneralPage, self).__init__(parent)
        self.agent = agent

        updateGroup = QGroupBox("选项:")
        self.autorunCheckBox = QCheckBox("开机自动运行")
        self.showtaskbarCheckBox = QCheckBox("在任务栏显示")
        self.updateinfoCheckBox = QCheckBox("有更新时提醒升级")







        packagesGroup = QGroupBox("风格")

        self.closebuttontypeLabel = QLabel("点击关闭按钮:")
        self.closebuttontypeCombo = QComboBox()
        self.closebuttontypeCombo.setFixedWidth(250)
        self.closebuttontypeCombo.addItem("隐藏窗口")
        self.closebuttontypeCombo.addItem("关闭程序")

        self.styleLabel = QLabel("风格:")
        self.styleCombo = QComboBox()
        self.styleCombo.setFixedWidth(250)
        self.styleCombo.addItem("亮色")
        self.styleCombo.addItem("暗色")

        if agent != None:
            self.autorunCheckBox.setChecked(agent.autorun)
            self.showtaskbarCheckBox.setChecked(agent.showtaskbar)
            self.updateinfoCheckBox.setChecked(agent.updateinfo)
            self.closebuttontypeCombo.setCurrentText(agent.closebuttontype)
            self.styleCombo.setCurrentText(agent.style)





        updateLayout = QGridLayout()
        updateLayout.addWidget(self.autorunCheckBox, 0, 0)
        updateLayout.addWidget(self.showtaskbarCheckBox, 0, 1)
        updateLayout.addWidget(self.updateinfoCheckBox, 1, 0)

        updateGroup.setLayout(updateLayout)


        styleLayout = QGridLayout()
        styleLayout.addWidget(self.closebuttontypeLabel, 0, 0)
        styleLayout.addWidget(self.closebuttontypeCombo, 0, 1)
        styleLayout.addWidget(self.styleLabel, 1, 0)
        styleLayout.addWidget(self.styleCombo, 1, 1)

        packagesGroup.setLayout(styleLayout)

        mainLayout = QVBoxLayout()
        mainLayout.addWidget(updateGroup)
        mainLayout.addWidget(packagesGroup)

        mainLayout.addSpacing(12)

        mainLayout.addStretch(1)

        self.setLayout(mainLayout)


class InfoPage(QWidget):
    def __init__(self,agent, parent=None):
        super(InfoPage, self).__init__(parent)
        self.agent = agent


        updateGroup = QGroupBox("选项:")
        self.showinfoCheckBox = QCheckBox("显示通知")
        self.showinfoiconCheckBox = QCheckBox("通知区域图标")
        self.infosoundCheckBox = QCheckBox("播放声音")

        updateLayout = QGridLayout()
        updateLayout.addWidget(self.showinfoCheckBox, 0, 0)
        updateLayout.addWidget(self.showinfoiconCheckBox, 0, 1)
        updateLayout.addWidget(self.infosoundCheckBox, 1, 0)

        updateGroup.setLayout(updateLayout)



        if agent != None:
            self.showinfoCheckBox.setChecked(agent.showinfo)
            self.showinfoiconCheckBox.setChecked(agent.showinfoicon)
            self.infosoundCheckBox.setChecked(agent.infosound)





        mainLayout = QVBoxLayout()
        mainLayout.addWidget(updateGroup)
        mainLayout.addStretch(1)
        self.setLayout(mainLayout)


    def selectFolder(self):
        # 打开文件夹选择框
        folder_path = QFileDialog.getExistingDirectory(self, "请选择文件夹", "")
        if folder_path:
            # 如果用户选择了文件夹，将文件夹路径设置为 QLineEdit 的文本
            self.kmpathEdit.setText(folder_path)

if __name__ == '__main__':

    import sys

    app = QApplication(sys.argv)
    dialog = ConfigDialog()
    sys.exit(dialog.exec_())
