from PyQt5 import QtWidgets, QtCore, QtGui

class TaskWidget(QtWidgets.QWidget):
    def __init__(self):
        super(TaskWidget, self).__init__()
        self.messageEdit = QtWidgets.QTextEdit(self)  # 初始化QTextEdit
        self.messageEdit.installEventFilter(self)  # 安装事件过滤器

    def eventFilter(self, obj, event):
        """过滤事件以检测 '@' 键的按下，并显示选择框"""
        if obj == self.messageEdit and event.type() == QtCore.QEvent.KeyPress:
            if event.text() == "@":  # 检测 '@' 键
                self.showCompletionList()  # 显示选择框
                return True  # 事件被处理，返回True
        return super(TaskWidget, self).eventFilter(obj, event)  # 其他事件交给基类处理

    def showCompletionList(self):
        """显示选择框，供用户选择内容"""
        # 这里可以实现选择框的逻辑，比如使用QListWidget来展示选择项
        # 假设我们有一个固定的选择项列表
        choices = ["Alice", "Bob", "Charlie"]
        
        # 创建QListWidget作为选择框
        self.completionList = QtWidgets.QListWidget()
        self.completionList.addItems(choices)  # 添加选择项
        self.completionList.itemClicked.connect(self.insertCompletion)  # 连接点击事件

        # 显示选择框
        cursor = self.messageEdit.textCursor()  # 获取当前光标
        cursorRect = self.messageEdit.cursorRect(cursor)  # 获取光标位置矩形
        self.completionList.setGeometry(cursorRect.x(), cursorRect.y() + cursorRect.height(), 200, 100)
        self.completionList.show()  # 显示选择框
        self.completionList.setFocus()  # 使选择框获得焦点

    def insertCompletion(self, item):
        """插入用户选择的内容"""
        cursor = self.messageEdit.textCursor()  # 获取当前光标
        cursor.movePosition(QtGui.QTextCursor.Left, QtGui.QTextCursor.KeepAnchor, 1)  # 选择 '@'
        cursor.insertText("@" + item.text() + " ")  # 插入 '@' 和选择的文本
        self.messageEdit.setTextCursor(cursor)  # 更新光标位置
        self.completionList.close()  # 关闭选择框

# 应用示例代码
if __name__ == "__main__":
    import sys
    app = QtWidgets.QApplication(sys.argv)
    widget = TaskWidget()
    widget.resize(400, 300)
    widget.show()
    sys.exit(app.exec_())