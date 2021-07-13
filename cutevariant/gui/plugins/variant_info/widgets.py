"""Plugin to show all characteristics of a selected variant

VariantInfoWidget is showed on the GUI, it uses VariantPopupMenu to display a
contextual menu about the variant which is selected.
VariantPopupMenu is also used in viewquerywidget for the same purpose.
"""
import collections
from logging import DEBUG
import sqlite3

import typing
import copy

# Qt imports
from PySide2.QtCore import (
    QAbstractItemModel,
    QAbstractTableModel,
    QItemSelection,
    QModelIndex,
    QObject,
    QSortFilterProxyModel,
    QStringListModel,
    Qt,
    Slot,
    QSize,
)
from PySide2.QtWidgets import *
from PySide2.QtGui import QFont, QColor

# Custom imports
from cutevariant.gui import FIcon, style
from cutevariant.core import sql, get_sql_connection
from cutevariant.gui.plugin import PluginWidget
from cutevariant import commons as cm

from cutevariant.gui.widgets import DictWidget


from cutevariant.gui.widgets.qjsonmodel import QJsonModel, QJsonTreeItem

LOGGER = cm.logger()


# class VariantInfoModel(QJsonModel):
#     def data(self, index: QModelIndex, role: Qt.ItemDataRole):

#         item: QJsonTreeItem = index.internalPointer()
#         value = item.value

#         if role == Qt.ForegroundRole and index.column() == 1:

#             if value == "":
#                 return Qt.gray

#             value_type = type(value).__name__
#             if value_type in style.FIELD_TYPE:
#                 col = QColor(style.FIELD_TYPE[value_type]["color"])
#                 return col

#         if role == Qt.SizeHintRole:
#             return QSize(30, 30)

#         if role == Qt.DisplayRole and index.column() == 1:
#             if value == "":
#                 return item.childCount()

#         # TODO: make it smarter...
#         if role == Qt.UserRole:

#             # Returns a list indicating the path of this item in the variant dictionnary
#             path = [item.key]
#             while item.parent():
#                 path.insert(0, item.parent().key)
#                 item = item.parent()

#             # Remove root item
#             return path[1:]

#         return super().data(index, role)

#     def flags(self, index):
#         return Qt.ItemIsEnabled | Qt.ItemIsSelectable


class WatchModel(QAbstractTableModel):
    def __init__(self, parent: QObject) -> None:
        super().__init__(parent=parent)
        self._data = []
        self._watched_fields: typing.List[str] = ["chr", "pos"]
        self._headers = [self.tr("Field name"), self.tr("Field value")]

    def data(self, index=QModelIndex(), role=Qt.DisplayRole) -> typing.Any:
        """override from QAbstractTableModel"""

        if not index.isValid():
            return

        if role == Qt.DisplayRole:
            return self._data[index.row()][index.column()]

        if role == Qt.UserRole:
            return self._data[index.row()][2]

        return

    def headerData(
        self, section: int, orientation: Qt.Orientation, role: int
    ) -> typing.Any:
        """override from QAbstractTableModel"""

        if orientation == Qt.Horizontal and role == Qt.DisplayRole:
            return self._headers[section]

    def rowCount(self, parent: QModelIndex = QModelIndex()) -> int:
        """override from QAbstractTableModel"""
        return len(self._data)

    def columnCount(self, parent: QModelIndex = QModelIndex()) -> int:
        """override from QAbstractTableModel"""

        if parent == QModelIndex():
            return 2
        return 0

    def add_to_watch(self, field_name: str):
        """Adds a field to the watch

        Args:
            field_name (str): Name of the field to watch
        """
        if field_name not in self._watched_fields:
            self._watched_fields.append(field_name)

    def remove_from_watch(self, indexes: typing.List[QModelIndex]):
        """Remove fields from selected indexes"""

        ordered_indexes = indexes  # TODO order by row()
        for index in indexes:
            _, value, raw_field = self._data[index.row()]
            self._watched_fields.remove(raw_field)

    def _flatten_variant(self, variant: dict):
        result = []
        annotations: list = variant["annotations"]
        for i, annotation in enumerate(annotations):
            for ann, val in annotation.items():
                if ann != "variant_id":
                    result.append(([f"ann[{i}].{ann}"], val, f"ann.{ann}"))
        samples: list = variant["samples"]
        for sample in samples:
            name = sample["name"]
            for field, val in sample.items():
                if field not in ("name", "sample_id", "variant_id"):
                    result.append(
                        (f"samples.{name}.{field}", val, f"samples.{name}.{field}")
                    )
        return result

    def load(self, variant: dict = None):
        """Updates the model with the currently selected variant
        Computes the whole internal dict structure again

        Args:
            variant (dict): Full variant dict. Should contain all watched fields
        """
        # Cached dict is useful when rebuilding the model after adding/removing a watched field
        self.beginResetModel()
        self._data.clear()
        self._data = self._flatten_variant(variant)
        self.endResetModel()

    def clear(self):
        """Clear the model.
        This means clearing the data array,
        every watched field, as well as the cached dict
        """
        self.beginResetModel()
        self._data.clear()
        self._watched_fields.clear()
        self.endResetModel()


class VariantInfoWidget(PluginWidget):
    """Plugin to show all annotations of a selected variant"""

    ENABLE = True
    REFRESH_STATE_DATA = {"current_variant"}

    def __init__(self, parent=None):
        super().__init__(parent)

        self.setWindowIcon(FIcon(0xF0B73))
        # Current variant => set by on_refresh and on_open_project
        self.current_variant = None

        self.watch_model = WatchModel(self)
        self.watch_view = QTableView(self)

        self.watch_view.setModel(self.watch_model)
        self.watch_view.setContextMenuPolicy(Qt.ActionsContextMenu)

        # Make it look nice
        self.watch_view.horizontalHeader().setStretchLastSection(True)
        self.watch_view.verticalHeader().hide()
        self.watch_view.setAlternatingRowColors(True)
        self.watch_view.setShowGrid(False)
        self.watch_view.setSelectionBehavior(QAbstractItemView.SelectRows)

        vlayout = QVBoxLayout(self)
        vlayout.setContentsMargins(0, 0, 0, 0)

        self.toolbar = QToolBar("", self)
        self.toolbar.setIconSize(QSize(20, 20))

        self.searchbar = QLineEdit(self)
        self.searchbar.setPlaceholderText("Add a new field to watch ...")
        self.completer = QCompleter()

        self.searchbar.setCompleter(self.completer)
        self.searchbar.addAction(FIcon(0xF0419), QLineEdit.TrailingPosition)

        # self.searchbar.textChanged.connect(self.filter_model.setFilterRegExp)
        # self.searchbar.textChanged.connect(self.watch_filter_model.setFilterRegExp)

        vlayout.addWidget(self.toolbar)
        vlayout.addWidget(self.searchbar)
        vlayout.addWidget(self.watch_view)

        self.create_actions()

        # When the current index in the main view changes, we must update its 'add to watch' action
        # self.view.selectionModel().currentChanged.connect(self._update_watchable_field)

    def create_actions(self):

        actions = []
        self.add_to_watch_action = QAction(self.tr("Add to watch"), self)
        self.add_to_watch_action.setIcon(FIcon(0xF04FE))
        self.add_to_watch_action.triggered.connect(self._on_add_to_watch)
        actions.append(self.add_to_watch_action)

        self.remove_from_watch_action = QAction(self.tr("Remove from watch"))
        self.remove_from_watch_action.setIcon(FIcon(0xF0374))
        self.remove_from_watch_action.triggered.connect(self._on_remove_from_watch)
        actions.append(self.remove_from_watch_action)

        self.clear_watch_action = QAction(self.tr("Clear watched fields"))
        self.clear_watch_action.setIcon(FIcon(0xF0A7A))
        self.clear_watch_action.triggered.connect(self._on_clear_watch)
        actions.append(self.add_to_watch_action)

        # Load actions into toolbar and watch view
        for action in actions:
            self.toolbar.addAction(action)
            self.watch_view.addAction(action)

    def _on_remove_from_watch(self):
        """Called when the user triggers the 'remove from watch' action.
        Beware, it only applies to the watch view. If you've selected a field inside the main view, you
        may have some surprises
        """

        selected_indexes = self.watch_view.selectionModel().selectedRows()
        self.watch_model.remove_from_watch(selected_indexes)

    def _on_add_to_watch(self):

        # TODO ...
        action: QAction = self.sender()
        if isinstance(action.data(), str):
            field_name = action.data()
            if field_name:
                self.watch_model.add_to_watch(field_name)

    def _on_clear_watch(self):
        self.watch_model.clear()

    # def _update_watchable_field(self, index: QModelIndex):
    #     """When current index in the main view changes, add the field to watch to its respective action.
    #     This function also takes care of enabling/disabling the action everytime the current item changes

    #     Args:
    #         index (QModelIndex): Main view's current index
    #     """
    #     watched_field = None
    #     if index and index.isValid():
    #         path = index.data(Qt.UserRole)

    #         # Simple: if the field is in the variant table, path is only one key
    #         if len(path) == 1:
    #             if path[0] not in ("annotations", "samples"):
    #                 watched_field = path[0]
    #             else:
    #                 # path is only one element, but is a category. So we cannot add to watch
    #                 pass
    #         # If the path starts with annotations
    #         if len(path) == 3:
    #             category = path[0]
    #             if category == "annotations":
    #                 watched_field = f"ann.{path[2]}"

    #             if category == "samples":
    #                 _, sample_idx, field = path
    #                 sample_name = self.full_variant["samples"][int(sample_idx)]["name"]
    #                 watched_field = f"samples.{sample_name}.{field}"

    #     self.add_to_watch_action.setData(watched_field)
    #     self.add_to_watch_action.setEnabled(bool(watched_field))
    #     self.remove_from_watch_action.setData(watched_field)
    #     self.remove_from_watch_action.setEnabled(bool(watched_field))

    def on_open_project(self, conn):
        self.conn = conn

    def on_refresh(self):
        """Set the current variant by the variant displayed in the GUI"""
        self.current_variant = self.mainwindow.get_state_data("current_variant")

        self.full_variant = sql.get_one_variant(
            self.conn, self.current_variant["id"], True, True
        )

        self.watch_model.load(self.full_variant)

        self.completer.setModel(
            QStringListModel([i[2] for i in self.watch_model._data])
        )

        # # Remove variant_id and sample_id from watchable fields... These should not be accessible to the user, they are cutevariant internals
        # self.full_variant["annotations"] = [
        #     {k: v for k, v in annotation.items() if k != "variant_id"}
        #     for annotation in self.full_variant["annotations"]
        # ]
        # self.full_variant["samples"] = [
        #     {k: v for k, v in sample.items() if k not in ("variant_id", "sample_id")}
        #     for sample in self.full_variant["samples"]
        # ]
        # self.model.load(self.full_variant)
        # self.watch_model.load(self.full_variant)


if __name__ == "__main__":
    import sys

    app = QApplication(sys.argv)

    conn = get_sql_connection("/home/schutz/Dev/cutevariant/examples/test.db")

    w = VariantInfoWidget()
    w.conn = conn

    variant = sql.get_one_variant(conn, 1)

    w.current_variant = variant

    w.show()

    app.exec_()
