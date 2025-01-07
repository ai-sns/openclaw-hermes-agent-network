import PyQt5
from PyQt5 import QtWidgets
from PyQt5.QtCore import QDate, QSize, Qt, QRect

from PyQt5.QtGui import QIcon, QPixmap, QPainter, QPen, QPainterPath,QKeySequence
from PyQt5.QtWidgets import (QApplication, QCheckBox, QComboBox, QDateTimeEdit,
                             QDialog, QGridLayout, QGroupBox, QHBoxLayout, QLabel, QLineEdit,
                             QListView, QListWidget, QListWidgetItem, QPushButton, QSpinBox,
                             QStackedWidget, QVBoxLayout, QWidget, QDialogButtonBox, QRadioButton, QFileDialog,QShortcut,QMessageBox,QFormLayout)

from db.DBFactory import add_AgentCfg, update_AgentCfg,query_AgentCfg
from db.DBFactory import query_AiChatCfg_All
from db.DBFactory import query_PluginMng_All
from db.DBFactory import query_KMCfg_All,get_all_prompt_by_modelname,query_PluginMng_All_Tool


import datetime
import webbrowser
from web3 import Web3
import subprocess
from util import generate_random_id
from globals import global_agent_list,global_plugin_list,global_buddy_list
# from datetime import datetime
import regex as re
import llm_manager as llmmgr
class ConfigDialog(QDialog):
    def __init__(self, parent=None,agent=None):
        super(ConfigDialog, self).__init__(parent)
        self.setWindowFlags(self.windowFlags() | Qt.WindowMinMaxButtonsHint)  # 添加最小化和最大化按钮
        self.contentsWidget = QListWidget()
        self.contentsWidget.setViewMode(QListView.IconMode)
        self.contentsWidget.setIconSize(QSize(96, 84))
        self.contentsWidget.setMovement(QListView.Static)
        self.contentsWidget.setMaximumWidth(128)
        self.contentsWidget.setSpacing(12)
        # if idstr=="":
        #    idstr="001"

        # self.ai_chat_cfg = query_AgentCfg(user_id=idstr)

        if agent is None:
            agent_cfg = None
        else:
            agent_cfg = agent.agent_cfg

        self.agent_cfg = agent_cfg
        self.app =parent

        self.generalPage=GeneralPage(agent)
        self.techniquePage=TechniquePage(agent)
        self.snsPage=SNSPage(agent)
        self.securityPage=SecurityPage(agent)
        self.snsPage.setHidden(True)


        self.pagesWidget = QStackedWidget()
        self.pagesWidget.addWidget(self.generalPage)
        self.pagesWidget.addWidget(self.techniquePage)
        # self.pagesWidget.addWidget(self.snsPage)
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

        self.shortcut = QShortcut(QKeySequence('Ctrl+Enter'), self)
        self.shortcut.activated.connect(self.accept_close)

        cancel_button = button_box.button(QDialogButtonBox.Cancel)
        cancel_button.setText("取消")
        button_box.accepted.connect(self.accept_close)
        button_box.rejected.connect(self.reject_close)

        mainLayout.addWidget(button_box)



        self.setLayout(mainLayout)

        self.setWindowTitle("Ai智能体设置")

    def accept_close(self):
        print("accept")

        # generalpage
        name = self.generalPage.nameEdit.text()
        memo = self.generalPage.memoEdit.text()
        tborndate = self.generalPage.dateEdit.dateTime().toString("yyyy-MM-dd")
        borndate=datetime.datetime.strptime(tborndate, "%Y-%m-%d")

        borncontry = self.generalPage.bornareaCombo.currentText()
        language = self.generalPage.languageCombo.currentText()
        male_selected = self.generalPage.gender_male.isChecked()
        female_selected = self.generalPage.gender_female.isChecked()
        if male_selected==True:
            gender=1
        else:
            gender=0
        joinfederation = self.generalPage.releasesCheckBox.isChecked()
        syncfederation = self.generalPage.upgradesCheckBox.isChecked()

        # Technique
        defaultmodel =self.techniquePage.modelCombo.currentData()
        defaultrole = self.techniquePage.roleCombo.currentData()
        specialization = self.techniquePage.specializationText.toPlainText()
        plugins = ",".join([item.text() for item in self.techniquePage.pluginList.selectedItems()])

        kms = ",".join([item.text() for item in self.techniquePage.kmList.selectedItems()])
        last_plugins=""
        last_kms =""

        prompt = self.techniquePage.pmtText.toPlainText()

        # SNS
        i = self.snsPage.serverCombo.currentIndex()
        snsaccount = self.snsPage.sns_account_list[i]
        snsnickname = self.snsPage.sns_nick_name_list[i]


        islimittotalmessage = self.snsPage.systemCheckBox.isChecked()
        islimitmessagepp = self.snsPage.appsCheckBox.isChecked()
        totalmessages = self.snsPage.hitsSpinBox.value()
        ppmessages = self.snsPage.hitsSpinBox_p.value()

        # Security
        readfile = self.securityPage.systemCheckBox.isChecked()
        writefile = self.securityPage.appsCheckBox.isChecked()
        deletefile = self.securityPage.docsCheckBox.isChecked()
        execfile = self.securityPage.execCheckBox.isChecked()
        uselastmodel = self.securityPage.modelchoiceCheckBox.isChecked()
        uselastrole = self.securityPage.rolechoiceCheckBox.isChecked()
        uselastplugins = self.securityPage.uselastpluginsCheckBox.isChecked()
        uselastkms = self.securityPage.uselastkmsCheckBox.isChecked()
        callpluginbyinstruct = self.securityPage.plugincallCheckBox.isChecked()
        autorunrounds = self.securityPage.hitsSpinBox.value()
        federationid = "None"
        if self.agent_cfg == None:
            idstr=generate_random_id()
            add_AgentCfg(idstr,name,memo,borndate ,borncontry,language,gender,joinfederation,syncfederation,federationid,defaultmodel,defaultrole,defaultmodel,defaultrole,specialization,plugins,kms,last_plugins,last_kms,prompt,snsaccount,snsnickname,islimittotalmessage,islimitmessagepp,totalmessages,ppmessages,readfile,writefile,deletefile,execfile,uselastmodel,uselastrole,uselastplugins,uselastkms,callpluginbyinstruct,autorunrounds)

            self.app.get_all_agent()
            agents = global_agent_list.values()  # 前面已经从数据库中初始化了agent列表，直接使用前面已经初始化的列表获取其agent_cfg即可
            new_agent=list(agents)[-1]
            visible_count = sum(1 for agent in agents if agent.agent_cfg.is_show)
            self.app.createToolBoxUnit_AgentChat(new_agent,visible_count)
        else:
            idstr=self.agent_cfg.user_id
            update_AgentCfg(self.agent_cfg.id, name=name,memo=memo,borndate=borndate,borncontry=borncontry,language=language,gender=gender,joinfederation=joinfederation,syncfederation=syncfederation,defaultmodel=defaultmodel,defaultrole=defaultrole,specialization=specialization,plugins=plugins,kms=kms,prompt=prompt,snsaccount=snsaccount,snsnickname=snsnickname,islimittotalmessage=islimittotalmessage,islimitmessagepp=islimitmessagepp,totalmessages=totalmessages,ppmessages=ppmessages,readfile=readfile,writefile=writefile,deletefile=deletefile,execfile=execfile,uselastmodel=uselastmodel,uselastrole=uselastrole,uselastplugins=uselastplugins,uselastkms=uselastkms,callpluginbyinstruct=callpluginbyinstruct,autorunrounds=autorunrounds)
            tool_box_item = self.app.toolBox_AgentChat.findChild(QWidget, idstr)
            self.app.toolBox_AgentChat.setItemText(self.app.toolBox_AgentChat.indexOf(tool_box_item), f"{name} ({memo})" if memo else name)
            # self.app.toolBox_AgentChat.setItemIcon(self.app.toolBox_AgentChat.indexOf(settingWidget), QIcon('images/setting.png'))

        self.name=name
        self.memo = memo
        self.specialization = specialization
        self.snsaccount = snsaccount
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

        # queryButton = QListWidgetItem(self.contentsWidget)
        # queryButton.setIcon(QIcon(':/images/update.png'))
        # queryButton.setText("社交配置")
        # queryButton.setTextAlignment(Qt.AlignHCenter)
        # queryButton.setFlags(Qt.ItemIsSelectable | Qt.ItemIsEnabled)

        updateButton = QListWidgetItem(self.contentsWidget)
        updateButton.setIcon(QIcon(':/images/update.png'))
        updateButton.setText("其他设置")
        updateButton.setTextAlignment(Qt.AlignHCenter)
        updateButton.setFlags(Qt.ItemIsSelectable | Qt.ItemIsEnabled)



        self.contentsWidget.adjustSize()
        self.contentsWidget.setFixedHeight(500)
        self.contentsWidget.currentItemChanged.connect(self.changePage)

class GeneralPage(QWidget):
    def __init__(self, agent, parent=None):
        super(GeneralPage, self).__init__(parent)
        if agent is None:
            agent_cfg = None
        else:
            agent_cfg = agent.agent_cfg
        self.agent_cfg = agent_cfg

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

        self.nameLabel = QLabel("姓名:")
        self.nameEdit = QLineEdit()

        self.memoLabel = QLabel("简介:")
        self.memoEdit = QLineEdit()

        self.dateLabel = QLabel("出生日期:")
        self.dateEdit = QDateTimeEdit(QDate.currentDate())

        self.bornareaLabel = QLabel("出生地区:")
        self.bornareaCombo = QComboBox()
        self.bornareaCombo.addItem("中国")
        self.bornareaCombo.addItem("美国")
        self.bornareaCombo.addItem("英国")
        self.bornareaCombo.addItem("法国")
        self.bornareaCombo.addItem("德国")

        self.languageLabel = QLabel("第一语言:")
        self.languageCombo = QComboBox()
        self.languageCombo.addItem("中文")
        self.languageCombo.addItem("英文")
        self.languageCombo.addItem("韩语")
        self.languageCombo.addItem("日语")
        self.languageCombo.addItem("法语")

        self.genderLabel = QLabel("性别:")
        self.genderLayout = QHBoxLayout()
        self.gender_male = QRadioButton('男性')
        self.gender_female = QRadioButton('女性')
        self.genderLayout.addWidget(self.gender_male)
        self.genderLayout.addWidget(self.gender_female)

        self.releasesCheckBox = QCheckBox("加入Ai联邦")
        self.upgradesCheckBox = QCheckBox("自动同步信息至Ai联邦")

        if agent != None:
            self.nameEdit.setText(agent_cfg.name)  # Assuming index 0 represents self.nameEdit text
            self.memoEdit.setText(agent_cfg.memo)  # Assuming index 1 represents memoEdit text
            self.dateEdit.setDateTime(agent_cfg.borndate)  # Assuming index 2 represents self.dateEdit value
            self.bornareaCombo.setCurrentText(agent_cfg.borncontry)  # Assuming index 3 represents self.bornareaCombo current text
            self.languageCombo.setCurrentText(agent_cfg.language)  # Assuming index 4 represents self.self.languageCombo  current text
            if agent_cfg.gender == 1:
                self.gender_male.setChecked(True)  # Assuming index 5 represents self.radio_male checked state
                self.gender_female.setChecked(False)  # Assuming index 6 represents self.radio_female checked state
            else:
                self.gender_male.setChecked(False)  # Assuming index 5 represents self.radio_male checked state
                self.gender_female.setChecked(True)  # Assuming index 6 represents self.radio_female checked state
            self.releasesCheckBox.setChecked(agent_cfg.joinfederation)  # Assuming index 7 represents self.releasesCheckBox checked state
            self.upgradesCheckBox.setChecked(agent_cfg.syncfederation)

        # startQueryButton = QPushButton("获取Ai联邦身份证")
        startQueryButton = QPushButton("区块链验证Ai联邦身份信息")
        startQueryButton.clicked.connect(self.openblockchain)

        packagesLayout = QGridLayout()
        packagesLayout.addWidget(self.nameLabel, 0, 0)
        packagesLayout.addWidget(self.nameEdit, 0, 1)
        packagesLayout.addWidget(self.memoLabel, 1, 0)
        packagesLayout.addWidget(self.memoEdit, 1, 1)
        packagesLayout.addWidget(self.dateLabel, 2, 0)
        packagesLayout.addWidget(self.dateEdit, 2, 1)
        packagesLayout.addWidget(self.bornareaLabel, 3, 0)
        packagesLayout.addWidget(self.bornareaCombo, 3, 1)
        packagesLayout.addWidget(self.languageLabel, 4, 0)
        packagesLayout.addWidget(self.languageCombo, 4, 1)
        packagesLayout.addWidget(self.genderLabel, 5, 0)
        packagesLayout.addLayout(self.genderLayout, 5, 1)
        packagesLayout.addWidget(self.releasesCheckBox, 6, 0)
        packagesLayout.addWidget(self.upgradesCheckBox, 6, 1)

        packagesGroup.setLayout(packagesLayout)

        mainLayout = QVBoxLayout()

        mainLayout.addLayout(hLayout)

        mainLayout.addWidget(packagesGroup)
        mainLayout.addSpacing(12)

        self.federal_id = ClickableLabel("0xA4A47FDcC12b15110e70E7DD6829644C39680c6b")
        mainLayout.addWidget(self.federal_id)
        mainLayout.addSpacing(12)
        mainLayout.addWidget(startQueryButton)
        mainLayout.addStretch(1)

        self.setLayout(mainLayout)
        self.setAvatar(QPixmap("images/avatar.png"))

    def openblockchain(self):
        url="https://sepolia.etherscan.io/address/0xBD0322cBe5739Eb1A598179D4BD672147195653F"
        webbrowser.open(url)

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
        if agent is None:
            agent_cfg = None
        else:
            agent_cfg = agent.agent_cfg
        self.agent_cfg = agent_cfg

        modelroleGroup = QGroupBox("模型与角色:")

        # self.modelLabel = QLabel("模型:")
        self.modelCombo = QComboBox()


        # ai_chat_records = query_AiChatCfg_All()
        # self.modelCombo.addItem("N/A")
        # self.sns_account_list.append("N/A")
        # self.sns_nick_name_list.append("N/A")
        # for ai_chat_record in ai_chat_records:
        #     ai_chat_account = ai_chat_record.account
        #     ai_chat_nick_name = ai_chat_record.nickname
        #
        #     if ai_chat_account == cur_sns_account:
        #         ai_chat_nick_name = cur_nick_name
        #
        #     if ai_chat_account == "N/A":
        #         self.modelCombo.addItem("N/A")
        #     else:
        #         self.modelCombo.addItem(ai_chat_nick_name + "(" + ai_chat_account + ")")
        #
        #     self.sns_account_list.append(ai_chat_account)
        #     self.sns_nick_name_list.append(ai_chat_nick_name)
        #
        # self.modelCombo.currentIndexChanged.connect(self.on_combobox_changed)

        llm_model_list =llmmgr.get_all_llm_model_list()

        # 清空组合框以避免重复项
        self.modelCombo.clear()

        # 将每个 LLM 模型添加到组合框中
        for llm_model in llm_model_list:
            self.modelCombo.addItem(llm_model,llm_model)
        # 连接当前文本更改信号到相应的处理方法
        # 使用 lambda 以避免立即调用 set_role_combo_choice
        self.modelCombo.currentTextChanged.connect(self.set_role_combo_choice)

        modelLayout = QFormLayout()
        modelLayout.addRow("缺省模型:",self.modelCombo)


        # self.roleLabel = QLabel("角色:")
        self.roleCombo = QComboBox()
        roleLayout = QFormLayout()
        roleLayout.addRow("缺省角色:",self.roleCombo)
        # roleLayout.addWidget(self.roleLabel)
        # roleLayout.addWidget(self.roleCombo)

        modelroleLayout = QVBoxLayout()
        modelroleLayout.addLayout(modelLayout)
        modelroleLayout.addLayout(roleLayout)
        modelroleGroup.setLayout(modelroleLayout)

        self.set_role_combo_choice()



        packagesGroup = QGroupBox("Agent介绍")

        self.specializationText = QtWidgets.QPlainTextEdit()
        self.specializationText.setFixedHeight(100)
        self.specializationText.setPlaceholderText("在此设置Agent的介绍，重点介绍它有什么功能，如：它拥有各类法律法规数据库，能解答各类法律法规")


        packagesLayout = QGridLayout()
        packagesLayout.addWidget(self.specializationText, 1, 0)


        packagesGroup.setLayout(packagesLayout)

        pluginGroup = QGroupBox("指定插件工具(未指定,则可使用全部):")

        self.pluginList = QListWidget()
        self.pluginList.setFixedHeight(65)
        self.pluginList.setSelectionMode(QListWidget.MultiSelection)

        records = query_PluginMng_All_Tool(is_delete=0)

        for record in records:
            tech_item = QListWidgetItem(self.pluginList)
            tech_item.setText(record.name)


        pluginLayout = QVBoxLayout()
        pluginLayout.addWidget(self.pluginList)
        pluginGroup.setLayout(pluginLayout)

        kmGroup = QGroupBox("指定知识库(未指定,则可使用全部):")

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

        pmtGroup = QGroupBox("*角色系统提示词:")

        self.pmtText = QtWidgets.QPlainTextEdit()
        self.pmtText.setFixedHeight(100)
        self.pmtText.setPlaceholderText("在此设置Agent的角色系统提示词，比如：你是位律师，擅长解答各类法律法规，你要用专业的知识给用户解答")

        if agent is not None:
            selected_packages = agent_cfg.plugins.split(',')  # Assuming index 1 represents selected packages
            for i in range(self.pluginList.count()):
                item = self.pluginList.item(i)
                if item.text() in selected_packages:
                    item.setSelected(True)
            selected_kms = agent_cfg.kms.split(',')  # Assuming index 2 represents selected kms
            for i in range(self.kmList.count()):
                item = self.kmList.item(i)
                if item.text() in selected_kms:
                    item.setSelected(True)

            self.modelCombo.setCurrentText(agent_cfg.defaultmodel)
            # for i in range(self.roleCombo.count()):
            #     item = self.roleCombo.item(i)
            #     if item. in selected_kms:
            #         item.setSelected(True)


            if agent_cfg.defaultrole:
                # 遍历每个项，查找匹配数据
                for i in range(self.roleCombo.count()):
                    # 获取当前项的数据
                    item_data = self.roleCombo.itemData(i)

                    # 如果找到了匹配的值
                    if item_data == int(agent_cfg.defaultrole):
                        # 将该项设为选中
                        self.roleCombo.setCurrentIndex(i)
                        break

            self.specializationText.setPlainText(agent_cfg.specialization)
            self.pmtText.setPlainText(agent_cfg.prompt)  # Assuming index 3 represents pmtText plain text

        pmtLayout = QVBoxLayout()
        pmtLayout.addWidget(self.pmtText)
        pmtGroup.setLayout(pmtLayout)

        mainLayout = QVBoxLayout()
        pmtGroup.setHidden(True)#隐藏掉了
        mainLayout.addWidget(modelroleGroup)
        mainLayout.addWidget(pmtGroup)
        mainLayout.addWidget(packagesGroup)
        #mainLayout.addSpacing(12)
        mainLayout.addWidget(pluginGroup)
        mainLayout.addWidget(kmGroup)

        mainLayout.addStretch(1)

        self.setLayout(mainLayout)

    def set_role_combo_choice(self):
        """
        设置角色组合框的选择项，根据选中的模型连接器名称获取相应的角色记录，并将其添加到角色组合框中。

        :return: None
        """
        # 获取当前选择的模型连接器名称，并从中提取实际的名称
        model_connector_name = self.modelCombo.currentText().split(":")[0]

        # 获取与模型连接器名称相关的角色记录
        role_records = get_all_prompt_by_modelname(f"{model_connector_name}")

        # 清空角色组合框以避免重复添加
        self.roleCombo.clear()

        # 检查是否找到了角色记录
        if role_records:
            # 遍历角色记录并将其添加到角色组合框
            for role_record in role_records:
                # 假设 role_record 有一个 `name` 属性或字段用于显示
                self.roleCombo.addItem(role_record.title,role_record.id,)  # 使用 role_record 的名称添加项
        else:
            print(f"No role records found for model: {model_connector_name}")  # 记录未找到的情况


class SNSPage(QWidget):
    def __init__(self, agent,parent=None):
        super(SNSPage, self).__init__(parent)
        if agent is None:
            agent_cfg = None
        else:
            agent_cfg = agent.agent_cfg
        self.agent_cfg = agent_cfg
        cur_sns_account = ""
        cur_nick_name = ""
        self.sns_account_list = []
        self.sns_nick_name_list = []

        if agent != None:
            cur_sns_account = agent_cfg.snsaccount
            cur_nick_name = agent_cfg.snsnickname

        configGroup = QGroupBox("请选择已注册的Ai社交帐号:")

        self.serverLabel = QLabel("帐号:")
        self.serverCombo = QComboBox()
        ai_chat_records = query_AiChatCfg_All()
        self.serverCombo.addItem("N/A")
        self.sns_account_list.append("N/A")
        self.sns_nick_name_list.append("N/A")
        for ai_chat_record in ai_chat_records:
            ai_chat_account=ai_chat_record.account
            ai_chat_nick_name = ai_chat_record.nickname
            if ai_chat_account==cur_sns_account:
                ai_chat_nick_name = cur_nick_name
            if ai_chat_account=="N/A":
                self.serverCombo.addItem("N/A")
            else:
                self.serverCombo.addItem(ai_chat_nick_name + "(" + ai_chat_account + ")")

            self.sns_account_list.append(ai_chat_account)
            self.sns_nick_name_list.append(ai_chat_nick_name)
        self.serverCombo.currentIndexChanged.connect(self.on_combobox_changed)



        serverLayout = QHBoxLayout()
        serverLayout.addWidget(self.serverLabel)
        serverLayout.addWidget(self.serverCombo)

        configLayout = QVBoxLayout()
        configLayout.addLayout(serverLayout)
        configGroup.setLayout(configLayout)


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

            if cur_sns_account=="":
                self.serverCombo.setCurrentText("N/A")
            else:
                if cur_nick_name=="N/A":
                    self.serverCombo.setCurrentText("N/A")
                else:
                    self.serverCombo.setCurrentText(cur_nick_name + "(" + cur_sns_account + ")")


            self.systemCheckBox.setChecked(agent_cfg.islimittotalmessage)
            self.appsCheckBox.setChecked(agent_cfg.islimitmessagepp)
            self.hitsSpinBox.setValue(agent_cfg.totalmessages)
            self.hitsSpinBox_p.setValue(agent_cfg.ppmessages)


        updateLayout = QGridLayout()
        updateLayout.addWidget(self.systemCheckBox,0,0)
        updateLayout.addWidget(self.appsCheckBox,0,1)
        updateLayout.addWidget(self.hitsSpinBox, 1, 0, 1, 2)
        updateLayout.addWidget(self.hitsSpinBox_p, 2, 0, 1, 2)
        updateGroup.setLayout(updateLayout)



        mainLayout = QVBoxLayout()
        mainLayout.addWidget(configGroup)
        mainLayout.addWidget(updateGroup)
        mainLayout.addStretch(1)

        self.setLayout(mainLayout)

    def on_combobox_changed(self, index):
        """
        当QComboBox的选项变化时调用此方法
        :param index: 当前选中项的索引
        """
        # 获取当前选中的选项文本
        cur_sns_account = self.agent_cfg.snsaccount
        cur_nick_name = self.agent_cfg.snsnickname

        selected_name = self.serverCombo.currentText()

        match = re.search(r'\((.*?)\)', selected_name)
        if match:
            selected_account =  match.group(1)  # 返回匹配到的内容
        else:
            selected_account = "N/A"



        if selected_name !="N/A" and selected_name!=cur_nick_name + "(" + cur_sns_account + ")":
            agent_belonged = query_AgentCfg(snsaccount=selected_account)
            if agent_belonged:
                QMessageBox.information(self, '提示', '该社交帐号已经分配了其他Agent，请选择别的社交帐号!')
                if cur_nick_name != "N/A":
                    self.serverCombo.setCurrentText(cur_nick_name + "(" + cur_sns_account + ")")
                else:
                    self.serverCombo.setCurrentText("N/A")
            # else:
            #     self.serverCombo.setCurrentText(selected_name)
            #     snsaccount=self.ai_chat_cfg.account
            #     snsnickname = self.ai_chat_cfg.nickname
            #     update_AgentCfg(agent_belonged.id,snsaccount=snsaccount,snsnickname=snsnickname)

class SecurityPage(QWidget):
    def __init__(self,agent, parent=None):
        super(SecurityPage, self).__init__(parent)
        if agent is None:
            agent_cfg = None
        else:
            agent_cfg = agent.agent_cfg
        self.agent_cfg = agent_cfg

        preferenceGroup = QGroupBox("偏好设置:")
        self.modelchoiceCheckBox = QCheckBox("启动后使用最近一次使用的模型")
        self.rolechoiceCheckBox = QCheckBox("启动后使用最近一次使用的角色")
        self.uselastpluginsCheckBox = QCheckBox("启动后启用最近一次使用的插件")
        self.uselastkmsCheckBox = QCheckBox("启动后启用最近一次使用的知识库")
        self.plugincallCheckBox = QCheckBox("插件可通过指令调用")
        self.modelfrequentCheckBox = QCheckBox("对话界面启用常用模型列表")
        self.rolefrequentCheckBox = QCheckBox("对话界面启用常用角色列表")

        preferenceLayout = QGridLayout()
        preferenceLayout.addWidget(self.modelchoiceCheckBox, 0, 0)
        preferenceLayout.addWidget(self.rolechoiceCheckBox, 1, 0)
        preferenceLayout.addWidget(self.uselastpluginsCheckBox, 2, 0)
        preferenceLayout.addWidget(self.uselastkmsCheckBox, 3, 0)
        preferenceLayout.addWidget(self.plugincallCheckBox, 4, 0)
        preferenceLayout.addWidget(self.modelfrequentCheckBox, 5, 0)
        preferenceLayout.addWidget(self.rolefrequentCheckBox, 6, 0)

        preferenceGroup.setLayout(preferenceLayout)



        updateGroup = QGroupBox("任务模式设置:")
        self.systemCheckBox = QCheckBox("读取本地文件")
        self.appsCheckBox = QCheckBox("写入本地文件")
        self.docsCheckBox = QCheckBox("删除本地文件")
        self.execCheckBox = QCheckBox("本地运行程序")

        self.systemCheckBox.setHidden(True)
        self.appsCheckBox.setHidden(True)
        self.docsCheckBox.setHidden(True)
        self.execCheckBox.setHidden(True)

        self.hitsSpinBox = QSpinBox()
        self.hitsSpinBox.setPrefix("任务可自动执行")
        self.hitsSpinBox.setSuffix("轮,而不需要询问")
        # self.hitsSpinBox.setSpecialValueText("请点击调节按钮设置智能体能无询问自动执行的轮数")
        self.hitsSpinBox.setMinimum(10)
        self.hitsSpinBox.setMaximum(100)
        self.hitsSpinBox.setSingleStep(10)

        if agent != None:
            self.systemCheckBox.setChecked(agent_cfg.readfile)
            self.appsCheckBox.setChecked(agent_cfg.writefile)
            self.docsCheckBox.setChecked(agent_cfg.deletefile)
            self.execCheckBox.setChecked(agent_cfg.execfile)

            self.modelchoiceCheckBox.setChecked(agent_cfg.uselastmodel)
            self.rolechoiceCheckBox.setChecked(agent_cfg.uselastrole)
            self.uselastpluginsCheckBox.setChecked(agent_cfg.uselastplugins)
            self.uselastkmsCheckBox.setChecked(agent_cfg.uselastkms)
            self.plugincallCheckBox.setChecked(agent_cfg.callpluginbyinstruct)


            self.hitsSpinBox.setValue(agent_cfg.autorunrounds)


        startUpdateButton = QPushButton("测试验证")
        startUpdateButton.setHidden(True)
        updateLayout = QGridLayout()
        # updateLayout.addWidget(self.systemCheckBox,0,0)
        # updateLayout.addWidget(self.appsCheckBox,0,1)
        # updateLayout.addWidget(self.docsCheckBox,1,0)
        # updateLayout.addWidget(self.execCheckBox,1,1)
        updateLayout.addWidget(self.hitsSpinBox, 2, 0, 1, 2)
        updateGroup.setLayout(updateLayout)



        mainLayout = QVBoxLayout()

        mainLayout.addWidget(preferenceGroup)

        mainLayout.addWidget(updateGroup)

        mainLayout.addSpacing(12)
        # mainLayout.addWidget(startUpdateButton)
        mainLayout.addStretch(1)






        self.setLayout(mainLayout)

class ClickableAvatarLabel(QLabel):
    clicked = PyQt5.QtCore.pyqtSignal()

    def mousePressEvent(self, event):
        self.clicked.emit()

class ClickableLabel(QLabel):
    clicknum=0
    def __init__(self, text):
        super().__init__(text)
        self.setTextInteractionFlags(Qt.TextSelectableByMouse)
        self.setStyleSheet("QLabel { color: blue; text-decoration: underline;cursor: pointer;margin-left:20px } QLabel:hover { color: red; text-decoration: underline;cursor: pointer;margin-left:20px }")

    def mousePressEvent(self, event):

        # 在点击时创建对话框并传递参数
        print("clicknum", self.clicknum)
        if self.clicknum % 2 ==0:
            dialog = CustomDialog(self.text())
            dialog.exec_()
        else:
            bat_file_path = r'C:\dev\magic_ai\DigitalIdentity\scripts\getcontract.bat'
            subprocess.call(['start', 'cmd', '/c', bat_file_path], shell=True)

        self.clicknum += 1


class CustomDialog(QDialog):
    def __init__(self, parameter, parent=None):
        super().__init__(parent)

        self.setWindowTitle("Ai联邦区块链数字身份信息")
        self.setWindowIcon(QIcon("images/aisns.png"))

        # 创建对话框布局
        identity_information = self.get_Digital_ID(parameter)
        layout = QVBoxLayout(self)
        self.label = QLabel(f"Ai联邦身份ID: {parameter}", self)
        layout.addWidget(self.label)
        layout.addSpacing(12)

        self.label2 = QLabel(f"姓名: {identity_information[0]}", self)
        layout.addWidget(self.label2)
        layout.addSpacing(12)
        self.label3 = QLabel(f"年龄: {identity_information[3]}", self)
        layout.addWidget(self.label3)
        layout.addSpacing(12)
        self.label4 = QLabel(f"技能: {identity_information[5]}", self)
        layout.addWidget(self.label4)
        layout.addSpacing(12)
        self.label5 = QLabel(f"训练时长: {identity_information[6]}", self)
        layout.addWidget(self.label5)
        # layout.addSpacing(12)



    def get_Digital_ID(self,contract_address):
        # 替换为你的以太坊节点的 URL
        web3 = Web3(Web3.HTTPProvider('https://eth-sepolia.g.alchemy.com/v2/-G9pG9qsVoQ2athWw_TqT-AjpDhnnDde'))

        # contract_address = '0xA4A47FDcC12b15110e70E7DD6829644C39680c6b'  # 替换为你的智能合约地址
        contract_abi = [
            {
                "inputs": [],
                "stateMutability": "nonpayable",
                "type": "constructor"
            },
            {
                "anonymous": False,
                "inputs": [
                    {
                        "indexed": True,
                        "internalType": "address",
                        "name": "userAddress",
                        "type": "address"
                    },
                    {
                        "indexed": False,
                        "internalType": "string",
                        "name": "key",
                        "type": "string"
                    },
                    {
                        "indexed": False,
                        "internalType": "string",
                        "name": "value",
                        "type": "string"
                    }
                ],
                "name": "AttributeUpdated",
                "type": "event"
            },
            {
                "anonymous": False,
                "inputs": [
                    {
                        "indexed": True,
                        "internalType": "address",
                        "name": "userAddress",
                        "type": "address"
                    },
                    {
                        "indexed": False,
                        "internalType": "string",
                        "name": "username",
                        "type": "string"
                    },
                    {
                        "indexed": False,
                        "internalType": "uint256",
                        "name": "userAge",
                        "type": "uint256"
                    }
                ],
                "name": "IdentityCreated",
                "type": "event"
            },
            {
                "anonymous": False,
                "inputs": [
                    {
                        "indexed": True,
                        "internalType": "address",
                        "name": "userAddress",
                        "type": "address"
                    }
                ],
                "name": "IdentityVerified",
                "type": "event"
            },
            {
                "inputs": [],
                "name": "createIdentity",
                "outputs": [],
                "stateMutability": "nonpayable",
                "type": "function"
            },
            {
                "inputs": [
                    {
                        "internalType": "address",
                        "name": "",
                        "type": "address"
                    }
                ],
                "name": "identities",
                "outputs": [
                    {
                        "internalType": "string",
                        "name": "username",
                        "type": "string"
                    },
                    {
                        "internalType": "address",
                        "name": "userAddress",
                        "type": "address"
                    },
                    {
                        "internalType": "bool",
                        "name": "isVerified",
                        "type": "bool"
                    },
                    {
                        "internalType": "uint256",
                        "name": "userAge",
                        "type": "uint256"
                    }
                ],
                "stateMutability": "view",
                "type": "function"
            },
            {
                "inputs": [
                    {
                        "internalType": "address",
                        "name": "",
                        "type": "address"
                    },
                    {
                        "internalType": "string",
                        "name": "",
                        "type": "string"
                    }
                ],
                "name": "identityAttributes",
                "outputs": [
                    {
                        "internalType": "string",
                        "name": "",
                        "type": "string"
                    }
                ],
                "stateMutability": "view",
                "type": "function"
            },
            {
                "inputs": [],
                "name": "owner",
                "outputs": [
                    {
                        "internalType": "address",
                        "name": "",
                        "type": "address"
                    }
                ],
                "stateMutability": "view",
                "type": "function"
            },
            {
                "inputs": [
                    {
                        "internalType": "string",
                        "name": "key",
                        "type": "string"
                    },
                    {
                        "internalType": "string",
                        "name": "value",
                        "type": "string"
                    }
                ],
                "name": "updateAttribute",
                "outputs": [],
                "stateMutability": "nonpayable",
                "type": "function"
            },
            {
                "inputs": [],
                "name": "verifyIdentity",
                "outputs": [],
                "stateMutability": "nonpayable",
                "type": "function"
            }
        ]  # 替换为你的智能合约 ABI

        # 使用合约 ABI 和地址创建合约实例
        digital_identity_contract = web3.eth.contract(address=contract_address, abi=contract_abi)

        user_address = '0x9Fe7b441f3011EDCb84Da228BCacA98a982F9E55'  # 替换为要查询的用户地址

        key = 'Ai_Federation_ID'  # 替换为要获取的属性键
        # 查询数字身份信息
        identity_attributes = digital_identity_contract.functions.identityAttributes(user_address, key).call()
        print(f'正在获取 key {key} of user {user_address}: {identity_attributes}')
        Ai_Federation_ID=identity_attributes

        key = 'Technique'  # 替换为要获取的属性键
        # 查询数字身份信息
        identity_attributes = digital_identity_contract.functions.identityAttributes(user_address, key).call()
        print(f'正在获取 key {key} of user {user_address}: {identity_attributes}')
        Technique = identity_attributes

        key = 'Training_Time'  # 替换为要获取的属性键
        # 查询数字身份信息
        identity_attributes = digital_identity_contract.functions.identityAttributes(user_address, key).call()
        print(f'正在获取 key {key} of user {user_address}: {identity_attributes}')
        Training_Time = identity_attributes

        # 查询数字身份信息
        identity_information = digital_identity_contract.functions.identities(user_address).call()
        identity_information.append(Ai_Federation_ID)
        identity_information.append(Technique)
        identity_information.append(Training_Time)
        if identity_information[0] == '0x0000000000000000000000000000000000000000':
            print('User Identity does not exist')
        else:
            print('User Identity Information:', identity_information)
            print('User Identity Information:', identity_information[0])
            print('User Identity Information:', identity_information[1])
            print('User Identity Information:', identity_information[2])
            print('User Identity Information:', identity_information[3])
            print('User Identity Information:', identity_information[4])
            print('User Identity Information:', identity_information[5])
            print('User Identity Information:', identity_information[6])

        return identity_information

if __name__ == '__main__':

    import sys

    app = QApplication(sys.argv)
    dialog = ConfigDialog()
    sys.exit(dialog.exec_())
