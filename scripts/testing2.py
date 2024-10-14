import os
import sys
from PyQt5.QtWidgets import QWidget, QApplication, QMessageBox, QMainWindow, QPushButton, QVBoxLayout
from PyQt5.QtWebEngineWidgets import QWebEngineView
from PyQt5.QtWebChannel import QWebChannel
from PyQt5.QtCore import pyqtSlot, Qt, QUrl, QFileInfo, pyqtProperty
from PyQt5.QtCore import QDateTime
from PyQt5.QtCore import QThread, pyqtSignal
from pathlib import Path
import copy
class Myshared(QWidget):
    on_message = pyqtSignal(str)
    def __init__(self):
        super().__init__()
        self.theinnervalue = "cjrok"

    def PyQt52WebValue(self):
        return self.theinnervalue

    def Web2PyQt5Value(self, tmpstr):
        self.theinnervalue = self.theinnervalue + tmpstr
        QMessageBox.information(self, "从网页来的信息", tmpstr)

    thevalue = pyqtProperty(str, fget=PyQt52WebValue, fset=Web2PyQt5Value)
class Myshared2(QWidget):
    on_message = pyqtSignal(str)
    def __init__(self):
        super().__init__()
        self.theinnervalue = "cjrok2"

    def PyQt52WebValue(self):
        return self.theinnervalue

    def Web2PyQt5Value(self, tmpstr):
        self.theinnervalue = self.theinnervalue + tmpstr
        QMessageBox.information(self, "从网页来的信息", tmpstr)

    thevalue = pyqtProperty(str, fget=PyQt52WebValue, fset=Web2PyQt5Value)

class MainWindow(QMainWindow):
    def __init__(self):
        super(MainWindow, self).__init__()
        # self.channel=None

        channel = QWebChannel()
        shared = Myshared()
        self.channel = channel
        self.shared = shared

        self.setWindowTitle('Javascript 调用 PyQt5')
        self.setGeometry(5, 30, 1355, 730)

        # 设置布局和按钮
        layout = QVBoxLayout()
        self.browser = QWebEngineView()
        self.browser2 = QWebEngineView()
        self.button = QPushButton('更新时间戳')
        self.button2 = QPushButton('更新时间戳2')
        self.button.clicked.connect(self.btclick)
        self.button2.clicked.connect(self.btclick2)

        # # 加载外部网页
        # url = QUrl(QFileInfo("./index3.html").absoluteFilePath())
        # self.browser.page().load(url)

        # 将浏览器和按钮添加到布局
        container = QWidget()
        layout.addWidget(self.browser)
        layout.addWidget(self.browser2)
        layout.addWidget(self.button)
        layout.addWidget(self.button2)
        container.setLayout(layout)
        self.setCentralWidget(container)

    def calljs(self, shared):
        jscode = "PyQt52WebValueHtml('来自 PyQt 的信息，你好网页');"
        self.browser.page().runJavaScript(jscode)

    @pyqtSlot()
    def btclick(self):
        current_timestamp = QDateTime.currentDateTime().toString()
        shared.theinnervalue = current_timestamp
        print(f'更新后的值: {shared.theinnervalue}')

        current_timestamp = QDateTime.currentDateTime().toString()
        shared.theinnervalue = current_timestamp
        print(f'更新后的值2: {shared.theinnervalue}')


        tmpStr="""
        
# 示例代码

这是一个Python代码示例：

`\`\`python
def hello_world():
    print("Hello, world!")

hello_world()
```

这是一个JavaScript代码示例：

```javascript
function helloWorld() {
    console.log("Hello, world!");
}

helloWorld();
```

这是一个表格示例：

| Header 1 | Header 2 | Header 3 |
|----------|----------|----------|
| Row 1 Col 1 | Row 1 Col 2 | Row 1 Col 3 |
| Row 2 Col 1 | Row 2 Col 2 | Row 2 Col 3 |
| Row 3 Col 1 | Row 3 Col 2 | Row 3 Col 3 |



 当然可以！以下是使用Python实现的冒泡排序算法：

`\`\`python
def bubble_sort(arr):
    n = len(arr)
    for i in range(n):
        # 内层循环从头开始两两比较，直到已排序部分
        for j in range(0, n - i - 1):
            if arr[j] > arr[j + 1]:
                arr[j], arr[j + 1] = arr[j + 1], arr[j]

# 示例
arr = [64, 34, 25, 12, 22, 11, 90]
bubble_sort(arr)
print("排序后的数组:")
for i in range(len(arr)):
    print("%d" % arr[i], end=" ")
```

这段代码实现了冒泡排序算法。`bubble_sort`函数接受一个列表作为参数，对列表进行升序排序。你可以通过修改示例中的数组`arr`来测试不同的输入。

        """



        shared.on_message.emit(tmpStr)

    @pyqtSlot()
    def btclick2(self):
        current_timestamp = QDateTime.currentDateTime().toString()
        shared2.theinnervalue = current_timestamp
        print(f'更新后的值: {shared2.theinnervalue}')

        current_timestamp = QDateTime.currentDateTime().toString()
        shared2.theinnervalue = current_timestamp
        print(f'更新后的值2: {shared2.theinnervalue}')

        tmpStr = """

# 示例代码222

这是一个Python代码示例：

`\`\`python
def hello_world():
    print("Hello, world!")

hello_world()
```

这是一个JavaScript代码示例：

```javascript
function helloWorld() {
    console.log("Hello, world!");
}

helloWorld();
```

这是一个表格示例：

| Header 1 | Header 2 | Header 3 |
|----------|----------|----------|
| Row 1 Col 1 | Row 1 Col 2 | Row 1 Col 3 |
| Row 2 Col 1 | Row 2 Col 2 | Row 2 Col 3 |
| Row 3 Col 1 | Row 3 Col 2 | Row 3 Col 3 |



 当然可以！以下是使用Python实现的冒泡排序算法：

`\`\`python
def bubble_sort(arr):
    n = len(arr)
    for i in range(n):
        # 内层循环从头开始两两比较，直到已排序部分
        for j in range(0, n - i - 1):
            if arr[j] > arr[j + 1]:
                arr[j], arr[j + 1] = arr[j + 1], arr[j]

# 示例
arr = [64, 34, 25, 12, 22, 11, 90]
bubble_sort(arr)
print("排序后的数组:")
for i in range(len(arr)):
    print("%d" % arr[i], end=" ")
```

这段代码实现了冒泡排序算法。`bubble_sort`函数接受一个列表作为参数，对列表进行升序排序。你可以通过修改示例中的数组`arr`来测试不同的输入。

        """

        shared2.on_message.emit(tmpStr)


class Customcls():
    def __init__(self):
        # super(MainWindow, self).__init__()
        # # self.channel=None

        channel = QWebChannel()
        shared = Myshared()
        self.channel = channel
        self.shared = shared
    def getchannel(self):
        channel = QWebChannel()
        return channel

    def getshared(self):
        shared = Myshared()
        return shared


def setupit():
   global channellist
   channellist = []
   global sharedlist
   sharedlist = []
   channel = QWebChannel()
   shared = Myshared()
   channellist.append(channel)
   sharedlist.append(shared)

   channel2 = QWebChannel()
   shared2 = Myshared2()
   channellist.append(channel2)
   sharedlist.append(shared2)


   tchannel=channellist[0]
   tshared = sharedlist[0]

   tchannel.registerObject("con", tshared)


   win.browser.page().setWebChannel(tchannel)

   # global channel2
   # global shared2
   # channel2 = QWebChannel()
   # shared2 = Myshared()
   # channel2.registerObject("con", shared2)

   tchannel2 = channellist[1]
   tshared2 = sharedlist[1]
   tchannel2.registerObject("con", tshared2)
   win.browser2.page().setWebChannel(tchannel2)

   # channel=customcls.getchannel()
   # shared=customcls.getshared()

   # customcls2=copy.deepcopy(customcls)


    # channel=customcls2.channel
    # shared=customcls2.shared


if __name__ == '__main__':
    app = QApplication(sys.argv)
    win = MainWindow()
    customcls=Customcls()

    # 加载外部网页
    url = QUrl(QFileInfo("./index3.html").absoluteFilePath())

    file_path = os.path.join(Path(__file__).resolve().parent, "index3.html")
    print(file_path)
    url_string = QUrl.fromLocalFile(file_path)


    print(url)
    # win.browser.page().load(url)

    print(url_string)
    win.browser.page().load(url_string)
    win.browser2.page().load(url_string)
    # channela = win.channel
    # shareda = win.shared

    # channel = QWebChannel()
    # shared = Myshared()
    # win.channel=channel
    # channel.registerObject("con", shared)
    #
    # win.browser.page().setWebChannel(channel)
    setupit()

    # channel2 = QWebChannel()
    # shared2 = Myshared()
    # win.channel2=channel2
    # channel2.registerObject("con", shared2)
    #
    # win.browser2.page().setWebChannel(channel2)




    win.show()
    sys.exit(app.exec_())
