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

def load_plugin(tabs,name,plugin_file_name,plugin_class_name, *args, **kwagrs):
    plugin_name = plugin_file_name  # 插件模块名
    try:
        # 动态加载插件
        plugin_module = importlib.import_module(f'pluginsmanager.plugins_gui.plugins.{plugin_name}')

        # 获取插件类
        plugin_class = getattr(plugin_module, plugin_class_name)
        plugin_instance = plugin_class()  # 创建插件实例

        # 创建插件的控件
        plugin_widget = plugin_instance.create_widget(*args, **kwagrs)

        # 添加新的标签页
        # tab_index = self.tabs.addTab(plugin_widget, f"Plugin {self.tabs.count() + 1}")
        tab_index = tabs.addTab(plugin_instance, name)
        #tab_index = self.tabs.insertTab(0,plugin_widget, f"Plugin {self.tabs.count() + 1}")

        # 自动切换到新添加的标签页
        tabs.setCurrentIndex(tab_index)

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
