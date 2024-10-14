import sys
import json
import os
import yaml
from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QGroupBox, QGridLayout,
    QLabel, QLineEdit, QCheckBox, QSlider, QTextEdit,
    QDialogButtonBox
)
from PyQt5.QtCore import Qt, pyqtSignal, QSettings
from PyQt5.QtGui import QIcon
from PyQt5 import QtCore, QtGui, QtWidgets
from .ui_OpenAIConnectionDialog import ui_OpenAIConnectionDialog

class OpenAIConnectionDialog(QDialog, ui_OpenAIConnectionDialog):
    configured = pyqtSignal()

    def __init__(self, parent=None):
        parent = None  # 程序调用没有parent
        super(OpenAIConnectionDialog, self).__init__(parent)

        self.url_mapping = {
            "general": "wss://spark-api.xf-yun.com/v1.1/chat",
            "generalv2": "wss://spark-api.xf-yun.com/v2.1/chat",
            "generalv3": "wss://spark-api.xf-yun.com/v3.1/chat",
            "generalv3.5": "wss://spark-api.xf-yun.com/v3.5/chat",
            "4.0Ultra": "wss://spark-api.xf-yun.com/v4.0/chat"
        }


        self.setupUi(self)
        self.accepted.connect(self.saveSettings)  # 点击确认了之后，将调用saveSettings函数
        self.readSettings()

    def readSettings(self):
        try:
            file_path = os.path.join(os.path.dirname(__file__), 'config.yaml')
            with open(file_path, "r", encoding='utf-8') as f:
                config = yaml.safe_load(f)
                self.url_edit.setText(config.get("base_url", "wss://spark-api.xf-yun.com/v1.1/chat"))
                self.api_key_edit.setText(config.get("api_key", ""))
                self.model_combobox.setCurrentText(config.get("model", ""))
                self.max_tokens_edit.setText(str(config.get("max_tokens", "")))
                self.temperature_slider.setValue(int(config.get("temperature", 0) * 100))
                self.top_p_slider.setValue(int(config.get("top_p", 0) * 100))
                self.stream_checkbox.setChecked(config.get("stream", False))
                self.custom_params_checkbox.setChecked(config.get("custom_params", False))
                self.description_textedit.setPlainText(config.get("description", ""))
                self.parameters_textedit.setPlainText(config.get("parameters", ""))

        except FileNotFoundError:
            pass


    def saveSettings(self):
        config = {
            "base_url": self.url_edit.text(),
            "api_key": self.api_key_edit.text(),
            "model": self.model_combobox.currentText(),
            "max_tokens": int(self.max_tokens_edit.text()),
            "temperature": round(self.temperature_slider.value() / 100, 1),
            "top_p": round(self.top_p_slider.value() / 100, 1),
            "stream": self.stream_checkbox.isChecked(),
            "description": self.description_textedit.toPlainText(),
            "custom_params": self.custom_params_checkbox.isChecked(),
            "parameters": self.parameters_textedit.toPlainText()
        }
        file_path = os.path.join(os.path.dirname(__file__), 'config.yaml')
        with open(file_path, "w", encoding='utf-8') as f:
            yaml.dump(config, f, default_flow_style=False)
        self.configured.emit()
