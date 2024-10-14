# main.py
import sys
import importlib
from PyQt5.QtWidgets import QApplication, QWidget, QVBoxLayout, QPushButton, QTabWidget



def initUI():
    layout = QVBoxLayout()

    # 创建标签页控件
    tabs = QTabWidget()
    layout.addWidget(tabs)

    # 创建加载插件的按钮
    button = QPushButton("Load Plugin")
    button.clicked.connect(load_plugin)
    layout.addWidget(button)

    return layout

def load_plugin(parent,record, *args, **kwagrs):
    try:
        plugin_directory=record.plugin_directory
        # 动态加载插件
        plugin_module = importlib.import_module(f'pluginsmanager.plugins_headless.plugins.{plugin_directory}.application')
        # 获取插件类
        plugin_class = getattr(plugin_module, "Main")
        plugin_instance = plugin_class(record)  # 创建插件实例
        return plugin_instance
    except Exception as e:
        print(f"Error loading plugin: {e}")


if __name__ == "__main__":
    app = QApplication(sys.argv)
    layout = QVBoxLayout()

    # 创建标签页控件
    tabs = QTabWidget()
    layout.addWidget(tabs)

    # 创建加载插件的按钮
    button = QPushButton("Load Plugin")
    button.clicked.connect(load_plugin)
    layout.addWidget(button)

    tabs.show()
    load_plugin(tabs)
    sys.exit(app.exec_())
