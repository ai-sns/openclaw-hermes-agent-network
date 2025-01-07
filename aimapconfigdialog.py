import webbrowser

import PyQt5
from PyQt5 import QtWidgets
from PyQt5.QtCore import QDate, QSize, Qt, QRect, pyqtSignal
from PyQt5.QtGui import QIcon, QPixmap, QPainter, QPen, QPainterPath, QIntValidator
from PyQt5.QtWidgets import (QApplication, QCheckBox, QComboBox, QDateTimeEdit,
                             QDialog, QGridLayout, QGroupBox, QHBoxLayout, QLabel, QLineEdit,
                             QListView, QListWidget, QListWidgetItem, QPushButton, QSpinBox,
                             QStackedWidget, QVBoxLayout, QWidget, QDialogButtonBox, QRadioButton, QFileDialog, QSizePolicy, QMessageBox, QTextEdit, QPlainTextEdit)
from db.DBFactory import add_AiChatCfg, query_AiChatCfg, query_AiChatCfg_All, update_AiChatCfg, delete_AiChatCfg
from db.DBFactory import add_AgentCfg,query_AgentCfg,query_AgentCfg_All,update_AgentCfg,delete_AgentCfg
from agentconfigdialog import ConfigDialog as AgentConfigDialog
import configdialog_rc
import datetime
import random
import string
# from datetime import datetime



class ConfigDialog(QDialog):
    configured = pyqtSignal(str,str,str,str)
    connectcancel = pyqtSignal(str)

    def __init__(self, parent=None, ai_chat_cfg=None):
        super(ConfigDialog, self).__init__(parent)
        print("initialing.....")
        self.contentsWidget = QListWidget()
        self.contentsWidget.setViewMode(QListView.IconMode)
        self.contentsWidget.setIconSize(QSize(96, 84))
        self.contentsWidget.setMovement(QListView.Static)
        self.contentsWidget.setMaximumWidth(128)
        self.contentsWidget.setSpacing(12)
        # self.contentsWidget.setStyleSheet("QListWidget{margin-top: -150px; border: solid 1px red;}")

        self.ai_chat_cfg = ai_chat_cfg
        self.app =parent

        self.generalPage = GeneralPage(self.ai_chat_cfg,parent=self.app)
        self.userinfoPage = UserInfoPage(self.ai_chat_cfg)
        self.connectionPage = ConnectionPage(self.ai_chat_cfg)
        self.securityPage = SecurityPage(self.ai_chat_cfg)

        self.pagesWidget = QStackedWidget()
        self.pagesWidget.addWidget(self.generalPage)
        self.pagesWidget.addWidget(self.userinfoPage)
        self.pagesWidget.addWidget(self.connectionPage)
        self.pagesWidget.addWidget(self.securityPage)

        closeButton = QPushButton("Close")

        self.createIcons()#创建contentsWidget的列表，工具列表
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
        # mainLayout.addLayout(buttonsLayout)

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

        self.setWindowTitle("Ai漫游地球设置")

    def accept_close(self):
        print("accept")

        # generalpage
        account = self.generalPage.accountEdit.text()
        if not account:  # Check if plugins are empty
            QMessageBox.warning(self, "警告", "帐号不能为空。")
            return
        password = self.generalPage.passwordEdit.text()
        if not password:  # Check if plugins are empty
            QMessageBox.warning(self, "警告", "密码不能为空。")
            return
        nickname = self.generalPage.nicknameEdit.text()
        if not nickname:  # Check if plugins are empty
            QMessageBox.warning(self, "警告", "昵称不能为空。")
            return
        sign = self.generalPage.signEdit.toPlainText()
        if not sign:  # Check if plugins are empty
            QMessageBox.warning(self, "警告", "自我介绍不能为空。")
            return
        status = self.generalPage.statusCombo.currentText()

        """
               当QComboBox的选项变化时调用此方法
               :param index: 当前选中项的索引
               """
        # 获取当前选中的选项文本
        cur_nick_name = self.generalPage.cur_nick_name
        selected_name = self.generalPage.serverCombo.currentText()
        if selected_name=="N/A" and self.generalPage.humantakeoverYesRadio.isChecked()==False:
            QMessageBox.warning(self, "警告", "必须指定该帐号属于哪个Agent或设置为人类接管帐号。")
            return

        if self.generalPage.humantakeoverYesRadio.isChecked() == True:
            humantakeover=1
        else:
            humantakeover=0


        if self.generalPage.ai_chat_cfg:
            agent_belonged=query_AgentCfg(snsaccount= self.generalPage.ai_chat_cfg.account)
        else:
            agent_belonged=None

        if agent_belonged:
            update_AgentCfg(agent_belonged.id, snsaccount="N/A", snsnickname="N/A")
        if selected_name != "N/A":
            new_agent_belonged = query_AgentCfg(name=selected_name)
            self.generalPage.agent_belonged=new_agent_belonged
            if self.generalPage.ai_chat_cfg:
                snsaccount = self.generalPage.ai_chat_cfg.account
                snsnickname = self.generalPage.ai_chat_cfg.nickname
                update_AgentCfg(new_agent_belonged.id, snsaccount=snsaccount, snsnickname=snsnickname)

        # userinfopage
        name = self.userinfoPage.nameEdit.text()
        tborndate = self.userinfoPage.borndateEdit.dateTime().toString("yyyy-MM-dd")
        borndate = datetime.datetime.strptime(tborndate, "%Y-%m-%d")
        male_selected = self.userinfoPage.gender_male.isChecked()
        female_selected = self.userinfoPage.gender_female.isChecked()
        if male_selected == True:
            gender = 1
        else:
            gender = 0
        area = self.userinfoPage.areaCombo.currentText()
        city = self.userinfoPage.cityEdit.text()
        address = self.userinfoPage.addressEdit.text()
        mail = self.userinfoPage.mailEdit.text()
        imaccount = self.userinfoPage.imaccountEdit.text()
        phone = self.userinfoPage.phoneEdit.text()
        organization = self.userinfoPage.organizationEdit.text()
        title = self.userinfoPage.titleEdit.text()
        orgposition = self.userinfoPage.positionEdit.text()
        memo = self.userinfoPage.memoEdit.text()

        # connection
        serveraddress = self.connectionPage.serveraddressEdit.text()
        port = self.connectionPage.portEdit.text()
        ssl = self.connectionPage.sslCheckBox.isChecked()
        resource = self.connectionPage.resourceEdit.text()

        proxyused = self.connectionPage.proxyusedCheckBox.isChecked()
        proxyaddress = self.connectionPage.proxyaddressEdit.text()
        proxyport = self.connectionPage.proxyportEdit.text()
        proxyssl = self.connectionPage.proxysslCheckBox.isChecked()


        # Security
        savepasswordlocal = self.securityPage.savepasswordlocalCheckBox.isChecked()
        autoconnect = self.securityPage.autoconnectCheckBox.isChecked()
        sendreceipt = self.securityPage.sendreceiptCheckBox.isChecked()
        sendreadflag = self.securityPage.sendreadflagCheckBox.isChecked()
        sendchatstatus = self.securityPage.sendchatstatusCheckBox.isChecked()
        sendgroupchatstatus = self.securityPage.sendgroupchatstatusCheckBox.isChecked()
        agreeallfriendrequest = self.securityPage.agreeallfriendrequestCheckBox.isChecked()


        # update_AiChatCfg(1, name, memo, borndate, borncontry, language, gender, joinfederation, syncfederation, specialization, plugins, kms, prompt, snsaccount, islimittotalmessage, islimitmessagepp, totalmessages, ppmessages, readfile, writefile, deletefile, execfile, autorunrounds)
        if self.ai_chat_cfg == None:
            idstr = self.generate_random_id()
            add_AiChatCfg(idstr, account,password,nickname,sign,status,humantakeover,name,borndate,gender,area,city,address,mail,imaccount,phone,organization,title,orgposition,memo,serveraddress,port,ssl,resource,proxyused,proxyaddress,proxyport,proxyssl,savepasswordlocal,autoconnect,sendreceipt,sendreadflag,sendchatstatus,sendgroupchatstatus,agreeallfriendrequest)
            ai_chat_cfg=query_AiChatCfg(user_id=idstr)
            self.app.createToolBoxUnit_AiChat(ai_chat_cfg,1)
            self.app.toolBox_AiChat.setCurrentIndex(self.app.toolBox_AiChat.count()-2)
            self.ai_chat_cfg=ai_chat_cfg

            if selected_name != "N/A":
                new_agent_belonged = query_AgentCfg(name=selected_name)
                snsaccount = account
                snsnickname = nickname
                update_AgentCfg(new_agent_belonged.id, snsaccount=snsaccount, snsnickname=snsnickname)

        else:
            idstr = self.ai_chat_cfg.user_id
            update_AiChatCfg(self.ai_chat_cfg.id, account = account, password = password, nickname = nickname, sign = sign, status = status,humantakeover=humantakeover, name = name, borndate = borndate, gender = gender, area = area, city = city, address = address, mail = mail, imaccount = imaccount, phone = phone, organization = organization, title = title, orgposition = orgposition, memo = memo, serveraddress = serveraddress, port = port, ssl = ssl, resource = resource, proxyused = proxyused, proxyaddress = proxyaddress, proxyport = proxyport, proxyssl = proxyssl, savepasswordlocal = savepasswordlocal, autoconnect = autoconnect, sendreceipt = sendreceipt, sendreadflag = sendreadflag, sendchatstatus = sendchatstatus, sendgroupchatstatus = sendgroupchatstatus, agreeallfriendrequest = agreeallfriendrequest)
            tool_box_item = self.app.toolBox_AiChat.findChild(QWidget, idstr)
            self.app.toolBox_AiChat.setItemText(self.app.toolBox_AiChat.indexOf(tool_box_item),"漫游地球-"+nickname)

        if status=="离线":
            status ="0"
        elif humantakeover==1:
            status = "2"
        else:#在线
            status = "1"


        self.configured.emit(self.ai_chat_cfg.user_id, account, password,status)

        self.accept()
        self.close()

    def reject_close(self):
        print("reject")
        self.close()

    def showEvent(self, event):
        agent_belonged=None
        if self.ai_chat_cfg is not None:
            agent_belonged = query_AgentCfg(snsaccount=self.ai_chat_cfg.account)

        cur_nick_name = ""

        if agent_belonged:
            cur_nick_name = agent_belonged.name

        if cur_nick_name == "":
            self.generalPage.serverCombo.setCurrentText("N/A")
        else:
            self.generalPage.serverCombo.setCurrentText(cur_nick_name)


        super().showEvent(event)

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
        techButton.setText("个人资料")
        techButton.setTextAlignment(Qt.AlignHCenter)
        techButton.setFlags(Qt.ItemIsSelectable | Qt.ItemIsEnabled)

        queryButton = QListWidgetItem(self.contentsWidget)
        queryButton.setIcon(QIcon(':/images/update.png'))
        queryButton.setText("连接配置")
        queryButton.setTextAlignment(Qt.AlignHCenter)
        queryButton.setFlags(Qt.ItemIsSelectable | Qt.ItemIsEnabled)
        queryButton.setHidden(True)#暂时先隐藏

        updateButton = QListWidgetItem(self.contentsWidget)
        updateButton.setIcon(QIcon(':/images/query.png'))
        updateButton.setText("隐私安全")
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
    def __init__(self, ai_chat_cfg, parent=None):
        super(GeneralPage, self).__init__(parent)
        self.ai_chat_cfg = ai_chat_cfg
        self.app =parent

        self.avatar_label = ClickableAvatarLabel()
        self.avatar_label.setAlignment(Qt.AlignCenter)
        self.avatar_label.setFixedSize(70, 70)

        # 创建水平布局
        hLayout = QHBoxLayout()
        hLayout.addStretch()  # 在 avatar_label 前面添加伸展因子，将其推到水平中心
        hLayout.addWidget(self.avatar_label)
        hLayout.addStretch()  # 在 avatar_label 后面再添加一个伸展因子 必须前后都有

        self.avatar_label.clicked.connect(self.uploadAvatar)

        packagesGroup = QGroupBox("基本资料")

        self.accountLabel = QLabel("帐号:")
        self.accountEdit = QLineEdit()
        # self.accountEdit.setReadOnly(True)
        self.passwordLabel = QLabel("密码:")
        self.passwordEdit = QLineEdit()
        self.passwordEdit.setEchoMode(QLineEdit.Password)
        self.nicknameLabel = QLabel("昵称:")
        self.nicknameEdit = QLineEdit()
        self.signLabel = QLabel("自我介绍:")
        self.signEdit = QPlainTextEdit()
        line_height = self.signEdit.fontMetrics().height()  # 获取当前字体的一行高度
        self.signEdit.setFixedHeight(line_height * 3)

        self.statusLabel = QLabel("在线状态:")
        self.statusCombo = QComboBox()
        self.statusCombo.addItem("在线")
        self.statusCombo.addItem("离线")


        if ai_chat_cfg != None:
            self.accountEdit.setText(ai_chat_cfg.account)  # Assuming index 0 represents self.nameEdit text
            self.passwordEdit.setText(ai_chat_cfg.password)  # Assuming index 1 represents memoEdit text
            self.nicknameEdit.setText(ai_chat_cfg.nickname)  # Assuming index 2 represents self.dateEdit value
            self.signEdit.setPlainText(ai_chat_cfg.sign)  # Assuming index 3 represents self.bornareaCombo current text
            self.statusCombo.setCurrentText(ai_chat_cfg.status)  # Assuming index 4 represents self.self.languageCombo  current text
            agent_belonged = query_AgentCfg(snsaccount=ai_chat_cfg.account)
        else:
            agent_belonged = None

        layout_belong_to_agent = QHBoxLayout()
        belong_to_agent_title = QLabel("还没有帐号?")
        self.belong_to_agent = ClickableLabel(agent_belonged, self)
        self.belong_to_agent.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)  # 设置该标签顶到最左边

        layout_belong_to_agent.addWidget(belong_to_agent_title)
        layout_belong_to_agent.addWidget(self.belong_to_agent)


        self.agent_belonged=agent_belonged


        cur_nick_name = ""
        if agent_belonged:
            cur_nick_name = agent_belonged.name
        self.sns_nick_name_list = []

        configGroup = QGroupBox("该帐号属于哪个Agent:")

        self.serverLabel = QLabel("Agent:")
        self.serverCombo = QComboBox()
        ai_chat_records = query_AgentCfg_All()
        self.serverCombo.addItem("N/A")
        self.sns_nick_name_list.append("N/A")
        for ai_chat_record in ai_chat_records:
            ai_chat_nick_name = ai_chat_record.name
            self.serverCombo.addItem(ai_chat_nick_name)
            self.sns_nick_name_list.append(ai_chat_nick_name)


        if cur_nick_name == "":
            self.serverCombo.setCurrentText("N/A")
        else:
            self.serverCombo.setCurrentText(cur_nick_name)

        self.cur_nick_name=cur_nick_name

        serverLayout = QGridLayout()
        serverLayout.addWidget(self.serverLabel, 0, 0)
        serverLayout.addWidget(self.serverCombo, 0, 1,1,2)

        # 创建人类接管聊天的标签
        self.humantakeoverLabel = QLabel("人类接管帐号:")

        # 创建单选框选项：是
        self.humantakeoverYesRadio = QRadioButton("是")
        self.humantakeoverYesRadio.setObjectName("humantakeoverYesRadio")

        # 创建单选框选项：否
        self.humantakeoverNoRadio = QRadioButton("否")
        self.humantakeoverNoRadio.setObjectName("humantakeoverNoRadio")


        if ai_chat_cfg != None:
            if ai_chat_cfg.humantakeover==1:  # Assuming index 0 represents self.nameEdit text
                self.humantakeoverYesRadio.setChecked(True)
                self.humantakeoverNoRadio.setChecked(False)
            else:  # Assuming index 0 represents self.nameEdit text
                self.humantakeoverYesRadio.setChecked(False)
                self.humantakeoverNoRadio.setChecked(True)
        else:
            self.humantakeoverYesRadio.setChecked(False)
            self.humantakeoverNoRadio.setChecked(True)




        # 将标签和单选框添加到布局中
        serverLayout.addWidget(self.humantakeoverLabel, 1, 0)
        serverLayout.addWidget(self.humantakeoverYesRadio, 1, 1)  # 添加“是”选项
        serverLayout.addWidget(self.humantakeoverNoRadio, 1, 2)  # 添加“否”选项

        configLayout = QVBoxLayout()
        configLayout.addLayout(serverLayout)
        configGroup.setLayout(configLayout)
        self.serverCombo.currentIndexChanged.connect(self.on_combobox_changed)








        # startQueryButton = QPushButton("确认更改状态")

        packagesLayout = QGridLayout()
        packagesLayout.addWidget(self.accountLabel, 0, 0)
        packagesLayout.addWidget(self.accountEdit, 0, 1)
        packagesLayout.addWidget(self.passwordLabel, 1, 0)
        packagesLayout.addWidget(self.passwordEdit, 1, 1)
        packagesLayout.addWidget(self.nicknameLabel, 2, 0)
        packagesLayout.addWidget(self.nicknameEdit, 2, 1)
        packagesLayout.addWidget(self.signLabel, 3, 0)
        packagesLayout.addWidget(self.signEdit, 3, 1)
        packagesLayout.addWidget(self.statusLabel, 4, 0)
        packagesLayout.addWidget(self.statusCombo, 4, 1)


        packagesGroup.setLayout(packagesLayout)

        mainLayout = QVBoxLayout()

        mainLayout.addLayout(hLayout)

        mainLayout.addWidget(packagesGroup)
        mainLayout.addSpacing(6)
        mainLayout.addLayout(layout_belong_to_agent)
        mainLayout.addSpacing(40)
        mainLayout.addWidget(configGroup)
        mainLayout.addSpacing(12)
        # mainLayout.addWidget(startQueryButton)
        mainLayout.addStretch(1)

        self.setLayout(mainLayout)
        self.setAvatar(QPixmap("images/avatar.png"))

    def on_combobox_changed(self, index):
        """
        当QComboBox的选项变化时调用此方法
        :param index: 当前选中项的索引
        """
        # 获取当前选中的选项文本
        cur_nick_name=self.cur_nick_name
        selected_name = self.serverCombo.currentText()
        if selected_name !="N/A" and selected_name!=cur_nick_name:
            agent_belonged = query_AgentCfg(name=selected_name)
            if self.ai_chat_cfg:
                if agent_belonged.snsaccount != "N/A" and agent_belonged.snsaccount != self.accountEdit.text():
                    QMessageBox.information(self, '提示', '该Agent已经分配了其他社交帐号，请选择别的Agent!')
                    self.serverCombo.setCurrentText(cur_nick_name)
            else:
                if agent_belonged.snsaccount != "N/A":
                    QMessageBox.information(self, '提示', '该Agent已经分配了其他社交帐号，请选择别的Agent!')
                    self.serverCombo.setCurrentText(cur_nick_name)
            # else:
            #     self.serverCombo.setCurrentText(selected_name)
            #     snsaccount=self.ai_chat_cfg.account
            #     snsnickname = self.ai_chat_cfg.nickname
            #     update_AgentCfg(agent_belonged.id,snsaccount=snsaccount,snsnickname=snsnickname)





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


class UserInfoPage(QWidget):
    def __init__(self, agent, parent=None):
        super(UserInfoPage, self).__init__(parent)
        self.agent = agent

        packagesGroup = QGroupBox("个人资料")

        self.nameLabel = QLabel("姓名:")
        self.nameEdit = QLineEdit()
        self.borndateLabel = QLabel("生日:")
        self.borndateEdit = QDateTimeEdit(QDate.currentDate())
        self.genderLabel = QLabel("性别:")
        self.genderLayout = QHBoxLayout()
        self.gender_male = QRadioButton('男性')
        self.gender_female = QRadioButton('女性')
        self.genderLayout.addWidget(self.gender_male)
        self.genderLayout.addWidget(self.gender_female)
        self.areaLabel = QLabel("地区:")
        self.areaCombo = QComboBox()
        self.areaCombo.addItem("中国")
        self.areaCombo.addItem("美国")
        self.areaCombo.addItem("英国")
        self.areaCombo.addItem("法国")
        self.areaCombo.addItem("德国")
        self.cityLabel = QLabel("城市:")
        self.cityEdit = QLineEdit()
        self.addressLabel = QLabel("地址:")
        self.addressEdit = QLineEdit()
        self.mailLabel = QLabel("邮件:")
        self.mailEdit = QLineEdit()
        self.imaccountLabel = QLabel("其他IM:")
        self.imaccountEdit = QLineEdit()
        self.phoneLabel = QLabel("电话:")
        self.phoneEdit = QLineEdit()
        self.organizationLabel = QLabel("组织:")
        self.organizationEdit = QLineEdit()
        self.titleLabel = QLabel("头衔:")
        self.titleEdit = QLineEdit()
        self.positionLabel = QLabel("角色:")
        self.positionEdit = QLineEdit()
        self.memoLabel = QLabel("简介:")
        self.memoEdit = QLineEdit()

        if agent != None:
            self.nameEdit.setText(agent.name)  # Assuming index 0 represents self.nameEdit text
            self.borndateEdit.setDateTime(agent.borndate)  # Assuming index 2 represents self.dateEdit value
            if agent.gender == 1:
                self.gender_male.setChecked(True)  # Assuming index 5 represents self.radio_male checked state
                self.gender_female.setChecked(False)  # Assuming index 6 represents self.radio_female checked state
            else:
                self.gender_male.setChecked(False)  # Assuming index 5 represents self.radio_male checked state
                self.gender_female.setChecked(True)  # Assuming index 6 represents self.radio_female checked state
            self.areaCombo.setCurrentText(agent.area)  # Assuming index 3 represents self.bornareaCombo current text
            self.cityEdit.setText(agent.city)
            self.addressEdit.setText(agent.address)
            self.mailEdit.setText(agent.mail)
            self.imaccountEdit.setText(agent.imaccount)
            self.phoneEdit.setText(agent.phone)
            self.organizationEdit.setText(agent.organization)
            self.titleEdit.setText(agent.title)
            self.positionEdit.setText(agent.orgposition)
            self.memoEdit.setText(agent.memo)


        packagesLayout = QGridLayout()
        packagesLayout.addWidget(self.nameLabel, 0, 0)
        packagesLayout.addWidget(self.nameEdit, 0, 1)
        packagesLayout.addWidget(self.borndateLabel, 1, 0)
        packagesLayout.addWidget(self.borndateEdit, 1, 1)
        packagesLayout.addWidget(self.genderLabel, 2, 0)
        packagesLayout.addLayout(self.genderLayout, 2, 1)
        packagesLayout.addWidget(self.areaLabel, 3, 0)
        packagesLayout.addWidget(self.areaCombo, 3, 1)
        packagesLayout.addWidget(self.cityLabel, 4, 0)
        packagesLayout.addWidget(self.cityEdit, 4, 1)
        packagesLayout.addWidget(self.addressLabel, 5, 0)
        packagesLayout.addWidget(self.addressEdit, 5, 1)
        packagesLayout.addWidget(self.mailLabel, 6, 0)
        packagesLayout.addWidget(self.mailEdit, 6, 1)
        packagesLayout.addWidget(self.imaccountLabel, 7, 0)
        packagesLayout.addWidget(self.imaccountEdit, 7, 1)
        packagesLayout.addWidget(self.phoneLabel, 8, 0)
        packagesLayout.addWidget(self.phoneEdit, 8, 1)
        packagesLayout.addWidget(self.organizationLabel, 9, 0)
        packagesLayout.addWidget(self.organizationEdit, 9, 1)
        packagesLayout.addWidget(self.titleLabel, 10, 0)
        packagesLayout.addWidget(self.titleEdit, 10, 1)
        packagesLayout.addWidget(self.positionLabel, 11, 0)
        packagesLayout.addWidget(self.positionEdit, 11, 1)
        packagesLayout.addWidget(self.memoLabel, 12, 0)
        packagesLayout.addWidget(self.memoEdit, 12, 1)

        packagesGroup.setLayout(packagesLayout)

        mainLayout = QVBoxLayout()

        mainLayout.addWidget(packagesGroup)
        mainLayout.addSpacing(12)
        mainLayout.addStretch(1)

        self.setLayout(mainLayout)


class ConnectionPage(QWidget):
    def __init__(self, agent, parent=None):
        super(ConnectionPage, self).__init__(parent)
        self.agent = agent

        configGroup = QGroupBox("服务器设置:")

        self.serveraddressLabel = QLabel("地址:")
        self.serveraddressEdit = QLineEdit()
        self.portLabel = QLabel("端口:")
        self.portEdit = QLineEdit()
        intValidator = QIntValidator()
        self.portEdit.setValidator(intValidator)
        self.sslLabel = QLabel("ssl:")
        self.sslCheckBox = QCheckBox("启用")
        self.resourceLabel = QLabel("资源:")
        self.resourceEdit = QLineEdit()

        packagesLayout = QGridLayout()
        packagesLayout.addWidget(self.serveraddressLabel, 0, 0)
        packagesLayout.addWidget(self.serveraddressEdit, 0, 1)
        packagesLayout.addWidget(self.portLabel, 1, 0)
        packagesLayout.addWidget(self.portEdit, 1, 1)
        packagesLayout.addWidget(self.sslLabel, 2, 0)
        packagesLayout.addWidget(self.sslCheckBox, 2, 1)
        packagesLayout.addWidget(self.resourceLabel, 3, 0)
        packagesLayout.addWidget(self.resourceEdit, 3, 1)

        configGroup.setLayout(packagesLayout)

        updateGroup = QGroupBox("代理设置:")
        self.proxyusedLabel = QLabel("代理服务器:")
        self.proxyusedCheckBox = QCheckBox("启用")
        self.proxyaddressLabel = QLabel("地址:")
        self.proxyaddressEdit = QLineEdit()
        self.proxyportLabel = QLabel("端口:")
        self.proxyportEdit = QLineEdit()
        intValidator = QIntValidator()
        self.proxyportEdit.setValidator(intValidator)
        self.proxysslLabel = QLabel("ssl:")
        self.proxysslCheckBox = QCheckBox("启用")

        updateLayout = QGridLayout()
        updateLayout.addWidget(self.proxyusedLabel, 0, 0)
        updateLayout.addWidget(self.proxyusedCheckBox, 0, 1)
        updateLayout.addWidget(self.proxyaddressLabel, 1, 0)
        updateLayout.addWidget(self.proxyaddressEdit, 1, 1)
        updateLayout.addWidget(self.proxyportLabel, 2, 0)
        updateLayout.addWidget(self.proxyportEdit, 2, 1)
        updateLayout.addWidget(self.proxysslLabel, 3, 0)
        updateLayout.addWidget(self.proxysslCheckBox, 3, 1)


        updateGroup.setLayout(updateLayout)

        if agent != None:
            self.serveraddressEdit.setText(agent.serveraddress)
            self.portEdit.setText(str(agent.port))
            self.sslCheckBox.setChecked(agent.ssl)
            self.resourceEdit.setText(agent.resource)

            self.proxyusedCheckBox.setChecked(agent.proxyused)
            self.proxyaddressEdit.setText(agent.proxyaddress)
            self.proxyportEdit.setText(str(agent.proxyport))
            self.proxysslCheckBox.setChecked(agent.proxyssl)




        mainLayout = QVBoxLayout()
        mainLayout.addWidget(configGroup)
        mainLayout.addWidget(updateGroup)
        mainLayout.addStretch(1)

        self.setLayout(mainLayout)


class SecurityPage(QWidget):
    def __init__(self, agent, parent=None):
        super(SecurityPage, self).__init__(parent)
        self.agent = agent

        updateGroup = QGroupBox("隐私与安全:")
        self.savepasswordlocalCheckBox = QCheckBox("本地保存密码")
        self.autoconnectCheckBox = QCheckBox("启动时自动连接")
        self.sendreceiptCheckBox = QCheckBox("发送消息回执")
        self.sendreadflagCheckBox = QCheckBox("发送已读标志")
        self.sendchatstatusCheckBox = QCheckBox("发送聊天状态")
        self.sendgroupchatstatusCheckBox = QCheckBox("群聊中发送聊天状态")
        self.agreeallfriendrequestCheckBox = QCheckBox("同意所有联系人请求")

        packagesGroup = QGroupBox("修改密码")

        self.oldpasswordLabel = QLabel("老密码:")
        self.oldpasswordEdit = QLineEdit()
        self.oldpasswordEdit.setEchoMode(QLineEdit.Password)
        self.newpasswordLabel = QLabel("新密码:")
        self.newpasswordEdit = QLineEdit()
        self.newpasswordEdit.setEchoMode(QLineEdit.Password)
        self.confrimpasswordLabel = QLabel("确认密码:")
        self.confirmpasswordEdit = QLineEdit()
        self.confirmpasswordEdit.setEchoMode(QLineEdit.Password)

        if agent != None:
            self.savepasswordlocalCheckBox.setChecked(agent.savepasswordlocal)
            self.autoconnectCheckBox.setChecked(agent.autoconnect)
            self.sendreceiptCheckBox.setChecked(agent.sendreceipt)
            self.sendreadflagCheckBox.setChecked(agent.sendreadflag)
            self.sendchatstatusCheckBox.setChecked(agent.sendchatstatus)
            self.sendgroupchatstatusCheckBox.setChecked(agent.sendgroupchatstatus)
            self.agreeallfriendrequestCheckBox.setChecked(agent.agreeallfriendrequest)


        startUpdateButton = QPushButton("修改密码")

        updateLayout = QGridLayout()
        updateLayout.addWidget(self.savepasswordlocalCheckBox, 0, 0)
        updateLayout.addWidget(self.autoconnectCheckBox, 0, 1)
        updateLayout.addWidget(self.sendreceiptCheckBox, 1, 0)
        updateLayout.addWidget(self.sendreadflagCheckBox, 1, 1)
        updateLayout.addWidget(self.sendchatstatusCheckBox, 2, 0)
        updateLayout.addWidget(self.sendgroupchatstatusCheckBox, 2, 1)
        updateLayout.addWidget(self.agreeallfriendrequestCheckBox, 3, 0)
        updateGroup.setLayout(updateLayout)
        updateGroup.setHidden(True)#暂时隐藏

        passwordLayout = QGridLayout()
        passwordLayout.addWidget(self.oldpasswordLabel, 0, 0)
        passwordLayout.addWidget(self.oldpasswordEdit, 0, 1)
        passwordLayout.addWidget(self.newpasswordLabel, 1, 0)
        passwordLayout.addWidget(self.newpasswordEdit, 1, 1)
        passwordLayout.addWidget(self.confrimpasswordLabel, 2, 0)
        passwordLayout.addWidget(self.confirmpasswordEdit, 2, 1)
        packagesGroup.setLayout(passwordLayout)

        mainLayout = QVBoxLayout()
        mainLayout.addWidget(updateGroup)
        mainLayout.addWidget(packagesGroup)

        mainLayout.addSpacing(12)
        mainLayout.addWidget(startUpdateButton)
        mainLayout.addStretch(1)

        self.setLayout(mainLayout)


class ClickableAvatarLabel(QLabel):
    clicked = PyQt5.QtCore.pyqtSignal()

    def mousePressEvent(self, event):
        self.clicked.emit()


class ClickableLabel(QLabel):
    clicknum=0
    def __init__(self, agent,parent=None):
        self.agent=agent
        self.app = parent.app
        self.parent = parent
        text="注册"
        super().__init__(text)
        self.setTextInteractionFlags(Qt.TextSelectableByMouse)
        self.setStyleSheet("QLabel { color: blue; text-decoration: underline;font-family:微软雅黑;font-size:8pt;cursor: pointer;} QLabel:hover { color: red; text-decoration: underline;font-family:微软雅黑;font-size:8pt;cursor: pointer;}")

    def changeEvent(self, event):
        print(self.text())


    def mousePressEvent(self, event):
        webbrowser.open("https://compliance.conversations.im/")

if __name__ == '__main__':
    import sys

    app = QApplication(sys.argv)
    dialog = ConfigDialog()
    sys.exit(dialog.exec_())
