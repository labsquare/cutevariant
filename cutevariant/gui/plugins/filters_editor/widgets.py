# Standard imports
import re
from cutevariant.gui.mainwindow import MainWindow
from cutevariant.config import Config
from logging import Filter
import sys
import json
import os
import pickle
import typing
import uuid
from ast import literal_eval
from functools import lru_cache
from typing import Any, Iterable, Text
import sqlite3
import glob

# Qt imports
from PySide6.QtWidgets import (
    QInputDialog,
    QWidget,
    QTreeView,
    QFrame,
    QToolButton,
    QPushButton,
    QCompleter,
    QStackedWidget,
    QDialog,
    QLineEdit,
    QFileDialog,
    QApplication,
    QStyledItemDelegate,
    QToolBar,
    QAbstractItemView,
    QHeaderView,
    QComboBox,
    QSizePolicy,
    QMessageBox,
    QHBoxLayout,
    QVBoxLayout,
    QMenu,
    QStyle,
    QAbstractItemDelegate,
)
from PySide6.QtCore import (
    QAbstractListModel,
    QUrl,
    Qt,
    QObject,
    Signal,
    Slot,
    QDir,
    QAbstractItemModel,
    QModelIndex,
    QMimeData,
    QEvent,
    QStandardPaths,
    QStringListModel,
    QSize,
    QByteArray,
    QFileInfo,
    QSettings,
    QRect,
    QLocale,
    QPoint,
)
from PySide6.QtGui import (
    QMouseEvent,
    QPainter,
    QPalette,
    QFont,
    QPen,
    QBrush,
    QIcon,
    QIntValidator,
    QDoubleValidator,
    QActionGroup,
    QAction,
    QKeySequence,
    QContextMenuEvent,
    QStandardItemModel,
    QColor,
)

# Custom imports
from cutevariant.gui import style, plugin, FIcon
from cutevariant.core import sql, get_sql_connection
from cutevariant.core.vql import parse_one_vql
from cutevariant.core.querybuilder import (
    build_vql_query,
    fields_to_vql,
)
import cutevariant.constants as cst
from cutevariant.gui.sql_thread import SqlThread
from cutevariant.gui.widgets import FiltersWidget, FilterItem, PresetAction

from cutevariant import LOGGER

# TYPE_OPERATORS = {
#     "str": ["$eq", "$ne", "$in", "$nin", "$regex", "$has"],
#     "float": ["$eq", "$ne", "$gte", "$gt", "$lt", "$lte"],
#     "int": ["$eq", "$ne", "$gte", "$gt", "$lt", "$lte"],
#     "bool": ["$eq"],
# }

from cutevariant.core.querybuilder import PY_TO_VQL_OPERATORS


class FiltersPresetModel(QAbstractListModel):
    def __init__(self, config_path=None, parent: QObject = None) -> None:
        super().__init__(parent=parent)
        self.config_path = config_path
        self._presets = []

    def data(self, index: QModelIndex, role: int) -> typing.Any:
        if role == Qt.DisplayRole or role == Qt.EditRole:
            if index.row() >= 0 and index.row() < self.rowCount():
                return self._presets[index.row()][0]
        if role == Qt.UserRole:
            if index.row() >= 0 and index.row() < self.rowCount():
                return self._presets[index.row()][1]

        return

    def setData(self, index: QModelIndex, value: str, role: int) -> bool:
        """Renames the preset
        The content is read-only from the model's point of view

        Args:
            index (QModelIndex): [description]
            value (str): [description]
            role (int): [description]

        Returns:
            bool: True on success
        """
        if role == Qt.EditRole:
            self._presets[index.row()] = (value, self._presets[index.row()][1])
            return True
        else:
            return False

    def flags(self, index: QModelIndex) -> Qt.ItemFlags:
        if not index.isValid():
            return Qt.NoItemFlags
        return super().flags(index) | Qt.ItemIsEditable

    def rowCount(self, parent: QModelIndex = QModelIndex()) -> int:
        return len(self._presets)

    def add_preset(self, name: str, filter: dict):
        """Add filter preset

        Args:
            name (str): preset name
            filter (dict): one filter dict
        """
        self.beginInsertRows(QModelIndex(), 0, 0)
        self._presets.insert(0, (name, filter))
        self.endInsertRows()

    def rem_presets(self, indexes: typing.List[int]):
        indexes.sort(reverse=True)
        self.beginResetModel()
        for idx in indexes:
            del self._presets[idx]
        self.endResetModel()

    def load(self):
        self.beginResetModel()
        config = Config("filters_editor")
        presets = config.get("presets", {})
        self._presets = [(preset_name, filters) for preset_name, filters in presets.items()]
        self.endResetModel()

    def save(self):
        config = Config("filters_editor", self.config_path)
        # config["presets"] = {
        #     preset_name: filters for preset_name, filters in self._presets
        # }
        if "presets" not in config:
            config["presets"] = {}
        for preset_name, filters in self._presets:
            config["presets"][preset_name] = filters
        config.save()

    def clear(self):
        self.beginResetModel()
        self._presets.clear()
        self.endResetModel()

    def preset_names(self):
        return [p[0] for p in self._presets]


class PresetButton(QToolButton):
    """A toolbutton that works with a drop down menu filled with a model"""

    preset_clicked = Signal(QAction)

    def __init__(self, parent: QWidget = None) -> None:
        super().__init__(parent=parent)
        self._menu = QMenu(self.tr("Presets"), self)
        self._menu.triggered.connect(self.preset_clicked)
        self.setPopupMode(QToolButton.InstantPopup)
        self._model: QAbstractItemModel = None
        self.setMenu(self._menu)
        self.setText(self.tr("Presets"))

    def set_model(self, model: QAbstractItemModel):
        self._model = model

    def mousePressEvent(self, e: QMouseEvent) -> None:
        if self._model:
            self._menu.clear()
            for i in range(self._model.rowCount()):
                index = self._model.index(i, 0)
                preset_name = index.data(Qt.DisplayRole)
                fields = index.data(Qt.UserRole)
                act: QAction = self._menu.addAction(preset_name)
                act.setData(fields)
        return super().mousePressEvent(e)


class FiltersEditorWidget(plugin.PluginWidget):
    """Displayed widget plugin to allow creation/edition/deletion of filters"""

    ENABLE = True
    REFRESH_STATE_DATA = {"filters"}
    changed = Signal()

    def __init__(self, conn=None, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Filters")
        self.setWindowIcon(FIcon(0xF0232))

        self.settings = QSettings()
        self.view = FiltersWidget()
        self.model = self.view.model()
        self.view.selectionModel().selectionChanged.connect(self.on_selection_changed)
        self.view.setToolTip(
            self.tr(
                "Filter conditions creation: Add, remove, hide, group, drag and drop filter conditions to filter variants"
            )
        )

        # Create toolbar
        self.toolbar = QToolBar()
        self.toolbar.setIconSize(QSize(16, 16))
        self.toolbar.setToolButtonStyle(Qt.ToolButtonIconOnly)

        self._setup_actions()

        # Save button
        # self.save_action = self.toolbar.addAction(self.tr("Save Preset"))
        # self.save_action.setIcon(FIcon(0xF0818))
        # self.save_action.triggered.connect(self.on_save_preset)
        # self.save_action.setToolTip(self.tr("Save as a new Preset"))

        # Presets model
        self.presets_model = FiltersPresetModel(parent=self)
        self.load_presets()

        # self.presets_button = PresetButton(self)
        # self.presets_button.set_model(self.presets_model)
        # self.presets_button.preset_clicked.connect(self.on_select_preset)

        # self.toolbar.addWidget(self.presets_button)

        # Presets toolbutton (with dropdown menu)

        # apply_action = self.toolbar.addAction("Apply")
        # self.apply_button = self.toolbar.widgetForAction(apply_action)
        # self.apply_button.setText("Apply")
        # self.apply_button.setIcon(FIcon(0xF0E1E, "white"))
        # self.apply_button.setStyleSheet("background-color: #038F6A; color:white")
        # self.apply_button.setAutoRaise(False)
        # self.apply_button.setToolButtonStyle(Qt.ToolButtonTextBesideIcon)
        # self.apply_button.triggered.connect(self.on_apply)
        main_layout = QVBoxLayout()

        main_layout.addWidget(self.toolbar)
        main_layout.addWidget(self.view)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(1)
        self.setLayout(main_layout)

        self.current_preset_name = ""

    def _setup_actions(self):
        apply_action = self.toolbar.addAction(FIcon(0xF040A), "Apply filters", self.on_apply)
        apply_action.setToolTip(
            self.tr("Apply Filters<hr>Apply defined filter conditions to variants")
        )

        auto_icon = QIcon()
        auto_icon.addPixmap(FIcon(0xF04E6).pixmap(16, 16), QIcon.Normal, QIcon.On)
        auto_icon.addPixmap(FIcon(0xF04E8).pixmap(16, 16), QIcon.Normal, QIcon.Off)
        self.auto_action = self.toolbar.addAction(
            auto_icon, "Automatic Apply selection when checked"
        )
        self.auto_action.setToolTip(
            self.tr("Auto Apply<hr>Enable/Disable Auto Apply when filter conditions are defined")
        )

        self.auto_action.setCheckable(True)
        self.auto_action.toggled.connect(apply_action.setDisabled)

        self.toolbar.addSeparator()

        self.add_condition_action = self.toolbar.addAction(
            FIcon(0xF0EF1), "Add condition", self.on_add_condition
        )
        self.add_condition_action.setToolTip(
            self.tr(
                "Add filter condition<hr>Add a filter condition to filter variants on a field, with an operator and a value"
            )
        )

        self.add_group_action = self.toolbar.addAction(
            FIcon(0xF0EF0), "Add group", self.on_add_logic
        )
        self.add_group_action.setToolTip(
            self.tr(
                "Add filter condition group<hr>Add a group of filter conditions, with operator AND or OR"
            )
        )

        self.clear_all_action = self.toolbar.addAction(
            FIcon(0xF0234), self.tr("Clear all"), self.on_clear_all
        )
        self.clear_all_action.setToolTip(
            self.tr(
                "Clear all filter conditions<hr>Remove all filter conditions and group of filter conditions.<br>No filter conditions will be applied"
            )
        )

        spacer = QWidget()
        spacer.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.toolbar.addWidget(spacer)

        # preset_action = self.toolbar.addAction(FIcon(0xF1268), self.tr("Presets"))

        self.preset_menu = QMenu()
        self.preset_button = QPushButton()
        # self.preset_button.setToolTip(self.tr("Presets"))
        self.preset_button.setToolTip(
            self.tr(
                "Presets<hr>- Load a existing preset<br>- Save the current preset<br>- Delete an existing preset<br>- Reload configured presets"
            )
        )
        self.preset_button.setIcon(FIcon(0xF035C))
        self.preset_button.setMenu(self.preset_menu)
        self.preset_button.setFlat(True)

        self.toolbar.addWidget(self.preset_button)

        # preset_action.setMenu(self.preset_menu)
        # preset_action.setToolTip(self.tr("A list a predefined fields selections"))
        # self.toolbar.widgetForAction(preset_action).setPopupMode(
        #     QToolButton.InstantPopup
        # )

        # Create preset combobox with actions

        self.view.model().filtersChanged.connect(self.on_filter_changed)

    @property
    def filters(self):
        return self.view.get_filters()

    @filters.setter
    def filters(self, filters):
        self.view.set_filters(filters)
        self.view.expandAll()

    def on_filter_changed(self):

        if self.auto_action.isChecked():
            self.on_apply()

    def on_open_project(self, conn):
        """Overrided from PluginWidget"""
        self.model.conn = conn
        self.conn = conn

        # Clear lru_cache
        self.view.clear_cache()
        self.on_refresh()

    def on_close_project(self):
        self.model.clear()

    def on_duplicate_filter(self):
        """Duplicate filter condition from context menu

        See contextMenu()
        """
        item_index = self.view.selectionModel().currentIndex()
        parent_index = item_index.parent()
        if not parent_index:
            return

        data = self.model.item(item_index).data
        self.model.add_condition_item(data, parent_index)

    def on_remove_filter(self):
        selected_index = self.view.selectionModel().currentIndex()
        if not selected_index:
            return

        # Safety, to avoid removing root item
        if not selected_index.parent().isValid():
            return

        confirmation = QMessageBox.question(
            self,
            self.tr("Please confirm"),
            self.tr(
                f"Do you really want to remove selected filter ? \nYou cannot undo this operation"
            ),
        )
        if confirmation == QMessageBox.Yes:
            self.model.remove_item(selected_index)

        # # The user deleted the preset that was selected last. So make it clear to the user that the preset doesn't exist anymore
        # if self.presets_button.text() not in action_names:
        #     self.presets_button.setText(self.tr("Select preset"))

        # self.presets_menu.addSeparator()

        # reset_act = QAction(self.tr("Clear"), self)
        # reset_act.triggered.connect(self.on_preset_clicked)

        # # When triggered, we will check for data and if None, we reset
        # reset_act.setData(None)
        # self.presets_menu.addAction(reset_act)
        # self.presets_menu.addAction(
        #     FIcon(0xF11E7), "Edit preset", self.on_edit_preset_pressed
        # )
        # self.presets_menu.addAction(FIcon(0xF0193), "Save", self.on_save_over_preset)
        # self.presets_menu.addAction(FIcon(0xF0415), "Save as new", self.on_save_preset)
        # self.presets_menu.addAction(FIcon(0xF054C), "Revert", self.on_revert_preset)

        # if selected_preset_action:
        #     selected_preset_action.trigger()

    def on_refresh(self):

        current_filters = self.mainwindow.get_state_data("filters")
        if self.filters == current_filters:
            # No change in filters = no refresh
            return

        self.model.clear()
        self.model.set_filters(current_filters)

        self.refresh_buttons()
        self._update_view_geometry()

    def refresh_buttons(self):
        """Actualize the enable states of Add/Del buttons"""

        if self.filters:
            # Data

            # Add button: Is an item selected ?
            index = self.view.currentIndex()
            if index.isValid() and self.model.item(index).type == FilterItem.LOGIC_TYPE:
                self.add_condition_action.setEnabled(True)
                self.add_group_action.setEnabled(True)
            else:
                # item is CONDITION_TYPE or there is no item selected (because of deletion)
                self.add_condition_action.setEnabled(False)
                self.add_group_action.setEnabled(False)

    def on_preset_changed(self):

        self.preset_menu.clear()
        for name in self.presets_model.preset_names():
            action = self.preset_menu.addAction(name)
            action.setData(self.presets_model.item(name))
            action.triggered.connect(self._on_select_preset)

    def on_apply(self):
        """Triggered when filters changed FROM THIS plugin

        Set the filters of the mainwindow and trigger a refresh of all plugins.
        """
        if self.mainwindow:

            # Close editor on validate, to avoid unset data
            self.close_current_editor()
            # Refresh other plugins only if the filters are modified
            self.mainwindow.set_state_data("filters", self.filters)
            self.mainwindow.refresh_plugins(sender=self)

        self.refresh_buttons()

    def close_current_editor(self):
        row = self.view.currentIndex().row()
        column = 2
        parent = self.view.currentIndex().parent()
        index = self.model.index(row, column, parent)

        widget = self.view.indexWidget(index)
        self.view.commitData(widget)
        self.view.closeEditor(
            widget,
            QAbstractItemDelegate.NoHint,
        )

    def on_add_logic(self):
        """Add logic item to the current selected index"""
        index = self.view.currentIndex()
        if index:
            self.model.add_logic_item(parent=index)
            # self.view.setFirstColumnSpanned(0, index.parent(), True)

            self._update_view_geometry()

    def load_presets(self):
        """Refresh self's preset model
        This method should be called by __init__ and on refresh
        """
        self.preset_menu.clear()
        config = Config("filters_editor")

        self.preset_menu.addAction("Save preset", self.on_save_preset)
        self.preset_menu.addSeparator()
        if "presets" in config:
            presets = config["presets"]
            for name, filters in presets.items():
                action = PresetAction(name, filters, self)
                action.set_close_icon(FIcon(0xF05E8, "red"))
                action.triggered.connect(self.on_select_preset)
                action.removed.connect(self.on_delete_preset)
                self.preset_menu.addAction(action)

        self.preset_menu.addSeparator()
        self.preset_menu.addAction("Reload presets", self.load_presets)

    def on_delete_preset(self):

        if not self.sender():
            return

        name = self.sender().text()

        ret = QMessageBox.warning(
            self,
            self.tr("Remove preset"),
            self.tr(f"Are you sure you want to delete preset {name}"),
            QMessageBox.Yes | QMessageBox.No,
        )

        if ret == QMessageBox.No:
            return

        config = Config("filters_editor")
        if "presets" not in config:
            config["presets"] = {}
        presets = config["presets"]
        if name in presets:
            del presets[name]
            config.save()
            self.load_presets()

    def on_select_preset(self):
        """Activate when preset has changed from preset_combobox"""

        data = self.sender().data()

        if data:
            self.filters = data
            self.on_apply()

    def on_save_preset(self):

        # So we don't accidentally save a preset that has not been applied yet...
        self.on_apply()

        name, ok = QInputDialog.getText(
            self,
            self.tr("Input dialog"),
            self.tr("Preset name:"),
            QLineEdit.Normal,
            QDir.home().dirName(),
        )
        i = 1
        while name in self.presets_model.preset_names():
            name = re.sub(r"\(\d+\)", "", name) + f" ({i})"
            i += 1

        if ok:
            self.mainwindow: MainWindow
            config = Config("filters_editor")
            if "presets" not in config:
                config["presets"] = {}
            if name in config["presets"]:
                ret = QMessageBox.warning(
                    self,
                    self.tr("Overwrite preset"),
                    self.tr(f"Preset {name} already exists. Do you want to overwrite it ?"),
                    QMessageBox.Yes | QMessageBox.No,
                )

                if ret == QMessageBox.No:
                    return
            self.presets_model.add_preset(name, self.mainwindow.get_state_data("filters"))
            self.presets_model.save()

        self.load_presets()

    def _update_view_geometry(self):
        """Set column Spanned to True for all Logic Item

        Allow Logic Item Editor to take all the space inside the row
        """
        self.view.expandAll()

        # self.view.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeToContents)
        # self.view.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeToContents)

        # for index in self.model.match(
        #     self.model.index(0, 0),
        #     FilterModel.TypeRole,
        #     FilterItem.LOGIC_TYPE,
        #     -1,
        #     Qt.MatchRecursive,
        # ):
        #     self.view.setFirstColumnSpanned(0, index.parent(), True)

    def on_add_condition(self):
        """Add new condition item

        - Add condition item to the current selected operator
        - Or add new operator and new condition item on a new filter
        """
        index = self.view.currentIndex()

        if index.isValid():
            if self.model.item(index).type == FilterItem.LOGIC_TYPE:
                # Add condition item to existing logic operator
                self.model.add_condition_item(parent=index)
        else:
            if self.model.rowCount() == 0:
                # Full new logic operator and condition item
                self.model.add_logic_item(parent=QModelIndex())
                gpindex = self.model.index(0, 0, QModelIndex())
                self.model.add_condition_item(parent=gpindex)

        self._update_view_geometry()
        self.refresh_buttons()

    def on_clear_all(self):
        """Clear all filters

        Ask user to be sure

        """

        ret = QMessageBox.question(
            self,
            self.tr("Remove all filters"),
            self.tr("Are you sure you want to remove all filters "),
        )

        if ret == QMessageBox.Yes:
            self.model.clear()
            if self.auto_action.isChecked():
                self.on_apply()

    def on_open_condition_dialog(self):
        """Open the condition creation dialog
        TODO: not used anymore
        """
        dialog = FieldDialog(conn=self.conn, parent=self)
        if dialog.exec_() == dialog.Accepted:
            cond = dialog.get_condition()
            index = self.view.currentIndex()
            if index:
                self.model.add_condition_item(parent=index, value=cond)

    def on_selection_changed(self):
        """Enable/Disable add button depending item type

        Notes:
            Disable Add button on CONDITION_TYPE
        """
        self.refresh_buttons()

    def remove_unchecked(self):
        """
        Remove unchecked filters from the filters tree model
        The trick here is that unchecked filters result in filters expression that has already
        been computed. So there is no need to compute it again.
        """
        self.model.filters = self.filters

    def contextMenuEvent(self, event: QContextMenuEvent):

        pos = self.view.viewport().mapFromGlobal(event.globalPos())
        index = self.view.indexAt(pos)

        if index.isValid():
            menu = QMenu(self)

            item = self.model.item(index)
            if item.type == FilterItem.LOGIC_TYPE:
                menu.addAction(self.add_condition_action)
                menu.addAction(self.add_group_action)

            # Check if this is not the root item
            if index.parent().isValid():
                menu.addAction(self.tr("Remove"), self.on_remove_filter)
                menu.addAction(self.tr("Duplicate"), self.on_duplicate_filter)

            menu.exec_(event.globalPos())


if __name__ == "__main__":

    app = QApplication(sys.argv)
    app.setStyle("fusion")

    style.dark(app)

    from cutevariant.core.importer import import_reader
    from cutevariant.core.reader import FakeReader
    import cutevariant.constants as cst
    from cutevariant.gui.ficon import FIcon, setFontPath

    setFontPath(cst.FONT_FILE)

    conn = sql.get_sql_connection(":memory:")
    import_reader(conn, FakeReader())

    data = {
        "$and": [
            {"chr": "chr12"},
            {"ref": "chr12"},
            {"ann.gene": "chr12"},
            {"ann.gene": "chr12"},
            {"pos": 21234},
            {"favorite": True},
            {"qual": {"$gte": 40}},
            {"ann.gene": {"$in": ["CFTR", "GJB2"]}},
            {"qual": {"$in": {"$wordset": "boby"}}},
            {"qual": {"$nin": {"$wordset": "boby"}}},
            {"samples.boby.gt": 1},
            {
                "$and": [
                    {"ann.gene": "chr12"},
                    {"ann.gene": "chr12"},
                    {"$or": [{"ann.gene": "chr12"}, {"ann.gene": "chr12"}]},
                ]
            },
        ]
    }

    # print(FilterModel.is_logic(data["$and"][6]))

    view = QTreeView()
    model = FilterModel()

    delegate = FilterDelegate()

    view.setModel(model)
    view.setItemDelegate(delegate)

    view.setModel(model)
    view.setAcceptDrops(True)
    view.setDragEnabled(True)
    view.setDropIndicatorShown(True)
    view.setSelectionBehavior(QAbstractItemView.SelectRows)
    view.setDragDropMode(QAbstractItemView.DragDrop)

    model.conn = conn
    model.load(data)

    view.expandAll()

    view.resize(800, 800)
    view.show()

    # view = QTreeView()
    # view.setEditTriggers(QAbstractItemView.DoubleClicked)
    # view.setAlternatingRowColors(True)
    # view.setUniformRowHeights(True)

    # view.setFirstColumnSpanned(0, QModelIndex(), True)
    # view.resize(500, 500)
    # view.show()
    # view.expandAll()

    app.exec_()
