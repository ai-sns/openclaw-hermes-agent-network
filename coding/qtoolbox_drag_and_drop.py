# filename: qtoolbox_drag_and_drop.py
import sys
from PyQt5.QtWidgets import QApplication, QToolBox, QListWidget, QVBoxLayout, QWidget, QToolButton

class DraggableQToolBox(QToolBox):
    def __init__(self):
        super().__init__()
        self.setAcceptDrops(True)

    def dragEnterEvent(self, event):
        if event.mimeData().hasFormat("application/x-item"):
            event.accept()
    
    def dropEvent(self, event):
        source = event.source()
        if source and source is not self:
            item = source.currentItem()
            if item:
                self.addItem(item.clone(), item.text())
                source.takeItem(source.row(item))
                event.accept()

class MainWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("QToolBox Drag and Drop Example")
        
        self.toolbox = DraggableQToolBox()
        self.list_widget = QListWidget()
        self.list_widget.addItems(["Item 1", "Item 2", "Item 3"])
        
        layout = QVBoxLayout()
        layout.addWidget(self.list_widget)
        layout.addWidget(self.toolbox)
        self.setLayout(layout)

        self.list_widget.setDragEnabled(True)

    def startDrag(self, event):
        item = self.list_widget.currentItem()
        if item:
            drag = QDrag(self)
            mime_data = QMimeData()
            mime_data.setText(item.text())
            drag.setMimeData(mime_data)
            drag.exec_(Qt.MoveAction)

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())