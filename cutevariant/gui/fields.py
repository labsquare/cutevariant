from PySide2.QtWidgets import * 
from PySide2.QtCore import * 
from PySide2.QtGui import * 
import sys
from cutevariant.gui import style
# Some fields editors 

from cutevariant.core import sql, get_sql_connexion

class BaseField(QWidget):
    """Base class for Field widget """
    def __init__(self, parent = None):
        super().__init__(parent)

    def set_value(self, value):
        raise NotImplemented()

    def get_value(self):
        raise NotImplemented()



class IntegerField(BaseField):
    """Field with a slider and a spin box to edit integer value """
    def __init__(self, parent = None):
        super().__init__(parent)
        self.stack = QStackedWidget()        
        self.slider = QSlider(Qt.Horizontal)
        self.spin_box = QSpinBox()

        self.stack.addWidget(self.slider)
        self.stack.addWidget(self.spin_box)

        h_layout = QHBoxLayout()
        h_layout.addWidget(self.stack)
        self.setLayout(h_layout)

        self.slider.valueChanged.connect(self._show_tooltip)
        self.slider.setStyleSheet("QSlider::sub-page {background:'orange'}")

    def set_value(self, value: int):
        self.slider.setValue(value)

    def get_value(self) -> int:
        return self.slider.setValue(self.slider.value())

    def set_range(self, min_, max_):
        self.slider.setRange(min_,max_)

    def _show_tooltip(self, value):

        tip = QToolTip()
        pos = self.mapToGlobal(self.slider.pos() + QPoint(self.slider.width() / 2, 0))
        tip.showText(pos, str(value))

    def mouseDoubleClickEvent(self, event):
        self.stack.setCurrentIndex(not self.stack.currentIndex())



class FloatField(BaseField):
    """Field with a spin_box and a spin box to edit integer value """
    def __init__(self, parent = None):
        super().__init__(parent)
        self.spin_box = QDoubleSpinBox()
        h_layout = QHBoxLayout()
        h_layout.addWidget(self.spin_box)
        self.setLayout(h_layout)

        self.spin_box.valueChanged.connect(self._show_tooltip)

    def set_value(self, value: int):
        self.spin_box.setValue(value)

    def get_value(self) -> int:
        return self.spin_box.setValue(self.spin_box.value())

    def set_range(self, min_, max_):
        self.spin_box.setRange(min_,max_)

    def _show_tooltip(self, value):

        tip = QToolTip()
        pos = self.mapToGlobal(self.spin_box.pos() + QPoint(self.spin_box.width() / 2, 0))
        tip.showText(pos, str(value))


class FieldBuilder(QObject):

    def __init__(self, conn):
        self.conn = conn

    def create(self, sql_field):
        field = sql.get_field_by_name(self.conn, sql_field)
        print(field)
        if field["type"] == 'int':
            
            w = IntegerField()
            w.set_range(*sql.get_field_range(conn,sql_field))
            return w

        if field["type"] == 'float':
            w = FloatField()
            w.set_range(*sql.get_field_range(conn,sql_field))
            return w



        return QLineEdit()





class MyDelegate(QItemDelegate):
    def __init__(self, parent=None):
        super().__init__(parent)

    def createEditor(self, parent, option, index):
        if index.column() == 2:
            w = FieldBuilder(conn).create("pos")
            w.setParent(parent)
            return w


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

        



app = QApplication(sys.argv)
app.setStyle("fusion")

style.dark(app)

conn = get_sql_connexion("/home/schutz/Dev/cutevariant/examples/test.db")

model = QStandardItemModel()
model.appendRow([QStandardItem("sacha"),QStandardItem("sacha"),QStandardItem("")])
model.appendRow([QStandardItem("sacha"),QStandardItem("sacha"),QStandardItem("")])
model.appendRow([QStandardItem("sacha"),QStandardItem("sacha"),QStandardItem("")])


view = QTreeView()
view.setModel(model)
view.setItemDelegate(MyDelegate())


w = FieldBuilder(conn).create("pos")

view.show()

app.exec_()





