from PySide2.QtWidgets import *
from PySide2.QtCore import *
from PySide2.QtGui import *


from .abstractquerywidget import AbstractQueryWidget 
from cutevariant.core import Query
from cutevariant.core.model import Field



class FilterQueryModel(QStandardItemModel):

    FieldRole = Qt.UserRole + 1
    OperatorRole = Qt.UserRole + 2 
    ValueRole = Qt.UserRole + 3 
    TypeRole = Qt.UserRole + 4

    def __init__(self):
            super().__init__()
            self.query = None


    def setQuery(self, query: Query):
        self.query = query
        self.clear()
        self.appendRow(self.toItem(self.query.filter))

    def getQuery(self) -> Query:
        self.query.filter = self.fromItem(self.item(0))
        return self.query


    def toItem(self, data : dict ) -> QStandardItem:
        if len(data) == 1: # je ne sais pas comment on fait en python pour vérifier le type d'une variable
            operator = list(data.keys())[0]
            item = QStandardItem(operator)
            item.setData("logic", FilterQueryModel.TypeRole)
            item.setEditable(False)
            for k in data[operator]:
                item.appendRow(self.toItem(k))
            return item
        else:
            item = QStandardItem(str(data["field"]) + str(data["operator"]) + str(data["value"]))
            item.setData("field", FilterQueryModel.TypeRole)
            item.setData(data["field"], FilterQueryModel.FieldRole)
            item.setData(data["operator"], FilterQueryModel.OperatorRole)
            item.setData(data["value"], FilterQueryModel.ValueRole)
            item.setEditable(False)
            return item


    def fromItem(self, item : QStandardItem) -> dict:
        if item.data(FilterQueryModel.TypeRole) == "logic":
            op = item.text()
            data = {op : []}

            for i in range(item.rowCount()):
                data[op].append(self.fromItem(item.child(i)))
            return data 

        else:
            data = {}
            data["field"] = item.data(FilterQueryModel.FieldRole)
            data["operator"] = item.data(FilterQueryModel.OperatorRole)
            data["value"] = item.data(FilterQueryModel.ValueRole)
            return data


class FilterEditDialog(QDialog):
    def __init__(self, item: QStandardItem):
        super().__init__()
        self.field = QLineEdit()
        self.operator = QLineEdit()
        self.value = QLineEdit()
        self.item = item

        form_layout = QFormLayout()

        form_layout.addRow("field", self.field)
        form_layout.addRow("operator", self.operator)
        form_layout.addRow("value", self.value)

        layout = QVBoxLayout()
        buttonBox = QDialogButtonBox(QDialogButtonBox.Save|QDialogButtonBox.Cancel)
        buttonBox.accepted.connect(self.save)
        buttonBox.rejected.connect(self.close)

        layout.addLayout(form_layout)
        layout.addWidget(buttonBox)
        self.setLayout(layout)

        self.load()

    def load(self):
        self.field.setText(self.item.data(FilterQueryModel.FieldRole))
        self.operator.setText(self.item.data(FilterQueryModel.OperatorRole))
        self.value.setText(self.item.data(FilterQueryModel.ValueRole))

    def save(self):
        self.item.setText(self.field.text() + self.operator.text() + self.value.text())
        self.item.setData("field", FilterQueryModel.TypeRole)
        self.item.setData(self.field.text(),FilterQueryModel.FieldRole)
        self.item.setData(self.operator.text(), FilterQueryModel.OperatorRole)
        self.item.setData(self.value.text(), FilterQueryModel.ValueRole)
        



class FilterQueryWidget(AbstractQueryWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Filter")
        self.view = QTreeView()
        self.model = FilterQueryModel()
        self.view.setModel(self.model)

        layout = QVBoxLayout()
        layout.addWidget(self.view)
        self.setLayout(layout)

        self.model.itemChanged.connect(self.changed)
        self.view.doubleClicked.connect(self.edit)





    def setQuery(self, query: Query):
        self.model.setQuery(query)


    def getQuery(self) -> Query:
        return self.model.getQuery() 

    def edit(self, index):
        dialog = FilterEditDialog(self.model.itemFromIndex(index))
        
        if dialog.exec_():
            dialog.save()
