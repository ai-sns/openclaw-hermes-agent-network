import copy
import zipfile
import shutil
import sys
import time
from PyQt5 import QtCore, QtGui, QtWidgets

import math

from PyQt5.QtCore import (pyqtSignal, QLineF, QPointF, QRect, QRectF, QSize,
                          QSizeF, Qt)
from PyQt5.QtGui import (QBrush, QColor, QFont, QIcon, QIntValidator, QPainter,
                         QPainterPath, QPen, QPixmap, QPolygonF)
from PyQt5.QtWidgets import (QAction, QApplication, QButtonGroup, QComboBox,
                             QFontComboBox, QGraphicsItem, QGraphicsLineItem, QGraphicsPolygonItem,
                             QGraphicsScene, QGraphicsTextItem, QGraphicsView, QGridLayout,
                             QHBoxLayout, QLabel, QMainWindow, QMenu, QMessageBox, QSizePolicy,
                             QToolBox, QToolButton, QWidget, QToolBar, QDialog, QTabWidget, QLineEdit, QVBoxLayout)

from PyQt5.QtCore import QDir, Qt
from PyQt5.QtGui import QFont, QPalette
from PyQt5.QtWidgets import (QApplication, QCheckBox, QColorDialog, QDialog,
                             QErrorMessage, QFileDialog, QFontDialog, QFrame, QGridLayout,
                             QInputDialog, QLabel, QLineEdit, QMessageBox, QPushButton, QStatusBar)

from PyQt5.QtCore import QFile, QFileInfo, Qt
from PyQt5.QtGui import QStandardItem, QStandardItemModel
from PyQt5.QtWidgets import QApplication, QDialog, QHeaderView, QTableView, QVBoxLayout

# from TaskListGroupLabel import TaskListGroupLabel
from NoteListLabel import NoteListLabel
from TaskListGroupLabel import TaskListGroupLabel
from model_metric import ModelEvaluationDialog

sys.path.append("..")
sys.path.append("../..")
import MainWindow_rc

from TaskPage import TaskPage
from TaskPageGroup import TaskPageGroup
from configdialog import ConfigDialog
from userconfigdialog import ConfigDialog as UserConfigDialog
from agentconfigdialog import ConfigDialog as AgentConfigDialog
from agentmuticonfigdialog import ConfigDialog as AgentMutiConfigDialog
from aichatconfigdialog import ConfigDialog as AiChatConfigDialog
from humanchatconfigdialog import ConfigDialog as HumanChatConfigDialog
from kmconfigdialog import ConfigDialog as KmConfigDialog
from agentmng import FreezeTableDialog as AgentFreezeTableDialog
from agentmultimng import FreezeTableDialog as AgentMultiFreezeTableDialog
from aiaccountmng import FreezeTableDialog as AiFreezeTableDialog
from humanaccountmng import FreezeTableDialog as HumanFreezeTableDialog
from kmmng import FreezeTableDialog as KmFreezeTableDialog
from logsmng import FreezeTableDialog as LogsFreezeTableDialog

from db.DBFactory import add_AgentCfg, query_AgentCfg_All, update_AgentCfg, delete_AgentCfg, query_AgentCfg
from db.DBFactory import add_KMData, query_KMData_All, update_KMData, delete_KMData, query_KMData
from db.DBFactory import add_KMCfg, query_KMCfg_All, update_KMCfg, delete_KMCfg, query_KMCfg
from db.DBFactory import add_HumanChatCfg, query_HumanChatCfg_All, update_HumanChatCfg, delete_HumanChatCfg, \
    query_HumanChatCfg
from db.DBFactory import add_AiChatCfg, query_AiChatCfg_All, update_AiChatCfg, delete_AiChatCfg, query_AiChatCfg
from db.DBFactory import add_MutiAgentCfg, query_MutiAgentCfg_All, update_MutiAgentCfg, delete_MutiAgentCfg, \
    query_MutiAgentCfg
from db.DBFactory import add_PluginMng, query_PluginMng_All, query_PluginMng, update_PluginMng, delete_PluginMng, \
    query_PluginMng_All_Tool
from db.DBFactory import add_LogsMng, query_LogsMng_All, update_LogsMng, delete_LogsMng, query_LogsMng

from pluginsmanager import PluginEngine
from pluginsmanager.plugins_headless.plugin_mng import load_plugin as load_plugin_tool
from workflow_manager import WorkFlowManager
from task_schedule import TaskSchedule
from prompts import PromptDialog,PromptManager,MainWindow as Prompt_Manager
import argparse

from pluginsmanager import FileSystem

from langchainhandler import *
import os
from pathlib import Path
from globals import global_plugin_list

from BuddyList import BuddyList
from BuddyListHuman import BuddyListHuman
from InfoList import InfoList
from TaskList import TaskList
from TechList import TechList
from TaskListLabel import TaskListLabel
from TaskListGroup import TaskListGroup
from MemberList import MemberList
from KMList import KMList
from NoteList import NoteList
import http.client
import json
import requests
from PyQt5.QtCore import Qt, pyqtSignal, pyqtSlot, QSize, QUrl, QThread
from PyQt5.QtWidgets import QTreeWidgetItem
from globals import global_agent_list
from Agent import Agent, AgentMode
from AddBuddyDialog import AddBuddyDialog
from AddGroupDialog import AddGroupDialog
from noteeditor.msword import Main as NoteEditor
from function_manager import FunctionManager
from skill_manager import SkillManager
from util import open_file
from keyvalue_mng import KeyValueManager


class Arrow(QGraphicsLineItem):
    def __init__(self, startItem, endItem, parent=None, scene=None):
        super(Arrow, self).__init__(parent, scene)

        self.arrowHead = QPolygonF()

        self.myStartItem = startItem
        self.myEndItem = endItem
        self.setFlag(QGraphicsItem.ItemIsSelectable, True)
        self.myColor = Qt.black
        self.setPen(QPen(self.myColor, 2, Qt.SolidLine, Qt.RoundCap,
                         Qt.RoundJoin))

    def setColor(self, color):
        self.myColor = color

    def startItem(self):
        return self.myStartItem

    def endItem(self):
        return self.myEndItem

    def boundingRect(self):
        extra = (self.pen().width() + 20) / 2.0
        p1 = self.line().p1()
        p2 = self.line().p2()
        return QRectF(p1, QSizeF(p2.x() - p1.x(), p2.y() - p1.y())).normalized().adjusted(-extra, -extra, extra, extra)

    def shape(self):
        path = super(Arrow, self).shape()
        path.addPolygon(self.arrowHead)
        return path

    def updatePosition(self):
        line = QLineF(self.mapFromItem(self.myStartItem, 0, 0), self.mapFromItem(self.myEndItem, 0, 0))
        self.setLine(line)

    def paint(self, painter, option, widget=None):
        if (self.myStartItem.collidesWithItem(self.myEndItem)):
            return

        myStartItem = self.myStartItem
        myEndItem = self.myEndItem
        myColor = self.myColor
        myPen = self.pen()
        myPen.setColor(self.myColor)
        arrowSize = 20.0
        painter.setPen(myPen)
        painter.setBrush(self.myColor)

        centerLine = QLineF(myStartItem.pos(), myEndItem.pos())
        endPolygon = myEndItem.polygon()
        p1 = endPolygon.first() + myEndItem.pos()

        intersectPoint = QPointF()
        for i in endPolygon:
            p2 = i + myEndItem.pos()
            polyLine = QLineF(p1, p2)
            intersectType = polyLine.intersect(centerLine, intersectPoint)
            if intersectType == QLineF.BoundedIntersection:
                break
            p1 = p2

        self.setLine(QLineF(intersectPoint, myStartItem.pos()))
        line = self.line()

        angle = math.acos(line.dx() / line.length())
        if line.dy() >= 0:
            angle = (math.pi * 2.0) - angle

        arrowP1 = line.p1() + QPointF(math.sin(angle + math.pi / 3.0) * arrowSize,
                                      math.cos(angle + math.pi / 3) * arrowSize)
        arrowP2 = line.p1() + QPointF(math.sin(angle + math.pi - math.pi / 3.0) * arrowSize,
                                      math.cos(angle + math.pi - math.pi / 3.0) * arrowSize)

        self.arrowHead.clear()
        for point in [line.p1(), arrowP1, arrowP2]:
            self.arrowHead.append(point)

        painter.drawLine(line)
        painter.drawPolygon(self.arrowHead)
        if self.isSelected():
            painter.setPen(QPen(myColor, 1, Qt.DashLine))
            myLine = QLineF(line)
            myLine.translate(0, 4.0)
            painter.drawLine(myLine)
            myLine.translate(0, -8.0)
            painter.drawLine(myLine)


class DiagramTextItem(QGraphicsTextItem):
    lostFocus = pyqtSignal(QGraphicsTextItem)

    selectedChange = pyqtSignal(QGraphicsItem)

    def __init__(self, parent=None, scene=None):
        super(DiagramTextItem, self).__init__(parent, scene)

        self.setFlag(QGraphicsItem.ItemIsMovable)
        self.setFlag(QGraphicsItem.ItemIsSelectable)

    def itemChange(self, change, value):
        if change == QGraphicsItem.ItemSelectedChange:
            self.selectedChange.emit(self)
        return value

    def focusOutEvent(self, event):
        self.setTextInteractionFlags(Qt.NoTextInteraction)
        self.lostFocus.emit(self)
        super(DiagramTextItem, self).focusOutEvent(event)

    def mouseDoubleClickEvent(self, event):
        if self.textInteractionFlags() == Qt.NoTextInteraction:
            self.setTextInteractionFlags(Qt.TextEditorInteraction)
        super(DiagramTextItem, self).mouseDoubleClickEvent(event)


class DiagramItem(QGraphicsPolygonItem):
    Step, Conditional, StartEnd, Io = range(4)

    def __init__(self, diagramType, contextMenu, parent=None):
        super(DiagramItem, self).__init__(parent)

        self.arrows = []

        self.diagramType = diagramType
        self.contextMenu = contextMenu

        path = QPainterPath()
        if self.diagramType == self.StartEnd:
            path.moveTo(200, 50)
            path.arcTo(150, 0, 50, 50, 0, 90)
            path.arcTo(50, 0, 50, 50, 90, 90)
            path.arcTo(50, 50, 50, 50, 180, 90)
            path.arcTo(150, 50, 50, 50, 270, 90)
            path.lineTo(200, 25)
            self.myPolygon = path.toFillPolygon()
        elif self.diagramType == self.Conditional:
            self.myPolygon = QPolygonF([
                QPointF(-100, 0), QPointF(0, 100),
                QPointF(100, 0), QPointF(0, -100),
                QPointF(-100, 0)])
        elif self.diagramType == self.Step:
            self.myPolygon = QPolygonF([
                QPointF(-100, -100), QPointF(100, -100),
                QPointF(100, 100), QPointF(-100, 100),
                QPointF(-100, -100)])
        else:
            self.myPolygon = QPolygonF([
                QPointF(-120, -80), QPointF(-70, 80),
                QPointF(120, 80), QPointF(70, -80),
                QPointF(-120, -80)])

        self.setPolygon(self.myPolygon)
        self.setFlag(QGraphicsItem.ItemIsMovable, True)
        self.setFlag(QGraphicsItem.ItemIsSelectable, True)

    def removeArrow(self, arrow):
        try:
            self.arrows.remove(arrow)
        except ValueError:
            pass

    def removeArrows(self):
        for arrow in self.arrows[:]:
            arrow.startItem().removeArrow(arrow)
            arrow.endItem().removeArrow(arrow)
            self.scene().removeItem(arrow)

    def addArrow(self, arrow):
        self.arrows.append(arrow)

    def image(self):
        pixmap = QPixmap(250, 250)
        pixmap.fill(Qt.transparent)
        painter = QPainter(pixmap)
        painter.setPen(QPen(Qt.black, 8))
        painter.translate(125, 125)
        painter.drawPolyline(self.myPolygon)
        return pixmap

    def contextMenuEvent(self, event):
        self.scene().clearSelection()
        self.setSelected(True)
        self.myContextMenu.exec_(event.screenPos())

    def itemChange(self, change, value):
        if change == QGraphicsItem.ItemPositionChange:
            for arrow in self.arrows:
                arrow.updatePosition()

        return value


class DiagramScene(QGraphicsScene):
    InsertItem, InsertLine, InsertText, MoveItem = range(4)

    itemInserted = pyqtSignal(DiagramItem)

    textInserted = pyqtSignal(QGraphicsTextItem)

    itemSelected = pyqtSignal(QGraphicsItem)

    def __init__(self, itemMenu, parent=None):
        super(DiagramScene, self).__init__(parent)

        self.myItemMenu = itemMenu
        self.myMode = self.MoveItem
        self.myItemType = DiagramItem.Step
        self.line = None
        self.textItem = None
        self.myItemColor = Qt.white
        self.myTextColor = Qt.black
        self.myLineColor = Qt.black
        self.myFont = QFont()

    def setLineColor(self, color):
        self.myLineColor = color
        if self.isItemChange(Arrow):
            item = self.selectedItems()[0]
            item.setColor(self.myLineColor)
            self.update()

    def setTextColor(self, color):
        self.myTextColor = color
        if self.isItemChange(DiagramTextItem):
            item = self.selectedItems()[0]
            item.setDefaultTextColor(self.myTextColor)

    def setItemColor(self, color):
        self.myItemColor = color
        if self.isItemChange(DiagramItem):
            item = self.selectedItems()[0]
            item.setBrush(self.myItemColor)

    def setFont(self, font):
        self.myFont = font
        if self.isItemChange(DiagramTextItem):
            item = self.selectedItems()[0]
            item.setFont(self.myFont)

    def setMode(self, mode):
        self.myMode = mode

    def setItemType(self, type):
        self.myItemType = type

    def editorLostFocus(self, item):
        cursor = item.textCursor()
        cursor.clearSelection()
        item.setTextCursor(cursor)

        if item.toPlainText():
            self.removeItem(item)
            item.deleteLater()

    def mousePressEvent(self, mouseEvent):
        if (mouseEvent.button() != Qt.LeftButton):
            return

        if self.myMode == self.InsertItem:
            item = DiagramItem(self.myItemType, self.myItemMenu)
            item.setBrush(self.myItemColor)
            self.addItem(item)
            item.setPos(mouseEvent.scenePos())
            self.itemInserted.emit(item)
        elif self.myMode == self.InsertLine:
            self.line = QGraphicsLineItem(QLineF(mouseEvent.scenePos(),
                                                 mouseEvent.scenePos()))
            self.line.setPen(QPen(self.myLineColor, 2))
            self.addItem(self.line)
        elif self.myMode == self.InsertText:
            textItem = DiagramTextItem()
            textItem.setFont(self.myFont)
            textItem.setTextInteractionFlags(Qt.TextEditorInteraction)
            textItem.setZValue(1000.0)
            textItem.lostFocus.connect(self.editorLostFocus)
            textItem.selectedChange.connect(self.itemSelected)
            self.addItem(textItem)
            textItem.setDefaultTextColor(self.myTextColor)
            textItem.setPos(mouseEvent.scenePos())
            self.textInserted.emit(textItem)

        super(DiagramScene, self).mousePressEvent(mouseEvent)

    def mouseMoveEvent(self, mouseEvent):
        if self.myMode == self.InsertLine and self.line:
            newLine = QLineF(self.line.line().p1(), mouseEvent.scenePos())
            self.line.setLine(newLine)
        elif self.myMode == self.MoveItem:
            super(DiagramScene, self).mouseMoveEvent(mouseEvent)

    def mouseReleaseEvent(self, mouseEvent):
        if self.line and self.myMode == self.InsertLine:
            startItems = self.items(self.line.line().p1())
            if len(startItems) and startItems[0] == self.line:
                startItems.pop(0)
            endItems = self.items(self.line.line().p2())
            if len(endItems) and endItems[0] == self.line:
                endItems.pop(0)

            self.removeItem(self.line)
            self.line = None

            if len(startItems) and len(endItems) and \
                    isinstance(startItems[0], DiagramItem) and \
                    isinstance(endItems[0], DiagramItem) and \
                    startItems[0] != endItems[0]:
                startItem = startItems[0]
                endItem = endItems[0]
                arrow = Arrow(startItem, endItem)
                arrow.setColor(self.myLineColor)
                startItem.addArrow(arrow)
                endItem.addArrow(arrow)
                arrow.setZValue(-1000.0)
                self.addItem(arrow)
                arrow.updatePosition()

        self.line = None
        super(DiagramScene, self).mouseReleaseEvent(mouseEvent)

    def isItemChange(self, type):
        for item in self.selectedItems():
            if isinstance(item, type):
                return True
        return False


class WorkerThread(QThread):
    finished = pyqtSignal()

    def __init__(self, filepath, persist_directory, embedding_model_name, emb_type, chunk_size, chunk_overlap):
        super(WorkerThread, self).__init__()
        self.filepath = filepath
        self.persist_directory = persist_directory
        self.embedding_model_name = embedding_model_name
        self.emb_type = emb_type
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap

    def run(self):
        filepath = self.filepath
        persist_directory = self.persist_directory
        embedding_model_name = self.embedding_model_name
        emb_type = self.emb_type
        chunk_size = self.chunk_size
        chunk_overlap = self.chunk_overlap
        print("开始向量化....")
        savevector(filepath, persist_directory, embedding_model_name, emb_type, chunk_size, chunk_overlap)
        self.finished.emit()  # 发射信号，通知主线程


class Ui_MainWindow(object):
    InsertTextButton = 10
    CurTabTextChatTech = ""  # agent 对话列表
    CurTabTextChatMem = ""  # agent  成员列表
    CurTabTextAI = ""  # AI社交
    CurTabTextNote = ""  # 我的笔记
    CurTabTextKmlist = ""  # 知识列表

    def setupUi(self, MainWindow):
        MainWindow.setObjectName("MainWindow")
        MainWindow.resize(QtCore.QSize(QtCore.QRect(0, 0, 316, 407).size()).expandedTo(MainWindow.minimumSizeHint()))
        MainWindow.setWindowIcon(QtGui.QIcon("images/aisns.png"))
        MainWindow.setUnifiedTitleAndToolBarOnMac(False)

        self.centralwidget = QtWidgets.QWidget(MainWindow)
        self.centralwidget.setObjectName("centralwidget")

        self.rwidget = QWidget()

        # self.vboxlayout = QtWidgets.QVBoxLayout(self.centralwidget)
        self.vboxlayout = QtWidgets.QVBoxLayout(self.rwidget)
        self.vboxlayout.setObjectName("vboxlayout")

        self.statusBox = QtWidgets.QComboBox(self.centralwidget)
        self.statusBox.setObjectName("statusBox")
        self.vboxlayout.addWidget(self.statusBox)

        self.statusEdit = QtWidgets.QLineEdit(self.centralwidget)
        self.statusEdit.setObjectName("statusEdit")
        self.vboxlayout.addWidget(self.statusEdit)
        MainWindow.setCentralWidget(self.centralwidget)

        # self.menubar = QtWidgets.QMenuBar(MainWindow)
        # self.menubar.setGeometry(QtCore.QRect(0, 0, 316, 29))
        # self.menubar.setObjectName("menubar")
        #
        # self.menuContacts = QtWidgets.QMenu(self.menubar)
        # self.menuContacts.setObjectName("menuContacts")
        #
        # self.menuAffichage = QtWidgets.QMenu(self.menubar)
        # self.menuAffichage.setObjectName("menuAffichage")
        #
        # self.menuHelp = QtWidgets.QMenu(self.menubar)
        # self.menuHelp.setObjectName("menuHelp")
        #
        # self.menuBuddies = QtWidgets.QMenu(self.menubar)
        # self.menuBuddies.setObjectName("menuBuddies")

        # MainWindow.setMenuBar(self.menubar)#打开菜单

        self.actionConnection = QtWidgets.QAction(MainWindow)
        self.actionConnection.setIcon(QtGui.QIcon("images/status/log-in.png"))
        self.actionConnection.setObjectName("actionConnection")

        self.actionDeconnection = QtWidgets.QAction(MainWindow)
        self.actionDeconnection.setEnabled(False)
        self.actionDeconnection.setIcon(QtGui.QIcon("images/status/log-out.png"))
        self.actionDeconnection.setObjectName("actionDeconnection")

        self.actionOffline_buddies = QtWidgets.QAction(MainWindow)
        # self.actionOffline_buddies.setCheckable(True)
        self.actionOffline_buddies.setObjectName("actionOffline_buddies")

        self.actionAway_buddies = QtWidgets.QAction(MainWindow)
        # self.actionAway_buddies.setCheckable(True)
        # self.actionAway_buddies.setChecked(True)
        self.actionAway_buddies.setObjectName("actionAway_buddies")

        self.togglechatbox = QtWidgets.QAction(MainWindow)
        self.togglechatbox.setIcon(QtGui.QIcon("images/about.png"))
        self.togglechatbox.setObjectName("togglechatbox")

        self.actionShow_agent_homepage = QtWidgets.QAction(MainWindow)
        self.actionShow_agent_homepage.setCheckable(True)
        self.actionShow_agent_homepage.setChecked(True)
        self.actionShow_agent_homepage.setObjectName("actionShow_agent_homepage")

        self.actionShow_ai_homepage = QtWidgets.QAction(MainWindow)
        self.actionShow_ai_homepage.setCheckable(True)
        self.actionShow_ai_homepage.setChecked(True)
        self.actionShow_ai_homepage.setObjectName("actionShow_ai_homepage")

        self.actionShow_human_homepage = QtWidgets.QAction(MainWindow)
        self.actionShow_human_homepage.setCheckable(True)
        self.actionShow_human_homepage.setChecked(True)
        self.actionShow_human_homepage.setObjectName("actionShow_human_homepage")

        self.actionShow_km_homepage = QtWidgets.QAction(MainWindow)
        self.actionShow_km_homepage.setCheckable(True)
        self.actionShow_km_homepage.setChecked(True)
        self.actionShow_km_homepage.setObjectName("actionShow_km_homepage")

        self.actionShow_plugin_homepage = QtWidgets.QAction(MainWindow)
        self.actionShow_plugin_homepage.setCheckable(True)
        self.actionShow_plugin_homepage.setChecked(True)
        self.actionShow_plugin_homepage.setObjectName("actionShow_plugin_homepage")

        self.actionAbout = QtWidgets.QAction(MainWindow)
        self.actionAbout.setIcon(QtGui.QIcon("images/about.png"))
        self.actionAbout.setObjectName("actionAbout")

        self.actionAboutQt = QtWidgets.QAction(MainWindow)
        self.actionAboutQt.setIcon(QtGui.QIcon("images/qt4.png"))
        self.actionAboutQt.setObjectName("actionAboutQt")

        self.actionQuit = QtWidgets.QAction(MainWindow)
        self.actionQuit.setIcon(QtGui.QIcon("images/exit.png"))
        self.actionQuit.setObjectName("actionQuit")

        self.actionAdd_a_buddy = QtWidgets.QAction(MainWindow)
        self.actionAdd_a_buddy.setIcon(QtGui.QIcon("images/add.png"))
        self.actionAdd_a_buddy.setObjectName("actionAdd_a_buddy")

        self.actionAdd_a_group = QtWidgets.QAction(MainWindow)
        self.actionAdd_a_group.setIcon(QtGui.QIcon("images/add.png"))
        self.actionAdd_a_group.setObjectName("actionAdd_a_group")

        self.actionPreferences = QtWidgets.QAction(MainWindow)
        self.actionPreferences.setIcon(QtGui.QIcon("images/setting.png"))
        self.actionPreferences.setObjectName("actionPreferences")

        self.actionConsole = QtWidgets.QAction(MainWindow)
        self.actionConsole.setObjectName("actionConsole")
        # self.menuContacts.addAction(self.actionConnection)
        # self.menuContacts.addAction(self.actionDeconnection)
        # self.menuContacts.addAction(self.actionQuit)
        # self.menuAffichage.addAction(self.actionOffline_buddies)
        # self.menuAffichage.addAction(self.actionAway_buddies)
        # # self.menuAffichage.addAction(self.actionConsole)
        # self.menuHelp.addAction(self.actionAbout)
        # self.menuHelp.addAction(self.actionAboutQt)
        # # self.menuBuddies.addAction(self.actionAdd_a_buddy)
        # # self.menuBuddies.addAction(self.actionAdd_a_group)
        # self.menuBuddies.addAction(self.togglechatbox)
        # self.menuBuddies.addAction(self.actionShow_agent_homepage)
        # self.menuBuddies.addAction(self.actionShow_ai_homepage)
        # self.menuBuddies.addAction(self.actionShow_human_homepage)
        # self.menuBuddies.addAction(self.actionShow_km_homepage)
        # self.menuBuddies.addAction(self.actionShow_plugin_homepage)
        # self.menubar.addAction(self.menuContacts.menuAction())
        # self.menubar.addAction(self.menuBuddies.menuAction())
        # self.menubar.addAction(self.menuAffichage.menuAction())
        # self.menubar.addAction(self.menuHelp.menuAction())

        # add ui tools
        self.createActions()
        self.createMenus()
        self.createToolBox_AgentChat()
        self.createToolBox_AiChat()
        self.createToolBox_HumanChat()
        self.createToolBox_WorkFlow()
        self.createToolBox_KM()
        self.createToolBox_Plugin()
        self.createToolBox_Setting()
        self.createToolbars()

        # The main layout of the window
        self.main_vlayout = QtWidgets.QVBoxLayout(self.centralwidget)
        self.hlayout = QtWidgets.QHBoxLayout(self.centralwidget)

        self.stack_toolbox = QtWidgets.QStackedWidget()
        # sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Expanding)
        # sizePolicy.setHorizontalStretch(1)
        # sizePolicy.setVerticalStretch(0)
        # sizePolicy.setHeightForWidth(self.stack_toolbox.sizePolicy().hasHeightForWidth())
        # self.stack_toolbox.setSizePolicy(sizePolicy)
        # self.stack_toolbox.setAutoFillBackground(False)
        # self.stack_toolbox.setObjectName("stack_toolbox")

        self.stack_toolbox.addWidget(self.toolBox_AgentChat)
        self.stack_toolbox.addWidget(self.toolBox_AiChat)
        self.stack_toolbox.addWidget(self.toolBox_KM)
        self.stack_toolbox.addWidget(self.toolBox_HumanChat)

        self.stack_toolbox.addWidget(self.toolBox_Plugin)
        self.stack_toolbox.addWidget(self.toolBox_Setting)

        self.stack_toolbox.addWidget(self.toolBox_Workflow)

        self.stack_toolbox.setCurrentIndex(0)
        # self.stack_toolbox.setCurrentWidget(self.toolBox_AgentChat)

        self.hlayout.addWidget(self.stack_toolbox)

        # self.hlayout.addWidget(self.rwidget)

        # 创建一个垂直布局用于包含按钮
        self.vlayout = QtWidgets.QVBoxLayout()
        self.vlayout.setContentsMargins(0, 0, 0, 0)
        self.vlayout.setSpacing(0)

        self.toggle_button = QtWidgets.QPushButton("◀")
        self.toggle_button.setFixedWidth(20)
        self.toggle_button.setSizePolicy(QtWidgets.QSizePolicy.Fixed, QtWidgets.QSizePolicy.Expanding)
        self.toggle_button.clicked.connect(self.toggle_stack_toolbox)
        self.toggle_button.setCursor(Qt.PointingHandCursor)
        self.vlayout.addWidget(self.toggle_button)

        self.toggle_button.setStyleSheet("""
            QPushButton {
                color: #146ebe;
                font-size:16pt;
                border: 1px solid #c0c0c0;
                border-top: 0px solid #c0c0c0;
                border-left: 0px solid #c0c0c0;
                border-right: 0px solid #c0c0c0;
                border-bottom: 0px solid #c0c0c0;
            }
        """)

        self.hlayout.setContentsMargins(0, 0, 0, 0)
        self.hlayout.setSpacing(0)

        self.hlayout.addLayout(self.vlayout)

        self.stack_toolbox_visible = True

        # 可移动窗口

        self.main_vlayout.addLayout(self.hlayout)

        self.statusbar = QStatusBar()
        self.statusbar.setVisible(False)
        self.main_vlayout.addWidget(self.statusbar)

        self.retranslateUi(MainWindow)
        QtCore.QMetaObject.connectSlotsByName(MainWindow)

    def toggle_stack_toolbox(self):
        if self.stack_toolbox_visible:
            self.stack_toolbox.hide()
            self.toggle_button.setText("▶")
        else:
            self.stack_toolbox.show()
            self.toggle_button.setText("◀")
        self.stack_toolbox_visible = not self.stack_toolbox_visible

    def backgroundButtonGroupClicked(self, button):
        buttons = self.backgroundButtonGroup.buttons()
        for myButton in buttons:
            if myButton != button:
                button.setChecked(False)

        text = button.text()
        if text == "Blue Grid":
            self.scene.setBackgroundBrush(QBrush(QPixmap(':/images/background1.png')))
        elif text == "White Grid":
            self.scene.setBackgroundBrush(QBrush(QPixmap(':/images/background2.png')))
        elif text == "Gray Grid":
            self.scene.setBackgroundBrush(QBrush(QPixmap(':/images/background3.png')))
        else:
            self.scene.setBackgroundBrush(QBrush(QPixmap(':/images/background4.png')))

        self.scene.update()
        self.view.update()

    def buttonGroupClicked(self, id):
        buttons = self.buttonGroup.buttons()
        for button in buttons:
            if self.buttonGroup.button(id) != button:
                button.setChecked(False)

        if id == self.InsertTextButton:
            self.scene.setMode(DiagramScene.InsertText)
        else:
            pass
            # self.scene.setItemType(id)
            # self.scene.setMode(DiagramScene.InsertItem)

    def buttonGroupClicked_plugin_cfg(self, id):
        buttons = self.buttonGroup_Plugin.buttons()
        for button in buttons:
            if self.buttonGroup_Plugin.button(id) != button:
                button.setChecked(False)

    def buttonGroupClicked_plugin_install(self, id):
        buttons = self.buttonGroup_Plugin_install.buttons()
        for button in buttons:
            button.setChecked(False)

    def settingbuttonGroupClicked(self, id):
        buttons = self.settingbuttonGroup.buttons()
        for button in buttons:
            if self.settingbuttonGroup.button(id) != button:
                button.setChecked(False)
            button.setChecked(False)  # 出来按钮状态

        if id == self.InsertTextButton:
            self.scene.setMode(DiagramScene.InsertText)
        else:
            pass
            # self.scene.setItemType(id)
            # self.scene.setMode(DiagramScene.InsertItem)

    def deleteItem(self):
        for item in self.scene.selectedItems():
            if isinstance(item, DiagramItem):
                item.removeArrows()
            self.scene.removeItem(item)

    def pointerGroupClicked(self, i):
        self.scene.setMode(self.pointerTypeGroup.checkedId())

    def bringToFront(self):
        if not self.scene.selectedItems():
            return

        selectedItem = self.scene.selectedItems()[0]
        overlapItems = selectedItem.collidingItems()

        zValue = 0
        for item in overlapItems:
            if (item.zValue() >= zValue and isinstance(item, DiagramItem)):
                zValue = item.zValue() + 0.1
        selectedItem.setZValue(zValue)

    def sendToBack(self):
        if not self.scene.selectedItems():
            return

        selectedItem = self.scene.selectedItems()[0]
        overlapItems = selectedItem.collidingItems()

        zValue = 0
        for item in overlapItems:
            if (item.zValue() <= zValue and isinstance(item, DiagramItem)):
                zValue = item.zValue() - 0.1
        selectedItem.setZValue(zValue)

    def itemInserted(self, item):
        self.pointerTypeGroup.button(DiagramScene.MoveItem).setChecked(True)
        self.scene.setMode(self.pointerTypeGroup.checkedId())
        self.buttonGroup.button(item.diagramType).setChecked(False)

    def textInserted(self, item):

        self.buttonGroup.button(self.InsertTextButton).setChecked(False)
        self.scene.setMode(self.pointerTypeGroup.checkedId())

    def currentFontChanged(self, font):
        self.handleFontChange()

    def fontSizeChanged(self, font):
        self.handleFontChange()

    def sceneScaleChanged(self, scale):
        newScale = scale.left(scale.indexOf("%")).toDouble()[0] / 100.0
        oldMatrix = self.view.matrix()
        self.view.resetMatrix()
        self.view.translate(oldMatrix.dx(), oldMatrix.dy())
        self.view.scale(newScale, newScale)

    def textColorChanged(self):
        self.textAction = self.sender()
        self.fontColorToolButton.setIcon(
            self.createColorToolButtonIcon(':/images/textpointer.png',
                                           QColor(self.textAction.data())))
        self.textButtonTriggered()

    def itemColorChanged(self):
        self.fillAction = self.sender()
        self.fillColorToolButton.setIcon(
            self.createColorToolButtonIcon(':/images/floodfill.png',
                                           QColor(self.fillAction.data())))
        self.fillButtonTriggered()

    def lineColorChanged(self):
        self.lineAction = self.sender()
        self.lineColorToolButton.setIcon(
            self.createColorToolButtonIcon(':/images/linecolor.png',
                                           QColor(self.lineAction.data())))
        self.lineButtonTriggered()

    def textButtonTriggered(self):
        self.scene.setTextColor(QColor(self.textAction.data()))

    def fillButtonTriggered(self):
        self.scene.setItemColor(QColor(self.fillAction.data()))

    def lineButtonTriggered(self):
        self.scene.setLineColor(QColor(self.lineAction.data()))

    def handleFontChange(self):
        font = self.fontCombo.currentFont()
        font.setPointSize(self.fontSizeCombo.currentText().toInt()[0])
        if self.boldAction.isChecked():
            font.setWeight(QFont.Bold)
        else:
            font.setWeight(QFont.Normal)
        font.setItalic(self.italicAction.isChecked())
        font.setUnderline(self.underlineAction.isChecked())

        self.scene.setFont(font)

    def itemSelected(self, item):
        font = item.font()
        color = item.defaultTextColor()
        self.fontCombo.setCurrentFont(font)
        self.fontSizeCombo.setEditText(str(font.pointSize()))
        self.boldAction.setChecked(font.weight() == QFont.Bold)
        self.italicAction.setChecked(font.italic())
        self.underlineAction.setChecked(font.underline())

    def about(self):
        QMessageBox.about(self, "About Diagram Scene",
                          "The <b>Diagram Scene</b> example shows use of the graphics framework.")

    def download_file(self, url, file_path):
        # 发送 GET 请求并获取响应对象
        response = requests.get(url)

        # 检查响应状态码是否为成功
        if response.status_code == 200:
            # 打开文件并写入响应内容
            with open(file_path, 'wb') as file:
                file.write(response.content)
            print(f"文件 '{file_path}' 下载成功！")
        else:
            print(f"下载失败，状态码：{response.status_code}")

    def unzip_file(self, zip_file_path, extract_to_path):
        # 创建一个ZipFile对象，并打开要解压的zip文件
        with zipfile.ZipFile(zip_file_path, 'r') as zip_ref:
            # 解压缩到指定位置
            zip_ref.extractall(extract_to_path)

        print("解压缩完成！")

    # Agent tool box

    def createToolBoxUnit_AgentChat(self, agent, pos=-1):

        agent_cfg = agent.agent_cfg
        if agent_cfg.is_show == False:
            return
        # Create layout and buttons
        layout = QGridLayout()
        layout.addWidget(self.create_new_task_button("新建对话", agent, DiagramItem.Conditional), 0, 0)
        layout.addWidget(self.create_agent_cfg_button("更多设置", agent, DiagramItem.Step), 0, 1)

        # Create search input
        textEdit = QLineEdit()
        textEdit.setPlaceholderText("🔍关键词+回车搜索，空+回车复原")
        textEdit.setToolTip("关键字以+++开头表示在搜索结果中继续搜索")
        layout.addWidget(textEdit, 1, 0, 1, 2)

        # Create task and tech lists and add them to tab widget
        tabWidget = QTabWidget()
        layout.addWidget(tabWidget, 2, 0, 3, 2)
        taskList = TaskList(self, agent)
        techList = TechList(self, agent)
        labelList = TaskListLabel(self, agent)
        # self.taskList_Task = taskList
        # self.techList_Tech = techList
        # self.labelList_label = labelList

        self.tasklist_list[agent_cfg.user_id] = taskList
        self.techlist_list[agent_cfg.user_id] = techList
        # self.labellist_list[agent_cfg.user_id] = labelList  # 功能？
        tabWidget.addTab(taskList, "对话列表")
        tabWidget.addTab(techList, "技能列表")
        tabWidget.addTab(labelList, "标签列表")  # -->
        self.CurTabTextChatTech = "对话列表"
        # 直接在 connect 方法中使用 lambda 函数处理标签页切换
        tabWidget.currentChanged.connect(
            lambda index: setattr(self, 'CurTabTextChatTech', tabWidget.tabText(index))
        )
        # Stretch settings
        # layout.setRowStretch(3, 10)
        # layout.setColumnStretch(2, 10)
        # 设置行的拉伸系数
        layout.setRowStretch(3, 10)  # 第3行的拉伸系数
        layout.setColumnStretch(0, 1)  # 设置第0列的拉伸系数以均衡布局
        layout.setColumnStretch(1, 1)  # 设置第1列的拉伸系数以均衡布局

        # Create and set widget
        itemWidget = QWidget()
        itemWidget.setObjectName(agent_cfg.user_id)
        itemWidget.setLayout(layout)
        self.toolBox_AgentChat.setMinimumWidth(itemWidget.sizeHint().width())
        if pos == -1:
            self.toolBox_AgentChat.addItem(itemWidget, QIcon('images/agentsingle.png'),
                                           f"{agent_cfg.name} ({agent_cfg.memo})" if agent_cfg.memo else agent_cfg.name)
        else:
            self.toolBox_AgentChat.insertItem(pos - 1, itemWidget, QIcon('images/agentsingle.png'),
                                              f"{agent_cfg.name} ({agent_cfg.memo})" if agent_cfg.memo else agent_cfg.name)

        # Connect returnPressed signal to search function
        # textEdit.returnPressed.connect(lambda: self.taskList_Task.search(textEdit.text()))
        textEdit.returnPressed.connect(lambda: taskList_on_return_pressed(textEdit.text()))

        # -->内部函数
        def taskList_on_return_pressed(key_word):
            if self.CurTabTextChatTech == "对话列表":  # 这里是你的判断条件
                print("对话列表")
                taskList.search(key_word)
            elif self.CurTabTextChatTech == "标签列表":
                print("标签列表")
                labelList.search(key_word)
            elif self.CurTabTextChatTech == "技能列表":
                # todo
                print("技能列表")
                techList.search(key_word)
            else:
                print("其他")

    def createToolBoxUnit_MutiAgentChat(self, agent_cfg_multi, pos=-1):
        if agent_cfg_multi.is_show == False:
            return
        # two button 两个按钮
        layout = QGridLayout()

        layout.addWidget(self.create_new_group_task_button("新建对话", agent_cfg_multi, DiagramItem.Conditional),
                         0, 0)
        layout.addWidget(self.create_muti_agent_cfg_button("更多设置", agent_cfg_multi, DiagramItem.Step), 0,
                         1)

        # search input 搜索框
        textEdit = QLineEdit()
        textEdit.setPlaceholderText("关键词+回车搜索，空+回车复原")
        textEdit.setToolTip("关键字以+++开头表示在搜索结果中继续搜索")
        layout.addWidget(textEdit, 1, 0, 1, 2)

        # task tab 任务页签
        tabWidget = QTabWidget()
        layout.addWidget(tabWidget, 2, 0, 3, 2)  # rowspan为3，此时tab在垂直方向上铺满
        task_list_group = TaskListGroup(self, agent_cfg_multi)
        member_list = MemberList(self, agent_cfg_multi)
        task_list_group_label = TaskListGroupLabel(self, agent_cfg_multi)
        self.tasklist_group_list[agent_cfg_multi.group_id] = task_list_group
        self.memberlist_group_list[agent_cfg_multi.group_id] = member_list

        self.task_list_group = task_list_group
        self.member_list = member_list

        tabWidget.addTab(task_list_group, "对话列表")
        tabWidget.addTab(member_list, "成员列表")
        tabWidget.addTab(task_list_group_label, "标签列表")
        self.CurTabTextChatMem = "对话列表"
        # 直接在 connect 方法中使用 lambda 函数处理标签页切换
        tabWidget.currentChanged.connect(
            lambda index: setattr(self, 'CurTabTextChatMem', tabWidget.tabText(index))
        )
        layout.setRowStretch(3, 10)
        # layout.setColumnStretch(2, 10)
        itemWidget = QWidget()
        itemWidget.setLayout(layout)
        itemWidget.setObjectName(agent_cfg_multi.group_id)
        self.toolBox_AgentChat.setMinimumWidth(itemWidget.sizeHint().width())

        if pos == -1:
            self.toolBox_AgentChat.addItem(itemWidget, QIcon('images/agentmulti.png'),
                                           f"{agent_cfg_multi.name} ({agent_cfg_multi.memo})" if agent_cfg_multi.memo else agent_cfg_multi.name)
        else:
            self.toolBox_AgentChat.insertItem(pos - 1, itemWidget, QIcon('images/agentmulti.png'),
                                              f"{agent_cfg_multi.name} ({agent_cfg_multi.memo})" if agent_cfg_multi.memo else agent_cfg_multi.name)
        # textEdit.returnPressed.connect(lambda: task_list_group.search(textEdit.text()))
        textEdit.returnPressed.connect(lambda: task_list_group_on_return_pressed(textEdit.text()))

        # --> 内部调用
        def task_list_group_on_return_pressed(key_word):
            if self.CurTabTextChatMem == "对话列表":  # 这里是你的判断条件
                task_list_group.search(key_word)
            elif self.CurTabTextChatMem == "标签列表":
                task_list_group_label.search(key_word)
            elif self.CurTabTextChatMem == "成员列表":
                print("成员列表---未实现")
                member_list.search(key_word)
            else:
                print("其他列表")

    def createToolBox_AgentChat(self):
        self.toolBox_AgentChat = QToolBox()
        self.toolBox_AgentChat.setSizePolicy(QSizePolicy(QSizePolicy.Maximum, QSizePolicy.Ignored))

        self.buttonGroup = QButtonGroup()
        self.buttonGroup.setExclusive(False)
        self.buttonGroup.buttonClicked[int].connect(self.buttonGroupClicked)

        agents = global_agent_list.values()  # 前面已经从数据库中初始化了agent列表，直接使用前面已经初始化的列表获取其agent_cfg即可
        for agent in agents:
            self.createToolBoxUnit_AgentChat(agent)

        agent_cfgs_multi = query_MutiAgentCfg_All()
        for agent_cfg_multi in agent_cfgs_multi:
            self.createToolBoxUnit_MutiAgentChat(agent_cfg_multi)

        # ai_chat_cfg setting智能体设置

        self.settingbuttonGroup = QButtonGroup()
        self.settingbuttonGroup.setExclusive(False)
        self.settingbuttonGroup.buttonClicked[int].connect(self.settingbuttonGroupClicked)

        settingLayout = QGridLayout()
        settingLayout.addWidget(self.createCellWidgetAgentNew("新增Agent",
                                                              'images/userplus.png'), 0, 0)
        settingLayout.addWidget(self.createCellWidgetAgentMng("管理Agent",
                                                              'images/usermng.png'), 0, 1)

        settingLayout.addWidget(self.createCellWidgetAgentMultiNew("新增Agent群",
                                                                   'images/agentmultiadd.png'), 1, 0)
        settingLayout.addWidget(self.createCellWidgetAgentMultiMng("管理Agent群",
                                                                   'images/agentmultimng.png'), 1, 1)

        settingLayout.addWidget(self.createCellWidgetAgentMultiEval("模型评测",
                                                                   'images/billboard.png'), 2, 0)
        # settingLayout.addWidget(self.createCellWidgetAgentMultiMng("提示词管理",
        #                                                            'images/fileline.png'), 2, 1)

        settingLayout.addWidget(self.createCellWidgetAgentMultiPrompt("提示词管理",
                                                                   'images/fileline.png'), 2, 1)

        settingLayout.setRowStretch(3, 10)
        # settingLayout.setColumnStretch(2, 10)

        settingWidget = QWidget()
        settingWidget.setLayout(settingLayout)



        self.toolBox_AgentChat.addItem(settingWidget, "Ai智能体管理")
        # 动态修改其值
        self.toolBox_AgentChat.setItemText(self.toolBox_AgentChat.indexOf(settingWidget), "Ai智能体管理")
        self.toolBox_AgentChat.setItemIcon(self.toolBox_AgentChat.indexOf(settingWidget), QIcon('images/setting.png'))

        self.toolBox_AgentChat.currentChanged.connect(self.on_agentchat_toolbox_item_changed)

        # 打印 QToolBox 的样式表
        current_stylesheet = self.toolBox_AgentChat.styleSheet()
        print("Current QToolBox Stylesheet:")
        print(current_stylesheet)



        self.toolBox_AgentChat.setStyleSheet("""
        QToolBox {
            background: #f0f0f0;  /* 整体背景颜色 */
            border-radius: 8px;
            padding: 5px;
        }
        QToolBox::tab {
            background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                                        stop:0 #ffffff, stop:1 #e0e0e0);  /* 渐变背景 */
            
            border-radius: 6px;
            color: #333;  /* 文本颜色 */
            /*padding: 10px 15px;*/
            padding-bottom:0px;
            margin: 0px;
            font-size: 14px;
            transition: background 0.3s;  /* 背景过渡效果 */
            height: 100px;  /* 确保标签有足够的高度 */
        }
        QToolBox::tab:selected {
        
            background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                                        stop:0 #e0e0e0, stop:1 #f0f0f0); 
            /*background: qlineargradient(x1:0, y1:0, x2:1, y2:0,stop:0 #4facfe, stop:1 #00f2fe); */ /* 选中的标签渐变色 */
            /*color: #ffffff;*/  /* 选中状态下的文本颜色 */
            font-weight: bold;
            box-shadow: 0px 2px 5px rgba(0, 0, 0, 0.2);
        }
        QToolBox::tab:hover {
            background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                                                    stop:0 #e0e0e0, stop:1 #f0f0f0); 
        }
        QToolBox::tab QLabel {
            color: #333; /* 确保标签内的文本颜色 */
        }

        QToolBox > QWidget {  /* 仅设置QToolBox子项的背景 */
            background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                                        stop:0 #e0e0e0, stop:1 #e0e0e0);
            border-radius: 6px;
            padding: 10px;
        }

            """)

        # settingWidget.setStyleSheet("""
        #     QWidget {
        #
        #         border-radius: 6px;
        #     }
        # """)
    # Ai Chat tool box

    def on_agentchat_toolbox_item_changed(self, index):
        # 获取当前 item 的文本并打印
        text = self.toolBox_AgentChat.itemText(index)

        agents = global_agent_list.values()  # 前面已经从数据库中初始化了agent列表，直接使用前面已经初始化的列表获取其agent_cfg即可
        for agent in agents:
            if agent.name == text.split(' (')[0]:
                self.open_exist_agent_task_chat(agent)

        print(f'Current item text: {text},current index{index}')

    def createToolBoxUnit_AiChat(self, agent, pos=-1):

        # two button 两个按钮
        print("createToolBoxUnit_AiChat-->")
        layout = QGridLayout()

        layout = QGridLayout()
        layout.addWidget(self.create_new_contact_group_button("添加联系人/组", agent, DiagramItem.Conditional),
                         0, 0)
        layout.addWidget(self.create_ai_cfg_button("登录设置", agent, DiagramItem.Step), 0,
                         1)

        # search input 搜索框
        textEdit = QLineEdit()
        textEdit.setPlaceholderText("搜索...")
        # textEdit.setToolTip("关键字以+++开头表示在搜索结果中继续搜索")
        layout.addWidget(textEdit, 1, 0, 1, 2)

        # task tab 任务页签
        tabWidget = QTabWidget()
        layout.addWidget(tabWidget, 2, 0, 3, 2)  # rowspan为3，此时tab在垂直方向上铺满
        buddyList = BuddyList(self, agent)
        infoList = InfoList(self, agent)
        self.buddylist_list[agent.user_id] = buddyList
        self.contactlist_list[agent.user_id] = infoList

        tabWidget.addTab(buddyList, "聊天")
        tabWidget.addTab(infoList, "通知")
        self.CurTabTextAI = "聊天"

        # 直接在 connect 方法中使用 lambda 函数处理标签页切换
        tabWidget.currentChanged.connect(
            lambda index: setattr(self, 'CurTabTextAI', tabWidget.tabText(index))
        )

        layout.setRowStretch(3, 10)
        # layout.setColumnStretch(2, 10)
        itemWidget = QWidget()
        itemWidget.setLayout(layout)
        itemWidget.setObjectName(agent.user_id)
        self.toolBox_AiChat.setMinimumWidth(itemWidget.sizeHint().width() + 50)

        if pos == -1:
            self.toolBox_AiChat.addItem(itemWidget, QIcon('images/messageoffline.png'), agent.nickname)
        else:
            self.toolBox_AiChat.insertItem(self.toolBox_AiChat.count() - 1, itemWidget,
                                           QIcon('images/messageoffline.png'), agent.nickname)
        # textEdit.returnPressed.connect(lambda: buddyList.search(textEdit.text()))
        textEdit.returnPressed.connect(lambda: self.filterItemsBuddyList(textEdit.text()))

    def filterItemsBuddyList(self, text):
        """根据用户输入的关键词过滤树节点"""
        # 过滤树形控件中的项目 topLevelItemCount
        if hasattr(self, 'BuddyList') or hasattr(self, 'InfoList'):
            if self.CurTabTextAI == "聊天":
                search_list = self.BuddyList
            else:
                search_list = self.InfoList
            print("tree--:", search_list.tree)
            for i in range(search_list.topLevelItemCount()):
                top_item = search_list.topLevelItem(i)
                self.filter_children(top_item, text)
                # print("tree--:",self.BuddyList.tree)
                # for i in range(self.BuddyList.topLevelItemCount()):
                #     top_item = self.BuddyList.topLevelItem(i)
                #     self.filter_children(top_item, text)

    def filter_children(self, parent, text):
        for i in range(parent.childCount()):
            child = parent.child(i)
            if text.lower() in child.text(0).lower():
                child.setHidden(False)
            else:
                child.setHidden(True)
            if child.childCount() > 0:
                self.filter_children(child, text)

    def createToolBox_AiChat(self):
        self.toolBox_AiChat = QToolBox()
        self.toolBox_AiChat.setSizePolicy(QSizePolicy(QSizePolicy.Maximum, QSizePolicy.Ignored))

        self.buttonGroup_AiChat = QButtonGroup()
        self.buttonGroup_AiChat.setExclusive(False)
        self.buttonGroup_AiChat.buttonClicked[int].connect(self.buttonGroupClicked)

        records = query_AiChatCfg_All()
        for record in records:
            # print(f"ID: {record.id}, Name: {record.name}, Memo: {record.memo}")
            self.createToolBoxUnit_AiChat(record)

        self.backgroundButtonGroup_AiChat = QButtonGroup()

        backgroundLayout = QGridLayout()
        backgroundLayout.addWidget(self.createCellWidgetAiChatNew("添加社交帐号",
                                                                  'images/userplus.png'), 0, 0)
        backgroundLayout.addWidget(self.createCellWidgetAiChatMng("管理社交帐号",
                                                                  'images/usermng.png'), 0, 1)

        backgroundLayout.setRowStretch(2, 10)
        # backgroundLayout.setColumnStretch(2, 10)

        backgroundWidget = QWidget()
        backgroundWidget.setLayout(backgroundLayout)

        self.toolBox_AiChat.addItem(backgroundWidget, QIcon('images/setting.png'), "帐号管理")

    # Human Chat tool box

    def createToolBoxUnit_HumanChat(self, agent):

        # two button 两个按钮
        layout = QGridLayout()
        layout.addWidget(self.create_new_contact_group_button("添加联系人/组", None, DiagramItem.Conditional),
                         0, 0)
        layout.addWidget(self.create_human_cfg_button("更多设置", agent, DiagramItem.Step), 0,
                         1)

        # search input 搜索框
        textEdit = QLineEdit()
        textEdit.setPlaceholderText("搜索...")
        layout.addWidget(textEdit, 1, 0, 1, 2)

        tabWidget = QTabWidget()
        layout.addWidget(tabWidget, 2, 0, 3, 2)  # rowspan为3，此时tab在垂直方向上铺满
        buddyList = BuddyListHuman(self)
        infoList = InfoList(self, agent)
        self.buddylist_human_list[agent.user_id] = buddyList
        self.contactlist_human_list[agent.user_id] = infoList

        tabWidget.addTab(buddyList, "聊天")
        tabWidget.addTab(infoList, "通知")

        buddyList.rename_signal.connect(self.addBuddy)
        infoList.rename_signal.connect(self.addBuddy)

        layout.setRowStretch(3, 10)
        # layout.setColumnStretch(2, 10)
        itemWidget = QWidget()
        itemWidget.setLayout(layout)

        self.toolBox_HumanChat.setMinimumWidth(itemWidget.sizeHint().width())
        self.toolBox_HumanChat.addItem(itemWidget, QIcon('images/messageoffline.png'), agent.nickname)

    def createToolBox_HumanChat(self):
        self.toolBox_HumanChat = QToolBox()
        self.toolBox_HumanChat.setSizePolicy(QSizePolicy(QSizePolicy.Maximum, QSizePolicy.Ignored))

        self.buttonGroup_HumanChat = QButtonGroup()
        self.buttonGroup_HumanChat.setExclusive(False)
        self.buttonGroup_HumanChat.buttonClicked[int].connect(self.buttonGroupClicked)

        records = query_HumanChatCfg_All()
        for record in records:
            # print(f"ID: {record.id}, Name: {record.name}, Memo: {record.memo}")
            self.createToolBoxUnit_HumanChat(record)

        self.backgroundButtonGroup_HumanChat = QButtonGroup()

        backgroundLayout = QGridLayout()
        backgroundLayout.addWidget(self.createCellWidgetHumanChatNew("新增帐号",
                                                                     'images/userplus.png'), 0, 0)
        backgroundLayout.addWidget(self.createCellWidgetHumanChatMng("管理帐号",
                                                                     'images/usermng.png'), 0, 1)

        backgroundLayout.setRowStretch(2, 10)
        # backgroundLayout.setColumnStretch(2, 10)

        backgroundWidget = QWidget()
        backgroundWidget.setLayout(backgroundLayout)

        self.toolBox_HumanChat.addItem(backgroundWidget, QIcon('images/setting.png'), "帐号管理")

        # KM Tool Box

    # KM tool box
    # @pyqtSlot(QTreeWidgetItem, int)
    def km_item_click(self, item, col, kmrecord):
        print("in clickitem")
        print(item.type())
        print(QTreeWidgetItem.UserType + 1)
        # if item and item.type() == QTreeWidgetItem.UserType + 1:
        id_value = item.data(col, Qt.UserRole)
        if id_value == None:
            return (False)
        name = item.text(col)
        km_path = kmrecord.kmpath
        file_path = os.path.join(os.getcwd(), "km", km_path, "doc", name)
        open_file(file_path)

        # item.on_click()

    def createToolBoxUnit_KM_Notes(self, kmrecord, pos=-1):

        # Create layout and buttons
        layout = QGridLayout()
        layout.addWidget(self.create_new_note_button("新建笔记", kmrecord, "images/fileplus.png"),
                         0, 0)
        layout.addWidget(self.create_note_cfg_button("更多设置", DiagramItem.Step), 0,
                         1)
        # Create search input
        textEdit = QLineEdit()
        textEdit.setPlaceholderText("关键词+回车搜索，空+回车复原")
        textEdit.setToolTip("关键字以+++开头表示在搜索结果中继续搜索")
        layout.addWidget(textEdit, 1, 0, 1, 2)

        # Create task and tech lists and add them to tab widget
        tabWidget = QTabWidget()
        layout.addWidget(tabWidget, 2, 0, 3, 2)
        # notelist_recent = NoteList(self, kmrecord, "recent")
        # notelist_recent.setObjectName("recentnotelist")
        notelist_all = NoteList(self, kmrecord, "all")
        notelist_all.setObjectName("allnotelist")
        notelist_all_label = NoteListLabel(self, kmrecord, "label")
        notelist_all_label.setObjectName("labelallnotelist")
        # self.notelist_recent = notelist_recent
        self.notelist_all = notelist_all
        self.notelist_all_label = notelist_all_label

        # self.notelist_recent_list[kmrecord.km_id] = notelist_recent
        self.notelist_all_list[kmrecord.km_id] = notelist_all

        # tabWidget.addTab(notelist_recent, "最新")
        tabWidget.addTab(notelist_all, "全部")
        tabWidget.addTab(notelist_all_label, "标签")
        # self.CurTabTextNote = "最新"
        self.CurTabTextNote = "全部"
        # 直接在 connect 方法中使用 lambda 函数处理标签页切换
        tabWidget.currentChanged.connect(
            lambda index: setattr(self, 'CurTabTextNote', tabWidget.tabText(index))
        )

        # Stretch settings
        layout.setRowStretch(3, 10)
        # layout.setColumnStretch(2, 10)

        # Create and set widget
        itemWidget = QWidget()
        itemWidget.setObjectName(kmrecord.km_id)
        itemWidget.setLayout(layout)
        self.toolBox_KM.setMinimumWidth(itemWidget.sizeHint().width())

        # self.toolBox_KM.addItem(itemWidget, "我的笔记")

        if pos == -1:
            self.toolBox_KM.addItem(itemWidget, QIcon('images/note.png'), kmrecord.name)
        else:
            self.toolBox_KM.insertItem(self.toolBox_KM.count() - 1, itemWidget, QIcon('images/note.png'), kmrecord.name)

        # Connect returnPressed signal to search function
        # textEdit.returnPressed.connect(lambda: notelist_all.search(textEdit.text()))
        textEdit.returnPressed.connect(lambda: self.notelist_on_return_pressed(textEdit.text()))

    def notelist_on_return_pressed(self, key_word):
        if self.CurTabTextNote == "全部":  # 这里是你的判断条件
            self.notelist_all.search(key_word)
        elif self.CurTabTextNote == "标签":  # -->  增加 标签 页签
            self.notelist_all_label.search(key_word)
        elif self.CurTabTextNote == "最新":  # 这里是你的判断条件
            self.notelist_recent.search(key_word)
        else:
            print("其他")

    def createToolBoxUnit_KM(self, kmrecord, pos=-1):
        # two button 两个按钮
        layout = QGridLayout()
        layout.addWidget(self.create_new_km_button("新建知识", kmrecord, "images/fileplus.png"),
                         0, 0)
        layout.addWidget(self.create_km_cfg_button("更多设置", kmrecord, DiagramItem.Step), 0,
                         1)
        # search input 搜索框
        textEdit = QLineEdit()
        textEdit.setPlaceholderText("关键词+回车搜索，空+回车复原")
        textEdit.setToolTip("关键字以+++开头表示在搜索结果中继续搜索")
        textEdit.setPlaceholderText("搜索...")
        layout.addWidget(textEdit, 1, 0, 1, 2)
        # task tab 任务页签

        tabWidget = QTabWidget()
        layout.addWidget(tabWidget, 2, 0, 3, 2)  # rowspan为3，此时tab在垂直方向上铺满
        kmlist_list = KMList(self, kmrecord, False)
        kmlist_list_deleted = KMList(self, kmrecord, True)

        kmlist_list.itemDoubleClicked.connect(lambda item, column: self.km_item_click(item, column, kmrecord))
        self.kmlist_all = kmlist_list
        self.kmlist_deleted = kmlist_list_deleted

        self.kmlist_list[kmrecord.km_id] = kmlist_list
        self.kmlist_list_deleted[kmrecord.km_id] = kmlist_list_deleted

        tabWidget.addTab(kmlist_list, "知识列表")
        tabWidget.addTab(kmlist_list_deleted, "回收站")
        self.CurTabTextKmlist = "知识列表"
        # 直接在 connect 方法中使用 lambda 函数处理标签页切换
        tabWidget.currentChanged.connect(
            lambda index: setattr(self, 'CurTabTextKmlist', tabWidget.tabText(index))
        )

        layout.setRowStretch(3, 10)
        # layout.setColumnStretch(2, 10)
        itemWidget = QWidget()
        itemWidget.setObjectName(kmrecord.km_id)
        itemWidget.setLayout(layout)
        self.toolBox_KM.setMinimumWidth(itemWidget.sizeHint().width())
        if pos == -1:
            self.toolBox_KM.addItem(itemWidget, QIcon('images/filelist.png'), kmrecord.name)
        else:
            self.toolBox_KM.insertItem(self.toolBox_KM.count() - 1, itemWidget, QIcon('images/filelist.png'),
                                       kmrecord.name)
        # Connect returnPressed signal to search function
        textEdit.returnPressed.connect(lambda: kmlist_list.search(textEdit.text()))
        # textEdit.returnPressed.connect(lambda: self.kmlist_on_return_pressed(textEdit.text()))

    def kmlist_on_return_pressed(self, key_word):
        if self.CurTabTextKmlist == "知识列表":  # 这里是你的判断条件
            self.kmlist_all.search(key_word)
        else:
            self.kmlist_deleted.search(key_word)

    def createToolBox_KM(self):
        self.toolBox_KM = QToolBox()
        self.toolBox_KM.setSizePolicy(QSizePolicy(QSizePolicy.Maximum, QSizePolicy.Ignored))

        self.buttonGroup_KM = QButtonGroup()
        self.buttonGroup_KM.setExclusive(False)
        self.buttonGroup_KM.buttonClicked[int].connect(self.buttonGroupClicked)

        records = query_KMCfg_All()
        for record in records:
            # print(f"ID: {record.id}, Name: {record.name}, Memo: {record.memo}")
            if record.kmtype == "1":
                self.createToolBoxUnit_KM_Notes(record)
            else:
                self.createToolBoxUnit_KM(record)

        self.backgroundButtonGroup_KM = QButtonGroup()
        # self.backgroundButtonGroup_KM.buttonClicked.connect(self.backgroundButtonGroupClicked)

        backgroundLayout = QGridLayout()
        backgroundLayout.addWidget(self.createCellWidgetKMNew("新增知识库",
                                                              'images/bookplus.png'), 0, 0)
        backgroundLayout.addWidget(self.createCellWidgetKMMng("管理知识库",
                                                              'images/filecabinet.png'), 0, 1)

        backgroundLayout.addWidget(self.createCellWidgetKVMng("管理键值对",
                                                              'images/database.png'), 1, 0)

        backgroundLayout.setRowStretch(2, 10)
        # backgroundLayout.setColumnStretch(2, 10)

        backgroundWidget = QWidget()
        backgroundWidget.setLayout(backgroundLayout)

        self.toolBox_KM.addItem(backgroundWidget, QIcon('images/setting.png'), "知识库设置")

        # Plugin Tool Box

    # Plugin tool box
    def createToolBoxUnit_Plugin(self, record):
        pass

    def createToolBox_Plugin(self):
        self.toolBox_Plugin = QToolBox()
        self.toolBox_Plugin.setSizePolicy(QSizePolicy(QSizePolicy.Maximum, QSizePolicy.Ignored))

        # 已装模型插件
        self.buttonGroup_Plugin = QButtonGroup()
        self.buttonGroup_Plugin.setExclusive(False)
        self.buttonGroup_Plugin.buttonClicked[int].connect(self.buttonGroupClicked_plugin_cfg)

        self.layout = QGridLayout()

        self.textEdit = QLineEdit()
        self.textEdit.setPlaceholderText("搜索...")
        self.textEdit.textChanged.connect(self.filterTextEdit)
        self.layout.addWidget(self.textEdit, 0, 0, 1, 2)
        i = 0
        row = 1
        col = 0
        records = query_PluginMng_All(plugin_type="LLM_Connector")
        # print("records-->:", records)
        for record in records:
            print(f"ID: {record.id}, Name: {record.name}, Memo: {record.description}")
            # self.createToolBoxUnit_AgentChat(record)
            print("row:", row)
            print("col:", col)
            print("col % 2：", col % 2)
            print("cjr in plugin...")
            self.layout.addWidget(self.create_plugin_cfg_button(record, DiagramItem.Conditional),
                                  row, col % 2)

            if (col % 2) == 1:
                row = row + 1
            col = col + 1

        self.layout.setRowStretch(row + 1, 10)
        # self.layout.setColumnStretch(2, 10)

        itemWidget = QWidget()
        itemWidget.setLayout(self.layout)

        self.toolBox_Plugin.setMinimumWidth(itemWidget.sizeHint().width())
        self.toolBox_Plugin.addItem(itemWidget, QIcon('images/llm.png'), "模型插件")

        # 已装工具插件
        self.buttonGroup_Plugin_tool = QButtonGroup()
        self.buttonGroup_Plugin_tool.setExclusive(False)
        self.buttonGroup_Plugin_tool.buttonClicked[int].connect(self.buttonGroupClicked_plugin_cfg)

        self.layout_tool = QGridLayout()

        self.textEdit_tool = QLineEdit()
        self.textEdit_tool.setPlaceholderText("搜索...")
        self.textEdit_tool.textChanged.connect(self.filterTextEditTool)
        self.layout_tool.addWidget(self.textEdit_tool, 0, 0, 1, 2)
        i = 0
        row = 1
        col = 0
        records = query_PluginMng_All_Tool()
        for record in records:
            print(f"ID: {record.id}, Name: {record.name}, Memo: {record.description}")
            # self.createToolBoxUnit_AgentChat(record)
            print("row:", row)
            print("col:", col)
            print("col % 2：", col % 2)
            self.layout_tool.addWidget(self.create_plugin_tool_cfg_button(record, DiagramItem.Conditional),
                                       row, col % 2)

            if (col % 2) == 1:
                row = row + 1
            col = col + 1

        self.layout_tool.setRowStretch(row + 1, 10)
        # self.layout_tool.setColumnStretch(2, 10)

        itemWidget = QWidget()
        itemWidget.setLayout(self.layout_tool)

        self.toolBox_Plugin.setMinimumWidth(itemWidget.sizeHint().width())
        self.toolBox_Plugin.addItem(itemWidget, QIcon('images/plugin_tool.png'), "工具插件")

        # 已装函数插件
        self.buttonGroup_Plugin_function = QButtonGroup()
        self.buttonGroup_Plugin_function.setExclusive(False)
        self.buttonGroup_Plugin_function.buttonClicked[int].connect(self.buttonGroupClicked_plugin_cfg)

        layout_function = QGridLayout()

        textEdit_function = QLineEdit()
        textEdit_function.setPlaceholderText("搜索...")
        textEdit_function.returnPressed.connect(lambda: self.function_search(textEdit_function.text()))

        layout_function.addWidget(textEdit_function, 0, 0, 1, 2)
        i = 0
        row = 1
        col = 0
        layout_function.addWidget(self.create_plugin_function_button("1", DiagramItem.Conditional),
                                  1, 0)

        layout_function.addWidget(self.create_plugin_function_button("0", DiagramItem.Conditional),
                                  1, 1)

        layout_function.setRowStretch(row + 1, 10)
        # layout_function.setColumnStretch(2, 10)

        itemWidget = QWidget()
        itemWidget.setLayout(layout_function)

        self.toolBox_Plugin.setMinimumWidth(itemWidget.sizeHint().width())
        self.toolBox_Plugin.addItem(itemWidget, QIcon('images/function.png'), "自定义函数")

        # 已学技能
        self.buttonGroup_Plugin_skill = QButtonGroup()
        self.buttonGroup_Plugin_skill.setExclusive(False)
        self.buttonGroup_Plugin_skill.buttonClicked[int].connect(self.buttonGroupClicked_plugin_cfg)

        layout_skill = QGridLayout()

        textEdit_skill = QLineEdit()
        textEdit_skill.setPlaceholderText("搜索...")
        textEdit_skill.returnPressed.connect(lambda: self.skill_search(textEdit_skill.text()))

        layout_skill.addWidget(textEdit_skill, 0, 0, 1, 2)
        i = 0
        row = 1
        col = 0
        layout_skill.addWidget(self.create_plugin_skill_button("1", DiagramItem.Conditional),
                                  1, 0)

        layout_skill.addWidget(self.create_plugin_skill_button("0", DiagramItem.Conditional),
                                  1, 1)

        layout_skill.setRowStretch(row + 1, 10)
        # layout_skill.setColumnStretch(2, 10)

        itemWidget = QWidget()
        itemWidget.setLayout(layout_skill)

        self.toolBox_Plugin.setMinimumWidth(itemWidget.sizeHint().width())
        self.toolBox_Plugin.addItem(itemWidget, QIcon('images/skill.png'), "已学技能")





        # 插件市场
        self.buttonGroup_Plugin_install = QButtonGroup()
        self.buttonGroup_Plugin_install.setExclusive(False)
        self.buttonGroup_Plugin_install.buttonClicked[int].connect(self.buttonGroupClicked_plugin_install)

        self.backgroundLayout = QGridLayout()

        self.textEdit2 = QLineEdit()
        self.textEdit2.setPlaceholderText("搜索...")
        self.textEdit2.textChanged.connect(self.filterTextEdit2)
        self.backgroundLayout.addWidget(self.textEdit2, 0, 0, 1, 2)
        self.backgroundLayout.addWidget(self.create_install_plugin_local_button("导入本地插件",
                                                                                'images/add.png'), 1, 0)

        conn = http.client.HTTPConnection("www.ai-sns.org", 80)
        headers = {
            "Content-Type": "application/json"
        }
        body = {}

        try:
            # 尝试获取远程插件列表
            conn.request("GET", "/pluginlist.json", json.dumps(body), headers)
            response = conn.getresponse()

            if response.status != 200:
                raise Exception(f"HTTP请求失败，状态码: {response.status}")

            data = response.read().decode("utf-8")
            json_data = json.loads(data)
            # 写入本地文件
            file_path = os.path.join(Path(__file__).resolve().parent.parent, "pluginsmanager", "pluginlist.json")
            with open(file_path, "w", encoding='utf-8') as file:
                json.dump(json_data, file, ensure_ascii=False)

        except (http.client.HTTPException, json.JSONDecodeError, OSError) as e:
            # 如果网络请求失败，加载本地文件
            print(f"网络连接错误或JSON解析错误: {e}，使用本地插件列表。")
            file_path = os.path.join(Path(__file__).resolve().parent.parent, "pluginsmanager", "pluginlist.json")

            with open(file_path, "r", encoding='utf-8') as file:
                json_data = json.load(file)

        finally:
            conn.close()

        i = 0
        row = 1
        col = 0

        for plugin_data in json_data:

            if row == 1:
                col = 1

            self.backgroundLayout.addWidget(self.create_install_plugin_button(plugin_data,
                                                                              'images/plugin.png'), row, col % 2)
            if row == 1:
                row = row + 1
            else:
                if (col % 2) == 1:
                    row = row + 1
            col = col + 1

        # # 打开文件并加载JSON数据
        # with open(file_path, 'r') as file:
        #     json_data = json.load(file)
        #
        # for plugin_data in json_data:
        #     content = plugin_data["name"]
        #     print("pluginname2", content)

        self.backgroundLayout.setRowStretch(4, 10)
        self.backgroundLayout.setColumnStretch(4, 10)

        backgroundWidget = QWidget()
        backgroundWidget.setLayout(self.backgroundLayout)

        self.toolBox_Plugin.addItem(backgroundWidget, QIcon('images/market.png'), "插件市场")

    def filterTextEdit(self, text):
        # 根据输入框的内容过滤表格项的标题列

        # layout = QGridLayout()
        i = 0
        row = 1
        col = 0

        for i in range(self.layout.count()):
            item = self.layout.itemAt(i)

            # self.layout.itemAt(0).widget().deleteLater()  # 删除控件
            # self.layout.removeAt(0)  # 从布局中移除控件
            # item = self.layout.takeAt(0)
            # 如果项目是一个控件，则删除它
            if item.widget() and item.widget() is not None:
                # 检查是否是 QLineEdit 输入框
                if isinstance(item.widget(), QLineEdit):
                    print("Found a QLineEdit")
                # 检查是否是 QPushButton 按钮
                elif isinstance(item.widget(), QToolButton):
                    print("Found a QPushButton")
                    item.widget().deleteLater()
                else:
                    plugin_widget = item.widget()
                    print(type(plugin_widget).__name__)
                    if hasattr(plugin_widget, 'name'):
                        widget_name = plugin_widget.name
                        if text == "" or text in widget_name:
                            plugin_widget.setHidden(False)
                            # self.layout.removeWidget(plugin_widget)
                            # plugin_widget.setParent(None)
                            # self.layout.addWidget(plugin_widget, row, col % 2)
                            # if (col % 2) == 1:
                            #     row = row + 1
                            # col = col + 1
                            print("The widget has a 'name' attribute.", item.widget().name)
                        else:
                            plugin_widget.setHidden(True)

                    else:
                        print("The widget does not have a 'name' attribute.")

            # 如果项目是一个子布局，则递归清空子布

        # i = 0
        # row = 1
        # col = 0
        # records = query_PluginMng_All(plugin_type="LLM_Connector")
        # print("records-->:", records)
        # for record in records:
        #
        #     # self.createToolBoxUnit_AgentChat(record)
        #     if text not in record.name:
        #         continue
        #     print(f"ID: {record.id}, Name: {record.name}, Memo: {record.description}")
        #     self.layout.addWidget(self.create_plugin_cfg_button(record, DiagramItem.Conditional),
        #                           row, col % 2)
        #
        #     if (col % 2) == 1:
        #         row = row + 1
        #     col = col + 1
        #
        # self.layout.setRowStretch(row + 1, 10)
        # self.layout.setColumnStretch(2, 10)

    def filterTextEditTool(self, text):
        # 根据输入框的内容过滤表格项的标题列
        # layout = QGridLayout()
        i = 0
        row = 1
        col = 0
        for i in range(self.layout_tool.count()):
            item = self.layout_tool.itemAt(i)
            if item.widget() and item.widget() is not None:
                # 检查是否是 QLineEdit 输入框
                if isinstance(item.widget(), QLineEdit):
                    print("Found a QLineEdit")
                else:
                    plugin_widget = item.widget()
                    print(type(plugin_widget).__name__)
                    if hasattr(plugin_widget, 'name'):
                        widget_name = plugin_widget.name
                        if text == "" or text in widget_name:
                            plugin_widget.setHidden(False)
                            # self.layout.removeWidget(plugin_widget)
                            # plugin_widget.setParent(None)
                            self.layout.addWidget(plugin_widget, row, col % 2)
                            # if (col % 2) == 1:
                            #     row = row + 1
                            # col = col + 1
                            print("The widget has a 'name' attribute.", item.widget().name)
                        else:
                            plugin_widget.setHidden(True)

                    else:
                        print("The widget does not have a 'name' attribute.")

            # 如果项目是一个子布局，则递归清空子布

    def filterTextEdit2(self, text):
        # 根据输入框的内容过滤表格项的标题列
        for i in range(self.backgroundLayout.count()):
            item = self.backgroundLayout.itemAt(i)
            # 如果项目是一个控件，则删除它
            if item.widget() and item.widget() is not None:
                # 检查是否是 QLineEdit 输入框
                if isinstance(item.widget(), QLineEdit):
                    print("Found a QLineEdit")
                else:
                    plugin_widget = item.widget()
                    print(type(plugin_widget).__name__)
                    if hasattr(plugin_widget, 'name'):
                        widget_name = plugin_widget.name
                        if text == "" or text in widget_name:
                            plugin_widget.setHidden(False)
                            print("The widget has a 'name' attribute.", item.widget().name)
                        else:
                            plugin_widget.setHidden(True)
                    else:
                        print("The widget does not have a 'name' attribute.")

            # 如果项目是一个子布局，则递归清空子布

    # createToolBox_WorkFlow
    def createToolBoxUnit_WorkFlow(self, record):
        pass

    def createToolBox_WorkFlow(self):
        self.toolBox_Workflow = QToolBox()
        self.toolBox_Workflow.setSizePolicy(QSizePolicy(QSizePolicy.Maximum, QSizePolicy.Ignored))

        # 工作流
        self.buttonGroup_WorkFlow = QButtonGroup()
        self.buttonGroup_WorkFlow.setExclusive(False)
        self.buttonGroup_WorkFlow.buttonClicked[int].connect(self.buttonGroupClicked_plugin_cfg)

        layout_tool = QGridLayout()

        # textEdit_tool = QLineEdit()
        # textEdit_tool.setPlaceholderText("搜索...")
        # layout_tool.addWidget(textEdit_tool, 0, 0, 1, 2)
        i = 0
        row = 1
        col = 0

        layout_tool.addWidget(self.create_workflow_cfg_button(DiagramItem.Conditional),
                              0, 0)

        layout_tool.addWidget(self.create_task_schedule_button(DiagramItem.Conditional),
                              0, 1)

        layout_tool.setRowStretch(1, 10) # 第2行的拉伸系数
        layout_tool.setColumnStretch(0, 1)  # 设置第0列的拉伸系数以均衡布局
        layout_tool.setColumnStretch(1, 1)  # 设置第1列的拉伸系数以均衡布局

        itemWidget = QWidget()
        itemWidget.setLayout(layout_tool)

        self.toolBox_Workflow.setMinimumWidth(itemWidget.sizeHint().width())
        self.toolBox_Workflow.addItem(itemWidget, QIcon('images/workflow_toolbox.png'), "工作流")

    # Setting Tool Box

    def createToolBox_Setting(self):
        self.buttonGroup_Setting = QButtonGroup()
        self.buttonGroup_Setting.setExclusive(False)
        self.buttonGroup_Setting.buttonClicked[int].connect(self.buttonGroupClicked)

        layout = QGridLayout()
        layout.addWidget(self.createCellWidgetGeneralCfg("系统设置", DiagramItem.Conditional),
                         0, 0)
        layout.addWidget(self.createCellWidgetLogMng("系统日志", DiagramItem.Step), 0,
                         1)
        # layout.addWidget(self.createCellWidget("Input/Output", DiagramItem.Io), 1, 0)

        textButton = QToolButton()
        textButton.setCheckable(True)
        self.buttonGroup_Setting.addButton(textButton, self.InsertTextButton)
        textButton.setIcon(QIcon(QPixmap(':/images/textpointer.png').scaled(30, 30)))
        textButton.setIconSize(QSize(50, 50))

        textLayout = QGridLayout()
        textLayout.addWidget(textButton, 0, 0, Qt.AlignHCenter)
        textLayout.addWidget(QLabel("Text"), 1, 0, Qt.AlignCenter)
        textWidget = QWidget()
        textWidget.setLayout(textLayout)
        # layout.addWidget(textWidget, 1, 1)

        layout.setRowStretch(3, 10)
        # layout.setColumnStretch(2, 10)

        itemWidget = QWidget()
        itemWidget.setLayout(layout)

        self.toolBox_Setting = QToolBox()
        self.toolBox_Setting.setSizePolicy(QSizePolicy(QSizePolicy.Maximum, QSizePolicy.Ignored))
        self.toolBox_Setting.setMinimumWidth(itemWidget.sizeHint().width())
        self.toolBox_Setting.addItem(itemWidget, QIcon('images/setting.png'), "系统管理")

    def ShowAiAssistantStack(self):
        orgfont = QFont()
        orgfont.setBold(False)
        orgfont.setUnderline(False)

        font = QFont()
        font.setBold(True)
        # font.setUnderline(True)

        self.ai2meAction.setFont(orgfont)
        self.ai2aiAction.setFont(orgfont)
        self.chatAction.setFont(orgfont)
        self.workflowAction.setFont(orgfont)
        self.kmAction.setFont(orgfont)
        self.pluginAction.setFont(orgfont)
        self.settingAction.setFont(orgfont)

        self.ai2meAction.setFont(font)
        self.stack_toolbox.setCurrentIndex(0)
        self.showagenthome()

    def ShowAiChatStack(self):
        orgfont = QFont()
        orgfont.setBold(False)
        orgfont.setUnderline(False)

        font = QFont()
        font.setBold(True)
        # font.setUnderline(True)

        self.ai2meAction.setFont(orgfont)
        self.ai2aiAction.setFont(orgfont)
        self.chatAction.setFont(orgfont)
        self.workflowAction.setFont(orgfont)
        self.kmAction.setFont(orgfont)
        self.pluginAction.setFont(orgfont)
        self.settingAction.setFont(orgfont)

        self.ai2aiAction.setFont(font)
        self.stack_toolbox.setCurrentIndex(1)
        self.showaihome()

    def ShowKMStack(self):
        orgfont = QFont()
        orgfont.setBold(False)
        orgfont.setUnderline(False)

        font = QFont()
        font.setBold(True)
        # font.setUnderline(True)

        self.ai2meAction.setFont(orgfont)
        self.ai2aiAction.setFont(orgfont)
        self.chatAction.setFont(orgfont)
        self.workflowAction.setFont(orgfont)
        self.kmAction.setFont(orgfont)
        self.pluginAction.setFont(orgfont)
        self.settingAction.setFont(orgfont)

        self.kmAction.setFont(font)
        self.stack_toolbox.setCurrentIndex(2)
        self.showkmhome()

    def ShowHumanChatStack(self):
        orgfont = QFont()
        orgfont.setBold(False)
        orgfont.setUnderline(False)

        font = QFont()
        font.setBold(True)
        # font.setUnderline(True)

        self.ai2meAction.setFont(orgfont)
        self.ai2aiAction.setFont(orgfont)
        self.chatAction.setFont(orgfont)
        self.workflowAction.setFont(orgfont)
        self.kmAction.setFont(orgfont)
        self.pluginAction.setFont(orgfont)
        self.settingAction.setFont(orgfont)

        self.chatAction.setFont(font)
        self.stack_toolbox.setCurrentIndex(3)
        self.showhumanhome()

    def ShowWorkFlowStack(self):
        orgfont = QFont()
        orgfont.setBold(False)
        orgfont.setUnderline(False)

        font = QFont()
        font.setBold(True)
        # font.setUnderline(True)

        self.ai2meAction.setFont(orgfont)
        self.ai2aiAction.setFont(orgfont)
        self.chatAction.setFont(orgfont)
        self.workflowAction.setFont(orgfont)
        self.kmAction.setFont(orgfont)
        self.pluginAction.setFont(orgfont)
        self.settingAction.setFont(orgfont)

        self.workflowAction.setFont(font)
        self.stack_toolbox.setCurrentIndex(6)
        self.showpluginhome()

    def ShowPluginStack(self):
        orgfont = QFont()
        orgfont.setBold(False)
        orgfont.setUnderline(False)

        font = QFont()
        font.setBold(True)
        # font.setUnderline(True)

        self.ai2meAction.setFont(orgfont)
        self.ai2aiAction.setFont(orgfont)
        self.chatAction.setFont(orgfont)
        self.workflowAction.setFont(orgfont)
        self.kmAction.setFont(orgfont)
        self.pluginAction.setFont(orgfont)
        self.settingAction.setFont(orgfont)

        self.pluginAction.setFont(font)
        self.stack_toolbox.setCurrentIndex(4)
        self.showpluginhome()

    def ShowSettingStack(self):
        orgfont = QFont()
        orgfont.setBold(False)
        orgfont.setUnderline(False)

        font = QFont()
        font.setBold(True)
        # font.setUnderline(True)

        self.ai2meAction.setFont(orgfont)
        self.ai2aiAction.setFont(orgfont)
        self.chatAction.setFont(orgfont)
        self.workflowAction.setFont(orgfont)
        self.kmAction.setFont(orgfont)
        self.pluginAction.setFont(orgfont)
        self.settingAction.setFont(orgfont)
        # self.ai2aiAction.setFont(font)

        self.settingAction.setFont(font)
        self.stack_toolbox.setCurrentIndex(5)
        # self.stack_toolbox.setCurrentIndex(1)

    def createActions(self):
        self.toFrontAction = QAction(
            QIcon(':/images/bringtofront.png'), "Bring to &Front",
            self, shortcut="Ctrl+F", statusTip="Bring item to front",
            triggered=self.bringToFront)

        self.sendBackAction = QAction(
            QIcon(':/images/sendtoback.png'), "Send to &Back", self,
            shortcut="Ctrl+B", statusTip="Send item to back",
            triggered=self.sendToBack)

        self.deleteAction = QAction(QIcon(':/images/delete.png'),
                                    "&Delete", self, shortcut="Delete",
                                    statusTip="Delete item from diagram",
                                    triggered=self.deleteItem, iconText="删除")

        self.ai2meAction = QAction(QIcon('images/agent.png'),
                                   "为我处理工作的Ai智能体", self, shortcut="Ctrl+F",
                                   statusTip="为我处理工作的Ai智能体",
                                   triggered=self.ShowAiAssistantStack, iconText="Agent")

        # 创建一个字体对象，设置字体为粗体，带下划线
        font = QFont()
        font.setBold(True)
        # font.setUnderline(True)

        self.ai2meAction.setFont(font)
        # self.ai2meAction.setCheckable(True)  # 设置为可切换状态
        # self.ai2meAction.setChecked(True)  # 设置初始状态为选中状态

        self.ai2aiAction = QAction(
            QIcon('images/aichat.png'), "Ai和Ai之间的社交，比如在线聊天",
            self, shortcut="Ctrl+F", statusTip="Ai和Ai之间的社交，比如在线聊天",
            triggered=self.ShowAiChatStack, iconText="Ai社交")

        self.kmAction = QAction(
            QIcon('images/km.png'), "知识库",
            self, shortcut="Ctrl+F", statusTip="知识库",
            triggered=self.ShowKMStack, iconText="知识库")

        self.pluginAction = QAction(
            QIcon('images/tool.png'), "插件工具",
            self, shortcut="Ctrl+F", statusTip="插件工具",
            triggered=self.ShowPluginStack, iconText="插件工具")

        self.chatAction = QAction(
            QIcon('images/humanchat.png'), "人类的社交，比如在线聊天",
            self, shortcut="Ctrl+F", statusTip="人类的社交，比如在线聊天",
            triggered=self.ShowHumanChatStack, iconText="人类社交")

        self.workflowAction = QAction(
            QIcon('images/workflow.png'), "工作流",
            self, shortcut="Ctrl+F", statusTip="工作流",
            triggered=self.ShowWorkFlowStack, iconText="工作流")

        self.contactAction = QAction(
            QIcon(':/images/bringtofront.png'), "&Contact",
            self, shortcut="Ctrl+F", statusTip="通讯录",
            triggered=self.bringToFront, iconText="通讯录")

        self.settingAction = QAction(
            QIcon('images/setting.png'), "系统管理",
            self, shortcut="Ctrl+F", statusTip="系统管理",
            triggered=self.ShowSettingStack, iconText="系统管理")

        self.syshelpAction = QAction(
            QIcon('images/help.png'), "系统帮助",
            self, shortcut="Ctrl+H", statusTip="系统帮助",
            triggered=self.openwebhelp, iconText="系统帮助")

        self.exitAction = QAction("E&xit", self, shortcut="Ctrl+X",
                                  statusTip="Quit Scenediagram example", triggered=self.close)

        self.boldAction = QAction(QIcon(':/images/bold.png'),
                                  "Bold", self, checkable=True, shortcut="Ctrl+B",
                                  triggered=self.handleFontChange)

        self.italicAction = QAction(QIcon(':/images/italic.png'),
                                    "Italic", self, checkable=True, shortcut="Ctrl+I",
                                    triggered=self.handleFontChange)

        self.underlineAction = QAction(
            QIcon(':/images/underline.png'), "Underline", self,
            checkable=True, shortcut="Ctrl+U",
            triggered=self.handleFontChange)

        self.aboutAction = QAction("A&bout", self, shortcut="Ctrl+B",
                                   triggered=self.about)

    def createMenus(self):
        pass
        # self.fileMenu = self.menuBar().addMenu("开始(&F)")
        # self.fileMenu.addAction(self.exitAction)
        # self.fileMenu.setVisible(False)

        # self.itemMenu = self.menuBar().addMenu("账户(&A)")
        # self.itemMenu.addAction(self.deleteAction)
        # self.itemMenu.addSeparator()
        # self.itemMenu.addAction(self.toFrontAction)
        # self.itemMenu.addAction(self.sendBackAction)
        #
        # self.aboutMenu = self.menuBar().addMenu("查看(&V)")
        # self.aboutMenu.addAction(self.aboutAction)
        #
        # self.aboutMenu = self.menuBar().addMenu("帮助(&H)")
        # self.aboutMenu.addAction(self.aboutAction)

    def createToolbars(self):
        # Create Ai Toolbar
        ai_toolbar = QToolBar("Ai")
        ai_toolbar.addAction(self.ai2meAction)
        ai_toolbar.addAction(self.ai2aiAction)
        # ai_toolbar.addAction(self.chatAction)
        ai_toolbar.addAction(self.workflowAction)
        ai_toolbar.addAction(self.kmAction)
        ai_toolbar.addAction(self.pluginAction)
        ai_toolbar.setToolButtonStyle(Qt.ToolButtonTextUnderIcon)
        ai_toolbar.setFixedHeight(350)
        self.aiToolBar = self.addToolBar(Qt.LeftToolBarArea, ai_toolbar)

        # Create setting Toolbar
        setting_toolbar = QToolBar("Human")

        setting_toolbar.addAction(self.settingAction)
        setting_toolbar.addAction(self.syshelpAction)
        setting_toolbar.setToolButtonStyle(Qt.ToolButtonTextUnderIcon)
        self.settingToolBar = self.addToolBar(Qt.LeftToolBarArea, setting_toolbar)

        # 创建 AI Toolbar
        # ai2_toolbar = QToolBar("Ai2")
        # self.ai2meAction2 = QAction("AI to Me", self)
        # self.ai2aiAction2 = QAction("AI to AI", self)
        # self.chatAction2 = QAction("Chat", self)
        # ai2_toolbar.addAction(self.ai2meAction2)
        # ai2_toolbar.addAction(self.ai2aiAction2)
        # ai2_toolbar.addAction(self.chatAction2)
        # ai2_toolbar.setToolButtonStyle(Qt.ToolButtonTextUnderIcon)
        # ai2_toolbar.setFixedHeight(250)
        # self.aiToolBar2 = self.addToolBar(Qt.LeftToolBarArea, ai2_toolbar)

        # 创建一个垂直的工具栏容器
        toolbar_container = QToolBar()
        toolbar_container.setOrientation(Qt.Vertical)
        toolbar_container.addWidget(ai_toolbar)

        # toolbar_container.addWidget(ai2_toolbar)

        # 添加一个伸缩项，将 setting_toolbar 推到底部
        spacer = QWidget()
        spacer.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Expanding)
        toolbar_container.addWidget(spacer)

        toolbar_container.addWidget(setting_toolbar)


        # 将工具栏容器添加到主窗口的左侧
        self.addToolBar(Qt.LeftToolBarArea, toolbar_container)

    def create_install_plugin_button(self, plugin_data, image):

        plugin_name = plugin_data["name"]
        button = QToolButton()
        button.setText(plugin_name)
        button.setIcon(QIcon(image))
        button.setIconSize(QSize(50, 50))
        button.setCheckable(True)
        button.clicked.connect(lambda: self.plugin_install_dialog(plugin_data))
        self.buttonGroup_Plugin_install.addButton(button)

        layout = QGridLayout()
        layout.addWidget(button, 0, 0, Qt.AlignHCenter)
        layout.addWidget(QLabel(plugin_name), 1, 0, Qt.AlignCenter)

        widget = QWidget()
        widget.name = plugin_name
        widget.setLayout(layout)

        return widget

    def agentopendialog(self):
        model = QStandardItemModel()
        agents = query_AgentCfg_All(is_delete=0)
        header = ["显示", "user_id", "名称", "简介", "专长", "社交帐号"]
        model.setHorizontalHeaderLabels(header)
        row = 0
        for agent in agents:
            checkbox_item = QStandardItem()
            checkbox_item.setCheckable(True)
            checkbox_item.setCheckState(2 if agent.is_show else 0)
            model.setItem(row, 0, checkbox_item)

            newItem = QStandardItem(agent.user_id)
            print("agent.id:", agent.user_id)
            newItem.setFlags(newItem.flags() & ~Qt.ItemIsEditable)  # Make items non-editable
            model.setItem(row, 1, newItem)

            newItem = QStandardItem(agent.name)
            newItem.setFlags(newItem.flags() & ~Qt.ItemIsEditable)  # Make items non-editable
            model.setItem(row, 2, newItem)

            newItem2 = QStandardItem(agent.memo)
            newItem2.setFlags(newItem2.flags() & ~Qt.ItemIsEditable)  # Make items non-editable
            model.setItem(row, 3, newItem2)

            newItem3 = QStandardItem(agent.specialization)
            newItem3.setFlags(newItem3.flags() & ~Qt.ItemIsEditable)  # Make items non-editable
            model.setItem(row, 4, newItem3)

            newItem4 = QStandardItem(agent.snsaccount)
            newItem4.setFlags(newItem4.flags() & ~Qt.ItemIsEditable)  # Make items non-editable
            model.setItem(row, 5, newItem4)

            row += 1

        dialog = AgentFreezeTableDialog(model, self)
        dialog.exec_()

    def agentmultiopendialog(self):
        model = QStandardItemModel()
        agents = query_MutiAgentCfg_All(is_delete=0)
        header = ["显示", "group_id", "名称", "简介", "成员", "群主"]
        model.setHorizontalHeaderLabels(header)
        row = 0
        for agent in agents:
            checkbox_item = QStandardItem()
            checkbox_item.setCheckable(True)
            checkbox_item.setCheckState(2 if agent.is_show else 0)
            model.setItem(row, 0, checkbox_item)

            newItem = QStandardItem(agent.group_id)
            newItem.setFlags(newItem.flags() & ~Qt.ItemIsEditable)  # Make items non-editable
            model.setItem(row, 1, newItem)

            newItem = QStandardItem(agent.name)
            newItem.setFlags(newItem.flags() & ~Qt.ItemIsEditable)  # Make items non-editable
            model.setItem(row, 2, newItem)

            newItem2 = QStandardItem(agent.memo)
            newItem2.setFlags(newItem2.flags() & ~Qt.ItemIsEditable)  # Make items non-editable
            model.setItem(row, 3, newItem2)

            # newItem3 = QStandardItem(",".join([query_AgentCfg(user_id=user_id).name for user_id in agent.agents.split(",")]))
            newItem3 = QStandardItem(",".join(
                [query_AgentCfg(user_id=user_id).name for user_id in agent.agents.split(",")]) if agent.agents else "")
            newItem3.setFlags(newItem3.flags() & ~Qt.ItemIsEditable)  # Make items non-editable
            model.setItem(row, 4, newItem3)

            newItem4 = QStandardItem(query_AgentCfg(user_id=agent.agentcommander).name)
            newItem4.setFlags(newItem4.flags() & ~Qt.ItemIsEditable)  # Make items non-editable
            model.setItem(row, 5, newItem4)

            row += 1

        dialog = AgentMultiFreezeTableDialog(model, self)
        dialog.exec_()

    def aiopendialog(self):
        model = QStandardItemModel()
        agents = query_AiChatCfg_All(is_delete=0)
        header = ["", "user_id", "帐号", "昵称", "签名", "状态"]
        model.setHorizontalHeaderLabels(header)
        row = 0
        for agent in agents:
            checkbox_item = QStandardItem()
            checkbox_item.setCheckable(True)
            model.setItem(row, 0, checkbox_item)

            newItem = QStandardItem(agent.user_id)
            newItem.setFlags(newItem.flags() & ~Qt.ItemIsEditable)  # Make items non-editable
            model.setItem(row, 1, newItem)

            newItem = QStandardItem(agent.account)
            newItem.setFlags(newItem.flags() & ~Qt.ItemIsEditable)  # Make items non-editable
            model.setItem(row, 2, newItem)

            newItem2 = QStandardItem(agent.nickname)
            newItem2.setFlags(newItem2.flags() & ~Qt.ItemIsEditable)  # Make items non-editable
            model.setItem(row, 3, newItem2)

            newItem3 = QStandardItem(agent.sign)
            newItem3.setFlags(newItem3.flags() & ~Qt.ItemIsEditable)  # Make items non-editable
            model.setItem(row, 4, newItem3)

            newItem4 = QStandardItem(agent.status)
            newItem4.setFlags(newItem4.flags() & ~Qt.ItemIsEditable)  # Make items non-editable
            model.setItem(row, 5, newItem4)

            row += 1

        dialog = AiFreezeTableDialog(model, self)
        dialog.exec_()

    def humanopendialog(self):
        model = QStandardItemModel()
        agents = query_HumanChatCfg_All(is_delete=0)
        header = ["", "user_id", "帐号", "昵称", "签名", "状态"]
        model.setHorizontalHeaderLabels(header)
        row = 0
        for agent in agents:
            checkbox_item = QStandardItem()
            checkbox_item.setCheckable(True)
            model.setItem(row, 0, checkbox_item)

            newItem = QStandardItem(agent.user_id)
            newItem.setFlags(newItem.flags() & ~Qt.ItemIsEditable)  # Make items non-editable
            model.setItem(row, 1, newItem)

            newItem = QStandardItem(agent.account)
            newItem.setFlags(newItem.flags() & ~Qt.ItemIsEditable)  # Make items non-editable
            model.setItem(row, 2, newItem)

            newItem2 = QStandardItem(agent.nickname)
            newItem2.setFlags(newItem2.flags() & ~Qt.ItemIsEditable)  # Make items non-editable
            model.setItem(row, 3, newItem2)

            newItem3 = QStandardItem(agent.sign)
            newItem3.setFlags(newItem3.flags() & ~Qt.ItemIsEditable)  # Make items non-editable
            model.setItem(row, 4, newItem3)

            newItem4 = QStandardItem(agent.status)
            newItem4.setFlags(newItem4.flags() & ~Qt.ItemIsEditable)  # Make items non-editable
            model.setItem(row, 5, newItem4)

            row += 1

        dialog = HumanFreezeTableDialog(model)
        dialog.exec_()

    def kmopendialog(self):
        model = QStandardItemModel()
        agents = query_KMCfg_All(is_delete=0)
        header = ["", "km_id", "名称", "简介", "标签", "路径"]
        model.setHorizontalHeaderLabels(header)
        row = 0
        for agent in agents:
            checkbox_item = QStandardItem()
            checkbox_item.setCheckable(True)
            model.setItem(row, 0, checkbox_item)

            newItem = QStandardItem(agent.km_id)
            newItem.setFlags(newItem.flags() & ~Qt.ItemIsEditable)  # Make items non-editable
            model.setItem(row, 1, newItem)

            newItem = QStandardItem(agent.name)
            newItem.setFlags(newItem.flags() & ~Qt.ItemIsEditable)  # Make items non-editable
            model.setItem(row, 2, newItem)

            newItem = QStandardItem(agent.memo)
            newItem.setFlags(newItem.flags() & ~Qt.ItemIsEditable)  # Make items non-editable
            model.setItem(row, 3, newItem)

            newItem2 = QStandardItem(agent.label)
            newItem2.setFlags(newItem2.flags() & ~Qt.ItemIsEditable)  # Make items non-editable
            model.setItem(row, 4, newItem2)

            newItem3 = QStandardItem(agent.kmpath)
            newItem3.setFlags(newItem3.flags() & ~Qt.ItemIsEditable)  # Make items non-editable
            model.setItem(row, 5, newItem3)

            row += 1

        dialog = KmFreezeTableDialog(model, self)
        dialog.exec_()

    def kvopendialog(self):
        print("hello")
        self.keyvalue_manager = KeyValueManager(self)
        self.keyvalue_manager.exec_()

    def logopendialog(self):
        model = QStandardItemModel()
        agents = query_LogsMng_All(is_delete=0)
        header = ["", "logs_id", "内容", "类型", "时间"]
        model.setHorizontalHeaderLabels(header)
        row = 0
        for agent in agents:
            checkbox_item = QStandardItem()
            checkbox_item.setCheckable(True)
            model.setItem(row, 0, checkbox_item)

            newItem = QStandardItem(agent.logs_id)
            newItem.setFlags(newItem.flags() & ~Qt.ItemIsEditable)  # Make items non-editable
            model.setItem(row, 1, newItem)

            newItem = QStandardItem(agent.content)
            newItem.setFlags(newItem.flags() & ~Qt.ItemIsEditable)  # Make items non-editable
            model.setItem(row, 2, newItem)

            newItem = QStandardItem(agent.type)
            newItem.setFlags(newItem.flags() & ~Qt.ItemIsEditable)  # Make items non-editable
            model.setItem(row, 3, newItem)

            newItem2 = QStandardItem(str(agent.create_time))
            newItem2.setFlags(newItem2.flags() & ~Qt.ItemIsEditable)  # Make items non-editable
            model.setItem(row, 4, newItem2)

            row += 1

        dialog = LogsFreezeTableDialog(model)
        dialog.exec_()

    def createCellWidgetAiChatMng(self, text, image):
        # agetnconfigdlg = FreezeTableDialog(self)
        agentcfgbutton = QToolButton()
        agentcfgbutton.setIcon(QIcon(image))
        agentcfgbutton.setIconSize(QSize(50, 50))
        agentcfgbutton.setCheckable(True)
        agentcfgbutton.clicked.connect(self.aiopendialog)

        # self.backgroundButtonGroup.addButton(agentcfgbutton)

        layout = QGridLayout()
        layout.addWidget(agentcfgbutton, 0, 0, Qt.AlignHCenter)
        layout.addWidget(QLabel(text), 1, 0, Qt.AlignCenter)

        widget = QWidget()
        widget.setLayout(layout)

        return widget

    def createCellWidgetHumanChatMng(self, text, image):
        # agetnconfigdlg = FreezeTableDialog(self)
        agentcfgbutton = QToolButton()
        agentcfgbutton.setIcon(QIcon(image))
        agentcfgbutton.setIconSize(QSize(50, 50))
        agentcfgbutton.setCheckable(True)
        agentcfgbutton.clicked.connect(self.humanopendialog)

        # self.backgroundButtonGroup.addButton(agentcfgbutton)

        layout = QGridLayout()
        layout.addWidget(agentcfgbutton, 0, 0, Qt.AlignHCenter)
        layout.addWidget(QLabel(text), 1, 0, Qt.AlignCenter)

        widget = QWidget()
        widget.setLayout(layout)

        return widget

    def createCellWidgetKMMng(self, text, image):
        # agetnconfigdlg = FreezeTableDialog(self)
        agentcfgbutton = QToolButton()
        agentcfgbutton.setIcon(QIcon(image))
        agentcfgbutton.setIconSize(QSize(50, 50))
        agentcfgbutton.setCheckable(True)
        agentcfgbutton.clicked.connect(self.kmopendialog)

        # self.backgroundButtonGroup.addButton(agentcfgbutton)

        layout = QGridLayout()
        layout.addWidget(agentcfgbutton, 0, 0, Qt.AlignHCenter)
        layout.addWidget(QLabel(text), 1, 0, Qt.AlignCenter)

        widget = QWidget()
        widget.setLayout(layout)

        return widget

    def createCellWidgetKVMng(self, text, image):
        # agetnconfigdlg = FreezeTableDialog(self)
        agentcfgbutton = QToolButton()
        agentcfgbutton.setIcon(QIcon(image))
        agentcfgbutton.setIconSize(QSize(50, 50))
        agentcfgbutton.setCheckable(True)
        agentcfgbutton.clicked.connect(self.kvopendialog)

        # self.backgroundButtonGroup.addButton(agentcfgbutton)

        layout = QGridLayout()
        layout.addWidget(agentcfgbutton, 0, 0, Qt.AlignHCenter)
        layout.addWidget(QLabel(text), 1, 0, Qt.AlignCenter)

        widget = QWidget()
        widget.setLayout(layout)

        return widget

    def plugin_install_local(self):
        zip_file_path = self.setOpenFileName()
        if zip_file_path != "":
            self.plugin_install(zip_file_path)

    def create_install_plugin_local_button(self, text, image):

        button = QToolButton()
        button.setIcon(QIcon(image))
        button.setIconSize(QSize(50, 50))
        button.setCheckable(True)
        button.clicked.connect(self.plugin_install_local)

        self.buttonGroup_Plugin_install.addButton(button)

        layout = QGridLayout()
        layout.addWidget(button, 0, 0, Qt.AlignHCenter)
        layout.addWidget(QLabel(text), 1, 0, Qt.AlignCenter)

        widget = QWidget()
        widget.setLayout(layout)

        return widget

    def create_new_note_button(self, text, km_cfg, image):

        button = QToolButton()
        button.setIcon(QIcon('images/task.png'))
        button.setIconSize(QSize(50, 50))
        button.setCheckable(True)
        button.clicked.connect(lambda: self.create_new_note_editor(km_cfg))

        layout = QGridLayout()
        layout.addWidget(button, 0, 0, Qt.AlignHCenter)
        layout.addWidget(QLabel(text), 1, 0, Qt.AlignCenter)

        widget = QWidget()
        widget.setLayout(layout)

        return widget

    def create_new_note_editor(self, km_cfg):
        self.open_note_editor(km_cfg)

    def create_new_note_buttonbak(self, text, image):
        # agetnconfigdlg = FreezeTableDialog(self)
        agentcfgbutton = QToolButton()
        agentcfgbutton.setIcon(QIcon(image))
        agentcfgbutton.setIconSize(QSize(50, 50))
        agentcfgbutton.setCheckable(True)
        # agentcfgbutton.clicked.connect(lambda:self.createNewKM(kmrecord))

        # self.backgroundButtonGroup.addButton(agentcfgbutton)

        layout = QGridLayout()
        layout.addWidget(agentcfgbutton, 0, 0, Qt.AlignHCenter)
        layout.addWidget(QLabel(text), 1, 0, Qt.AlignCenter)

        widget = QWidget()
        widget.setLayout(layout)

        return widget

    def create_new_km_button(self, text, kmrecord, image):
        # agetnconfigdlg = FreezeTableDialog(self)
        agentcfgbutton = QToolButton()
        agentcfgbutton.setIcon(QIcon(image))
        agentcfgbutton.setIconSize(QSize(50, 50))
        agentcfgbutton.setCheckable(True)
        agentcfgbutton.clicked.connect(lambda: self.createNewKM(kmrecord))

        # self.backgroundButtonGroup.addButton(agentcfgbutton)

        layout = QGridLayout()
        layout.addWidget(agentcfgbutton, 0, 0, Qt.AlignHCenter)
        layout.addWidget(QLabel(text), 1, 0, Qt.AlignCenter)

        widget = QWidget()
        widget.setLayout(layout)

        return widget

    def createCellWidgetAgentMng(self, text, image):
        # agetnconfigdlg = FreezeTableDialog(self)
        agentcfgbutton = QToolButton()
        agentcfgbutton.setIcon(QIcon(image))
        agentcfgbutton.setIconSize(QSize(50, 50))
        agentcfgbutton.setCheckable(True)
        agentcfgbutton.clicked.connect(self.agentopendialog)

        self.settingbuttonGroup.addButton(agentcfgbutton)

        layout = QGridLayout()
        layout.addWidget(agentcfgbutton, 0, 0, Qt.AlignHCenter)
        layout.addWidget(QLabel(text), 1, 0, Qt.AlignCenter)

        widget = QWidget()
        widget.setLayout(layout)

        return widget

    def createCellWidgetAgentMultiMng(self, text, image):
        # agetnconfigdlg = FreezeTableDialog(self)
        agentcfgbutton = QToolButton()
        agentcfgbutton.setIcon(QIcon(image))
        agentcfgbutton.setIconSize(QSize(50, 50))
        agentcfgbutton.setCheckable(True)
        agentcfgbutton.clicked.connect(self.agentmultiopendialog)

        self.settingbuttonGroup.addButton(agentcfgbutton)

        layout = QGridLayout()
        layout.addWidget(agentcfgbutton, 0, 0, Qt.AlignHCenter)
        layout.addWidget(QLabel(text), 1, 0, Qt.AlignCenter)

        widget = QWidget()
        widget.setLayout(layout)

        return widget

    def createCellWidgetAgentMultiPrompt(self, text, image):
        # agetnconfigdlg = FreezeTableDialog(self)
        agentcfgbutton = QToolButton()
        agentcfgbutton.setIcon(QIcon(image))
        agentcfgbutton.setIconSize(QSize(50, 50))
        agentcfgbutton.setCheckable(True)
        # agentcfgbutton.clicked.connect(self.agentmultiopendialog)
        agentcfgbutton.clicked.connect(lambda: self.show_prompt_list("提示词列表"))

        self.settingbuttonGroup.addButton(agentcfgbutton)

        layout = QGridLayout()
        layout.addWidget(agentcfgbutton, 0, 0, Qt.AlignHCenter)
        layout.addWidget(QLabel(text), 1, 0, Qt.AlignCenter)

        widget = QWidget()
        widget.setLayout(layout)

        return widget

    def createCellWidgetAgentMultiEval(self, text, image):
        # agetnconfigdlg = FreezeTableDialog(self)
        agentcfgbutton = QToolButton()
        agentcfgbutton.setIcon(QIcon(image))
        agentcfgbutton.setIconSize(QSize(50, 50))
        agentcfgbutton.setCheckable(True)
        # agentcfgbutton.clicked.connect(self.agentmultiopendialog)
        agentcfgbutton.clicked.connect(lambda: self.show_eval_list("问题列表"))

        self.settingbuttonGroup.addButton(agentcfgbutton)

        layout = QGridLayout()
        layout.addWidget(agentcfgbutton, 0, 0, Qt.AlignHCenter)
        layout.addWidget(QLabel(text), 1, 0, Qt.AlignCenter)

        widget = QWidget()
        widget.setLayout(layout)

        return widget

    def createNewKM(self, kmrecord):
        filepath = self.setOpenFileName()
        filename = Path(filepath).name
        kmrecord = query_KMCfg(km_id=kmrecord.km_id)
        km_path = kmrecord.kmpath

        if filename != "":
            # doc_directory = os.path.join("km",km_path,"doc")
            doc_directory = os.path.join(os.getcwd(), "km", km_path, "doc")
            if not os.path.exists(doc_directory):
                os.makedirs(doc_directory)
            shutil.copy(filepath, doc_directory)
            # persist_directory = os.path.join("km",km_path,"vector")
            persist_directory = os.path.join(os.getcwd(), "km", km_path, "vector")
            if not os.path.exists(persist_directory):
                os.makedirs(persist_directory)
            embedding_model_name = kmrecord.embeddingmodel
            # embedding_model_name = 'shibing624/text2vec-bge-large-chinese'
            if embedding_model_name.lower() == "openai":
                emb_type = "openai"
            else:
                emb_type = "other"
            chunk_size = kmrecord.textblocklength
            chunk_overlap = kmrecord.overlaplength

            km_id = kmrecord.km_id
            filename = filename
            filenum = 1

            if kmrecord.vectorization == 1 and kmrecord.stopvectorization == 1:
                # 如果可向量化且暂停了向量化则需要等待向量化
                waitvectorization = True
            else:
                waitvectorization = False

            record_id = add_KMData(km_id, filename, filenum, chunk_size, chunk_overlap,waitvectorization)
            print(filename)
            km_list = self.kmlist_list[kmrecord.km_id]
            km_list.addItem(filename, record_id)

            if kmrecord.vectorization == 1 and kmrecord.stopvectorization == 0:
                # 如果可向量化且没有暂停向量化则需要向量化

                self.thread = WorkerThread(filepath, persist_directory, embedding_model_name, emb_type, chunk_size,
                                           chunk_overlap)
                self.thread.finished.connect(self.on_thread_finished)  # 连接信号
                self.thread.start()

    def on_thread_finished(self):
        """处理线程完成的信号"""
        print("线程已完成，准备清理")
        self.thread.quit()  # 请求线程退出
        self.thread.wait()  # 等待线程结束
        del self.thread  # 删除线程对象（如果需要）

    def setOpenFileName(self):
        openFileNameLabel = ""
        options = QFileDialog.Options()
        native = True
        if not native:
            options |= QFileDialog.DontUseNativeDialog
        fileName, _ = QFileDialog.getOpenFileName(self,
                                                  "QFileDialog.getOpenFileName()", openFileNameLabel,
                                                  "All Files (*);;Text Files (*.txt)", options=options)
        if fileName:
            openFileNameLabel = fileName
        print(openFileNameLabel)
        return openFileNameLabel

    def setOpenFileNames(self):
        openFilesPath = ""
        openFileNamesLabel = ""
        options = QFileDialog.Options()
        native = True
        if not native:
            options |= QFileDialog.DontUseNativeDialog
        files, _ = QFileDialog.getOpenFileNames(self,
                                                "QFileDialog.getOpenFileNames()", openFilesPath,
                                                "All Files (*);;Text Files (*.txt)", options=options)
        if files:
            openFilesPath = files[0]
            openFileNamesLabel = ("[%s]" % ', '.join(files))
        print(openFileNamesLabel)
        return openFileNamesLabel

    def open_agent_task_chat(self, agent):
        agent_cfg = agent.agent_cfg
        print("in createDialog")
        # if not self.dialog:
        # self.dialog = QDialog()
        if agent_cfg.user_id in self.agent_chat_window_list:
            dialog = self.agent_chat_window_list[agent_cfg.user_id]
        else:

            dialog = QWidget(self)  # 需要吧application作为父对象引入后面的流程中
            dialog.setWindowIcon(QIcon("images/mail.png"))

            msg = TaskPage(self, agent)
            msg.setObjectName('TaskPageObject')
            layout = QVBoxLayout(dialog)
            layout.addWidget(msg)
            dialog.setLayout(layout)
            # self.dialog.setWindowTitle(self.dialog.tr("Chat with ") + ai_chat_cfg.name)
            # self.dialog.show() #orgok
            # self.dialog.raise_() #orgok
            print("goingaddconver")
            self.conversation_pages.addWidget(dialog)
            print("goingaddconver2")
            # self.mainwindow.conversation_pages.setCurrentIndex(2) #setCurrentWidget
            self.agent_chat_window_list[agent_cfg.user_id] = dialog
        taskPage = dialog.findChild(TaskPage, "TaskPageObject")
        taskPage.new_task()
        taskPage.messageEdit.setFocus()
        self.conversation_pages.setCurrentWidget(dialog)

    def open_note_editor(self, km_cfg, id=0):

        if km_cfg.km_id in self.km_note_window_list:
            dialog = self.km_note_window_list[km_cfg.km_id]
        else:
            dialog = QWidget(self)  # 需要吧application作为父对象引入后面的流程中
            dialog.setWindowIcon(QIcon("images/mail.png"))
            layout = QVBoxLayout(dialog)

            editor = NoteEditor(self)

            editor.setObjectName('NoteEditorObject')

            editor.show()

            layout.addWidget(editor)
            dialog.setLayout(layout)
            self.km_note_window_list[km_cfg.km_id] = dialog

        self.conversation_pages.addWidget(dialog)

        self.conversation_pages.setCurrentWidget(dialog)

        note_editor = dialog.findChild(QMainWindow, "NoteEditorObject")

        note_editor.record_id = id
        note_editor.km_id = km_cfg.km_id
        note_editor.km_cfg = km_cfg
        note_editor.loadFile()

    def open_exist_agent_task_chat(self, agent):
        agent_cfg = agent.agent_cfg
        print("in createDialog")
        # if not self.dialog:
        # self.dialog = QDialog()
        if agent_cfg.user_id in self.agent_chat_window_list:
            dialog = self.agent_chat_window_list[agent_cfg.user_id]
        else:

            dialog = QWidget(self)  # 需要吧application作为父对象引入后面的流程中
            dialog.setWindowIcon(QIcon("images/mail.png"))

            msg = TaskPage(self, agent)
            msg.setObjectName('TaskPageObject')
            layout = QVBoxLayout(dialog)
            layout.addWidget(msg)
            dialog.setLayout(layout)
            # self.dialog.setWindowTitle(self.dialog.tr("Chat with ") + ai_chat_cfg.name)
            # self.dialog.show() #orgok
            # self.dialog.raise_() #orgok
            print("goingaddconver")
            self.conversation_pages.addWidget(dialog)
            print("goingaddconver2")
            # self.mainwindow.conversation_pages.setCurrentIndex(2) #setCurrentWidget
            self.agent_chat_window_list[agent_cfg.user_id] = dialog
            taskPage = dialog.findChild(TaskPage, "TaskPageObject")
            taskPage.new_task()
        self.conversation_pages.setCurrentWidget(dialog)

    def open_multi_agent_task_chat(self, agentcfg):
        if agentcfg.group_id in self.multi_agent_chat_window_list:
            dialog = self.multi_agent_chat_window_list[agentcfg.group_id]
        else:

            dialog = QWidget(self)  # 需要吧application作为父对象引入后面的流程中
            dialog.setWindowIcon(QIcon("images/mail.png"))

            msg = TaskPageGroup(self, agentcfg)
            msg.setObjectName('TaskPageGroupObject')
            layout = QVBoxLayout(dialog)
            layout.addWidget(msg)
            dialog.setLayout(layout)
            self.conversation_pages.addWidget(dialog)
            self.multi_agent_chat_window_list[agentcfg.group_id] = dialog
        taskPage = dialog.findChild(TaskPageGroup, "TaskPageGroupObject")
        taskPage.new_task()
        self.conversation_pages.setCurrentWidget(dialog)

    def plugin_install_dialog(self, plugin_data):
        plugin_name = plugin_data["name"]
        plugin_version = plugin_data["version"]
        plugin_company = plugin_data["company"]
        plugin_description = plugin_data["description"]
        plugin_url = plugin_data["url"]
        message_box = QMessageBox()
        message_box.setWindowTitle("您是否要安装该插件？")
        message_box.setText(
            "名称：" + plugin_name + ":" + plugin_version + "\n" + "公司：" + plugin_company + "\n" + "说明：" + plugin_description)

        message_box.setStandardButtons(QMessageBox.Ok | QMessageBox.Cancel)
        message_box.setDefaultButton(QMessageBox.Ok)

        # 显示消息框，并获取用户的响应
        user_response = message_box.exec_()

        # 根据用户的响应进行处理
        if user_response == QMessageBox.Ok:
            print("User clicked OK")
            file_name = os.path.basename(plugin_url)
            file__without_extension = os.path.splitext(file_name)[0]
            file_extension = os.path.splitext(file_name)[1]
            file_path = os.path.join(Path(__file__).resolve().parent.parent, "download", file_name)

            if os.path.exists(file_path):
                current_timestamp = str(time.time()).replace('.', '')
                file_name = file__without_extension + current_timestamp + file_extension
                file_path = os.path.join(Path(__file__).resolve().parent.parent, "download", file_name)
            self.download_file(plugin_url, file_path)
            self.plugin_install(file_path)
        else:
            print("User clicked Cancel")

    def plugin_install(self, zip_file_path):

        file__without_extension = os.path.splitext(os.path.basename(zip_file_path))[0]
        extract_to_path = os.path.join(Path(__file__).resolve().parent.parent, "download", "temp",
                                       file__without_extension)
        self.unzip_file(zip_file_path, extract_to_path)
        print("install.....")
        message_box = QMessageBox()
        message_box.setWindowTitle("提示")
        message_box.setText("安装成功!")

        message_box.setStandardButtons(QMessageBox.Ok)
        # message_box.setDefaultButton(QMessageBox.Ok)
        user_response = message_box.exec_()
        pass

    def createTaskGroup(self, agent):
        print("in createDialogGroup")
        # if not self.dialog:
        # self.dialog = QDialog()
        if agent.group_id in self.muti_agent_chat_window_list:
            dialog = self.muti_agent_chat_window_list[agent.group_id]
        else:
            dialog = QWidget(self)  # 需要吧application作为父对象引入后面的流程中
            dialog.setWindowIcon(QIcon("images/mail.png"))

            msg = TaskPageGroup(dialog, None, agent.group_id, agent.name)
            layout = QVBoxLayout(dialog)
            layout.addWidget(msg)
            dialog.setLayout(layout)
            # self.dialog.setWindowTitle(self.dialog.tr("Chat with ") + "wangwang")
            # self.dialog.show() #orgok
            # self.dialog.raise_() #orgok
            print("goingaddconver")
            self.conversation_pages.addWidget(dialog)
            print("goingaddconver2")
            # self.mainwindow.conversation_pages.setCurrentIndex(2) #setCurrentWidget
            self.muti_agent_chat_window_list[agent.group_id] = dialog
        self.conversation_pages.setCurrentWidget(dialog)
        print("goingaddconver3")

    def create_new_task_button(self, text, agent, diagramType):

        button = QToolButton()
        button.setIcon(QIcon('images/task.png'))
        button.setIconSize(QSize(50, 50))
        button.setCheckable(True)
        button.clicked.connect(lambda: self.create_new_task_chat(agent))

        self.buttonGroup.addButton(button, diagramType)  # to toggle button status改变按钮点击的状态

        layout = QGridLayout()
        layout.addWidget(button, 0, 0, Qt.AlignHCenter)
        layout.addWidget(QLabel(text), 1, 0, Qt.AlignCenter)

        widget = QWidget()
        widget.setLayout(layout)

        return widget

    def create_new_task_chat(self, agent):
        agent_cfg = agent.agent_cfg
        taskList = self.tasklist_list[agent_cfg.user_id]
        taskList.deselect_all_items()
        self.open_agent_task_chat(agent)

    def create_new_group_task_button(self, text, agentcfg, diagramType):
        # item = DiagramItem(diagramType, self.itemMenu)
        # icon = QIcon(item.image())

        button = QToolButton()
        button.setIcon(QIcon('images/task.png'))
        button.setIconSize(QSize(50, 50))
        button.setCheckable(True)
        button.clicked.connect(lambda: self.open_multi_agent_task_chat(agentcfg))

        self.buttonGroup.addButton(button, diagramType)

        layout = QGridLayout()
        layout.addWidget(button, 0, 0, Qt.AlignHCenter)
        layout.addWidget(QLabel(text), 1, 0, Qt.AlignCenter)

        widget = QWidget()
        widget.setLayout(layout)

        return widget

    def createCellWidget(self, text, diagramType):
        # item = DiagramItem(diagramType, self.itemMenu)
        # icon = QIcon(item.image())
        agetnconfigdlg = AgentConfigDialog(self)
        agentcfgbutton = QToolButton()
        agentcfgbutton.setIcon(QIcon('images/moresetting.png'))
        agentcfgbutton.setIconSize(QSize(50, 50))
        agentcfgbutton.setCheckable(True)
        agentcfgbutton.clicked.connect(agetnconfigdlg.exec_)

        self.buttonGroup.addButton(agentcfgbutton, diagramType)

        layout = QGridLayout()
        layout.addWidget(agentcfgbutton, 0, 0, Qt.AlignHCenter)
        layout.addWidget(QLabel(text), 1, 0, Qt.AlignCenter)

        widget = QWidget()
        widget.setLayout(layout)

        return widget

    def createCellWidgetLogMng(self, text, diagramType):
        agentcfgbutton = QToolButton()
        agentcfgbutton.setIcon(QIcon('images/moresetting.png'))
        agentcfgbutton.setIconSize(QSize(50, 50))
        agentcfgbutton.setCheckable(True)
        agentcfgbutton.clicked.connect(self.logopendialog)

        self.buttonGroup.addButton(agentcfgbutton, diagramType)

        layout = QGridLayout()
        layout.addWidget(agentcfgbutton, 0, 0, Qt.AlignHCenter)
        layout.addWidget(QLabel(text), 1, 0, Qt.AlignCenter)

        widget = QWidget()
        widget.setLayout(layout)

        return widget

    def createCellWidgetGeneralCfg(self, text, diagramType):
        # item = DiagramItem(diagramType, self.itemMenu)
        # icon = QIcon(item.image())
        agetnconfigdlg = ConfigDialog(self)
        agentcfgbutton = QToolButton()
        agentcfgbutton.setIcon(QIcon('images/moresetting.png'))
        agentcfgbutton.setIconSize(QSize(50, 50))
        agentcfgbutton.setCheckable(True)
        agentcfgbutton.clicked.connect(agetnconfigdlg.exec_)

        self.buttonGroup.addButton(agentcfgbutton, diagramType)

        layout = QGridLayout()
        layout.addWidget(agentcfgbutton, 0, 0, Qt.AlignHCenter)
        layout.addWidget(QLabel(text), 1, 0, Qt.AlignCenter)

        widget = QWidget()
        widget.setLayout(layout)

        return widget

    def create_human_cfg_button(self, text, agent, diagramType):
        agentconfigdlg = HumanChatConfigDialog(self, agent)
        self.human_chat_cfg_dialog_list[agent.user_id] = agentconfigdlg
        agentcfgbutton = QToolButton()
        agentcfgbutton.setIcon(QIcon('images/moresetting.png'))
        agentcfgbutton.setIconSize(QSize(50, 50))
        agentcfgbutton.setCheckable(True)
        agentconfigdlg.configured.connect(self.on_configured_human)
        agentcfgbutton.clicked.connect(agentconfigdlg.exec_)

        self.buttonGroup.addButton(agentcfgbutton, diagramType)

        layout = QGridLayout()
        layout.addWidget(agentcfgbutton, 0, 0, Qt.AlignHCenter)
        layout.addWidget(QLabel(text), 1, 0, Qt.AlignCenter)

        widget = QWidget()
        widget.setLayout(layout)

        return widget

    def create_km(self):
        print("create agent")
        agetnconfigdlg = KmConfigDialog(self)
        agetnconfigdlg.exec_()

    def createCellWidgetKMNew(self, text, image):
        # item = DiagramItem(diagramType, self.itemMenu)
        # icon = QIcon(item.image())

        agentcfgbutton = QToolButton()
        agentcfgbutton.setIcon(QIcon(image))
        agentcfgbutton.setIconSize(QSize(50, 50))
        agentcfgbutton.setCheckable(True)
        agentcfgbutton.clicked.connect(self.create_km)

        self.buttonGroup.addButton(agentcfgbutton)

        layout = QGridLayout()
        layout.addWidget(agentcfgbutton, 0, 0, Qt.AlignHCenter)
        layout.addWidget(QLabel(text), 1, 0, Qt.AlignCenter)

        widget = QWidget()
        widget.setLayout(layout)

        return widget

    def create_note_cfg_button(self, text, diagramType):
        # pass
        kmrecord = query_KMCfg(name="我的笔记")
        agentconfigdlg = KmConfigDialog(self, kmrecord)
        self.km_cfg_dialog_list[kmrecord.km_id] = agentconfigdlg
        agentcfgbutton = QToolButton()
        agentcfgbutton.setIcon(QIcon('images/moresetting.png'))
        agentcfgbutton.setIconSize(QSize(50, 50))
        agentcfgbutton.setCheckable(True)
        agentcfgbutton.clicked.connect(agentconfigdlg.exec_)

        self.buttonGroup.addButton(agentcfgbutton, diagramType)

        layout = QGridLayout()
        layout.addWidget(agentcfgbutton, 0, 0, Qt.AlignHCenter)
        layout.addWidget(QLabel(text), 1, 0, Qt.AlignCenter)

        widget = QWidget()
        widget.setLayout(layout)

        return widget

    def create_km_cfg_button(self, text, kmrecord, diagramType):
        agentconfigdlg = KmConfigDialog(self, kmrecord)
        self.km_cfg_dialog_list[kmrecord.km_id] = agentconfigdlg
        agentcfgbutton = QToolButton()
        agentcfgbutton.setIcon(QIcon('images/moresetting.png'))
        agentcfgbutton.setIconSize(QSize(50, 50))
        agentcfgbutton.setCheckable(True)
        agentcfgbutton.clicked.connect(agentconfigdlg.exec_)

        self.buttonGroup.addButton(agentcfgbutton, diagramType)

        layout = QGridLayout()
        layout.addWidget(agentcfgbutton, 0, 0, Qt.AlignHCenter)
        layout.addWidget(QLabel(text), 1, 0, Qt.AlignCenter)

        widget = QWidget()
        widget.setLayout(layout)

        return widget

    def create_ai_cfg_button(self, text, agent, diagramType):
        agentconfigdlg = AiChatConfigDialog(self, agent)
        self.ai_chat_cfg_dialog_list[agent.user_id] = agentconfigdlg
        agentcfgbutton = QToolButton()
        agentcfgbutton.setIcon(QIcon('images/moresetting.png'))
        agentcfgbutton.setIconSize(QSize(50, 50))
        agentcfgbutton.setCheckable(True)
        agentconfigdlg.configured.connect(self.on_configured_ai)
        agentcfgbutton.clicked.connect(agentconfigdlg.exec_)

        self.buttonGroup.addButton(agentcfgbutton, diagramType)

        layout = QGridLayout()
        layout.addWidget(agentcfgbutton, 0, 0, Qt.AlignHCenter)
        layout.addWidget(QLabel(text), 1, 0, Qt.AlignCenter)

        widget = QWidget()
        widget.setLayout(layout)

        return widget

    def createCellWidget(self, text, diagramType):
        # item = DiagramItem(diagramType, self.itemMenu)
        # icon = QIcon(item.image())
        agetnconfigdlg = AgentConfigDialog(self)
        agentcfgbutton = QToolButton()
        agentcfgbutton.setIcon(QIcon('images/moresetting.png'))
        agentcfgbutton.setIconSize(QSize(50, 50))
        agentcfgbutton.setCheckable(True)
        agentcfgbutton.clicked.connect(agetnconfigdlg.exec_)

        self.buttonGroup.addButton(agentcfgbutton, diagramType)

        layout = QGridLayout()
        layout.addWidget(agentcfgbutton, 0, 0, Qt.AlignHCenter)
        layout.addWidget(QLabel(text), 1, 0, Qt.AlignCenter)

        widget = QWidget()
        widget.setLayout(layout)

        return widget

    def open_multi_agent_cfg_dialog(self, agent):
        group_id = agent.group_id
        agent_group_cfg = query_MutiAgentCfg(group_id=group_id)
        agentconfigdlg = AgentMutiConfigDialog(self, agent_group_cfg)
        agentconfigdlg.exec_()

    def create_muti_agent_cfg_button(self, text, agent, diagramType):
        # item = DiagramItem(diagramType, self.itemMenu)
        # icon = QIcon(item.image())
        # agentconfigdlg = AgentMutiConfigDialog(self, agent)
        agentcfgbutton = QToolButton()
        agentcfgbutton.setIcon(QIcon('images/moresetting.png'))
        agentcfgbutton.setIconSize(QSize(50, 50))
        agentcfgbutton.setCheckable(True)
        agentcfgbutton.clicked.connect(lambda: self.open_multi_agent_cfg_dialog(agent))

        self.buttonGroup.addButton(agentcfgbutton, diagramType)

        layout = QGridLayout()
        layout.addWidget(agentcfgbutton, 0, 0, Qt.AlignHCenter)
        layout.addWidget(QLabel(text), 1, 0, Qt.AlignCenter)

        widget = QWidget()
        widget.setLayout(layout)

        return widget

    def open_agent_cfg_dialog(self, agent):

        user_id = agent.agent_cfg.user_id
        agent_cfg = query_AgentCfg(user_id=user_id)
        agent = Agent(agent_cfg)
        agentconfigdlg = AgentConfigDialog(self, agent)

        self.agent_cfg_dialog_list[agent_cfg.user_id] = agentconfigdlg
        agentconfigdlg.exec_()

    def create_agent_cfg_button(self, text, agent, diagramType):
        # item = DiagramItem(diagramType, self.itemMenu)
        # icon = QIcon(item.image())
        agent_cfg = agent.agent_cfg
        # agentconfigdlg = AgentConfigDialog(self, agent)
        # self.agent_cfg_dialog_list[agent_cfg.user_id] = agentconfigdlg
        agentcfgbutton = QToolButton()
        agentcfgbutton.setIcon(QIcon('images/moresetting.png'))
        agentcfgbutton.setIconSize(QSize(50, 50))
        agentcfgbutton.setCheckable(True)
        agentcfgbutton.clicked.connect(lambda: self.open_agent_cfg_dialog(agent))

        self.buttonGroup.addButton(agentcfgbutton, diagramType)

        layout = QGridLayout()
        layout.addWidget(agentcfgbutton, 0, 0, Qt.AlignHCenter)
        layout.addWidget(QLabel(text), 1, 0, Qt.AlignCenter)

        widget = QWidget()
        widget.setLayout(layout)

        return widget

    def create_agent(self):
        print("create agent")
        agetnconfigdlg = AgentConfigDialog(self)
        agetnconfigdlg.exec_()

    def createCellWidgetAgentNew(self, text, image):
        # item = DiagramItem(diagramType, self.itemMenu)
        # icon = QIcon(item.image())

        agentcfgbutton = QToolButton()
        agentcfgbutton.setIcon(QIcon(image))
        agentcfgbutton.setIconSize(QSize(50, 50))
        agentcfgbutton.setCheckable(True)
        agentcfgbutton.clicked.connect(self.create_agent)

        self.settingbuttonGroup.addButton(agentcfgbutton)

        layout = QGridLayout()
        layout.addWidget(agentcfgbutton, 0, 0, Qt.AlignHCenter)
        layout.addWidget(QLabel(text), 1, 0, Qt.AlignCenter)

        widget = QWidget()
        widget.setLayout(layout)

        return widget

    def create_multi_agent(self):
        print("create agent")
        agetnconfigdlg = AgentMutiConfigDialog(self)
        agetnconfigdlg.exec_()

    def createCellWidgetAgentMultiNew(self, text, image):
        # item = DiagramItem(diagramType, self.itemMenu)
        # icon = QIcon(item.image())

        agentcfgbutton = QToolButton()
        agentcfgbutton.setIcon(QIcon(image))
        agentcfgbutton.setIconSize(QSize(50, 50))
        agentcfgbutton.setCheckable(True)
        agentcfgbutton.clicked.connect(self.create_multi_agent)

        self.settingbuttonGroup.addButton(agentcfgbutton)

        layout = QGridLayout()
        layout.addWidget(agentcfgbutton, 0, 0, Qt.AlignHCenter)
        layout.addWidget(QLabel(text), 1, 0, Qt.AlignCenter)

        widget = QWidget()
        widget.setLayout(layout)

        return widget

    def createCellWidgetAiChatNew(self, text, image):
        # item = DiagramItem(diagramType, self.itemMenu)
        # icon = QIcon(item.image())
        agentconfigdlg = AiChatConfigDialog(self)
        agentcfgbutton = QToolButton()
        agentcfgbutton.setIcon(QIcon(image))
        agentcfgbutton.setIconSize(QSize(50, 50))
        agentcfgbutton.setCheckable(True)
        agentconfigdlg.configured.connect(self.on_configured_ai)
        agentcfgbutton.clicked.connect(agentconfigdlg.exec_)

        self.buttonGroup.addButton(agentcfgbutton)

        layout = QGridLayout()
        layout.addWidget(agentcfgbutton, 0, 0, Qt.AlignHCenter)
        layout.addWidget(QLabel(text), 1, 0, Qt.AlignCenter)

        widget = QWidget()
        widget.setLayout(layout)

        return widget

    def createCellWidgetHumanChatNew(self, text, image):
        # item = DiagramItem(diagramType, self.itemMenu)
        # icon = QIcon(item.image())
        agetnconfigdlg = HumanChatConfigDialog(self)
        agentcfgbutton = QToolButton()
        agentcfgbutton.setIcon(QIcon(image))
        agentcfgbutton.setIconSize(QSize(50, 50))
        agentcfgbutton.setCheckable(True)
        agentcfgbutton.clicked.connect(agetnconfigdlg.exec_)

        self.buttonGroup.addButton(agentcfgbutton)

        layout = QGridLayout()
        layout.addWidget(agentcfgbutton, 0, 0, Qt.AlignHCenter)
        layout.addWidget(QLabel(text), 1, 0, Qt.AlignCenter)

        widget = QWidget()
        widget.setLayout(layout)

        return widget

        # for plugin

    def __description(self) -> str:
        return "Create your own anime meta data"

    def __usage(self) -> str:
        return "vrv-meta.py --service vrv"

    def __init_cli(self) -> argparse:
        parser = argparse.ArgumentParser(description=self.__description(), usage=self.__usage())
        parser.add_argument(
            '-l', '--log', default='DEBUG', help="""
                Specify log level which should use. Default will always be DEBUG, choose between the following options
                CRITICAL, ERROR, WARNING, INFO, DEBUG
                """
        )
        parser.add_argument(
            '-d', '--directory', default=f'{FileSystem.get_plugins_directory()}', help="""
                (Optional) Supply a directory where plugins should be loaded from. The default is ./plugins
                """
        )
        return parser

    def __print_program_end(self) -> None:
        print("-----------------------------------")
        print("End of execution")
        print("-----------------------------------")

    def __init_app(self, parameters: dict) -> None:
        return PluginEngine(options=parameters).start()

    def show_plugin_cfg(self, plugin_full_name):
        print("opening baichuan connector...")
        __cli_args = self.__init_cli().parse_args()
        print("cjrok")
        print(__cli_args.log)
        print("cjrok2")
        # delegate = self.__init_app({
        #     'log_level': __cli_args.log,
        #     'directory': __cli_args.directory
        # })

        delegate = global_plugin_list[plugin_full_name]

        if plugin_full_name == "函数管理器: 1.0.0":
            content = delegate.invoke(command=["open_config_dialog"], app=self)
        else:
            content = delegate.invoke(command=["open_config_dialog"])

    def show_plugin_tool_cfg(self, record):
        plugin = load_plugin_tool(self, record)
        plugin.open_config_dialog()

    def show_workflow_list(self, plugin_full_name):
        workflow_dialog = WorkFlowManager()
        workflow_dialog.setObjectName("workflowmanager")
        self.conversation_pages.addWidget(workflow_dialog)
        self.conversation_pages.setCurrentWidget(workflow_dialog)

    def show_task_schedule(self):
        task_schedule_dialog = TaskSchedule()
        task_schedule_dialog.setObjectName("taskschedule")
        self.conversation_pages.addWidget(task_schedule_dialog)
        self.conversation_pages.setCurrentWidget(task_schedule_dialog)


    def show_prompt_list(self, plugin_full_name):
        prompt_dialog = PromptManager(self)
        prompt_dialog.setObjectName("promptmanager")
        self.conversation_pages.addWidget(prompt_dialog)
        self.conversation_pages.setCurrentWidget(prompt_dialog)

    def show_eval_list(self, plugin_full_name):
        eval_dialog = ModelEvaluationDialog()
        eval_dialog.setObjectName("evalmanager")
        self.conversation_pages.addWidget(eval_dialog)
        self.conversation_pages.setCurrentWidget(eval_dialog)



    def show_function_list(self, type_str):

        fun_dialog = FunctionManager(type_str)
        fun_dialog.setObjectName("functionmanager")
        self.conversation_pages.addWidget(fun_dialog)
        self.conversation_pages.setCurrentWidget(fun_dialog)

    def show_skill_list(self,type_str):

        skill_dialog = SkillManager(type_str)
        skill_dialog.setObjectName("skillmanager")
        self.conversation_pages.addWidget(skill_dialog)
        self.conversation_pages.setCurrentWidget(skill_dialog)

    def create_plugin_skill_button(self, type_str, diagramType):

        button = QToolButton()
        button.setIcon(QIcon('images/plugin.png'))
        button.setIconSize(QSize(50, 50))
        button.setCheckable(True)
        if type_str=="1":
            button_label="已发布"
        else:
            button_label = "未发布"

        button.clicked.connect(lambda: self.show_skill_list(type_str))

        self.buttonGroup_Plugin.addButton(button, diagramType)
        # self.buttonGroup.addButton(button, diagramType)

        layout = QGridLayout()
        layout.addWidget(button, 0, 0, Qt.AlignHCenter)
        layout.addWidget(QLabel(button_label), 1, 0, Qt.AlignCenter)

        widget = QWidget()
        widget.setLayout(layout)

        return widget

    def create_plugin_function_button(self, type_str, diagramType):

        button = QToolButton()
        button.setIcon(QIcon('images/plugin.png'))
        button.setIconSize(QSize(50, 50))
        button.setCheckable(True)
        if type_str == "1":
            button_label = "已发布"
        else:
            button_label = "未发布"

        button.clicked.connect(lambda: self.show_function_list(type_str))

        self.buttonGroup_Plugin.addButton(button, diagramType)
        # self.buttonGroup.addButton(button, diagramType)

        layout = QGridLayout()
        layout.addWidget(button, 0, 0, Qt.AlignHCenter)
        layout.addWidget(QLabel(button_label), 1, 0, Qt.AlignCenter)

        widget = QWidget()
        widget.setLayout(layout)

        return widget

    def function_search(self, keyword, type_str="0"):
        # type_str:"0","1","2"
        print("keyword", keyword)

        if keyword == "$$$cjrok":
            type_str = "2"
        print(keyword)
        print("type_str", type_str)
        fun_dialog = FunctionManager(type_str)
        fun_dialog.setObjectName("functionmanager")
        self.conversation_pages.addWidget(fun_dialog)
        self.conversation_pages.setCurrentWidget(fun_dialog)

    def skill_search(self, keyword,type_str="0"):
        # type_str:"0","1","2"
        print("keyword",keyword)

        if keyword=="$$$cjrok":
            type_str="2"
        print(keyword)
        print("type_str",type_str)
        skill_dialog = SkillManager(type_str)
        skill_dialog.setObjectName("skillmanager")
        self.conversation_pages.addWidget(skill_dialog)
        self.conversation_pages.setCurrentWidget(skill_dialog)




    def create_plugin_cfg_button(self, record, diagramType):

        button = QToolButton()
        button.setIcon(QIcon('images/plugin.png'))
        button.setIconSize(QSize(50, 50))
        button.setCheckable(True)

        button.clicked.connect(lambda: self.show_plugin_cfg(record.name + ": " + record.version))

        self.buttonGroup_Plugin.addButton(button, diagramType)
        # self.buttonGroup.addButton(button, diagramType)

        layout = QGridLayout()
        layout.addWidget(button, 0, 0, Qt.AlignHCenter)
        layout.addWidget(QLabel(record.name), 1, 0, Qt.AlignCenter)

        widget = QWidget()
        # 增加名称
        widget.name = record.name
        widget.setLayout(layout)

        return widget

    def create_plugin_tool_cfg_button(self, record, diagramType):

        button = QToolButton()
        button.setIcon(QIcon('images/plugin.png'))
        button.setIconSize(QSize(50, 50))
        button.setCheckable(True)

        button.clicked.connect(lambda: self.show_plugin_tool_cfg(record))

        self.buttonGroup_Plugin.addButton(button, diagramType)
        # self.buttonGroup.addButton(button, diagramType)

        layout = QGridLayout()
        layout.addWidget(button, 0, 0, Qt.AlignHCenter)
        layout.addWidget(QLabel(record.name), 1, 0, Qt.AlignCenter)

        widget = QWidget()
        widget.name = record.name
        widget.setLayout(layout)

        return widget

    def create_workflow_cfg_button(self, diagramType):

        button = QToolButton()
        button.setIcon(QIcon('images/plugin.png'))
        button.setIconSize(QSize(50, 50))
        button.setCheckable(True)

        button.clicked.connect(lambda: self.show_workflow_list("工作流列表"))
        # button.clicked.connect(lambda: self.show_prompt_list("提示词管理"))
        self.buttonGroup_WorkFlow.addButton(button, diagramType)
        # self.buttonGroup.addButton(button, diagramType)

        layout = QGridLayout()
        layout.addWidget(button, 0, 0, Qt.AlignHCenter)
        layout.addWidget(QLabel("全部工作流"), 1, 0, Qt.AlignCenter)

        widget = QWidget()
        widget.setLayout(layout)

        return widget

    def create_task_schedule_button(self, diagramType):

        button = QToolButton()
        button.setIcon(QIcon('images/Calendar.png'))
        button.setIconSize(QSize(50, 50))
        button.setCheckable(True)

        button.clicked.connect(self.show_task_schedule)
        self.buttonGroup_WorkFlow.addButton(button, diagramType)

        layout = QGridLayout()
        layout.addWidget(button, 0, 0, Qt.AlignHCenter)
        layout.addWidget(QLabel("任务运行"), 1, 0, Qt.AlignCenter)

        widget = QWidget()
        widget.setLayout(layout)

        return widget


    def createCellWidgetnewkm(self, text, diagramType):
        # item = DiagramItem(diagramType, self.itemMenu)
        # icon = QIcon(item.image())

        button = QToolButton()
        button.setIcon(QIcon('images/fileplus.png'))
        button.setIconSize(QSize(50, 50))
        button.setCheckable(True)

        self.buttonGroup.addButton(button, diagramType)

        layout = QGridLayout()
        layout.addWidget(button, 0, 0, Qt.AlignHCenter)
        layout.addWidget(QLabel(text), 1, 0, Qt.AlignCenter)

        widget = QWidget()
        widget.setLayout(layout)

        return widget

    def show_add_buddy_dialog(self, ai_chat_cfg):

        print("going to add buddy")
        # self.add_buddy()
        jid = ai_chat_cfg.account
        current_connectorThread = self.connectorThread_list.get(ai_chat_cfg.user_id, None)
        current_buddyList = self.buddylist_list.get(ai_chat_cfg.user_id, None)
        if current_connectorThread is None:
            QMessageBox.critical(self, "警告", "该帐号尚未登录！", QMessageBox.Ok)
            return
        else:
            if current_connectorThread.isConnected == False:
                QMessageBox.critical(self, "警告", "该帐号尚未登录！", QMessageBox.Ok)
                return
        newBuddy = AddBuddyDialog(self, current_connectorThread.jabber_xmpp, list(current_buddyList.groups.keys()), "")
        newBuddy.show()

    def create_new_contact_group_button(self, text, agent, diagramType):
        button = QToolButton()
        button.setIcon(QIcon('images/addchat.png'))
        button.setIconSize(QSize(50, 50))
        button.setCheckable(True)
        button.clicked.connect(lambda: self.show_add_buddy_dialog(agent))

        self.buttonGroup.addButton(button, diagramType)

        layout = QGridLayout()
        layout.addWidget(button, 0, 0, Qt.AlignHCenter)
        layout.addWidget(QLabel(text), 1, 0, Qt.AlignCenter)

        widget = QWidget()
        widget.setLayout(layout)

        return widget

    def createColorMenu(self, slot, defaultColor):
        colors = [Qt.black, Qt.white, Qt.red, Qt.blue, Qt.yellow]
        names = ["black", "white", "red", "blue", "yellow"]

        colorMenu = QMenu(self)
        for color, name in zip(colors, names):
            action = QAction(self.createColorIcon(color), name, self,
                             triggered=slot)
            action.setData(QColor(color))
            colorMenu.addAction(action)
            if color == defaultColor:
                colorMenu.setDefaultAction(action)
        return colorMenu

    def createColorToolButtonIcon(self, imageFile, color):
        pixmap = QPixmap(50, 80)
        pixmap.fill(Qt.transparent)
        painter = QPainter(pixmap)
        image = QPixmap(imageFile)
        target = QRect(0, 0, 50, 60)
        source = QRect(0, 0, 42, 42)
        painter.fillRect(QRect(0, 60, 50, 80), color)
        painter.drawPixmap(target, image, source)
        painter.end()

        return QIcon(pixmap)

    def createColorIcon(self, color):
        pixmap = QPixmap(20, 20)
        painter = QPainter(pixmap)
        painter.setPen(Qt.NoPen)
        painter.fillRect(QRect(0, 0, 20, 20), color)
        painter.end()

        return QIcon(pixmap)

    def retranslateUi(self, MainWindow):
        MainWindow.setWindowTitle(QtWidgets.QApplication.translate("MainWindow", "Ai-SNS"))
        self.statusBox.addItem(QtGui.QIcon("images/status/available.png"),
                               QtWidgets.QApplication.translate("MainWindow", "Available"))
        self.statusBox.addItem(QtGui.QIcon("images/status/chat.png"),
                               QtWidgets.QApplication.translate("MainWindow", "Chat"))
        self.statusBox.addItem(QtGui.QIcon("images/status/busy.png"),
                               QtWidgets.QApplication.translate("MainWindow", "Do not disturb"))
        self.statusBox.addItem(QtGui.QIcon("images/status/away.png"),
                               QtWidgets.QApplication.translate("MainWindow", "Away"))
        self.statusBox.addItem(QtGui.QIcon("images/status/extended-away.png"),
                               QtWidgets.QApplication.translate("MainWindow", "Extended Away"))
        self.statusBox.addItem(QtGui.QIcon("images/status/offline.png"),
                               QtWidgets.QApplication.translate("MainWindow", "Offline"))
        # self.menuContacts.setTitle(QtWidgets.QApplication.translate("MainWindow", "开始(&A)"))
        # self.menuBuddies.setTitle(QtWidgets.QApplication.translate("MainWindow", "视图(&V)"))
        # self.menuAffichage.setTitle(QtWidgets.QApplication.translate("MainWindow", "帮助(&H)"))
        # self.menuHelp.setTitle(QtWidgets.QApplication.translate("MainWindow", "关于(&T)"))
        #
        # self.actionConnection.setText(QtWidgets.QApplication.translate("MainWindow", "登录"))
        # self.actionConnection.setShortcut(QtWidgets.QApplication.translate("MainWindow", "Ctrl+O"))
        # self.actionDeconnection.setText(QtWidgets.QApplication.translate("MainWindow", "登出"))
        # self.actionOffline_buddies.setText(QtWidgets.QApplication.translate("MainWindow", "帮助文档"))
        # self.actionAway_buddies.setText(QtWidgets.QApplication.translate("MainWindow", "在线帮助"))
        # self.togglechatbox.setText(QtWidgets.QApplication.translate("MainWindow", "切换视图"))
        # self.togglechatbox.setShortcut(QtWidgets.QApplication.translate("MainWindow", "Ctrl+G"))
        # self.actionShow_agent_homepage.setText(QtWidgets.QApplication.translate("MainWindow", "显示Agent主页"))
        # self.actionShow_ai_homepage.setText(QtWidgets.QApplication.translate("MainWindow", "显示Ai社交主页"))
        # self.actionShow_human_homepage.setText(QtWidgets.QApplication.translate("MainWindow", "显示人类社交主页"))
        # self.actionShow_km_homepage.setText(QtWidgets.QApplication.translate("MainWindow", "显示知识库主页"))
        # self.actionShow_plugin_homepage.setText(QtWidgets.QApplication.translate("MainWindow", "显示插件市场主页"))
        #
        # self.actionAbout.setText(QtWidgets.QApplication.translate("MainWindow", "关于Ai-SNS"))
        # self.actionAboutQt.setText(QtWidgets.QApplication.translate("MainWindow", "关于Qt"))
        # self.actionQuit.setText(QtWidgets.QApplication.translate("MainWindow", "关闭"))
        # self.actionQuit.setShortcut(QtWidgets.QApplication.translate("MainWindow", "Ctrl+Q"))
        # self.actionAdd_a_buddy.setText(QtWidgets.QApplication.translate("MainWindow", "添加联系人"))
        # self.actionAdd_a_group.setText(QtWidgets.QApplication.translate("MainWindow", "添加组"))
        # self.actionPreferences.setText(QtWidgets.QApplication.translate("MainWindow", "选项"))
        # self.actionPreferences.setShortcut(QtWidgets.QApplication.translate("MainWindow", "Ctrl+P"))
        # self.actionConsole.setText(QtWidgets.QApplication.translate("MainWindow", "XML控制台"))
