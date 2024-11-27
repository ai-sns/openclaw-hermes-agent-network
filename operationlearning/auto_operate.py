# _*_ coding:utf-8 _*_

import pyautogui
import pynput
from pynput.mouse import Button, Controller as MouseController
from pynput.keyboard import Key, Controller as KeyboardController
import time
import json
import sys

import os
import io
import time
import json
import threading

from PyQt5.QtWidgets import QGraphicsScene, QInputDialog, QGraphicsTextItem, QGraphicsRectItem, QGraphicsEllipseItem, QGraphicsPathItem
from PyQt5.QtGui import QCursor
from PyQt5.QtCore import Qt, QRectF

from PyQt5 import QtGui
from PyQt5.QtWidgets import QShortcut, QToolBar, QAction, QGraphicsView, QTextEdit, QTabWidget, QFormLayout, QComboBox, QGraphicsPixmapItem
from PyQt5 import QtCore
from PyQt5.QtCore import QTimer, pyqtSignal
from PyQt5.QtGui import QBrush, QIcon, QFont, QPixmap, QPainterPath
from PyQt5.QtWidgets import QPushButton, QHBoxLayout, QLabel, QVBoxLayout, QMessageBox, QFileDialog, QWidget
import shutil

# Import custom modules
from .base import Base

import sys
import pyautogui
from PyQt5.QtWidgets import QApplication, QRubberBand, QMainWindow
from PyQt5.QtCore import Qt, QRect, QSize
from PyQt5.QtGui import QPainter, QPen, QColor


# Check command line arguments
def check_command_line_args():
    n = len(sys.argv)
    if n < 2:
        exit("Takes a compulsory argument - name of recording, and optional argument - record-all")

    if n > 3:
        exit("Only takes two arguments - name of recording and (optional) record-all")

    # Determine the recording setup based on arguments
    name_of_recording = str(sys.argv[1])
    record_all = n == 3 and str(sys.argv[2]) == "record-all"

    if n == 3 and not record_all:
        exit("The second argument given must be 'record-all', otherwise only pass the name of recording as a parameter")

    return name_of_recording, record_all


# Signal class to interact with the main thread
class SignalEmitter(QtCore.QObject):
    show_dialog_signal = pyqtSignal(int, int)
    wait_for_input_signal = pyqtSignal(str,str)

    def __init__(self):
        super().__init__()


# Initialize global variables
def initialize_globals():
    global storage, is_capturing, esc_count, last_esc_time, record_all, name_of_recording, signal_emitter, keyboard_listener, mouse_listener, number_of_plays, gstatus, gvalue
    storage = []
    is_capturing = True
    esc_count = 0
    last_esc_time = 0
    record_all = "record-all"
    name_of_recording = "C:/dev/ai-sns/record-and-play-pynput/record-and-play-pynput/data/test008.txt"
    gstatus = ""
    gvalue = ""
    number_of_plays = 1
    signal_emitter = SignalEmitter()


class CustomGraphicsView(QGraphicsView):
    def __init__(self):
        super().__init__()
        self.mode = None
        self.drawing = False
        self.start_point = None
        self.item = None

    def setPixmap(self, pixmap):
        self.scene().clear()
        self.pixmap_item = QGraphicsPixmapItem(pixmap)
        self.scene().addItem(self.pixmap_item)

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.start_point = self.mapToScene(event.pos())
            self.drawing = True
            if self.mode == "annotate_free":
                self.path_item = QPainterPath(self.start_point)
            elif self.mode in {"annotate_box", "crop_rect", "crop_circle"}:
                if self.item:
                    self.scene().removeItem(self.item)
                    self.item = None
            elif self.mode == "annotate_text":
                text, ok = QInputDialog.getText(self, 'Text Annotation', 'Enter text:')
                if ok:
                    text_item = QGraphicsTextItem(text)
                    text_item.setPos(self.start_point)
                    text_item.setFlags(QGraphicsTextItem.ItemIsMovable | QGraphicsTextItem.ItemIsSelectable)
                    self.scene().addItem(text_item)

    def mouseMoveEvent(self, event):
        if self.drawing:
            end_point = self.mapToScene(event.pos())
            if self.mode == "annotate_free":
                if self.path_item:
                    self.path_item.lineTo(end_point)
                    pen = QPen(Qt.blue, 2, Qt.SolidLine)
                    if self.item:
                        self.scene().removeItem(self.item)
                    self.item = QGraphicsPathItem(self.path_item)
                    self.item.setPen(pen)
                    self.item.setFlags(QGraphicsPathItem.ItemIsMovable | QGraphicsPathItem.ItemIsSelectable)
                    self.scene().addItem(self.item)
            elif self.mode == "annotate_box" or self.mode == "crop_rect":
                if self.item:
                    self.scene().removeItem(self.item)
                rect = QRectF(self.start_point, end_point)
                pen = QPen(Qt.red, 2, Qt.SolidLine)
                self.item = QGraphicsRectItem(rect)
                self.item.setPen(pen)
                self.item.setFlags(QGraphicsRectItem.ItemIsMovable | QGraphicsRectItem.ItemIsSelectable)
                self.scene().addItem(self.item)
            elif self.mode == "crop_circle":
                if self.item:
                    self.scene().removeItem(self.item)
                rect = QRectF(self.start_point, end_point)
                pen = QPen(Qt.red, 2, Qt.SolidLine)
                self.item = QGraphicsEllipseItem(rect)
                self.item.setPen(pen)
                self.item.setFlags(QGraphicsEllipseItem.ItemIsMovable | QGraphicsEllipseItem.ItemIsSelectable)
                self.scene().addItem(self.item)

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.drawing = False
            if self.mode == "crop_rect" and self.item:
                rect = self.item.rect().toRect()
                cropped = self.pixmap_item.pixmap().copy(rect)
                self.scene().clear()
                self.setPixmap(cropped)
            elif self.mode == "crop_circle" and self.item:
                rect = self.item.rect().toRect()
                # Create a circular cropped image
                cropped = self.pixmap_item.pixmap().copy(rect)
                circular_cropped = QPixmap(cropped.size())
                circular_cropped.fill(Qt.transparent)

                # Create a circular mask and apply it
                painter = QPainter(circular_cropped)
                painter.setRenderHint(QPainter.Antialiasing)
                path = QPainterPath()
                path.addEllipse(0, 0, rect.width(), rect.height())
                painter.setClipPath(path)
                painter.drawPixmap(0, 0, cropped)
                painter.end()

                self.scene().clear()
                self.setPixmap(circular_cropped)

    def enterEvent(self, event):
        self.setCursor(QCursor(Qt.CrossCursor))

    def leaveEvent(self, event):
        self.setCursor(QCursor(Qt.ArrowCursor))


class ScreenCapture(QMainWindow):
    on_captured_finished = pyqtSignal(tuple, QPixmap)

    def __init__(self):
        super().__init__()

        # Set the window to be transparent and fullscreen with no frame
        self.setWindowOpacity(0.3)
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint)
        self.setWindowState(Qt.WindowFullScreen)

        # Initialize the rubber band for selecting the region
        self.rubber_band = QRubberBand(QRubberBand.Rectangle, self)
        self.rubber_band.setStyleSheet("border: 10px solid red;")  # Set red border for the rubber band

        self.origin = None

    def paintEvent(self, event):
        # Create a painter to draw the red border for the entire window
        painter = QPainter(self)
        pen = QPen(QColor(255, 0, 0), 5)  # Red color, 2 pixels thick
        painter.setPen(pen)
        # Draw the border around the window
        painter.drawRect(self.rect())

    def mousePressEvent(self, event):
        # Set the origin point for the rubber band
        if event.button() == Qt.LeftButton:
            self.origin = event.pos()
            self.rubber_band.setGeometry(QRect(self.origin, QSize()))
            self.rubber_band.show()

    def mouseMoveEvent(self, event):
        # Update the rubber band geometry as the mouse moves
        if self.origin is not None:
            self.rubber_band.setGeometry(QRect(self.origin, event.pos()).normalized())

    def mouseReleaseEvent(self, event):
        # Capture the selected region
        if event.button() == Qt.LeftButton:
            self.rubber_band.hide()
            selected_rect = self.rubber_band.geometry()

            # Capture the screen and crop to the selected region
            self.setWindowOpacity(0)
            screenshot = pyautogui.screenshot()

            cropped_image = screenshot.crop((selected_rect.left(), selected_rect.top(),
                                             selected_rect.right(), selected_rect.bottom()))
            # cropped_image.show()
            # cropped_image.save()

            # Convert to QPixmap using a QByteArray
            byte_array = io.BytesIO()
            cropped_image.save(byte_array, format='PNG')
            byte_array.seek(0)
            pixmap = QPixmap()
            pixmap.loadFromData(byte_array.read())

            cropped_image.save(os.getcwd() + '\\cjrcaptureNew.png', 'png')
            # Close the window after capturing

            self.on_captured_finished.emit((selected_rect.left(), selected_rect.top(),
                                            selected_rect.right(), selected_rect.bottom()), pixmap)

            self.close()


class CaptureDialog(QWidget):
    capture_finished = pyqtSignal()  # 自定义信号，表示捕获完成

    def __init__(self):
        super().__init__()
        self.setWindowTitle("操作标注")
        self.setWindowFlag(Qt.WindowStaysOnTopHint)  # 设置窗口总在最上层

        # 设置对话框的布局
        layout = QVBoxLayout()

        # 创建工具栏并添加到布局中
        self.create_toolbar(layout)

        # 创建标签页
        self.tab_widget = QTabWidget()
        self.setLayout(layout)  # 设置布局

        # 操作模式下拉框
        form_layout = QFormLayout()
        self.mode_combobox = QComboBox()
        self.mode_combobox.addItem("输入内容", "set_value")
        self.mode_combobox.addItem("点击图标", "click_icon")
        form_layout.addRow("操作模式:", self.mode_combobox)

        # 将模式下拉框添加到标签的第一个页面
        layout.addLayout(form_layout)

        # 创建内容编辑框并添加到第一个标签页
        self.content_textEdit = QTextEdit()
        first_tab = QWidget()
        first_tab_layout = QVBoxLayout()
        first_tab_layout.addWidget(self.content_textEdit)
        first_tab.setLayout(first_tab_layout)
        self.tab_widget.addTab(first_tab, "文字")

        # 创建图形视图并添加到第二个标签页
        self.graphics_view = CustomGraphicsView()
        self.graphics_scene = QGraphicsScene(self)
        self.graphics_view.setScene(self.graphics_scene)

        second_tab = QWidget()
        second_tab_layout = QVBoxLayout()
        second_tab_layout.addWidget(self.graphics_view)
        second_tab.setLayout(second_tab_layout)
        self.tab_widget.addTab(second_tab, "图形")

        # 将标签页添加到主布局
        layout.addWidget(self.tab_widget)

        # 确认和取消按钮
        button_layout = QHBoxLayout()
        ok_button = QPushButton("确定")
        cancel_button = QPushButton("取消")
        button_layout.addWidget(ok_button)
        button_layout.addWidget(cancel_button)

        # 设置快捷键 Ctrl+Enter 绑定到 "确定" 按钮的点击事件
        shortcut = QShortcut(QtGui.QKeySequence("Ctrl+Enter"), ok_button)
        shortcut.activated.connect(ok_button.click)

        layout.addLayout(button_layout)

        # 设置焦点到内容编辑框
        self.content_textEdit.setFocus()

        # 连接按钮事件
        ok_button.clicked.connect(self.save)
        cancel_button.clicked.connect(self.finished)

    def create_toolbar(self, layout):
        """
        创建工具栏并添加图标操作
        """
        toolbar = QToolBar("工具选项")  # 创建工具栏
        toolbar.setMovable(True)  # 设置工具栏可移动
        toolbar.setFixedHeight(40)  # 设置工具栏固定高度
        toolbar.setStyleSheet("""
            QToolBar { 
                border: 1px solid gray; 
                background: #f0f0f0; 
                border-radius: 5px; 
            }
            QToolButton { 
                width: 25px; 
                height: 25px; 
                icon-size: 20px;  /* 设置图标大小 */
                padding: 4px; 
                margin: 2px; 
                border: none; 
                background: transparent; 
                border-radius: 3px; 
            } 
            QToolButton:hover { 
                background: #d9d9d9; 
                opacity: 0.8; 
            }
        """)  # 设置工具栏和按钮的样式

        # 创建操作并设置图标和工具提示
        fullscreen_action = QAction(QtGui.QIcon("images/fullscreen.png"), "全屏截取", self)
        fullscreen_action.setToolTip("全屏截取")  # 设置按钮的工具提示
        crop_action = QAction(QtGui.QIcon("images/crop.png"), "区域截取", self)
        crop_action.setToolTip("区域截取")  # 设置按钮的工具提示
        rect_action = QAction(QtGui.QIcon("images/rectangle.png"), "方形标注框", self)
        rect_action.setToolTip("方形标注框")  # 设置按钮的工具提示
        circle_action = QAction(QtGui.QIcon("images/circle.png"), "圆形标注框", self)
        circle_action.setToolTip("圆形标注框")  # 设置按钮的工具提示
        pen_action = QAction(QtGui.QIcon("images/pen.png"), "自由标注框", self)
        pen_action.setToolTip("自由标注框")  # 设置按钮的工具提示
        text_action = QAction(QtGui.QIcon("images/text.png"), "文本标注", self)
        text_action.setToolTip("文本标注")  # 设置按钮的工具提示

        # 将操作添加到工具栏
        toolbar.addAction(fullscreen_action)
        toolbar.addAction(crop_action)
        toolbar.addAction(rect_action)
        toolbar.addAction(circle_action)
        toolbar.addAction(pen_action)
        toolbar.addAction(text_action)

        # 连接操作的触发事件
        fullscreen_action.triggered.connect(self.capture_screenshot)
        crop_action.triggered.connect(self.capture_crop)
        rect_action.triggered.connect(lambda: self.print_tool("关闭"))

        # 将工具栏添加到布局的最上方
        layout.addWidget(toolbar)

    def print_tool(self, tool_name):
        """
        打印被点击工具的名称
        """
        print(f"选择了工具: {tool_name}")

    def capture_screenshot(self):
        # Capture the entire screen
        screenshot = pyautogui.screenshot()

        # Convert to QPixmap using a QByteArray
        byte_array = io.BytesIO()
        screenshot.save(byte_array, format='PNG')
        byte_array.seek(0)
        pixmap = QPixmap()
        pixmap.loadFromData(byte_array.read())

        # Show in the scene
        self.graphics_scene.clear()
        self.graphics_view.setPixmap(pixmap)

    def capture_crop(self):
        self.screen_capture_win = ScreenCapture()
        self.screen_capture_win.on_captured_finished.connect(self.handle_crop_capture)

        self.screen_capture_win.show()

    def handle_crop_capture(self, pos, pixmap):
        print(pos[0])
        print(pos[1])
        print(pos[2])
        print(pos[3])
        self.graphics_scene.clear()
        self.graphics_view.setPixmap(pixmap)

    def get_data(self):
        return {
            'mode': self.mode_combobox.currentText(),
            'content': self.content_textEdit.toPlainText().strip()
        }

    def finished(self):
        self.close()  # 关闭窗口时发射信号
        self.capture_finished.emit()  # 发射信号，通知窗口已关闭

    def save_image(self):
        """Render the scene to a pixmap and save it as an image file."""
        scene_rect = self.graphics_scene.sceneRect()
        image = QPixmap(scene_rect.size().toSize())
        image.fill(Qt.white)

        painter = QPainter(image)
        self.graphics_scene.render(painter)
        painter.end()

        options = QFileDialog.Options()
        file_name, _ = QFileDialog.getSaveFileName(self, "Save Image", "", "PNG Files (*.png);;JPEG Files (*.jpg;*.jpeg);;All Files (*)", options=options)
        if file_name:
            image.save(file_name)
        return file_name

    def save(self):
        global storage
        mode = self.mode_combobox.currentData()
        content = self.content_textEdit.toPlainText()
        image_path = self.save_image()
        json_object = {'action': 'annotated', 'mode': mode, 'content': content, 'image_path': image_path, '_time': time.time()}
        print(f"'action': 'annotated', 'mode': {mode},'content': {content},'image_path': {image_path}, '_time': {time.time()}")
        storage.append(json_object)
        self.close()  # 关闭窗口时发射信号
        self.capture_finished.emit()  # 发射信号，通知窗口已关闭


# Keyboard press event handler
def on_press(key):
    global is_capturing, esc_count, last_esc_time

    # Check ESC double-click condition
    if key == pynput.keyboard.Key.esc:
        if time.time() - last_esc_time < 0.5:
            esc_count += 1
            if esc_count == 2:
                is_capturing = not is_capturing
                esc_count = 0
                if not is_capturing:
                    mouse_position = pynput.mouse.Controller().position

                    # Emit signal to show dialog in the main thread
                    signal_emitter.show_dialog_signal.emit(mouse_position[0], mouse_position[1])
                print("State toggled: capturing is now", is_capturing)
        else:
            esc_count = 1
        last_esc_time = time.time()
        return

    # Handle other keys
    if is_capturing:
        try:
            char = key.char
        except AttributeError:
            char = str(key)
        json_object = {'action': 'pressed_key', 'key': char, '_time': time.time()}
        print(f"'action': 'pressed_key', 'key': {char}, '_time': {time.time()}")
        storage.append(json_object)


# Keyboard release event handler
def on_release(key):
    if is_capturing:
        try:
            char = key.char
        except AttributeError:
            char = str(key)
        json_object = {'action': 'released_key', 'key': char, '_time': time.time()}
        storage.append(json_object)


# Mouse move event handler
def on_move(x, y):
    if is_capturing and record_all:
        if len(storage) == 0 or (storage[-1]['action'] == 'moved' and time.time() - storage[-1]['_time'] > 0.02):
            json_object = {'action': 'moved', 'x': x, 'y': y, '_time': time.time()}
            storage.append(json_object)


# Mouse click event handler
def on_click(x, y, button, pressed):
    if is_capturing:
        json_object = {'action': 'pressed' if pressed else 'released', 'button': str(button), 'x': x, 'y': y, '_time': time.time()}
        print(f"'action': {'pressed' if pressed else 'released'}, 'button': {str(button)}, 'x': {x}, 'y': {y}, '_time': {time.time()}")
        storage.append(json_object)
        if len(storage) > 1 and storage[-1]['action'] == 'released' and storage[-1]['button'] == 'Button.right' and storage[-1]['_time'] - storage[-2]['_time'] > 2:
            with open(f'C:/dev/ai-sns/record-and-play-pynput/record-and-play-pynput/data/{name_of_recording}.txt', 'w') as outfile:
                json.dump(storage, outfile, ensure_ascii=False)
            return False


# Mouse scroll event handler
def on_scroll(x, y, dx, dy):
    if is_capturing:
        json_object = {'action': 'scroll', 'vertical_direction': int(dy), 'horizontal_direction': int(dx), 'x': x, 'y': y, '_time': time.time()}
        storage.append(json_object)


# Record function to be run on a separate thread
def auto_operate():
    global keyboard_listener, mouse_listener, storage, name_of_recording, number_of_plays, gstatus, gvalue

    with open(name_of_recording) as json_file:
        data = json.load(json_file)
    special_keys = {"Key.shift": Key.shift, "Key.tab": Key.tab, "Key.caps_lock": Key.caps_lock, "Key.ctrl": Key.ctrl, "Key.alt": Key.alt, "Key.cmd": Key.cmd, "Key.cmd_r": Key.cmd_r, "Key.alt_r": Key.alt_r, "Key.ctrl_r": Key.ctrl_r, "Key.shift_r": Key.shift_r, "Key.enter": Key.enter, "Key.backspace": Key.backspace, "Key.f19": Key.f19, "Key.f18": Key.f18, "Key.f17": Key.f17, "Key.f16": Key.f16, "Key.f15": Key.f15, "Key.f14": Key.f14, "Key.f13": Key.f13, "Key.media_volume_up": Key.media_volume_up, "Key.media_volume_down": Key.media_volume_down, "Key.media_volume_mute": Key.media_volume_mute, "Key.media_play_pause": Key.media_play_pause, "Key.f6": Key.f6, "Key.f5": Key.f5, "Key.right": Key.right, "Key.down": Key.down, "Key.left": Key.left, "Key.up": Key.up, "Key.page_up": Key.page_up, "Key.page_down": Key.page_down, "Key.home": Key.home, "Key.end": Key.end, "Key.delete": Key.delete,
                    "Key.space": Key.space,"Key.esc": Key.esc}

    mouse = MouseController()
    keyboard = KeyboardController()

    for loop in range(number_of_plays):
        for index, obj in enumerate(data):
            action, _time = obj['action'], obj['_time']
            try:
                next_movement = data[index + 1]['_time']
                pause_time = next_movement - _time
            except IndexError as e:
                pause_time = 1

            print("dataaction:",action)

            if action == "pressed_key" or action == "released_key":
                key = obj['key'] if 'Key.' not in obj['key'] else special_keys[obj['key']]
                print("action: {0}, time: {1}, key: {2}".format(action, _time, str(key)))
                if action == "pressed_key":
                    keyboard.press(key)
                else:
                    keyboard.release(key)
                time.sleep(pause_time)

            elif action == "annotated":
                print("annotated")
                mode = obj['mode']
                content = obj['content']
                image_path = obj['image_path']
                if mode == "set_value":
                    gstatus = "waiting_for_input_value"
                    print("set_value")
                    signal_emitter.wait_for_input_signal.emit(content,image_path)
                    while gstatus == "waiting_for_input_value":
                        time.sleep(0.5)
                        if gvalue != "":
                            keyboard.type(gvalue)
                            gvalue = ""

            else:
                move_for_scroll = True
                x, y = obj['x'], obj['y']
                if action == "scroll" and index > 0 and (data[index - 1]['action'] == "pressed" or data[index - 1]['action'] == "released"):
                    if x == data[index - 1]['x'] and y == data[index - 1]['y']:
                        move_for_scroll = False
                print("x: {0}, y: {1}, action: {2}, time: {3}".format(x, y, action, _time))
                mouse.position = (x, y)
                if action == "pressed" or action == "released" or action == "scroll" and move_for_scroll == True:
                    time.sleep(0.1)
                if action == "pressed":
                    mouse.press(Button.left if obj['button'] == "Button.left" else Button.right)
                elif action == "released":
                    mouse.release(Button.left if obj['button'] == "Button.left" else Button.right)
                elif action == "scroll":
                    horizontal_direction, vertical_direction = obj['horizontal_direction'], obj['vertical_direction']
                    mouse.scroll(horizontal_direction, vertical_direction)
                time.sleep(pause_time)


# Start recording in a new thread
def go_auto_operate():
    auto_operate_thread = threading.Thread(target=auto_operate)
    auto_operate_thread.start()


# Class definitions like CircularCountdown, ScreenBar, ScreenLabel
# remain unchanged, assuming the rest of your implementation doesn't need threading.


# 圆形倒计时窗口类
class CircularCountdown(QWidget):
    # 定义一个信号，用于在窗口关闭时发射
    countdown_finished = pyqtSignal()

    def __init__(self):
        super().__init__()

        # 设置窗口无边框且形状为圆形，并置于最前
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint)
        self.setAttribute(Qt.WA_TranslucentBackground)

        # 设置窗口大小
        self.resize(300, 300)

        # 设置倒计时初始值
        self.countdown_from = 2

        # 创建一个定时器
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_countdown)
        self.timer.start(1000)  # 每秒触发一次

        # 显示窗口
        self.show()

    def update_countdown(self):
        """更新倒计时显示"""
        if self.countdown_from > 0:
            self.countdown_from -= 1
            self.update()  # 触发重绘
        else:
            # 倒计时结束，关闭窗口
            self.timer.stop()
            self.close()  # 关闭窗口时发射信号
            self.countdown_finished.emit()  # 发射信号，通知窗口已关闭

    def paintEvent(self, event):
        """自定义绘制窗口"""
        painter = QPainter(self)

        # 设置画刷为半透明背景
        painter.setBrush(QBrush(QColor(0, 0, 0, 0)))
        painter.setPen(Qt.NoPen)

        # 绘制一个半透明黑色的圆形
        painter.setBrush(QBrush(QColor(0, 0, 0, 150)))  # 设置黑色且透明度为150
        painter.drawEllipse(0, 0, self.width(), self.height())

        # 设置字体并绘制文本
        painter.setFont(QFont("Helvetica", 80))
        painter.setPen(QColor(255, 255, 255))
        if self.countdown_from > 0:
            painter.drawText(self.rect(), Qt.AlignCenter, str(self.countdown_from))
        else:
            painter.setFont(QFont("Helvetica", 60))
            painter.drawText(self.rect(), Qt.AlignCenter, "开始")


# 屏幕工具栏类
class AutoOprateBar(Base):
    wait_for_input_from_ai_signal = pyqtSignal(str,str)
    def __init__(self):
        super(AutoOprateBar, self).__init__()
        self.status = "ready"
        self.box = QVBoxLayout()
        self.tip_box = QHBoxLayout()
        self.btn_box = QHBoxLayout()
        self.tip_label = QLabel(self)
        self.timer_label = QLabel(self)
        self.annotation_btn = QPushButton()
        self.start_btn = QPushButton()
        self.end_btn = QPushButton()
        self.close_btn = QPushButton()
        self.bind()
        self.set_style()
        initialize_globals()

    def set_style(self):
        self.start_btn.setEnabled(True)
        self.start_btn.setToolTip("开始记录")
        self.end_btn.setEnabled(False)
        self.end_btn.setToolTip("结束记录")
        self.start_btn.setIcon(QIcon('images/startcircle.png'))
        self.end_btn.setIcon(QIcon('images/stop.png'))
        self.close_btn.setIcon(QIcon('images/closecircle.png'))
        self.close_btn.setToolTip("关闭")
        # self.tip_label.setIcon(QIcon('operationlearning/res/full.png'))
        pixmap = QPixmap('images/arrowalldirect.png')  # 请将 'path_to_your_icon.png' 替换为你的图标路径
        icon_size = (22, 22)  # 指定图标的宽和高
        scaled_pixmap = pixmap.scaled(icon_size[0], icon_size[1], Qt.KeepAspectRatio, Qt.SmoothTransformation)

        self.tip_label.setPixmap(scaled_pixmap)
        self.annotation_btn.setIcon(QIcon('images/annotation.png'))
        self.annotation_btn.setToolTip("对操作进行描述和说明，让AI大模型了解")
        self.tip_label.setToolTip("鼠标按此，移动工具条")
        self.btn_box.addWidget(self.tip_label)
        self.btn_box.addWidget(self.annotation_btn, 0)
        self.btn_box.addWidget(self.end_btn, 0)
        self.btn_box.addWidget(self.start_btn, 0)

        # 初始化计时变量
        self.seconds = 0
        self.is_running = False

        self.timer_label.setFont(QFont("Arial", 12))
        self.timer_label.setStyleSheet("QLabel { background-color: pink; border-radius: 5px; padding-left:5px;padding-right:5px}")
        self.timer_label.setText("00:00:00")
        self.timer_label.setToolTip("记录时长")

        # 初始化计时器
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_time)

        self.btn_box.addWidget(self.timer_label)

        self.btn_box.addWidget(self.close_btn, 0)

        # self.box.addLayout(self.tip_box)
        self.box.addLayout(self.btn_box)
        self.box.setContentsMargins(5, 5, 5, 5)
        self.setWindowOpacity(0.7)
        self.frameGeometry()
        self.move(QApplication.desktop().frameGeometry().width() - 300, QApplication.desktop().frameGeometry().height() - 150)
        self.setLayout(self.box)

    def toggle_timer(self):
        """切换计时状态（开始/暂停）"""
        if self.is_running:
            self.timer.stop()
        else:
            self.timer.start(1000)  # 每秒更新一次
        self.is_running = not self.is_running

    def update_time(self):
        """更新显示时间"""
        self.seconds += 1
        h = self.seconds // 3600
        m = (self.seconds % 3600) // 60
        s = self.seconds % 60
        self.timer_label.setText(f"{h:02}:{m:02}:{s:02}")

    def on_countdown_finished(self):
        # Connect the signal to the slot function
        signal_emitter.show_dialog_signal.connect(self.show_dialog)
        signal_emitter.wait_for_input_signal.connect(self.get_value_for_auto_operation)
        go_auto_operate()

        # self.confwin = CaptureDialog()

    def bind(self):
        global is_capturing

        def annotation_signal():
            mouse_position = mouse.Controller().position
            # Emit signal to show dialog in the main thread
            # signal_emitter.show_dialog_signal.emit(mouse_position[0], mouse_position[1])
            # self.show_dialog(mouse_position[0], mouse_position[1])
            self.show_dialog(-1, -1)
            self.start_btn.setEnabled(False)

        def start_signal():
            global is_capturing
            self.toggle_timer()
            self.end_btn.setEnabled(True)
            if self.status == "paused" or self.status == "ready":
                self.status = "started"
                is_capturing = True
                self.start_btn.setIcon(QIcon("images/pause.png"))
                self.start_btn.setToolTip("暂停记录")
                self.annotation_btn.setEnabled(False)
                self.countdown_window = CircularCountdown()
                self.countdown_window.countdown_finished.connect(self.on_countdown_finished)
                self.countdown_window.show()

            elif self.status == "started":
                self.status = "paused"
                is_capturing = False
                self.start_btn.setIcon(QIcon("images/startcircle.png"))
                self.start_btn.setToolTip("开始记录")
                self.annotation_btn.setEnabled(True)

        def end_signal():
            self.end_record()

        self.annotation_btn.clicked.connect(annotation_signal)
        self.start_btn.clicked.connect(start_signal)
        self.end_btn.clicked.connect(end_signal)
        self.close_btn.clicked.connect(self.close)

    def close_win(self):
        self.end_record()
        self.close()

    def end_record(self):
        global keyboard_listener, mouse_listener
        keyboard_listener.stop()
        mouse_listener.stop()
        if len(storage) > 1:
            with open(f'C:/dev/ai-sns/record-and-play-pynput/record-and-play-pynput/data/{name_of_recording}.txt', 'w') as outfile:
                json.dump(storage, outfile, ensure_ascii=False)
        self.close()

    # Show dialog
    def show_dialog(self, x, y):
        self.dialog = CaptureDialog()
        if x > 0 and y > 0:
            self.dialog.move(x, y)
        self.dialog.show()
        self.dialog.capture_finished.connect(self.capture_finished_handle)
        # 确保对话框在最上层并获得焦点
        self.dialog.raise_()  # 将对话框置于最上层
        self.dialog.activateWindow()  # 激活对话框窗口

        self.annotation_btn.setEnabled(False)
        self.start_btn.setIcon(QIcon("images/startcircle.png"))
        self.start_btn.setEnabled(False)
        self.start_btn.setToolTip("开始记录")
        self.toggle_timer()
        self.end_btn.setEnabled(False)

    def capture_finished_handle(self):
        self.annotation_btn.setEnabled(True)
        self.start_btn.setEnabled(True)
        self.start_btn.setIcon(QIcon("images/pause.png"))
        self.start_btn.setToolTip("暂停记录")
        self.toggle_timer()
        self.end_btn.setEnabled(True)
        self.countdown_window = CircularCountdown()
        self.countdown_window.show()

    def get_value_for_auto_operation(self,question,img_path):
        print("get get_value_for_auto_operation signal")
        self.wait_for_input_from_ai_signal.emit(question,img_path)

    def feed_bak_from_ai(self,value):
        global gstatus,gvalue
        gstatus=""
        gvalue=value
