from PySide6.QtWidgets import *
from PySide6.QtCore import *
from PySide6.QtGui import *

import typing
import sqlite3

from cutevariant.core import sql
from cutevariant.gui import FIcon, style


class FieldsModel(QAbstractListModel):

    fields_changed = Signal(list)

    def __init__(self, conn: sqlite3.Connection = None, parent=None):
        super().__init__()
        self.conn = conn
        self._items = []
        self.dataChanged.connect(self.on_item_changed)

    def rowCount(self, parent=QModelIndex()):
        if parent == QModelIndex():
            return len(self._items)
        return 0

    def data(self, index: QModelIndex, role: Qt.ItemDataRole) -> typing.Any:

        if not index.isValid():
            return

        if role == Qt.DisplayRole:
            return self._items[index.row()]["name"]

        if role == Qt.ToolTipRole:
            return self._items[index.row()]["tooltip"]

        if role == Qt.UserRole:
            return self._items[index.row()]["search"]

        if role == Qt.CheckStateRole:
            return int(Qt.Checked if self._items[index.row()]["checked"] else Qt.Unchecked)

        if role == Qt.DecorationRole:
            data_type = self._items[index.row()]["type"]
            s = style.FIELD_TYPE.get(data_type)
            return QIcon(FIcon(s["icon"], s["color"]))

    def setData(self, index: QModelIndex, value: typing.Any, role: Qt.ItemDataRole) -> bool:

        if role == Qt.CheckStateRole:
            self._items[index.row()]["checked"] = True if value == Qt.Checked else False

            self.dataChanged.emit(index, index)

            return True

        return False

    def on_item_changed(self):
        self.fields_changed.emit(self.get_fields())

    def clear(self):
        self.beginResetModel()
        self._items.clear()
        self.endResetModel()

    def load(self):

        self.beginResetModel()
        self._items.clear()
        for field in sql.get_fields(self.conn):
            # Do not keep samples fields
            if field["category"] != "samples":

                new_item = field

                field["description"] = field["description"] or "No description"

                new_item["checked"] = False
                new_item["tooltip"] = self._create_tooltip(field)
                new_item["field_name"] = self._create_field_name(field)
                new_item["search"] = "{name} {description}".format(**field)
                self._items.append(new_item)

        self.endResetModel()

    def flags(self, index: QModelIndex) -> Qt.ItemFlags:
        if index.isValid():
            return Qt.ItemIsEnabled | Qt.ItemIsUserCheckable | Qt.ItemIsSelectable

        return Qt.NoItemFlags

    def _create_tooltip(self, field: dict) -> str:
        """Create rich text tooltip from a field"""
        return "<b>{name}</b> ({type}) <br/>table:{category} <hr/>{description}".format(**field)

    def _create_field_name(self, field: dict) -> str:
        """Create VQL fields name"""

        if field["category"] == "annotations":
            return "ann.{name}".format(**field)

        return field["name"]

    def set_fields(self, fields: typing.List[str]):

        self.beginResetModel()
        self._sorted_fields = fields
        for item in self._items:
            item["checked"] = item["field_name"] in fields

        self.endResetModel()

    def get_fields(self) -> typing.List[str]:

        fields = []
        for item in self._items:
            if item["checked"]:
                fields.append(item["field_name"])

        new_fields = []
        for f in self._sorted_fields:
            if f in fields:
                new_fields.append(f)

        new_fields += list(set(fields) - set(self._sorted_fields))

        return new_fields


class FieldsWidget(QWidget):

    fields_changed = Signal(list)

    def __init__(self, conn: sqlite3.Connection = None, parent=None):
        super().__init__()
        self.view = QListView()
        self.view.setIconSize(QSize(24, 24))
        self._model = FieldsModel()
        self._model.fields_changed.connect(self.fields_changed)
        self.proxy_model = QSortFilterProxyModel()
        self.proxy_model.setSourceModel(self._model)
        self.proxy_model.setFilterRole(int(Qt.UserRole))

        self.search_edit = QLineEdit()
        self.search_edit.setPlaceholderText("Search for a field ...")
        self.search_edit.textChanged.connect(self.proxy_model.setFilterRegularExpression)

        self.view.setModel(self.proxy_model)

        vbox = QVBoxLayout(self)
        vbox.addWidget(self.search_edit)
        vbox.addWidget(self.view)
        vbox.setContentsMargins(0, 0, 0, 0)
        self._model.conn = conn

    def load(self):
        if self._model.conn:

            self._model.load()

    def set_fields(self, fields: list):
        self._model.set_fields(fields)

    def get_fields(self) -> list:
        return self._model.get_fields()

    def clear(self):
        self._model.clear()

    @property
    def conn(self):
        return self._model.conn

    @conn.setter
    def conn(self, value: sqlite3.Connection):
        self._model.conn = value

    def show_checked_only(self, active=False):
        self.proxy_model.setFilterRole(Qt.CheckStateRole)
        self.proxy_model.setFilterKeyColumn(0)
        # Checked = "2" / Unchecked = "0" / All : ""
        is_checked_str = "2" if active else ""
        self.proxy_model.setFilterFixedString(is_checked_str)
        count = self.proxy_model.rowCount()


if __name__ == "__main__":

    import sys
    from cutevariant.core import sql

    conn = sql.get_sql_connection("/home/sacha/exome.db")

    app = QApplication(sys.argv)

    w = FieldsWidget(conn)
    w.load()

    w.set_fields(["chr", "pos"])

    w.show()

    app.exec()