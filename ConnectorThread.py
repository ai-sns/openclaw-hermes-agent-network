import time
from PyQt5.QtCore import QSettings, QThread, pyqtSignal
from PyQt5.QtWidgets import QMessageBox
from jabber import STATUS
import xmpp
import sys

import slixmpp
import asyncio
import sys


class SendMsgBot(slixmpp.ClientXMPP):

    """
    A basic Slixmpp bot that will log in, send a message,
    and then log out.
    """

    def __init__(self, jid, password, recipient, message):
        slixmpp.ClientXMPP.__init__(self, jid, password)

        # The message we wish to send, and the JID that
        # will receive it.
        self.recipient = recipient
        self.msg = message

        # The session_start event will be triggered when
        # the bot establishes its connection with the server
        # and the XML streams are ready for use. We want to
        # listen for this event so that we we can initialize
        # our roster.
        self.add_event_handler("session_start", self.start)

    async def start(self, event):
        """
        Process the session_start event.

        Typical actions for the session_start event are
        requesting the roster and broadcasting an initial
        presence stanza.

        Arguments:
            event -- An empty dictionary. The session_start
                     event does not provide any additional
                     data.
        """
        self.send_presence()
        await self.get_roster()

        self.send_message(mto=self.recipient,
                          mbody=self.msg,
                          mtype='chat')

        self.disconnect()

    def sendmessage(self,recipient,msg):
        self.send_message(mto=recipient,
                          mbody=msg,
                          mtype='chat')
        self.disconnect()



class MyXMPPClient(slixmpp.ClientXMPP):

    def __init__(self, jid, password, recipient_jid, message, con):
        super().__init__(jid, password)
        self.con = con
        self.recipient_jid = recipient_jid
        self.message = message
        self.add_event_handler("session_start", self.on_session_start)
        # self.add_event_handler("message", self.receivemessage)
        # self.add_event_handler("message", self.con.xmpp_message)
        self.add_event_handler("presence_subscribe", self.presence_subscribe)
        self.register_plugin('xep_0030')  # Service Discovery
        self.register_plugin('xep_0199')  # XMPP Ping
        # 设置心跳间隔（以秒为单位）
        self.heartbeat_interval = 3
        self.heartbeat_task = None
        # 注册roster更新事件处理器
        self.add_event_handler("roster_update", self.roster_update)
        self.rosternames = []
        self.con = con

    async def presence_subscribe(self, presence):
        # 获取订阅请求的 JID
        print("the presence:",presence)
        print("the status:", presence['status'])
        from_jid = presence['from']
        request_msg=presence['status']
        print(f"Subscription request from: {from_jid}")

        self.con.friend_subscribe_request.emit(f"{from_jid}",request_msg)


        # 接受订阅请求
        # self.send_presence(pto=from_jid, ptype='subscribed')
        # self.send_presence(pto=from_jid, ptype='subscribe')
        # print(f"Accepted subscription request from: {from_jid}")

        # 如果需要拒绝订阅请求，可以使用下面的代码而不是上面的接受代码
        # self.send_presence(pto=from_jid, ptype='unsubscribed')
        # print(f"Refused subscription request from: {from_jid}")

    def receivemessage(self, msg):
        print(msg)
        print(msg['type'])
        print(msg['body'])
        if msg['type'] in ('chat', 'normal'):
            msg.reply("你好，我是使用Slixmpp发送消息的机器人。").send()

    def sendmessage(self, tojid, msg):
        print("im in sendmessage presence,going")
        self.send_presence()
        self.send_message(
            mto=tojid,
            mbody=msg,
            mtype='chat'
        )

    async def on_session_start(self, event):
        self.send_presence()
        await self.get_roster()
        # 启动心跳任务
        self.heartbeat_task = asyncio.create_task(self.heartbeat())
        self.send_message(
            mto=self.recipient_jid,
            mbody=self.message,
            mtype='chat'
        )

    def roster_update(self, event):
        # 打印所有联系人
        print("Roster received:")
        groups = self.client_roster.groups()
        print("groups", groups)
        rosters = self.client_roster
        print("self.rosters", rosters)
        rosternames = list(self.client_roster.keys())
        print("rosternames", rosternames)
        print("rostername[0]", rosternames[0])
        self.rosternames = rosternames
        for group in groups:
            for jid in groups[group]:
                print("self.client_roster[jid]", self.client_roster[jid])
                # status = "Online" if self.client_roster[jid]['presence'] else "Offline"
                # print(f" - {jid} ({status})")
        self.con.connected.emit()

    def isConnected(self):
        return self.is_connected()

    def isConnecting(self):
        return self.is_connecting()

    async def heartbeat(self):
        while True:
            # 发送 Ping 消息到服务器
            try:
                await self['xep_0199'].ping()
                print("Ping sent to the server.")
            except Exception as e:
                print(f"Failed to ping server: {e}")

            # 等待指定的心跳间隔
            await asyncio.sleep(self.heartbeat_interval)

    def stop_heartbeat(self):
        if self.heartbeat_task is not None:
            self.heartbeat_task.cancel()
            self.heartbeat_task = None


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
    friend_subscribe_request = pyqtSignal(str,str)

    def __init__(self, status,jid,password):
        print("cjrok2")
        super(ConnectorThread, self).__init__()
        self.status = status
        self.jid = jid
        self.password = password
        self.xmpp=None


    def run(self):
        print("cjrok3")

        # if  self.connect():#xmpp模式
        if self.connectslixmpp():
            print("connect()1111")
            self.Terminated = False
            # self.connected.emit()
            self.connect()
        else:
            print("connect()1111222")
            self.Terminated = False
            # self.connected.emit()
            # self.connect()

        # while not self.Terminated:
        # self.jabber.Process(1)#xmpp
        # await asyncio.sleep(0)
        self.jabber.process(forever=False)  # slixmmp
        # time.sleep(1)
        # await asyncio.sleep(0)
        # time.sleep(2.0)
        # sys.stderr.write('Thread correctly stopped' + str(self.Terminated) + '\n\n')

    def connect(self):
        print("inconncttreadconnect")
        IP = "xabber.de"
        PORT = 5222
        from_user = self.jid.split('@')[0]
        password = self.password
        client = xmpp.Client(IP)  # 是否开启debug
        self.jabber_xmpp = client
        # connection=client.connect(server=(IP, PORT))
        # client.auth(from_user, password)
        # client.RegisterHandler("message", self.message)
        # client.sendInitPresence()

        to_user = ["chenchen@xabber.de"]
        msg = "测试！"

        client.connect(server=(IP, PORT))
        # client.auth(from_user, password, "botty")
        client.auth(from_user, password)

        client.sendInitPresence()
        # message = xmpp.Message(to_user[0], msg, typ="chat")
        # client.send(message)
        # client.RegisterHandler("message", self.xmpp_message)

        # self.register_handlers()
        # print("connecting cjrok666")
        # self.jabber.sendInitPresence(requestRoster=1)

        # while 1:
        #       client.Process(1)
        # return connection

    def connectslixmpp(self):
        print("connect slixmpp--v2")
        if sys.platform == 'win32':
            asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
        asyncio.set_event_loop(asyncio.new_event_loop())  # 需要创建一个loop，否则跑不起来，会报没有loop

        print("inconncttreadconnect")
        IP = "xabber.de"
        PORT = 5222
        jid = self.jid
        password = self.password
        recipient_jid = 'chenchen@xabber.de'
        message = 'Hello, this is a test message from slixmpp.'
        client = MyXMPPClient(jid, password, recipient_jid, message, self)
        self.jabber = client



        client.connect()

        print("onlysend222aaaa")

        client.send_message(
            mto="chenchen@xabber.de",
            mbody="我的回复aaaabbb-测试！",
            mtype='chat'
        )
        print("sndendaaaa")

        self.Terminated = False
        # self.connected.emit()

        # client.process(forever=True)
        asyncio.sleep(1)
        # self.jabber.process(1)
        client.add_event_handler("message", self.xmpp_message)
        print("end connect slixmpp")
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
        # self.onlysend()
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

    def xmpp_message(self, msg):
        print(msg)
        print(msg['type'])
        print(msg['body'])
        if msg['type'] in ('chat', 'normal'):
            message = msg['body']
            print("receiving msg..")
            nick = "wangwangget:"
            text = msg['body']
            print("[Message]{}:{}".format(nick, text))

            if message:
                self.message.emit(msg)

    def xmpp_messagebak(self, con, event):
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

    def send_messagebak(self, tojid, message):
        print("cjrok send_message")
        self.jabber.sendmessage(tojid, message)
        print("sndendaaaa")

    def send_message_xmpp(self, tojid, message):
        print("cjrok send_message by xmpp")
        m = xmpp.protocol.Message(to=tojid, body=message, typ='chat')
        self.debug.emit(str(m) + "\n\n")
        self.jabber_xmpp.send(m)

    def send_message(self, tojid, message):
        print("cjrok send_message by slixmppnew")

        self.jabber.send_message(
            mto=tojid,
            mbody=message,
            mtype='chat'
        )



    def send_message_slixmppbak(self, tojid, message):
        print("cjrok send_message by slixmpp")
        jid = self.jid
        password = self.password
        # recipient = "yangyang@xabber.de"
        # message = "Hello from slixmpp!"
        if self.xmpp==None:
            xmpp = SendMsgBot(jid, password, tojid, message)
        else:
            xmpp =self.xmpp
            xmpp.sendmessage(tojid, message)
        xmpp.register_plugin('xep_0030')  # Service Discovery
        xmpp.register_plugin('xep_0199')  # XMPP Ping

        # Connect to the XMPP server and start processing XMPP stanzas.
        xmpp.connect()
        xmpp.process(forever=False)


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

    def getRoster_xmpp(self):
        # pass
        # self.roster = self.jabber.get_roster()#slixmmp
        print("in getRoster")
        self.roster = self.jabber.getRoster()
        print("self.roster", self.roster)
        return self.roster.getItems()

    def getRoster(self):
        # pass
        # self.roster = self.jabber.get_roster()#slixmmp
        print("in getRoster")
        rosternames = self.jabber.rosternames
        print("self.roster", rosternames)
        return rosternames

    def getGroups_xmpp(self, jid):
        print("self.roster.getGroups", self.roster.getGroups)  # self.client_roster
        return self.roster.getGroups(jid) if self.roster.getGroups(jid) else ['Buddies']

    def getGroups(self, jid):

        return self.jabber.client_roster[jid]['groups'] if self.jabber.client_roster[jid]['groups'] else ['Buddies']

    def getName(self, jid):
        # return self.roster.getName(jid)#xmpp

        return self.jabber.client_roster[jid]['name']

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
        # return False

        if self.jabber:
            return self.jabber.isConnected()
        else:
            return False

    def accept_subscription(self,jid):
        # 接受订阅请求
        self.jabber.send_presence(pto=jid, ptype='subscribed')
        self.jabber.send_presence(pto=jid, ptype='subscribe')


        # 如果需要拒绝订阅请求，可以使用下面的代码而不是上面的接受代码
        # self.send_presence(pto=from_jid, ptype='unsubscribed')
        # print(f"Refused subscription request from: {from_jid}")

    def reject_subscription(self, jid):
        # 接受订阅请求
        self.jabber.send_presence(pto=jid, ptype='unsubscribed')
        self.jabber.send_presence(pto=jid, ptype='unsubscribe')

