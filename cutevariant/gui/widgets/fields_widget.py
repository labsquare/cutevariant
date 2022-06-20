from PySide6.QtWidgets import *
from PySide6.QtCore import *
from PySide6.QtGui import *

import typing
import sqlite3

import json

from cutevariant.core import sql
from cutevariant.gui import FIcon, style
from cutevariant import constants as cst


class FieldsModel(QAbstractListModel):

    fields_changed = Signal(list)

    def __init__(self, conn: sqlite3.Connection = None, parent=None):
        super().__init__()
        self.conn = conn
        self._items = []
        self.samples = []
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

        if role == Qt.UserRole + 1:
            return (self._items[index.row()]["name"], self._items[index.row()]["type"])

        if role == Qt.UserRole + 2:
            return self._items[index.row()]["field_name"]

        if role == Qt.CheckStateRole:
            return int(Qt.Checked if self._items[index.row()]["checked"] else Qt.Unchecked)

        if role == Qt.DecorationRole:
            data_type = self._items[index.row()].get("type", "str")
            s = cst.FIELD_TYPE.get(
                data_type, cst.FIELD_TYPE.get("str", {"icon": 0xF000E, "color": "red"})
            )
            color = QApplication.style().colors().get(s["color"], "black")
            return QIcon(FIcon(s.get("icon"), color))

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
            if field["category"] != "samples":
                self._items.append(self._create_item(field))

        for sample in self.samples:
            for field in sql.get_field_by_category(self.conn, "samples"):
                self._items.append(self._create_item(field, sample))

        self.endResetModel()

    def flags(self, index: QModelIndex) -> Qt.ItemFlags:
        if index.isValid():
            return (
                Qt.ItemIsEnabled
                | Qt.ItemIsUserCheckable
                | Qt.ItemIsSelectable
                | Qt.ItemIsDragEnabled
            )

        return Qt.NoItemFlags

    def _create_item(self, field: dict, sample: str = None) -> dict:

        new_item = field
        new_item["description"] = field["description"] or "No description"
        new_item["checked"] = False
        new_item["tooltip"] = self._create_tooltip(field)
        new_item["search"] = "{name} {description}".format(**field)

        if field["category"] == "annotations":
            new_item["field_name"] = "ann.{name}".format(**field)

        elif field["category"] == "samples":
            name = field["name"]
            new_item["field_name"] = f"samples.{sample}.{name}"
            new_item["name"] = f"{sample}.{name}"

        else:
            new_item["field_name"] = field["name"]

        return new_item

    def _create_tooltip(self, field: dict) -> str:
        """Create rich text tooltip from a field"""
        return "<b>{name}</b> ({type}) <br/>table:{category} <hr/>{description}".format(**field)

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

    def mimeData(self, indexes: typing.List[QModelIndex]) -> QMimeData:
        fields = [idx.data(Qt.UserRole + 1) for idx in indexes]
        self._mime_data = QMimeData("cutevariant/typed-json")
        self._mime_data.setData(
            "cutevariant/typed-json",
            bytes(json.dumps({"type": "fields", "fields": fields}), "utf-8"),
        )
        return self._mime_data

    def mimeTypes(self) -> typing.List[str]:
        return ["cutevariant/typed-json"]


class FieldsWidget(QWidget):

    fields_changed = Signal(list)

    def __init__(self, conn: sqlite3.Connection = None, parent=None):
        super().__init__()
        self.view = QListView()
        self.view.setIconSize(QSize(24, 24))
        self.view.setDragEnabled(True)
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

    def set_samples(self, samples: typing.List[str]):
        self._model.samples = samples

    def get_samples(self) -> typing.List[str]:
        return self._model.samples

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
    w.set_samples(["sacha"])
    w.load()

    w.set_fields(["chr", "pos"])

    w.show()

    app.exec()
