# filename: simple_qt_example.py

import sys
from PyQt5.QtWidgets import QApplication, QLabel, QWidget

def main():
    app = QApplication(sys.argv)
    window = QWidget()
    label = QLabel('Hello, PyQt5!', parent=window)
    window.setGeometry(100, 100, 280, 80)
    window.setWindowTitle('Simple PyQt5 Example')
    window.show()
    sys.exit(app.exec_())

if __name__ == '__main__':
    main()