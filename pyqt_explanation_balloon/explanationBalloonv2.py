import os
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QPainter, QBrush, QColor, QPen, QPainterPath, QTextOption, QIcon
from PyQt5.QtWidgets import QWidget, QGraphicsDropShadowEffect, QGridLayout, QPushButton


class ExplanationBalloon(QWidget):
    def __init__(self, widget, width: float, height: float, text: str):
        super().__init__()
        self.installEventFilter(self)
        self.__widget = widget
        self.__widget.installEventFilter(self)
        self.__window = self.__widget.window()
        self.__window.installEventFilter(self)

        self.__initUi(width, height, text)

    def __initUi(self, width, height, text):
        self.setFixedSize(int(width + 2), int(height + 10))
        self.__initBalloon(width, height, text)
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.SubWindow)
        self.setAttribute(Qt.WA_TranslucentBackground)
        eff = QGraphicsDropShadowEffect(self)
        eff.setOffset(0, 0)
        eff.setBlurRadius(5.0)
        self.setGraphicsEffect(eff)

        # Close Button Initialization
        self.__btnClose = QPushButton()
        ico_filename = os.path.join(os.path.dirname(__file__), 'ico/close.svg')
        self.__btnClose.setIcon(QIcon(ico_filename))
        self.__btnClose.clicked.connect(self.close)

        # Previous Button Initialization
        self.__btnPrev = QPushButton("上一步")
        self.__btnPrev.clicked.connect(self.move_left)

        # Next Button Initialization
        self.__btnNext = QPushButton("下一步")
        self.__btnNext.clicked.connect(self.move_right)

        # Layout setup
        lay = QGridLayout()
        lay.addWidget(self.__btnClose, 0, 0, 1, 1, Qt.AlignTop | Qt.AlignRight)
        lay.addWidget(self.__btnPrev, 1, 0, 1, 1, Qt.AlignLeft)
        lay.addWidget(self.__btnNext, 1, 1, 1, 1, Qt.AlignRight)
        lay.setContentsMargins(5, 5, 5, 5)
        self.setLayout(lay)

    def __initBalloon(self, width, height, text):
        self.__border_width = 1
        self.__width = width
        self.__height = height
        self.__text = text
        self.__background_color = QColor(241, 241, 241, 255)
        self.__balloon = self.__getBalloonShape(self.__width, self.__height)

    def __setIsosceles(self, x, y, width: float, height: float, orientation=Qt.Horizontal) -> QPainterPath:
        isosceles = QPainterPath()
        x1 = x
        y1 = y
        x2 = x1 + width
        y2 = y1
        x3 = (x1 + x2) / 2
        y3 = y1 + height
        isosceles.moveTo(x1, y1)
        isosceles.lineTo(x2, y2)
        isosceles.lineTo(x3, y3)
        isosceles.lineTo(x1, y1)
        return isosceles

    def paintEvent(self, e):
        painter = QPainter(self)
        brush = QBrush(self.__background_color)
        pen = QPen(QColor(Qt.darkGray), self.__border_width)
        painter.setPen(pen)
        painter.setBrush(brush)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.drawPath(self.__balloon)
        textOption = QTextOption()
        textOption.setAlignment(Qt.AlignCenter)
        textOption.setWrapMode(QTextOption.WordWrap)
        painter.drawText(self.__balloon.boundingRect(), self.__text, textOption)
        return super().paintEvent(e)

    def __getBalloonShape(self, width: float, height: float):
        path1 = QPainterPath()
        path1.addRoundedRect(0, 0, width, height, 10.0, 10.0)
        path2 = self.__setIsosceles(20.0, height - 3, 30.0, 10.0)
        path3 = path2.united(path1)
        return path3

    def setPosition(self):
        x, y = self.__widget.geometry().x(), self.__widget.geometry().y()
        x, y = x + self.__window.geometry().x(), y + self.__window.geometry().y()
        self.move(x, y - self.height())

    def setBackgroundColor(self, color: QColor):
        self.__background_color = color

    def eventFilter(self, obj, e):
        if isinstance(obj, type(self.__widget)):
            self.setPosition()
        elif isinstance(obj, type(self.__window)):
            self.raise_()
            if e.type() == 13 or e.type() == 14:
                self.setPosition()
        elif isinstance(obj, type(self)):
            if e.type() == 97:
                print(self.fontMetrics().boundingRect(self.__text))
        return super().eventFilter(obj, e)

    def move_right(self):
        """Move the balloon to the right by 10 pixels."""
        current_pos = self.pos()
        self.move(current_pos.x() + 10, current_pos.y())

    def move_left(self):
        """Move the balloon to the left by 10 pixels."""
        current_pos = self.pos()
        self.move(current_pos.x() - 10, current_pos.y())
