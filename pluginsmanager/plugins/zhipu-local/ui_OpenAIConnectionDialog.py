from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QGroupBox, QGridLayout,
    QLabel, QLineEdit, QCheckBox, QSlider, QTextEdit,
    QDialogButtonBox, QComboBox
)
from PyQt5.QtCore import Qt, pyqtSignal, QSettings
from PyQt5.QtGui import QIcon
from PyQt5 import QtCore, QtGui, QtWidgets
import json

class ui_OpenAIConnectionDialog(object):
    def setupUi(self, ConnectionDialog):
        ConnectionDialog.setObjectName("ConnectionDialog")
        ConnectionDialog.resize(400, 400)

        self.vboxlayout = QVBoxLayout(ConnectionDialog)
        self.vboxlayout.setObjectName("vboxlayout")

        # Group box for API configuration
        self.groupBox = QGroupBox(ConnectionDialog)
        self.groupBox.setObjectName("groupBox")
        self.gridlayout = QGridLayout(self.groupBox)
        self.gridlayout.setObjectName("gridlayout")
        self.vboxlayout.addWidget(self.groupBox)

        # URL
        self.url_label = QLabel("URL:")
        self.gridlayout.addWidget(self.url_label, 0, 0)
        self.url_edit = QLineEdit()
        self.gridlayout.addWidget(self.url_edit, 0, 1, 1, 2)

        # API key
        self.api_key_label = QLabel("API Key:")
        self.gridlayout.addWidget(self.api_key_label, 1, 0)
        self.api_key_edit = QLineEdit()
        self.api_key_edit.setEnabled(True)  # Make it editable by default
        self.gridlayout.addWidget(self.api_key_edit, 1, 1, 1, 2)

        # Model selection
        self.model_label = QLabel("Model:")
        self.gridlayout.addWidget(self.model_label, 2, 0)
        self.model_combobox = QComboBox()
        self.model_combobox.addItems(["THUDM/chatglm2-6b", "THUDM/chatglm2-6b-32k", "THUDM/chatglm3-6b", "THUDM/chatglm3-6b-32k", "THUDM/chatglm3-6b-128k", "THUDM/glm-4-9b-chat", "THUDM/glm-4-9b-chat-1m"])
        self.model_combobox.setEnabled(True)  # Make it editable by default
        self.model_combobox.setEditable(True)
        self.gridlayout.addWidget(self.model_combobox, 2, 1, 1, 2)

        # Max tokens
        self.max_tokens_label = QLabel("Max Tokens:")
        self.gridlayout.addWidget(self.max_tokens_label, 3, 0)
        self.max_tokens_edit = QLineEdit()
        self.max_tokens_edit.setEnabled(True)  # Make it editable by default
        self.gridlayout.addWidget(self.max_tokens_edit, 3, 1, 1, 2)

        # Temperature slider
        self.temperature_label = QLabel("Temperature:")
        self.gridlayout.addWidget(self.temperature_label, 4, 0)
        self.temperature_slider = QSlider(Qt.Horizontal)
        self.temperature_slider.setMinimum(0)
        self.temperature_slider.setMaximum(100)
        self.temperature_slider.setEnabled(True)  # Make it editable by default
        self.gridlayout.addWidget(self.temperature_slider, 4, 1)
        self.temperature_slider_value_label = QLabel("0.0")
        self.gridlayout.addWidget(self.temperature_slider_value_label, 4, 2)

        # Top P slider
        self.top_p_label = QLabel("Top P:")
        self.gridlayout.addWidget(self.top_p_label, 5, 0)
        self.top_p_slider = QSlider(Qt.Horizontal)
        self.top_p_slider.setMinimum(0)
        self.top_p_slider.setMaximum(100)
        self.top_p_slider.setEnabled(True)  # Make it editable by default
        self.gridlayout.addWidget(self.top_p_slider, 5, 1)
        self.top_p_slider_value_label = QLabel("0.0")
        self.gridlayout.addWidget(self.top_p_slider_value_label, 5, 2)

        # Stream checkbox
        self.stream_label = QLabel("Stream:")
        self.gridlayout.addWidget(self.stream_label, 6, 0)
        self.stream_checkbox = QCheckBox()
        self.gridlayout.addWidget(self.stream_checkbox, 6, 1, 1, 2)
        self.stream_checkbox.setEnabled(True)  # Make it editable by default

        # Description
        self.description_label = QLabel("Description:")
        self.gridlayout.addWidget(self.description_label, 7, 0)
        self.description_textedit = QTextEdit()
        self.gridlayout.addWidget(self.description_textedit, 7, 1, 1, 2)
        self.description_textedit.setEnabled(True)

        # Custom parameters checkbox
        self.custom_params_label = QLabel("Custom Parameters:")
        self.gridlayout.addWidget(self.custom_params_label, 8, 0)
        self.custom_params_checkbox = QCheckBox()
        self.gridlayout.addWidget(self.custom_params_checkbox, 8, 1, 1, 2)
        self.custom_params_checkbox.setEnabled(True)  # Enable by default

        # Parameters text edit
        self.parameters_textedit = QTextEdit()
        self.gridlayout.addWidget(self.parameters_textedit, 9, 0, 1, 3)
        self.parameters_textedit.setEnabled(False)  # Disable by default

        # Set column stretch
        self.gridlayout.setColumnStretch(0, 1)
        self.gridlayout.setColumnStretch(1, 2)
        self.gridlayout.setColumnStretch(2, 1)

        # Connect signals
        self.custom_params_checkbox.stateChanged.connect(self.toggle_parameters_edit)
        self.temperature_slider.valueChanged.connect(self.update_temperature_label)
        self.top_p_slider.valueChanged.connect(self.update_top_p_label)

        # Button box
        self.buttonBox = QDialogButtonBox(ConnectionDialog)
        self.buttonBox.setOrientation(Qt.Horizontal)
        self.buttonBox.setStandardButtons(QDialogButtonBox.Cancel | QDialogButtonBox.Ok)
        self.buttonBox.setObjectName("buttonBox")
        ok_button = self.buttonBox.button(QDialogButtonBox.Ok)
        ok_button.setText("确定")
        cancel_button = self.buttonBox.button(QDialogButtonBox.Cancel)
        cancel_button.setText("取消")
        self.vboxlayout.addWidget(self.buttonBox)

        self.retranslateUi(ConnectionDialog)
        self.buttonBox.accepted.connect(ConnectionDialog.accept)
        self.buttonBox.rejected.connect(ConnectionDialog.reject)
        ConnectionDialog.setWindowTitle("连接配置")
        ConnectionDialog.setWindowIcon(QIcon("images/aisns.png"))
        QtCore.QMetaObject.connectSlotsByName(ConnectionDialog)

    def retranslateUi(self, ConnectionDialog):
        self.groupBox.setTitle("大模型连接配置")
        self.url_label.setText("URL:")
        self.api_key_label.setText("API Key:")
        self.model_label.setText("Model:")
        self.max_tokens_label.setText("Max Tokens:")
        self.temperature_label.setText("Temperature:")
        self.top_p_label.setText("Top P:")
        self.stream_label.setText("Stream:")
        self.custom_params_label.setText("Custom Parameters:")
        self.description_label.setText("Description:")

    def toggle_parameters_edit(self, state):
        enabled = state == Qt.Checked
        # self.api_key_edit.setEnabled(not enabled)
        self.model_combobox.setEnabled(not enabled)
        self.max_tokens_edit.setEnabled(not enabled)
        self.temperature_slider.setEnabled(not enabled)
        self.top_p_slider.setEnabled(not enabled)
        self.stream_checkbox.setEnabled(not enabled)


        if enabled:
            # Convert configuration to JSON format and set it as default text
            config = {
                "model": self.model_combobox.currentText(),
                "max_tokens": int(self.max_tokens_edit.text()),
                "temperature": round(self.temperature_slider.value() / 100, 1),
                "top_p": round(self.top_p_slider.value() / 100, 1),
                "stream": self.stream_checkbox.isChecked(),
                "n": 1,
                "stop": None,
                "frequency_penalty": 0.0,
                "presence_penalty": 0.6
            }
            self.parameters_textedit.setPlainText(json.dumps(config, indent=4))
        self.parameters_textedit.setEnabled(enabled)

    def update_temperature_label(self, value):
        self.temperature_slider_value_label.setText(f"{value / 100:.1f}")

    def update_top_p_label(self, value):
        self.top_p_slider_value_label.setText(f"{value / 100:.1f}")
