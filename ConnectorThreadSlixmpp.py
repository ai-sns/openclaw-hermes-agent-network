import time
from PyQt5.QtCore import QSettings, QThread, pyqtSignal
from PyQt5.QtWidgets import QMessageBox
from jabber import STATUS
import xmpp
import sys

import slixmpp
import asyncio
import sys


class MyXMPPClient(slixmpp.ClientXMPP):
    def __init__(self, jid, password, recipient_jid, message):
        super().__init__(jid, password)
        self.recipient_jid = recipient_jid
        self.message = message
        self.add_event_handler("session_start", self.on_session_start)
        self.add_event_handler("message", self.receivemessage)
    def receivemessage(self, msg):
        print(msg)
        print(msg['type'])
        print(msg['body'])
        if msg['type'] in ('chat', 'normal'):
            msg.reply("你好，我是使用Slixmpp发送消息的机器人。").send()
    async def on_session_start(self, event):
        self.send_presence()
        await self.get_roster()
        self.send_message(
            mto=self.recipient_jid,
            mbody=self.message,
            mtype='chat'
        )
    def isConnected(self):
        return True
        #self.disconnect()

class ConnectorThread(QThread):
    connected = pyqtSignal()
    error = pyqtSignal(str, str)
    debug = pyqtSignal(str)
    message = pyqtSignal(object)
    presence = pyqtSignal(str, str, str)
    presence = pyqtSignal()
    subscriptionRequest = pyqtSignal(object)
    addBuddySig = pyqtSignal()
    rosterChange = pyqtSignal(object)
    connectSignal = pyqtSignal()

    def __init__(self, status):
        print("cjrok2")
        super(ConnectorThread, self).__init__()
        self.status = status

    def run(self):
        print("cjrok3")


        if  self.connect():
        #if self.connectslixmpp():
            print("connect()1111")
            self.Terminated = False
            self.connected.emit()
        else:
            print("connect()1111")
            self.Terminated = False
            self.connected.emit()

        while not self.Terminated:
            self.jabber.Process(1)
            #time.sleep(2.0)
        #sys.stderr.write('Thread correctly stopped' + str(self.Terminated) + '\n\n')

    def connectbak(self):
        print("cjrok")
        settings = QSettings("Trunat", "PyTalk")
        settings.beginGroup("Connection")

        self.userID = str(settings.value("userID", ""))
        self.password = str(settings.value("password", ""))
        self.server = str(settings.value("server", ""))
        self.useSSL = settings.value("useSSL", True, type=bool)

        if self.useSSL:
            self.port = settings.value("port", 5223, type=int)
        else:
            self.port = settings.value("port", 5222, type=int)

        self.ressource = str(settings.value("ressource", "PyTalk"))

        settings.endGroup()

        self.jid = xmpp.protocol.JID(self.userID)
        self.jabber = xmpp.Client(self.jid.getDomain(), debug=[])

        if self.server:
            server = (self.server, self.port)
        else:
            server = None
        print("connecting cjrok")
        IP = "xabber.de"
        PORT = 5222

        connection = self.jabber.connect(server=(IP, PORT))
        print("connecting cjrok222")
        if not connection:
            self.error.emit("Connection Error", "Could not connect")
            return False
        sys.stderr.write('Connected with %s\n' % connection)
        print("connecting cjrok33")
        #auth = self.jabber.auth(self.jid.getNode(), self.password, self.ressource)
        auth = self.jabber.auth("wangwang","wangwang")
        print("connecting cjrok4444")
        if not auth:
            self.error.emit("Authentication Error", "Could not authenticate")
            return False
        sys.stderr.write('Authenticate using %s\n' % auth)
        print("connecting cjrok5555")
        self.register_handlers()
        print("connecting cjrok666")
        self.jabber.sendInitPresence(requestRoster=1)
        print("connecting cjrok777")

        return connection

    def messagehandle(sess, mess):
        nick = mess.getFrom().getResource()
        text = mess.getBody()
        print("[Message]{}:{}".format(nick, text))

    def connecthandle(self):
        IP = "xabber.de"
        PORT = 5222
        from_user = "wangwang"
        password = "wangwang"
        client = xmpp.Client(IP)  # 是否开启debug
        client.connect(server=(IP, PORT))
        client.auth(from_user, password)
        client.RegisterHandler("message", self.xmpp_message)
        client.sendInitPresence()
        self.jabber = client


    def connect(self):
        print("inconncttreadconnect")
        IP = "xabber.de"
        PORT = 5222
        from_user = "wangwang"
        password = "wangwang"
        client = xmpp.Client(IP)  # 是否开启debug
        self.jabber=client
        # connection=client.connect(server=(IP, PORT))
        # client.auth(from_user, password)
        # client.RegisterHandler("message", self.message)
        # client.sendInitPresence()

        to_user = ["chenchen@xabber.de"]
        msg = "测试！"

        client.connect(server=(IP, PORT))
        #client.auth(from_user, password, "botty")
        client.auth(from_user, password)

        client.sendInitPresence()
        # message = xmpp.Message(to_user[0], msg, typ="chat")
        # client.send(message)
        client.RegisterHandler("message", self.xmpp_message)

        # self.register_handlers()
        # print("connecting cjrok666")
        # self.jabber.sendInitPresence(requestRoster=1)





        # while 1:
        #       client.Process(1)
        # return connection

    def connectokcanused(self):
        print("inconncttreadconnect")
        IP = "xabber.de"
        PORT = 5222
        from_user = "wangwang"
        password = "wangwang"
        client = xmpp.Client(IP)  # 是否开启debug
        self.jabber = client
        # connection=client.connect(server=(IP, PORT))
        # client.auth(from_user, password)
        # client.RegisterHandler("message", self.message)
        # client.sendInitPresence()

        to_user = ["chenchen@xabber.de"]
        msg = "测试！"

        client.connect(server=(IP, PORT))
        client.auth(from_user, password, "botty")
        client.sendInitPresence()
        message = xmpp.Message(to_user[0], msg, typ="chat")
        client.send(message)
        client.RegisterHandler("message", self.xmpp_message)

        # while 1:
        #       client.Process(1)
        # return connection

    def onlysend(self):
        print("onlysend")
        IP = "xabber.de"
        PORT = 5222
        from_user = "wangwang"
        password = "wangwang"
        #client = xmpp.Client(IP)  # 是否开启debug
        #self.jabber=client
        # connection=client.connect(server=(IP, PORT))
        # client.auth(from_user, password)
        # client.RegisterHandler("message", self.message)
        # client.sendInitPresence()

        to_user = ["chenchen@xabber.de"]
        msg = "我的回复-测试！"

        # client.connect(server=(IP, PORT))
        # client.auth(from_user, password, "botty")
        # client.sendInitPresence()
        message = xmpp.Message(to_user[0], msg, typ="chat")
        self.jabber.send(message)
        #client.RegisterHandler("message", self.xmpp_message)



    def connectslixmpp(self):
        print("connect slixmpp")
        if sys.platform == 'win32':
            asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
        asyncio.set_event_loop(asyncio.new_event_loop())#需要创建一个loop，否则跑不起来，会报没有loop
        jid = 'wangwang@xabber.de'
        print("inconncttreadconnect")
        IP = "xabber.de"
        PORT = 5222
        jid = 'wangwang@xabber.de'
        password = 'wangwang'
        recipient_jid = 'chenchen@xabber.de'
        message = 'Hello, this is a test message from slixmpp.'
        client = MyXMPPClient(jid, password, recipient_jid, message)
        self.jabber = client
        self.jabber.connect()

        print("onlysend222aaaa")

        self.jabber.send_message(
            mto="chenchen@xabber.de",
            mbody="我的回复aaaabbb-测试！",
            mtype='chat'
        )
        print("sndendaaaa")

        # self.Terminated = False
        # self.connected.emit()

        self.roster = self.jabber.get_roster()

        self.jabber.process(forever=False)
        asyncio.sleep(1)

        # self.jabber.process(1)
        print("end connect slixmpp")
        # return True
        # client.connect()
        # client.process(forever=False)

        # connection=client.connect(server=(IP, PORT))
        # client.auth(from_user, password)
        # client.RegisterHandler("message", self.message)
        # client.sendInitPresence()








        # while 1:
        #       client.Process(1)
        # return connection
    def onlysendslixmpp(self):
        print("onlysend222")


        self.jabber.send_message(
            mto="chenchen@xabber.de",
            mbody="我的回复-测试！",
            mtype='chat'
        )
        print("sndend")


    def messagebak(sess, mess):
        print("receiving msg..")
        nick = mess.getFrom().getResource()
        text = mess.getBody()
        print("[Message]{}:{}".format(nick, text))

    def disconnect(self):
        #self.onlysend()
        self.Terminated = True
        if self.jabber.isConnected():
            self.jabber.disconnect()

    def register_handlers(self):
        self.jabber.RegisterHandler('message', self.xmpp_message)
        self.jabber.RegisterHandler("iq", self.handle_version, typ="get", ns=xmpp.NS_VERSION)
        self.jabber.RegisterHandler("iq", self.handle_disco_info, typ="get", ns=xmpp.NS_DISCO_INFO)
        self.jabber.RegisterHandler("iq", self.rosterChange, typ="set", ns=xmpp.NS_ROSTER)
        self.jabber.RegisterHandler("presence", self.subscriptionRequest, typ="subscribe")
        self.jabber.RegisterHandler("presence", self.addBuddy, typ="subscribed")
        self.jabber.RegisterHandler("presence", self.presence)
        self.jabber.RegisterHandler("iq", self.request)
        self.jabber.RegisterDisconnectHandler(lambda: self.connectSignal.emit())

    def request(self, con, packet):
        self.debug.emit(str(packet) + "\n\n")

    def xmpp_message(self, con, event):
        print("in xmpp_message")
        self.debug.emit(str(event) + "\n\n")
        type_ = event.getType()
        if type_ and type_ in ['message', 'chat']:
            message = event.getBody()
            print("receiving msg..")
            nick = event.getFrom().getResource()
            text = event.getBody()
            print("[Message]{}:{}".format(nick, text))

            if message:
                 self.message.emit(event)

    def send_message(self, tojid, message):
        print("cjrok send_message")
        m = xmpp.protocol.Message(to=tojid, body=message, typ='chat')
        self.debug.emit(str(m) + "\n\n")
        self.jabber.send(m)

    def changeStatus(self, showId, status):
        p = xmpp.protocol.Presence()
        p.setShow(STATUS[showId])
        if status:
            p.setStatus(status)
        if showId == STATUS.available:
            p.setPriority(5)
        self.jabber.send(p)
        self.debug.emit(str(p) + "\n\n")

    def handle_version(self, con, iq):
        self.debug.emit(str(iq) + "\n")
        reply = iq.buildReply('result')
        reply.T.query.addChild(name="name", payload=settings.APPNAME)
        reply.T.query.addChild(name="version", payload=settings.VERSION)
        if platform.mac_ver()[0]:
            plateforme = "Mac OS %s" % platform.mac_ver()[0]
        elif platform.win32_ver()[0]:
            plateforme = "Windows %s" % platform.win32_ver()[0]
        else:
            plateforme = "%s %s" % (platform.uname()[0], platform.uname()[2])
        reply.T.query.addChild(name="os", payload=plateforme)
        self.debug.emit(str(reply) + "\n")
        self.jabber.send(reply)

    def handle_disco_info(self, con, iq):
        self.debug.emit(str(iq) + "\n")
        reply = iq.buildReply('result')
        reply.T.query.addChild(name="feature", attrs={'var': 'jabber:iq:version'})
        self.debug.emit(str(reply) + "\n")
        self.jabber.send(reply)

    # def getRoster(self):
    #     #pass
    #     self.roster = self.jabber.getRoster()
    #     return self.roster.getItems()

    def getRoster(self):
        #pass
        # self.roster = self.jabber.get_roster()#slixmmp
        print("in getRoster")
        self.roster = self.jabber.getRoster()
        print("self.roster",self.roster)
        return self.roster.getItems()

    def getGroups(self, jid):
        print("self.roster.getGroups",self.roster.getGroups)
        return self.roster.getGroups(jid) if self.roster.getGroups(jid) else ['Buddies']

    def getName(self, jid):
        return self.roster.getName(jid)

    def getStatus(self, jid):
        pass

    def presence(self, con, presence):
        self.debug.emit(str(presence) + "\n")
        jid = presence.getFrom().getStripped()
        if presence.getType() == "unavailable":
            self.presence.emit(jid, str(STATUS.unavailable))
        if not presence.getType():
            if not presence.getShow():
                self.presence.emit(jid, str(STATUS.available), presence.getStatus())
            else:
                status = presence.getShow()
                if status == "chat":
                    stat = STATUS.chat
                elif status == "dnd":
                    stat = STATUS.dnd
                elif status == "away":
                    stat = STATUS.away
                elif status == "xa":
                    stat = STATUS.xa
                else:
                    stat = STATUS.available
                self.presence.emit(jid, stat, presence.getStatus())

    def subscriptionRequest(self, con, presence):
        self.debug.emit(str(presence) + "\n")
        self.subscriptionRequest.emit(presence)

    def addBuddy(self, con, presence):
        self.debug.emit(str(presence) + "\n")
        self.addBuddySig.emit(presence)

    def rosterChange(self, con, iq):
        self.rosterChange.emit(iq)

    def isConnected(self):
        return self.jabber.isConnected(self)
