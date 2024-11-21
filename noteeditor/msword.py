import os
import sys
import webbrowser
import PyQt5
from PyQt5 import QtWidgets
from PyQt5 import QtPrintSupport
from PyQt5 import QtGui, QtCore
from PyQt5.QtCore import Qt, QUrl, QThread, pyqtSignal
from noteeditor.ext import *
from datetime import datetime as sys_datetime

from pytalk.noteeditor.ext import wordcount

sys.path.append("..")
sys.path.append("../..")
from db.DBFactory import  query_note_mng,add_note_mng,update_note_mng,query_KMCfg
from util import generate_random_id
from langchainhandler import savevector,update_vector

from PyQt5.QtWidgets import QApplication, QTextEdit, QVBoxLayout, QWidget, QMessageBox
from PyQt5.QtGui import QImage, QClipboard, QKeySequence, QDesktopServices, QTextDocument
from PyQt5.QtCore import Qt, QBuffer, QByteArray
import sys
import base64


class CustomizedQTextEdit(QtWidgets.QTextEdit):

    def mouseMoveEvent(self, e):
        self.anchor = None
        self.anchor = self.anchorAt(e.pos())
        if self.anchor:
            print("move anchor")
            QApplication.setOverrideCursor(Qt.PointingHandCursor)
        else:
            print("no move anchor")
            # QApplication.setOverrideCursor(Qt.IBeamCursor)
            QApplication.restoreOverrideCursor()

            self.anchor = None
        super().mouseMoveEvent(e)

    # def mousePressEvent(self, e):
    #     self.anchor = self.anchorAt(e.pos())
    #     if self.anchor:
    #         QApplication.setOverrideCursor(Qt.PointingHandCursor)

    def mouseReleaseEvent(self, e):
        if self.anchor:
            QDesktopServices.openUrl(QUrl(self.anchor))
            QApplication.setOverrideCursor(Qt.ArrowCursor)
            self.anchor = None
        super().mouseReleaseEvent(e)



    def leaveEvent(self, e):
        """
        Handles the event when the mouse leaves the widget area.

        :param e: QEvent
        """

        QApplication.restoreOverrideCursor()
        super().leaveEvent(e)


class Main(QtWidgets.QMainWindow):

    def __init__(self,parent=None):
        QtWidgets.QMainWindow.__init__(self,parent)

        self.app = parent
        self.filename = ""

        self.changesSaved = True

        self.record_id=0
        self.note_id = ""
        self.km_id = ""
        self.km_cfg = None
        self.is_first = False

        self.initUI()

    def re_init(self):
        self.filename = ""
        self.changesSaved = True
        self.note_id = ""
        self.is_first = False
        self.text.setText("")

    def initToolbar(self):

        self.newAction = QtWidgets.QAction(QtGui.QIcon("noteeditor/icons/new.png"),"New",self)
        self.newAction.setShortcut("Ctrl+N")
        self.newAction.setStatusTip("Create a new document from scratch.")
        self.newAction.triggered.connect(self.new)

        self.openAction = QtWidgets.QAction(QtGui.QIcon("noteeditor/icons/open.png"),"Open file",self)
        self.openAction.setStatusTip("Open existing document")
        self.openAction.setShortcut("Ctrl+O")
        self.openAction.triggered.connect(self.open)

        self.saveAction = QtWidgets.QAction(QtGui.QIcon("noteeditor/icons/save.png"),"Save",self)
        self.saveAction.setStatusTip("Save document")
        self.saveAction.setShortcut("Ctrl+S")
        self.saveAction.triggered.connect(self.save)

        self.printAction = QtWidgets.QAction(QtGui.QIcon("noteeditor/icons/print.png"),"Print document",self)
        self.printAction.setStatusTip("Print document")
        self.printAction.setShortcut("Ctrl+P")
        self.printAction.triggered.connect(self.printHandler)

        self.previewAction = QtWidgets.QAction(QtGui.QIcon("noteeditor/icons/preview.png"),"Page view",self)
        self.previewAction.setStatusTip("Preview page before printing")
        self.previewAction.setShortcut("Ctrl+Shift+P")
        self.previewAction.triggered.connect(self.preview)

        self.findAction = QtWidgets.QAction(QtGui.QIcon("noteeditor/icons/find.png"),"Find and replace",self)
        self.findAction.setStatusTip("Find and replace words in your document")
        self.findAction.setShortcut("Ctrl+F")
        self.findAction.triggered.connect(find.Find(self).show)

        self.cutAction = QtWidgets.QAction(QtGui.QIcon("noteeditor/icons/cut.png"),"Cut to clipboard",self)
        self.cutAction.setStatusTip("Delete and copy text to clipboard")
        self.cutAction.setShortcut("Ctrl+X")
        self.cutAction.triggered.connect(self.text.cut)

        self.copyAction = QtWidgets.QAction(QtGui.QIcon("noteeditor/icons/copy.png"),"Copy to clipboard",self)
        self.copyAction.setStatusTip("Copy text to clipboard")
        self.copyAction.setShortcut("Ctrl+C")
        self.copyAction.triggered.connect(self.text.copy)

        self.pasteAction = QtWidgets.QAction(QtGui.QIcon("noteeditor/icons/paste.png"),"Paste from clipboard",self)
        self.pasteAction.setStatusTip("Paste text from clipboard")
        self.pasteAction.setShortcut("Ctrl+V")
        # self.pasteAction.triggered.connect(self.text.paste)
        self.pasteAction.triggered.connect(self.paste_image)

        self.undoAction = QtWidgets.QAction(QtGui.QIcon("noteeditor/icons/undo.png"),"Undo last action",self)
        self.undoAction.setStatusTip("Undo last action")
        self.undoAction.setShortcut("Ctrl+Z")
        self.undoAction.triggered.connect(self.text.undo)

        self.redoAction = QtWidgets.QAction(QtGui.QIcon("noteeditor/icons/redo.png"),"Redo last undone thing",self)
        self.redoAction.setStatusTip("Redo last undone thing")
        self.redoAction.setShortcut("Ctrl+Y")
        self.redoAction.triggered.connect(self.text.redo)

        dateTimeAction = QtWidgets.QAction(QtGui.QIcon("noteeditor/icons/calender.png"),"Insert current date/time",self)
        dateTimeAction.setStatusTip("Insert current date/time")
        dateTimeAction.setShortcut("Ctrl+D")
        dateTimeAction.triggered.connect(datetime.DateTime(self).show)

        wordCountAction = QtWidgets.QAction(QtGui.QIcon("noteeditor/icons/count.png"),"See word/symbol count",self)
        wordCountAction.setStatusTip("See word/symbol count")
        wordCountAction.setShortcut("Ctrl+W")
        wordCountAction.triggered.connect(self.wordCount)

        tableAction = QtWidgets.QAction(QtGui.QIcon("noteeditor/icons/table.png"),"Insert table",self)
        tableAction.setStatusTip("Insert table")
        tableAction.setShortcut("Ctrl+T")
        tableAction.triggered.connect(table.Table(self).show)

        imageAction = QtWidgets.QAction(QtGui.QIcon("noteeditor/icons/image.png"),"Insert image",self)
        imageAction.setStatusTip("Insert image")
        imageAction.setShortcut("Ctrl+Shift+I")
        imageAction.triggered.connect(self.insertImage)

        bulletAction = QtWidgets.QAction(QtGui.QIcon("noteeditor/icons/bullet.png"),"Insert bullet List",self)
        bulletAction.setStatusTip("Insert bullet list")
        bulletAction.setShortcut("Ctrl+Shift+B")
        bulletAction.triggered.connect(self.bulletList)

        numberedAction = QtWidgets.QAction(QtGui.QIcon("noteeditor/icons/number.png"),"Insert numbered List",self)
        numberedAction.setStatusTip("Insert numbered list")
        numberedAction.setShortcut("Ctrl+Shift+L")
        numberedAction.triggered.connect(self.numberList)

        self.toolbar = self.addToolBar("Options")

        self.toolbar.addAction(self.newAction)
        self.toolbar.addAction(self.openAction)
        self.toolbar.addAction(self.saveAction)

        self.toolbar.addSeparator()

        self.toolbar.addAction(self.printAction)
        self.toolbar.addAction(self.previewAction)

        self.toolbar.addSeparator()

        self.toolbar.addAction(self.cutAction)
        self.toolbar.addAction(self.copyAction)
        self.toolbar.addAction(self.pasteAction)
        self.toolbar.addAction(self.undoAction)
        self.toolbar.addAction(self.redoAction)

        self.toolbar.addSeparator()

        self.toolbar.addAction(self.findAction)
        self.toolbar.addAction(dateTimeAction)
        self.toolbar.addAction(wordCountAction)
        self.toolbar.addAction(tableAction)
        self.toolbar.addAction(imageAction)

        self.toolbar.addSeparator()

        self.toolbar.addAction(bulletAction)
        self.toolbar.addAction(numberedAction)

        self.addToolBarBreak()


    def paste_image(self):
        clipboard = QApplication.clipboard()
        if clipboard.mimeData().hasImage():  # 检查剪贴板是否有图片
            image = clipboard.image()  # 获取剪贴板中的图片
            if not image.isNull():  # 检查 QImage 是否有效
                cursor = self.text.textCursor()
                cursor.insertImage(image)  # 在 QTextEdit 中插入图片

                # # 将图片转换为 Base64
                # self.image_base64 = self.image_to_base64(image)
                #
                # # 保存图片到本地
                # self.save_image_to_local(image)
                #
                # # 可选：显示 Base64 字符串
                # print(self.image_base64)
            else:
                QMessageBox.warning(self, "错误", "剪贴板中的图片无效！")
        else:
            self.text.paste()

    def image_to_base64(self, image):
        """将 QImage 转换为 Base64 编码的字符串。"""
        buffer = QBuffer()
        buffer.open(QBuffer.ReadWrite)
        image.save(buffer, 'PNG')  # 保存为 PNG 格式
        byte_array = buffer.data()
        return base64.b64encode(byte_array).decode('utf-8')  # 编码为 Base64 字符串

    def save_image_to_local(self, image):
        """将 QImage 保存到本地文件系统。"""
        file_path = r'C:\Users\IDD\Documents\pasted_image.png'  # 指定保存路径
        image.save(file_path, 'PNG')  # 保存为 PNG 格式
        print(f"图片已保存到: {file_path}")


    def initFormatbar(self):

        fontBox = QtWidgets.QFontComboBox(self)
        fontBox.currentFontChanged.connect(lambda font: self.text.setCurrentFont(font))

        fontSize = QtWidgets.QSpinBox(self)

        fontSize.setSuffix("pt")

        fontSize.valueChanged.connect(lambda size: self.text.setFontPointSize(size))

        fontSize.setValue(12)

        fontColor = QtWidgets.QAction(QtGui.QIcon("noteeditor/icons/font-color.png"),"Change font color",self)
        fontColor.triggered.connect(self.fontColorChanged)

        boldAction = QtWidgets.QAction(QtGui.QIcon("noteeditor/icons/bold.png"),"Bold",self)
        boldAction.triggered.connect(self.bold)

        italicAction = QtWidgets.QAction(QtGui.QIcon("noteeditor/icons/italic.png"),"Italic",self)
        italicAction.triggered.connect(self.italic)

        underlAction = QtWidgets.QAction(QtGui.QIcon("noteeditor/icons/underline.png"),"Underline",self)
        underlAction.triggered.connect(self.underline)

        strikeAction = QtWidgets.QAction(QtGui.QIcon("noteeditor/icons/strike.png"),"Strike-out",self)
        strikeAction.triggered.connect(self.strike)

        superAction = QtWidgets.QAction(QtGui.QIcon("noteeditor/icons/superscript.png"),"Superscript",self)
        superAction.triggered.connect(self.superScript)

        subAction = QtWidgets.QAction(QtGui.QIcon("noteeditor/icons/subscript.png"),"Subscript",self)
        subAction.triggered.connect(self.subScript)

        alignLeft = QtWidgets.QAction(QtGui.QIcon("noteeditor/icons/align-left.png"),"Align left",self)
        alignLeft.triggered.connect(self.alignLeft)

        alignCenter = QtWidgets.QAction(QtGui.QIcon("noteeditor/icons/align-center.png"),"Align center",self)
        alignCenter.triggered.connect(self.alignCenter)

        alignRight = QtWidgets.QAction(QtGui.QIcon("noteeditor/icons/align-right.png"),"Align right",self)
        alignRight.triggered.connect(self.alignRight)

        alignJustify = QtWidgets.QAction(QtGui.QIcon("noteeditor/icons/align-justify.png"),"Align justify",self)
        alignJustify.triggered.connect(self.alignJustify)

        indentAction = QtWidgets.QAction(QtGui.QIcon("noteeditor/icons/indent.png"),"Indent Area",self)
        indentAction.setShortcut("Ctrl+Tab")
        indentAction.triggered.connect(self.indent)

        dedentAction = QtWidgets.QAction(QtGui.QIcon("noteeditor/icons/dedent.png"),"Dedent Area",self)
        dedentAction.setShortcut("Shift+Tab")
        dedentAction.triggered.connect(self.dedent)

        backColor = QtWidgets.QAction(QtGui.QIcon("noteeditor/icons/highlight.png"),"Change background color",self)
        backColor.triggered.connect(self.highlight)

        self.formatbar = self.addToolBar("Format")

        self.formatbar.addWidget(fontBox)
        self.formatbar.addWidget(fontSize)

        self.formatbar.addSeparator()

        self.formatbar.addAction(fontColor)
        self.formatbar.addAction(backColor)

        self.formatbar.addSeparator()

        self.formatbar.addAction(boldAction)
        self.formatbar.addAction(italicAction)
        self.formatbar.addAction(underlAction)
        self.formatbar.addAction(strikeAction)
        self.formatbar.addAction(superAction)
        self.formatbar.addAction(subAction)

        self.formatbar.addSeparator()

        self.formatbar.addAction(alignLeft)
        self.formatbar.addAction(alignCenter)
        self.formatbar.addAction(alignRight)
        self.formatbar.addAction(alignJustify)

        self.formatbar.addSeparator()

        self.formatbar.addAction(indentAction)
        self.formatbar.addAction(dedentAction)

    def initMenubar(self):

        menubar = self.menuBar()

        file = menubar.addMenu("File")
        edit = menubar.addMenu("Edit")
        view = menubar.addMenu("View")

        # Add the most important actions to the menubar

        file.addAction(self.newAction)
        file.addAction(self.openAction)
        file.addAction(self.saveAction)
        file.addAction(self.printAction)
        file.addAction(self.previewAction)

        edit.addAction(self.undoAction)
        edit.addAction(self.redoAction)
        edit.addAction(self.cutAction)
        edit.addAction(self.copyAction)
        edit.addAction(self.pasteAction)
        edit.addAction(self.findAction)

        # Toggling actions for the various bars
        toolbarAction = QtWidgets.QAction("Toggle Toolbar",self)
        toolbarAction.triggered.connect(self.toggleToolbar)

        formatbarAction = QtWidgets.QAction("Toggle Formatbar",self)
        formatbarAction.triggered.connect(self.toggleFormatbar)

        statusbarAction = QtWidgets.QAction("Toggle Statusbar",self)
        statusbarAction.triggered.connect(self.toggleStatusbar)

        view.addAction(toolbarAction)
        view.addAction(formatbarAction)
        view.addAction(statusbarAction)

    def initUI(self):

        # self.text = QtWidgets.QTextEdit(self)
        self.text = CustomizedQTextEdit(self)


        self.text.setTabStopWidth(33)

        self.initToolbar()
        self.initFormatbar()
        self.initMenubar()

        self.setCentralWidget(self.text)

        # Initialize a statusbar for the window
        self.statusbar = self.statusBar()


        self.text.cursorPositionChanged.connect(self.cursorPosition)

        # We need our own context menu for tables
        self.text.setContextMenuPolicy(Qt.CustomContextMenu)
        self.text.customContextMenuRequested.connect(self.context)

        self.text.textChanged.connect(self.changed)

        self.setGeometry(100,100,1030,800)
        self.setWindowTitle("Kagoj")
        self.setWindowIcon(QtGui.QIcon("noteeditor/icons/word.png"))

    def changed(self):
        self.changesSaved = False

    def closeEvent(self,event):

        if self.changesSaved:

            event.accept()

        else:

            popup = QtWidgets.QMessageBox(self)
            popup.setWindowTitle("Kagoj")

            popup.setIcon(QtWidgets.QMessageBox.Warning)

            popup.setText("The document has been modified")

            popup.setInformativeText("Do you want to save your changes?")

            popup.setStandardButtons(QtWidgets.QMessageBox.Save   |
                                      QtWidgets.QMessageBox.Cancel |
                                      QtWidgets.QMessageBox.Discard)

            popup.setDefaultButton(QtWidgets.QMessageBox.Save)

            answer = popup.exec_()

            if answer == QtWidgets.QMessageBox.Save:
                self.save()

            elif answer == QtWidgets.QMessageBox.Discard:
                event.accept()

            else:
                event.ignore()

    def context(self,pos):


        cursor = self.text.textCursor()


        table = cursor.currentTable()


        if table:

            menu = PyQt5.QtWidgets.QMenu(self)

            appendRowAction = QtWidgets.QAction("Append row",self)
            appendRowAction.triggered.connect(lambda: table.appendRows(1))

            appendColAction = QtWidgets.QAction("Append column",self)
            appendColAction.triggered.connect(lambda: table.appendColumns(1))


            removeRowAction = QtWidgets.QAction("Remove row",self)
            removeRowAction.triggered.connect(self.removeRow)

            removeColAction = QtWidgets.QAction("Remove column",self)
            removeColAction.triggered.connect(self.removeCol)


            insertRowAction = QtWidgets.QAction("Insert row",self)
            insertRowAction.triggered.connect(self.insertRow)

            insertColAction = QtWidgets.QAction("Insert column",self)
            insertColAction.triggered.connect(self.insertCol)


            mergeAction = QtWidgets.QAction("Merge cells",self)
            mergeAction.triggered.connect(lambda: table.mergeCells(cursor))


            if not cursor.hasSelection():
                mergeAction.setEnabled(False)


            splitAction = QtWidgets.QAction("Split cells",self)

            cell = table.cellAt(cursor)

            if cell.rowSpan() > 1 or cell.columnSpan() > 1:

                splitAction.triggered.connect(lambda: table.splitCell(cell.row(),cell.column(),1,1))

            else:
                splitAction.setEnabled(False)


            menu.addAction(appendRowAction)
            menu.addAction(appendColAction)

            menu.addSeparator()

            menu.addAction(removeRowAction)
            menu.addAction(removeColAction)

            menu.addSeparator()

            menu.addAction(insertRowAction)
            menu.addAction(insertColAction)

            menu.addSeparator()

            menu.addAction(mergeAction)
            menu.addAction(splitAction)

            cursor = self.text.textCursor()

            if cursor.hasSelection():
                selected_text = cursor.selectedText()
                print(selected_text)

                # Check if the selected text is a URL
                if selected_text.startswith("http://") or selected_text.startswith("https://"):
                    openLinkAction = QtWidgets.QAction("Open Link", self)
                    openLinkAction.triggered.connect(lambda: webbrowser.open(selected_text))
                    menu.addAction(openLinkAction)




            pos = self.mapToGlobal(pos)


            if self.toolbar.isVisible():
                pos.setY(pos.y() + 45)

            if self.formatbar.isVisible():
                pos.setY(pos.y() + 45)


            menu.move(pos)

            menu.show()

        else:

            # event = QtGui.QContextMenuEvent(QtGui.QContextMenuEvent.Mouse,QtCore.QPoint())
            #
            # self.text.contextMenuEvent(event)

            print("in")
            # Create custom context menu
            menu = self.text.createStandardContextMenu()
            cursor = self.text.textCursor()

            if cursor.hasSelection():
                selected_text = cursor.selectedText()
                print(selected_text)

                # Check if the selected text is a URL
                if selected_text.startswith("http://") or selected_text.startswith("https://"):
                    openLinkAction = QtWidgets.QAction("Open Link", self)
                    openLinkAction.triggered.connect(lambda: webbrowser.open(selected_text))
                    menu.addAction(openLinkAction)

            menu.exec_(self.mapToGlobal(pos))

    def removeRow(self):


        cursor = self.text.textCursor()


        table = cursor.currentTable()


        cell = table.cellAt(cursor)


        table.removeRows(cell.row(),1)

    def removeCol(self):


        cursor = self.text.textCursor()

        table = cursor.currentTable()


        cell = table.cellAt(cursor)


        table.removeColumns(cell.column(),1)

    def insertRow(self):


        cursor = self.text.textCursor()

        table = cursor.currentTable()


        cell = table.cellAt(cursor)


        table.insertRows(cell.row(),1)

    def insertCol(self):


        cursor = self.text.textCursor()
        table = cursor.currentTable()


        cell = table.cellAt(cursor)


        table.insertColumns(cell.column(),1)


    def toggleToolbar(self):

        state = self.toolbar.isVisible()


        self.toolbar.setVisible(not state)

    def toggleFormatbar(self):

        state = self.formatbar.isVisible()


        self.formatbar.setVisible(not state)

    def toggleStatusbar(self):

        state = self.statusbar.isVisible()


        self.statusbar.setVisible(not state)

    def new(self):

        spawn = Main()

        spawn.show()

    def open(self):


        self.filename = QtWidgets.QFileDialog.getOpenFileName(self, 'Open File',".","(*.kagoj)")[0]

        if self.filename:
            with open(self.filename,"rt",encoding='utf-8') as file:
                self.text.setText(file.read())

    def save(self,title=""):
        record_id=0
        self.km_cfg = query_KMCfg(id=self.km_cfg.id)

        if self.km_cfg.vectorization == 1 and self.km_cfg.stopvectorization == 1:
            # 如果可向量化且暂停了向量化则需要等待向量化
            waitvectorization = True
        else:
            waitvectorization = False

        if not self.filename:
            note_id = generate_random_id()
            self.note_id = note_id
            self.filename = os.path.join(os.getcwd(),"km", self.km_id,"doc", note_id)
            content=self.text.toPlainText()
            first_line = content.strip().splitlines()[0] if content else "无标题"
            # 截取前 50 个字符
            if not title:
                title = first_line[:50]
            # title = content[:50]
            file_name = note_id
            tag_1 = ""
            tag_2 = ""
            tag_3 = ""

            record_id=add_note_mng(note_id, title, file_name, content,self.km_id, tag_1, tag_2,
                     tag_3,waitvectorization)
            self.is_first = True
        else:
            note_id = self.note_id
            content = self.text.toPlainText()
            create_time = sys_datetime.now()
            update_note_mng(note_id,content=content,create_time=create_time,waitvectorization=waitvectorization)



        if self.filename:
            self.filename_txt=self.filename.replace(".kagoj","")+".txt"

            if not self.filename.endswith(".kagoj"):
              self.filename += ".kagoj"
            try:
                # 打开文件以写入模式，使用 'utf-8' 编码

                html_content = self.text.toHtml()
                html_content = self.encode_images_to_base64(html_content)

                with open(self.filename, "wt", encoding='utf-8') as file:
                    file.write(html_content)



            except UnicodeEncodeError as e:
                # 捕捉编码错误并输出错误信息
                print(f"编码错误: {e}")
                # 可能需要更多的处理来替换或过滤掉无法编码的字符
                # 当前示例将无法编码的字符替换为问号
                safe_text = self.text.toHtml().encode('utf-8', 'replace').decode('utf-8')
                with open(self.filename, "wt", encoding='utf-8') as file:
                    file.write(safe_text)  # 写入安全的文本
            except Exception as e:
                # 捕捉其他可能的异常并输出错误信息
                print(f"发生错误: {e}")

            try:
                # 打开文件以写入模式，使用 'utf-8' 编码
                with open(self.filename_txt, "wt", encoding='utf-8') as file:
                    file.write(self.text.toPlainText())
            except UnicodeEncodeError as e:
                # 捕捉编码错误并输出错误信息
                print(f"编码错误: {e}")
                # 可能需要更多的处理来替换或过滤掉无法编码的字符
                # 当前示例将无法编码的字符替换为问号
                safe_text = self.text.toPlainText().encode('utf-8', 'replace').decode('utf-8')
                with open(self.filename_txt, "wt", encoding='utf-8') as file:
                    file.write(safe_text)  # 写入安全的文本
            except Exception as e:
                # 捕捉其他可能的异常并输出错误信息
                print(f"发生错误: {e}")

            self.changesSaved = True

        is_first = self.is_first
        if self.is_first == True:
            application = self.app
            # notelist_recent = application.notelist_recent_list[self.km_id]
            # notelist_recent.deselect_all_items()
            # notelist_recent.addItem(title.replace("\n", "")[:50], record_id, True)
            # first_toplevel_item = notelist_recent.topLevelItem(0)
            # first_subitem = first_toplevel_item.child(0)
            # first_subitem.setSelected(True)
            notelist_all = application.notelist_all_list[self.km_id]
            notelist_all.deselect_all_items()
            notelist_all.addItem(title.replace("\n", "")[:50], record_id, True)
            first_toplevel_item = notelist_all.topLevelItem(0)
            first_subitem = first_toplevel_item.child(0)
            first_subitem.setSelected(True)
            self.is_first = False


        if self.km_cfg.vectorization == 1 and self.km_cfg.stopvectorization == 0:
            # 如果可向量化且没有暂停向量化则需要向量化
            self.vectorize(is_first)


    def encode_images_to_base64(self, html_content):
        document = self.text.document()

        # Iterate over all blocks in the document
        for block_number in range(document.blockCount()):
            block = document.findBlockByNumber(block_number)
            iter = block.begin()
            while not iter.atEnd():
                fragment = iter.fragment()
                if fragment.isValid():
                    char_format = fragment.charFormat()
                    if char_format.isImageFormat():
                        image_format = char_format.toImageFormat()
                        image_name = image_format.name()

                        # Convert the image name to QUrl
                        image_url = QUrl(image_name)

                        # Load image from document resources
                        image = document.resource(QTextDocument.ImageResource, image_url)

                        if isinstance(image, QImage):
                            # Convert image to byte array using QBuffer
                            byte_array = QByteArray()
                            buffer = QBuffer(byte_array)
                            buffer.open(QBuffer.WriteOnly)
                            image.save(buffer, "PNG")

                            # Encode byte array to Base64
                            base64_data = base64.b64encode(byte_array).decode('utf-8')
                            # Replace src attribute with Base64 data
                            html_content = html_content.replace(image_name, f"data:image/png;base64,{base64_data}")

                iter += 1

        return html_content

    def preview(self):


        preview = QtPrintSupport.QPrintPreviewDialog()


        preview.paintRequested.connect(lambda p: self.text.print_(p))

        preview.exec_()

    def printHandler(self):


        dialog = QtPrintSupport.QPrintDialog()

        if dialog.exec_() == QtWidgets.QDialog.Accepted:
            self.text.document().print_(dialog.printer())

    def cursorPosition(self):

        cursor = self.text.textCursor()


        line = cursor.blockNumber() + 1
        col = cursor.columnNumber()

        self.statusbar.showMessage("Line: {} | Column: {}".format(line,col))

    def wordCount(self):

        wc = wordcount.WordCount(self)

        wc.getText()

        wc.show()

    def insertImage(self):


        filename = QtWidgets.QFileDialog.getOpenFileName(self, 'Insert image',".","Images (*.png *.xpm *.jpg *.bmp *.gif *.svg)")[0]

        if filename:


            image = QtGui.QImage(filename)


            if image.isNull():

                popup = QtWidgets.QMessageBox(QtWidgets.QMessageBox.Critical,
                                          "Image load error",
                                          "Could not load image file!",
                                          QtWidgets.QMessageBox.Ok,
                                          self)
                popup.show()

            else:

                cursor = self.text.textCursor()

                cursor.insertImage(image,filename)

    def fontColorChanged(self):


        color = QtWidgets.QColorDialog.getColor()


        self.text.setTextColor(color)

    def highlight(self):

        color = QtWidgets.QColorDialog.getColor()

        self.text.setTextBackgroundColor(color)

    def bold(self):

        if self.text.fontWeight() == QtGui.QFont.Bold:

            self.text.setFontWeight(QtGui.QFont.Normal)

        else:

            self.text.setFontWeight(QtGui.QFont.Bold)

    def italic(self):

        state = self.text.fontItalic()

        self.text.setFontItalic(not state)

    def underline(self):

        state = self.text.fontUnderline()

        self.text.setFontUnderline(not state)

    def strike(self):


        fmt = self.text.currentCharFormat()

        fmt.setFontStrikeOut(not fmt.fontStrikeOut())


        self.text.setCurrentCharFormat(fmt)

    def superScript(self):


        fmt = self.text.currentCharFormat()


        align = fmt.verticalAlignment()


        if align == QtGui.QTextCharFormat.AlignNormal:

            fmt.setVerticalAlignment(QtGui.QTextCharFormat.AlignSuperScript)

        else:

            fmt.setVerticalAlignment(QtGui.QTextCharFormat.AlignNormal)


        self.text.setCurrentCharFormat(fmt)

    def subScript(self):


        fmt = self.text.currentCharFormat()


        align = fmt.verticalAlignment()


        if align == QtGui.QTextCharFormat.AlignNormal:

            fmt.setVerticalAlignment(QtGui.QTextCharFormat.AlignSubScript)

        else:

            fmt.setVerticalAlignment(QtGui.QTextCharFormat.AlignNormal)


        self.text.setCurrentCharFormat(fmt)

    def alignLeft(self):
        self.text.setAlignment(Qt.AlignLeft)

    def alignRight(self):
        self.text.setAlignment(Qt.AlignRight)

    def alignCenter(self):
        self.text.setAlignment(Qt.AlignCenter)

    def alignJustify(self):
        self.text.setAlignment(Qt.AlignJustify)

    def indent(self):


        cursor = self.text.textCursor()

        if cursor.hasSelection():


            temp = cursor.blockNumber()


            cursor.setPosition(cursor.anchor())


            diff = cursor.blockNumber() - temp

            direction = QtGui.QTextCursor.Up if diff > 0 else QtGui.QTextCursor.Down


            for n in range(abs(diff) + 1):


                cursor.movePosition(QtGui.QTextCursor.StartOfLine)


                cursor.insertText("\t")


                cursor.movePosition(direction)

        else:

            cursor.insertText("\t")

    def handleDedent(self,cursor):

        cursor.movePosition(QtGui.QTextCursor.StartOfLine)


        line = cursor.block().text()


        if line.startswith("\t"):


            cursor.deleteChar()

        else:
            for char in line[:8]:

                if char != " ":
                    break

                cursor.deleteChar()

    def dedent(self):

        cursor = self.text.textCursor()

        if cursor.hasSelection():


            temp = cursor.blockNumber()


            cursor.setPosition(cursor.anchor())


            diff = cursor.blockNumber() - temp

            direction = QtGui.QTextCursor.Up if diff > 0 else QtGui.QTextCursor.Down


            for n in range(abs(diff) + 1):

                self.handleDedent(cursor)


                cursor.movePosition(direction)

        else:
            self.handleDedent(cursor)


    def bulletList(self):

        cursor = self.text.textCursor()



        cursor.insertList(QtGui.QTextListFormat.ListDisc)

    def numberList(self):

        cursor = self.text.textCursor()


        cursor.insertList(QtGui.QTextListFormat.ListDecimal)

    def loadFile(self):

        if not self.changesSaved:

            popup = QtWidgets.QMessageBox()
            popup.setWindowTitle("Kagoj")

            popup.setIcon(QtWidgets.QMessageBox.Warning)

            popup.setText("The document has been modified")

            popup.setInformativeText("Do you want to save your changes?")

            popup.setStandardButtons(QtWidgets.QMessageBox.Save   |
                                      QtWidgets.QMessageBox.Cancel |
                                      QtWidgets.QMessageBox.Discard)

            popup.setDefaultButton(QtWidgets.QMessageBox.Save)

            answer = popup.exec_()

            if answer == QtWidgets.QMessageBox.Save:
                self.save()

        self.re_init()

        record_id =self.record_id
        if record_id==0:
            self.changesSaved = True
            return
        else:
            record =query_note_mng(id=record_id)
            if record:
                filename=record.file_name
                filename =os.path.join(os.getcwd(),"km",self.km_id,"doc",filename+".kagoj")
                self.filename=filename
                self.note_id = record.note_id

            if self.filename:
                with open(self.filename,"rt", encoding='utf-8') as file:
                    self.text.setText(file.read())

        self.changesSaved = True

    def vectorize(self,is_first):
        note_id = self.note_id
        embedding_model_name = self.km_cfg.embeddingmodel
        persist_directory = os.path.join(os.getcwd(), "km", self.km_id, "vector")
        filepath = os.path.join(os.getcwd(), "km", self.km_id, "doc", note_id + ".txt")

        if embedding_model_name.lower()=="openai":
            emb_type = "openai"
        else:
            emb_type = "other"
        chunk_size = self.km_cfg.textblocklength
        chunk_overlap = self.km_cfg.overlaplength

        self.thread = WorkerThread(filepath, persist_directory, embedding_model_name,emb_type,chunk_size, chunk_overlap,is_first)
        self.thread.finished.connect(self.on_thread_finished)  # 连接信号
        self.thread.start()

    def on_thread_finished(self):
        """处理线程完成的信号"""
        print("线程已完成，准备清理")
        self.thread.quit()  # 请求线程退出
        self.thread.wait()  # 等待线程结束
        del self.thread  # 删除线程对象（如果需要）

class WorkerThread(QThread):
    finished = pyqtSignal()
    def __init__(self, filepath, persist_directory, embedding_model_name,emb_type,chunk_size, chunk_overlap,is_first):
        super(WorkerThread, self).__init__()
        self.filepath=filepath
        self.persist_directory=persist_directory
        self.embedding_model_name=embedding_model_name
        self.emb_type=emb_type
        self.chunk_size=chunk_size
        self.chunk_overlap=chunk_overlap
        self.is_first=is_first
    def run(self):
        filepath =  self.filepath
        persist_directory = self.persist_directory
        embedding_model_name = self.embedding_model_name
        emb_type = self.emb_type
        chunk_size = self.chunk_size
        chunk_overlap = self.chunk_overlap
        is_first = self.is_first
        print("开始向量化....")
        if is_first:
            savevector(filepath, persist_directory, embedding_model_name,emb_type,chunk_size, chunk_overlap)
        else:
            update_vector(filepath, persist_directory, embedding_model_name,emb_type,chunk_size, chunk_overlap)

        self.finished.emit()  # 发射信号，通知主线程



def main():
    app = QtWidgets.QApplication(sys.argv)

    main = Main()
    main.show()

    sys.exit(app.exec_())

if __name__ == "__main__":
    main()
