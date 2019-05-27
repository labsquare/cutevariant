from PySide2.QtWidgets import * 
from PySide2.QtCore import * 
from PySide2.QtGui import * 
import sys
from cutevariant.gui import style
# Some fields editors 


class MySlider(QSlider):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setOrientation(Qt.Horizontal)
        self.setStyleSheet("QSlider::sub-page {background:'orange'}")
        self.setMaximumWidth(100)
        self.sliderMoved.connect(self.slot_show_tooltip)

    def slot_show_tooltip(self, value):
        pos = QPoint(value , self.parent().pos().y())
        QToolTip.showText(self.mapToGlobal(pos), str(self.value()), self)


class MyDelegate(QItemDelegate):
    def __init__(self, parent=None):
        super().__init__(parent)

    def createEditor(self, parent, option, index):
        if index.column() == 2:
            box = MySlider(parent)
            return box

        if index.column() == 1:
            box = QLineEdit(parent)
            self.m = QStringListModel()
            self.m.setStringList(["sacha","olivier"])
            c = QCompleter(self.m)
            c.setCompletionMode(QCompleter.InlineCompletion)
            box.setCompleter(c)

            return box

        return super().createEditor(parent,option,index)

    def sizeHint(self,option,index):
        return QSize(40, 40)

        


model = QStandardItemModel()
model.setColumnCount(3)
root = QStandardItem("root")

root.appendRow([QStandardItem("salut"),QStandardItem(">"), QStandardItem("")])
root.appendRow([QStandardItem("salut"),QStandardItem(">"), QStandardItem("")])
root.appendRow([QStandardItem("salut"),QStandardItem(">"), QStandardItem("")])
root.appendRow([QStandardItem("salut"),QStandardItem(">"), QStandardItem("")])
root.appendRow([QStandardItem("salut"),QStandardItem(">"), QStandardItem("")])
root.appendRow([QStandardItem("salut"),QStandardItem(">"), QStandardItem("")])
root.appendRow([QStandardItem("salut"),QStandardItem(">"), QStandardItem("")])

model.appendRow(root)
app = QApplication(sys.argv)

app.setStyle("fusion")

style.dark(app)


view = QTreeView()
view.setModel(model)
view.setEditTriggers(QAbstractItemView.AllEditTriggers)
view.setItemDelegate(MyDelegate())
view.show()



app.exec_()





