import pyautogui
from PyQt5.QtWidgets import QWidget, QDialog, QScrollArea, QGridLayout, QPushButton, QVBoxLayout, QFileDialog
from PyQt5.QtCore import QSettings, Qt, QUrl, pyqtSignal
from PyQt5.QtGui import QIcon
from ui.ui_MessageWidgetHuman import Ui_MessageWidgetHuman
import hashlib
import webbrowser
import emoji

# 主要用于发送附件
import asyncio
from typing import Optional

import sys
import logging
from pathlib import Path
from getpass import getpass
from argparse import ArgumentParser

import slixmpp
from slixmpp import JID
from slixmpp.exceptions import IqTimeout

log = logging.getLogger(__name__)
from Agent import Agent


class HttpUpload(slixmpp.ClientXMPP):

    """
    A basic client asking an entity if they confirm the access to an HTTP URL.
    """

    def __init__(
        self,
        jid: JID,
        password: str,
        recipient: JID,
        filename: Path,
        domain: Optional[JID] = None,
        encrypted: bool = False,
        url:str="",
    ):
        slixmpp.ClientXMPP.__init__(self, jid, password)

        self.recipient = recipient
        self.filename = filename
        self.domain = domain
        self.encrypted = encrypted

        self.add_event_handler("session_start", self.start)

    async def start(self, event):
        log.info('Uploading file %s...', self.filename)

        file_name = Path(self.filename).name
        try:
            upload_file = self['xep_0363'].upload_file
            if self.encrypted and not self['xep_0454']:
                print(
                    'The xep_0454 module isn\'t available. '
                    'Ensure you have \'cryptography\' '
                    'from extras_require installed.',
                    file=sys.stderr,
                )
                return
            elif self.encrypted:
                upload_file = self['xep_0454'].upload_file
            self.url = await upload_file(
                self.filename, domain=self.domain, timeout=10,
            )
        except IqTimeout:
            raise TimeoutError('Could not send message in time')
        log.info('Upload success!')

        log.info('Sending file to %s', self.recipient)
        html = (
            f'<body xmlns="http://www.w3.org/1999/xhtml">'
            f'<a href="{self.url}">{file_name}</a></body>'
        )
        print("html",html)
        message = self.make_message(mto=self.recipient, mbody=self.url, mhtml=html)
        message['oob']['url'] = self.url
        message.send()
        self.disconnect()


class EmojiDialog(QDialog):
    def __init__(self, parent=None):
        super(EmojiDialog, self).__init__(parent)
        self.setWindowTitle('选择表情包')

        current_mouse_position = pyautogui.position()
        x_position, y_position = current_mouse_position
        # 打印鼠标位置的 x 和 y 坐标
        print("当前鼠标位置 - X坐标：", x_position)
        print("当前鼠标位置 - Y坐标：", y_position)

        self.setGeometry(x_position-300, y_position-320, 600, 300)



        # 创建滚动区域
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        self.scroll_content = QWidget(scroll_area)
        self.scroll_content.setGeometry(0, 0, 600, 300)

        grid_layout = QGridLayout(self.scroll_content)
        self.emoji_buttons = []

        emojis = emoji.EMOJI_DATA.values()
        row, col = 0, 0

        for e in emojis:
            emoji_button = QPushButton(emoji.emojize(e['en']), self)
            emoji_button.clicked.connect(self.selectEmoji)
            grid_layout.addWidget(emoji_button, row, col)
            col += 1
            if col > 4:
                col = 0
                row += 1

        scroll_area.setWidget(self.scroll_content)

        layout = QVBoxLayout()
        layout.addWidget(scroll_area)
        self.setLayout(layout)

    def selectEmoji(self):
        button = self.sender()
        selected_emoji = button.text()
        self.accepted_emoji = selected_emoji
        self.accept()


class MessageBoxHuman(QWidget, Ui_MessageWidgetHuman):

    def __init__(self, parent, con, jid, name):
        super(MessageBoxHuman, self).__init__(parent)
        self.human_take_over=False
        self.jid = jid
        self.name = name
        self.con = con
        self.setupUi(self)

        self.messageBrowser.setPlainText("")
        self.messageBrowser.setOpenLinks(False)

        self.messageEdit.setFocus()

        self.fontButton.clicked.connect(self.showEmoji)
        self.sendButton.clicked.connect(self.sendMessage_click)
        self.videoButton.clicked.connect(self.sendfile)


        self.messageBrowser.anchorClicked.connect(self.openLink)





    def receiveMessage(self, event):
        message = f"""\n<strong><span style="color: darkblue; font-size:14px;">{self.name} :</span></strong> {event['body']}"""
        self.messageBrowser.append(message)



    def sendMessage_click(self):
        if self.messageEdit.toPlainText():
            self.sendMessage(self.messageEdit.toPlainText())
            self.messageEdit.clear()


    def sendMessage(self,content):
        if content:
            message = f"""\n<strong><em><span style="color: darkred; font-size:14px;">{self.tr("Me")} :</span></em></strong> {content}"""
            self.messageBrowser.append(message)
            self.con.send_message(self.jid, content)


    def startVideo(self):
        hash_value = hashlib.md5(self.jid.encode('utf-8')).hexdigest()
        url = f"http://jtalk.trunat.fr/jtalk/?{hash_value}"
        message = f"""\n<a href="{url}">Click here to join the videoChat</a>"""
        self.messageBrowser.append(message)
        self.con.send_message(self.jid, f"Join me for a video chat here: {url}")
        webbrowser.open(url)

    def sendfile(self):
        filepath=self.setOpenFileName()
        if filepath == "":
            return("")
        filename = Path(filepath).name
        if sys.platform == 'win32':
            asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
        # Setup the command line arguments.
        parser = ArgumentParser()
        parser.add_argument("-q", "--quiet", help="set logging to ERROR",
                            action="store_const",
                            dest="loglevel",
                            const=logging.ERROR,
                            default=logging.INFO)
        parser.add_argument("-d", "--debug", help="set logging to DEBUG",
                            action="store_const",
                            dest="loglevel",
                            const=logging.DEBUG,
                            default=logging.INFO)

        # JID and password options.
        parser.add_argument("-j", "--jid", dest="jid", default="wangwang@xabber.de",
                            help="JID to use")
        parser.add_argument("-p", "--password", dest="password", default="wangwang",
                            help="password to use")

        # Other options.
        parser.add_argument("-r", "--recipient", dest="recipient", required=False, default="yangyang@xabber.de",
                            help="Recipient JID")
        parser.add_argument("-f", "--file", dest="file", required=False, default=filepath,
                            help="File to send")
        parser.add_argument("--domain",
                            help="Domain to use for HTTP File Upload (leave out for your own server’s)")

        parser.add_argument("-e", "--encrypt", dest="encrypted",
                            help="Whether to encrypt", action="store_true",
                            default=False)

        args = parser.parse_args()

        # Setup logging.
        logging.basicConfig(level=args.loglevel,
                            format='%(levelname)-8s %(message)s')

        if args.jid is None:
            args.jid = JID(input("Username: "))
        if args.password is None:
            args.password = getpass("Password: ")

        domain = args.domain
        if domain is not None:
            domain = JID(domain)

        if args.encrypted:
            print(
                'You are using the --encrypt flag. '
                'Be aware that the transport being used is NOT end-to-end '
                'encrypted. The server will be able to decrypt the file.',
                file=sys.stderr,
            )

        xmpp = HttpUpload(
            jid=args.jid,
            password=args.password,
            recipient=JID(args.recipient),
            filename=Path(args.file),
            domain=domain,
            encrypted=args.encrypted,
        )
        xmpp.register_plugin('xep_0066')
        xmpp.register_plugin('xep_0071')
        xmpp.register_plugin('xep_0128')
        xmpp.register_plugin('xep_0363')
        try:
            xmpp.register_plugin('xep_0454')
        except slixmpp.plugins.base.PluginNotFound:
            log.error(
                'Could not load xep_0454. '
                'Ensure you have \'cryptography\' from extras_require installed.'
            )

        # Connect to the XMPP server and start processing XMPP stanzas.
        xmpp.connect()
        xmpp.process(forever=False)



        message = f"""\n<strong><em><span style="color: darkred; font-size:14px;">{self.tr("Me")} :</span></em></strong> <a href='{xmpp.url}'>{filename}</a>"""
        self.messageBrowser.append(message)




    def setOpenFileName(self):
        openFileNameLabel=""
        options = QFileDialog.Options()
        native = True
        if not native:
            options |= QFileDialog.DontUseNativeDialog
        fileName, _ = QFileDialog.getOpenFileName(self,
                "QFileDialog.getOpenFileName()", openFileNameLabel,
                "All Files (*);;Text Files (*.txt)", options=options)
        if fileName:
            openFileNameLabel=fileName
        print(openFileNameLabel)
        return openFileNameLabel

    def setOpenFileNames(self):
        openFilesPath = ""
        openFileNameLabel = ""
        options = QFileDialog.Options()
        native = True
        if not native:
            options |= QFileDialog.DontUseNativeDialog
        files, _ = QFileDialog.getOpenFileNames(self,
                "QFileDialog.getOpenFileNames()", openFilesPath,
                "All Files (*);;Text Files (*.txt)", options=options)
        if files:
            openFilesPath = files[0]
            openFileNamesLabel=("[%s]" % ', '.join(files))
        print(openFileNamesLabel)
        return openFileNamesLabel

    def showEmoji(self):
        dialog = EmojiDialog(self)
        if dialog.exec_() == QDialog.Accepted:
            selected_emoji = dialog.accepted_emoji
            print(selected_emoji)
            self.messageEdit.insertPlainText(selected_emoji)
            self.messageEdit.setFocus()

    def openLink(self, url):
        webbrowser.open(url.toString())
