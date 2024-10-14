import PyQt5
from PyQt5 import QtWidgets
from PyQt5.QtCore import QDate, QSize, Qt, QRect
from PyQt5.QtGui import QIcon, QPixmap, QPainter, QPen, QPainterPath
from PyQt5.QtWidgets import (QApplication, QCheckBox, QComboBox, QDateTimeEdit,
                             QDialog, QGridLayout, QGroupBox, QHBoxLayout, QLabel, QLineEdit,
                             QListView, QListWidget, QListWidgetItem, QPushButton, QSpinBox,
                             QStackedWidget, QVBoxLayout, QWidget, QDialogButtonBox, QRadioButton, QFileDialog, QMessageBox)
from db.DBFactory import add_MutiAgentCfg,query_MutiAgentCfg,query_MutiAgentCfg_All,update_MutiAgentCfg,delete_MutiAgentCfg
from db.DBFactory import query_PluginMng_All
from db.DBFactory import query_KMCfg_All,query_AgentCfg_All
import configdialog_rc
import datetime
import random
import string
# from datetime import datetime

class ConfigDialog(QDialog):
    def __init__(self, parent=None,agent=None):
        super(ConfigDialog, self).__init__(parent)

        self.contentsWidget = QListWidget()
        self.contentsWidget.setViewMode(QListView.IconMode)
        self.contentsWidget.setIconSize(QSize(96, 84))
        self.contentsWidget.setMovement(QListView.Static)
        self.contentsWidget.setMaximumWidth(128)
        self.contentsWidget.setSpacing(12)

        self.agent = agent
        self.app = parent

        self.generalPage=GeneralPage(self.agent)
        self.techniquePage=TechniquePage(self.agent)
        self.snsPage=SNSPage(self.agent)
        self.securityPage=SecurityPage(self.agent)



        self.pagesWidget = QStackedWidget()
        self.pagesWidget.addWidget(self.generalPage)
        self.pagesWidget.addWidget(self.techniquePage)
        self.pagesWidget.addWidget(self.snsPage)
        self.pagesWidget.addWidget(self.securityPage)




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

        self.setWindowTitle("Ai Agent群设置")

    def accept_close(self):
        print("accept")

        # generalpage
        name = self.generalPage.nameEdit.text()
        memo = self.generalPage.memoEdit.text()
        agents=",".join([item.data(Qt.UserRole) for item in self.generalPage.agentsList.selectedItems()])

        if agents =="":
            QMessageBox.warning(self, "警告", "请选择至少一个群成员。")
            return


        agentcommander = self.generalPage.groupmasterCombo.itemData(self.generalPage.groupmasterCombo.currentIndex())

        # Technique

        specialization = self.techniquePage.specializationCombo.currentText()
        plugins = ",".join([item.text() for item in self.techniquePage.pluginList.selectedItems()])
        kms = ",".join([item.text() for item in self.techniquePage.kmList.selectedItems()])
        prompt = self.techniquePage.pmtText.toPlainText()

        # SNS
        islimittotalmessage = self.snsPage.systemCheckBox.isChecked()
        islimitmessagepp = self.snsPage.appsCheckBox.isChecked()
        totalmessages = self.snsPage.hitsSpinBox.value()
        ppmessages = self.snsPage.hitsSpinBox_p.value()

        # Security
        readfile = self.securityPage.systemCheckBox.isChecked()
        writefile = self.securityPage.appsCheckBox.isChecked()
        deletefile = self.securityPage.docsCheckBox.isChecked()
        execfile = self.securityPage.execCheckBox.isChecked()
        autorunrounds = self.securityPage.hitsSpinBox.value()



        if self.agent == None:
            idstr = self.generate_random_id()
            record_id=add_MutiAgentCfg(idstr, name, memo, agents, agentcommander, specialization, plugins, kms, prompt, islimittotalmessage, islimitmessagepp, totalmessages, ppmessages, readfile, writefile, deletefile, execfile, autorunrounds)
            multi_agent_cfg=query_MutiAgentCfg(id=record_id)
            self.app.createToolBoxUnit_MutiAgentChat(multi_agent_cfg, self.app.toolBox_AgentChat.count())
        else:
            idstr = self.agent.group_id
            update_MutiAgentCfg(self.agent.id, name = name,memo = memo,agents = agents,agentcommander = agentcommander,specialization = specialization,plugins = plugins,kms = kms,prompt = prompt,islimittotalmessage = islimittotalmessage,islimitmessagepp = islimitmessagepp,totalmessages = totalmessages,ppmessages = ppmessages,readfile = readfile,writefile = writefile,deletefile = deletefile,execfile = execfile,autorunrounds = autorunrounds)
            tool_box_item = self.app.toolBox_AgentChat.findChild(QWidget, idstr)
            self.app.toolBox_AgentChat.setItemText(self.app.toolBox_AgentChat.indexOf(tool_box_item), f"{name} ({memo})" if memo else name)
            member_list = self.app.memberlist_group_list[self.agent.group_id]
            member_list.reload()

        self.name = name
        self.memo = memo
        self.agents = agents
        self.agentcommander = agentcommander




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
        configButton.setText("基本配置")
        configButton.setTextAlignment(Qt.AlignHCenter)
        configButton.setFlags(Qt.ItemIsSelectable | Qt.ItemIsEnabled)

        techButton = QListWidgetItem(self.contentsWidget)
        techButton.setIcon(QIcon('images/technique.png'))
        techButton.setText("技能配置")
        techButton.setTextAlignment(Qt.AlignHCenter)
        techButton.setFlags(Qt.ItemIsSelectable | Qt.ItemIsEnabled)

        queryButton = QListWidgetItem(self.contentsWidget)
        queryButton.setIcon(QIcon(':/images/update.png'))
        queryButton.setText("社交配置")
        queryButton.setTextAlignment(Qt.AlignHCenter)
        queryButton.setFlags(Qt.ItemIsSelectable | Qt.ItemIsEnabled)

        updateButton = QListWidgetItem(self.contentsWidget)
        updateButton.setIcon(QIcon(':/images/query.png'))
        updateButton.setText("权限安全")
        updateButton.setTextAlignment(Qt.AlignHCenter)
        updateButton.setFlags(Qt.ItemIsSelectable | Qt.ItemIsEnabled)



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

        self.avatar_label = ClickableAvatarLabel()
        self.avatar_label.setAlignment(Qt.AlignCenter)
        self.avatar_label.setFixedSize(70, 70)
        # self.avatar_label.setStyleSheet("QLabel{border: 1px solid blue;}")

        # 创建水平布局
        hLayout = QHBoxLayout()
        hLayout.addStretch()  # 在 avatar_label 前面添加伸展因子，将其推到水平中心
        hLayout.addWidget(self.avatar_label)
        hLayout.addStretch()  # 在 avatar_label 后面再添加一个伸展因子 必须前后都有

        self.avatar_label.clicked.connect(self.uploadAvatar)

        packagesGroup = QGroupBox("基本资料")

        self.nameLabel = QLabel("名称:")
        self.nameEdit = QLineEdit()

        self.memoLabel = QLabel("简介:")
        self.memoEdit = QLineEdit()

        self.agentsListLabel = QLabel("群成员:")
        self.agentsList = QListWidget()
        self.agentsList.setFixedHeight(180)
        self.agentsList.setSelectionMode(QListWidget.MultiSelection)

        self.groupmasterLabel = QLabel("群主:")
        self.groupmasterCombo = QComboBox()
        self.groupmasterCombo.setFixedWidth(250)

        records = query_AgentCfg_All()

        for record in records:
            agent_item = QListWidgetItem(self.agentsList)
            agent_item.setText(f"{record.name} ({record.memo})" if record.memo else record.name)
            agent_item.setData(Qt.UserRole, record.user_id)
            self.groupmasterCombo.addItem(f"{record.name} ({record.memo})" if record.memo else record.name,record.user_id)


        if agent!=None:
            self.nameEdit.setText(agent.name)  # Assuming index 0 represents self.nameEdit text
            self.memoEdit.setText(agent.memo)  # Assuming index 1 represents memoEdit text
            selected_agents = agent.agents.split(',')  # Assuming index 2 represents selected kms
            for i in range(self.agentsList.count()):
                item = self.agentsList.item(i)

                if item.data(Qt.UserRole) in selected_agents:
                    item.setSelected(True)

            # 遍历 QComboBox 的所有项，找到对应的 itemData 值并设置为当前选中项
            for index in range(self.groupmasterCombo.count()):
                if self.groupmasterCombo.itemData(index) == agent.agentcommander:
                    self.groupmasterCombo.setCurrentIndex(index)
                    break  # 找到后停止循环
            # self.groupmasterCombo.setCurrentText(agent.agentcommander)


        packagesLayout = QGridLayout()
        packagesLayout.addWidget(self.nameLabel, 0, 0)
        packagesLayout.addWidget(self.nameEdit, 0, 1)
        packagesLayout.addWidget(self.memoLabel, 1, 0)
        packagesLayout.addWidget(self.memoEdit, 1, 1)
        packagesLayout.addWidget(self.agentsListLabel, 2, 0)
        packagesLayout.addWidget(self.agentsList, 2, 1)
        packagesLayout.addWidget(self.groupmasterLabel, 3, 0)
        packagesLayout.addWidget(self.groupmasterCombo, 3, 1)

        packagesGroup.setLayout(packagesLayout)

        mainLayout = QVBoxLayout()

        mainLayout.addLayout(hLayout)

        mainLayout.addWidget(packagesGroup)
        mainLayout.addSpacing(12)

        mainLayout.addStretch(1)

        self.setLayout(mainLayout)
        self.setAvatar(QPixmap("images/avatar.png"))

    def uploadAvatar(self):
        filename, _ = QFileDialog.getOpenFileName(self, 'Open File', '.', 'Image Files (*.png *.jpg *.jpeg *.bmp)')
        if filename:
            pixmap = QPixmap(filename)
            self.setAvatar(pixmap)

    def setAvatar(self, pixmap):
        size = QSize(70, 70)
        target = QPixmap(size)
        target.fill(Qt.transparent)

        # 绘制圆形头像
        painter = QPainter(target)
        painter.setRenderHint(QPainter.Antialiasing)

        # 绘制圆形边框
        pen = QPen(Qt.gray)
        pen.setWidth(2)
        painter.setPen(pen)
        painter.drawEllipse(1, 1, size.width() - 2, size.height() - 2)

        # 绘制头像
        clip_path = QPainterPath()
        clip_path.addEllipse(2, 2, size.width() - 4, size.height() - 4)
        painter.setClipPath(clip_path)
        # painter.drawPixmap(5, 5, size.width()-10, size.height()-10, pixmap.scaled(size.width()-10, size.height()-10, Qt.KeepAspectRatio, Qt.SmoothTransformation))

        # 将原始图像缩放到适当大小，并放置在中心
        diameter = min(size.width(), size.height())
        scaled_pixmap = pixmap.scaledToWidth(diameter, Qt.SmoothTransformation) if pixmap.width() < pixmap.height() else pixmap.scaledToHeight(diameter, Qt.SmoothTransformation)
        target_rect = QRect((size.width() - scaled_pixmap.width()) // 2, (size.height() - scaled_pixmap.height()) // 2, scaled_pixmap.width(), scaled_pixmap.height())
        painter.drawPixmap(target_rect, scaled_pixmap)

        painter.end()

        self.avatar_label.setPixmap(target)

class TechniquePage(QWidget):
    def __init__(self,agent, parent=None):
        super(TechniquePage, self).__init__(parent)
        self.agent = agent

        packagesGroup = QGroupBox("技能资料")

        self.specializationLabel = QLabel("专长领域:")
        self.specializationCombo = QComboBox()
        self.specializationCombo.setFixedWidth(250)
        self.specializationCombo.addItem("法律")
        self.specializationCombo.addItem("编程")
        self.specializationCombo.addItem("金融")
        self.specializationCombo.addItem("运动")
        self.specializationCombo.addItem("旅行")

        packagesLayout = QGridLayout()
        packagesLayout.addWidget(self.specializationLabel, 1, 0)
        packagesLayout.addWidget(self.specializationCombo, 1, 1)

        packagesGroup.setLayout(packagesLayout)

        pluginGroup = QGroupBox("指定可使用的插件工具:")

        self.pluginList = QListWidget()
        self.pluginList.setFixedHeight(65)
        self.pluginList.setSelectionMode(QListWidget.MultiSelection)

        records = query_PluginMng_All()

        for record in records:
            tech_item = QListWidgetItem(self.pluginList)
            tech_item.setText(record.name+": "+record.version)




        pluginLayout = QVBoxLayout()
        pluginLayout.addWidget(self.pluginList)
        pluginGroup.setLayout(pluginLayout)

        kmGroup = QGroupBox("指定可使用的知识库:")

        self.kmList = QListWidget()
        self.kmList.setFixedHeight(65)
        self.kmList.setSelectionMode(QListWidget.MultiSelection)

        records = query_KMCfg_All()

        for record in records:
            km_item = QListWidgetItem(self.kmList)
            km_item.setText(record.name)

        kmLayout = QVBoxLayout()
        kmLayout.addWidget(self.kmList)
        kmGroup.setLayout(kmLayout)

        pmtGroup = QGroupBox("请设置Prompt模板:")

        self.pmtText = QtWidgets.QTextEdit()
        self.pmtText.setFixedHeight(80)

        if agent != None:
            self.specializationCombo.setCurrentText(agent.specialization)  # Assuming index 0 represents specializationCombo current text
            selected_packages = agent.plugins.split(',')  # Assuming index 1 represents selected packages
            for i in range(self.pluginList.count()):
                item = self.pluginList.item(i)
                if item.text() in selected_packages:
                    item.setSelected(True)
            selected_kms = agent.kms.split(',')  # Assuming index 2 represents selected kms
            for i in range(self.kmList.count()):
                item = self.kmList.item(i)
                if item.text() in selected_kms:
                    item.setSelected(True)
            self.pmtText.setPlainText(agent.prompt)  # Assuming index 3 represents pmtText plain text

        pmtLayout = QVBoxLayout()
        pmtLayout.addWidget(self.pmtText)
        pmtGroup.setLayout(pmtLayout)

        mainLayout = QVBoxLayout()
        mainLayout.addWidget(packagesGroup)
        #mainLayout.addSpacing(12)
        mainLayout.addWidget(pluginGroup)
        mainLayout.addWidget(kmGroup)
        mainLayout.addWidget(pmtGroup)
        mainLayout.addStretch(1)

        self.setLayout(mainLayout)

class SNSPage(QWidget):
    def __init__(self, agent,parent=None):
        super(SNSPage, self).__init__(parent)
        self.agent = agent



        updateGroup = QGroupBox("指定聊天规则:")
        self.systemCheckBox = QCheckBox("限制每天聊天信息总数")
        self.appsCheckBox = QCheckBox("限制每天单联系人信息总数")

        self.hitsSpinBox = QSpinBox()
        self.hitsSpinBox.setPrefix("每天聊天总信息数:")
        self.hitsSpinBox.setSuffix("条")
        #self.hitsSpinBox.setSpecialValueText("请点击调节按钮设置智能体能无询问自动执行的轮数")
        self.hitsSpinBox.setMinimum(500)
        self.hitsSpinBox.setMaximum(1000)
        self.hitsSpinBox.setSingleStep(10)

        self.hitsSpinBox_p = QSpinBox()
        self.hitsSpinBox_p.setPrefix("每天聊天总信息数:")
        self.hitsSpinBox_p.setSuffix("条")
        #self.hitsSpinBox.setSpecialValueText("请点击调节按钮设置智能体能无询问自动执行的轮数")
        self.hitsSpinBox_p.setMinimum(50)
        self.hitsSpinBox_p.setMaximum(100)
        self.hitsSpinBox_p.setSingleStep(10)

        if agent != None:
            self.systemCheckBox.setChecked(agent.islimittotalmessage)
            self.appsCheckBox.setChecked(agent.islimitmessagepp)
            self.hitsSpinBox.setValue(agent.totalmessages)
            self.hitsSpinBox_p.setValue(agent.ppmessages)


        updateLayout = QGridLayout()
        updateLayout.addWidget(self.systemCheckBox,0,0)
        updateLayout.addWidget(self.appsCheckBox,0,1)
        updateLayout.addWidget(self.hitsSpinBox, 1, 0, 1, 2)
        updateLayout.addWidget(self.hitsSpinBox_p, 2, 0, 1, 2)
        updateGroup.setLayout(updateLayout)



        mainLayout = QVBoxLayout()
        mainLayout.addWidget(updateGroup)
        mainLayout.addStretch(1)

        self.setLayout(mainLayout)

class SecurityPage(QWidget):
    def __init__(self,agent, parent=None):
        super(SecurityPage, self).__init__(parent)
        self.agent = agent

        updateGroup = QGroupBox("指定本地权限:")
        self.systemCheckBox = QCheckBox("读取本地文件")
        self.appsCheckBox = QCheckBox("写入本地文件")
        self.docsCheckBox = QCheckBox("删除本地文件")
        self.execCheckBox = QCheckBox("本地运行程序")

        self.hitsSpinBox = QSpinBox()
        self.hitsSpinBox.setPrefix("任务可自动执行")
        self.hitsSpinBox.setSuffix("轮,而不需要询问")
        # self.hitsSpinBox.setSpecialValueText("请点击调节按钮设置智能体能无询问自动执行的轮数")
        self.hitsSpinBox.setMinimum(10)
        self.hitsSpinBox.setMaximum(100)
        self.hitsSpinBox.setSingleStep(10)

        if agent != None:
            self.systemCheckBox.setChecked(agent.readfile)
            self.appsCheckBox.setChecked(agent.writefile)
            self.docsCheckBox.setChecked(agent.deletefile)
            self.execCheckBox.setChecked(agent.execfile)
            self.hitsSpinBox.setValue(agent.autorunrounds)


        startUpdateButton = QPushButton("测试验证")

        updateLayout = QGridLayout()
        updateLayout.addWidget(self.systemCheckBox,0,0)
        updateLayout.addWidget(self.appsCheckBox,0,1)
        updateLayout.addWidget(self.docsCheckBox,1,0)
        updateLayout.addWidget(self.execCheckBox,1,1)
        updateLayout.addWidget(self.hitsSpinBox, 2, 0, 1, 2)
        updateGroup.setLayout(updateLayout)



        mainLayout = QVBoxLayout()
        mainLayout.addWidget(updateGroup)

        mainLayout.addSpacing(12)
        mainLayout.addWidget(startUpdateButton)
        mainLayout.addStretch(1)

        self.setLayout(mainLayout)

class ClickableAvatarLabel(QLabel):
    clicked = PyQt5.QtCore.pyqtSignal()

    def mousePressEvent(self, event):
        self.clicked.emit()

if __name__ == '__main__':

    import sys

    app = QApplication(sys.argv)
    dialog = ConfigDialog()
    sys.exit(dialog.exec_())
