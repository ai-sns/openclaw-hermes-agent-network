# _*_ coding:utf-8 _*_
from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QWidget, QApplication


class Base(QWidget):
    def __init__(self):
        super(Base, self).__init__()
        self.mMoveing = True
        self.mMovePosition = self.pos()
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint)

    def mousePressEvent(self, QMouseEvent):
        self.mMoveing = True
        self.mMovePosition = QMouseEvent.globalPos() - self.pos()
        return super().mousePressEvent(QMouseEvent)

    def mouseMoveEvent(self, QMouseEvent):
        if self.mMoveing and (QMouseEvent.buttons() and Qt.LeftButton) and (
                    QMouseEvent.globalPos() - self.mMovePosition).manhattanLength() > QApplication.startDragDistance():
            self.move(QMouseEvent.globalPos() - self.mMovePosition)
            self.mMovePosition = QMouseEvent.globalPos() - self.pos()
        return super().mouseMoveEvent(QMouseEvent)
