# filename: verify_pyqt5_installation.py
try:
    from PyQt5.QtWidgets import QApplication
    print("PyQt5 is installed successfully.")
except ImportError:
    print("PyQt5 is not installed.")