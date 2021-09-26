import functools
from typing import List
import sqlite3
import json
import os
from functools import lru_cache
import typing
import copy
import re

from PySide2.QtWidgets import *
from PySide2.QtCore import *
from PySide2.QtGui import *
from cutevariant.config import Config

from cutevariant.gui import plugin, FIcon, style
from cutevariant.gui.mainwindow import MainWindow
from cutevariant.core import sql


import cutevariant.commons as cm

from cutevariant import LOGGER


class FieldsPresetModel(QAbstractListModel):
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

    def add_preset(self, name: str, fields: list):
        """Add fields preset
        Args:
            name (str): preset name
            fields (list): list of field names
        """
        self.beginInsertRows(QModelIndex(), 0, 0)
        self._presets.insert(0, (name, fields))
        self.endInsertRows()

    def rem_presets(self, indexes: List[int]):
        indexes.sort(reverse=True)
        self.beginResetModel()
        for idx in indexes:
            del self._presets[idx]
        self.endResetModel()

    def load(self):
        self.beginResetModel()
        config = Config("fields_editor")
        presets = config.get("presets", {})
        self._presets = [
            (preset_name, fields) for preset_name, fields in presets.items()
        ]
        self.endResetModel()

    def save(self):
        config = Config("fields_editor", self.config_path)
        config["presets"] = {
            preset_name: fields for preset_name, fields in self._presets
        }
        config.save()

    def clear(self):
        self.beginResetModel()
        self._presets.clear()
        self.endResetModel()

    def preset_names(self):
        return [p[0] for p in self._presets]


class PresetsDialog(QDialog):

    """A dialog box to dispay and order fields from a preset config

    dialog = PresetsDialog()
    dialog.load()

    """

    def __init__(self, preset_name="test_preset", parent=None):
        super().__init__()

        self.setWindowTitle(self.tr("Edit Fields preset"))
        self.view = QListWidget()
        self.name_edit = QLineEdit()
        self.button_box = QDialogButtonBox(
            QDialogButtonBox.Save | QDialogButtonBox.Cancel
        )
        self.add_button = QToolButton()
        self.rem_button = QToolButton()
        self.up_button = QToolButton()
        self.down_button = QToolButton()
        self.name_edit.setPlaceholderText("Preset name ")
        self.add_button.setText("+")
        self.rem_button.setText("-")
        self.up_button.setText("▲")
        self.down_button.setText("▼")

        self.add_button.setAutoRaise(True)
        self.rem_button.setAutoRaise(True)
        self.up_button.setAutoRaise(True)
        self.down_button.setAutoRaise(True)

        self.view.setDragDropMode(QAbstractItemView.InternalMove)

        self.up_button.clicked.connect(self.move_up)
        self.down_button.clicked.connect(self.move_down)

        self.view.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

        vLayout = QVBoxLayout()

        tool_layout = QHBoxLayout()

        spacer = QWidget()
        spacer.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

        tool_layout.addWidget(self.add_button)
        tool_layout.addWidget(self.rem_button)
        tool_layout.addWidget(spacer)
        tool_layout.addWidget(self.up_button)
        tool_layout.addWidget(self.down_button)

        vLayout.addWidget(self.name_edit)
        vLayout.addWidget(self.view)
        vLayout.addLayout(tool_layout)
        vLayout.addWidget(self.button_box)

        self.setLayout(vLayout)

        self.preset_name = preset_name

        self.button_box.accepted.connect(self._save_and_close)
        self.button_box.rejected.connect(self.reject)

    @property
    def preset_name(self):
        return self.name_edit.text()

    @preset_name.setter
    def preset_name(self, name):
        """ Set preset name and load preset """
        self.name_edit.setText(name)
        self.load()

    def _save_and_close(self):
        self.save()
        self.accept()

    def load(self):
        """Load preset `preset_name` from config

        Load preset from the config file

        Args:
            preset_name (str): The preset key name
        """
        config = Config("fields_editor")
        presets = config.get("presets")
        if self.preset_name in presets:
            fields = presets[self.preset_name]
            self.fields = fields

    def save(self):
        """Save fields in config"""
        config = Config("fields_editor")
        presets = config["presets"]
        presets[self.preset_name] = self.fields
        config["presets"] = presets
        config.save()

    @property
    def fields(self):
        items = []
        for row in range(self.view.count()):
            items.append(self.view.item(row).text())

        return items

    @fields.setter
    def fields(self, fields):
        self.view.clear()
        self.view.addItems(fields)

    def move_up(self):
        row = self.view.currentRow()
        if row <= 0:
            return

        item = self.view.takeItem(row - 1)
        self.view.insertItem(row, item)

    def move_down(self):
        row = self.view.currentRow()
        if row > self.view.count() - 1:
            return
        item = self.view.takeItem(row + 1)
        self.view.insertItem(row, item)


def prepare_fields_for_editor(conn):
    """
    Returns a dict with field info for each category.
    Example result:
    {
        "variants":
        {
            "chr":{"type":"str","description":{"The chromosome the variant was found on"}},
            "pos":{...}
        },
        "annotations":
        {
            "ann.gene":{"type":"str","description":"Name of the gene where the variant is"}},
            "ann.impact":{...}
        },
        "samples":
        {
            "samples.boby.gt":{"type":"int","description":{"Genotype for this sample (0:hom. for ref, 1: het for alt, 2:hom for alt)}}
            "samples.boby.dp":{...}
        }
    }
    """

    results = {"variants": {}, "annotations": {}, "samples": {}}

    samples = [sample["name"] for sample in sql.get_samples(conn)]

    for field in sql.get_fields(conn):

        if field["category"] == "variants":
            name = field["name"]
            results["variants"][name] = {
                "type": field["type"],
                "description": field["description"],
            }

        if field["category"] == "annotations":
            name = field["name"]
            results["annotations"][f"ann.{name}"] = {
                "type": field["type"],
                "description": field["description"],
            }

        if field["category"] == "samples":
            name = field["name"]
            for sample in samples:
                results["samples"][f"samples.{sample}.{name}"] = {
                    "type": field["type"],
                    "description": field["description"],
                }

    return results


class FieldsModel(QStandardItemModel):
    """
    Standard key,value model (2 columns) with field name and its respective description
    """

    fields_loaded = Signal()

    def __init__(
        self, conn: sqlite3.Connection = None, category="variants", parent=None
    ):
        super().__init__(0, 2, parent)
        self._checkable_items = []
        self.conn = conn
        self._category = category
        self.setColumnCount(2)

    @property
    def conn(self):
        return self._conn

    @conn.setter
    def conn(self, conn):
        self._conn = conn
        if self._conn:
            self.load()
        else:
            self.clear()

    @property
    def checked_fields(self) -> List[str]:
        """Return checked fields

        Returns:
            List[str] : list of checked fields
        """
        selected_fields = []
        for item in self._checkable_items:
            if item.checkState() == Qt.Checked:
                selected_fields.append(item.data()["name"])
        return selected_fields

    def flags(self, index: QModelIndex) -> Qt.ItemFlags:
        return super().flags(index) | Qt.ItemIsDragEnabled

    @checked_fields.setter
    def checked_fields(self, fields: List[str]):
        """Check fields according name

        Arguments:
            columns (List[str]):
        """

        for item in self._checkable_items:
            item.setCheckState(Qt.Unchecked)
            if item.data()["name"] in fields:
                item.setCheckState(Qt.Checked)

    def load(self):
        """Load all fields from the model"""

        # Don't forget to reset the model
        self.clear()

        # Clear checkable items as well, the list may contain selected items from another project...
        self._checkable_items.clear()

        self.setColumnCount(2)
        self.setHorizontalHeaderLabels(["name", "description"])

        if self.conn:
            fields = prepare_fields_for_editor(self.conn).get(self._category, None)
            if not fields:
                LOGGER.warning("Cannot load field category %s", self._category)
            else:
                # This piece of code uses the get_indexed_fields function to retrieve the list of indexed fields in this category
                indexed_fields = sql.get_indexed_fields(self.conn)

                for field in fields:
                    field_name = field
                    if self._category == "annotations":
                        # Remove the ann. prefix (4 characters)
                        # field_name = field_name[4:]
                        pass
                    if self._category == "samples":
                        # Remove the samples. prefix (8 characters)
                        # field_name = field_name[8:]
                        pass

                    field_desc = fields[field]["description"]

                    field_name_item = QStandardItem(field_name)

                    field_name_item.setCheckable(True)
                    font = QFont()

                    field_name_item.setData(False, Qt.UserRole)

                    if (self._category, field_name.split(".")[-1]) in indexed_fields:
                        font.setUnderline(True)
                        field_name_item.setData(True, Qt.UserRole)
                    font.setBold(True)
                    field_name_item.setFont(font)
                    field_type = style.FIELD_TYPE.get(fields[field]["type"])
                    field_name_item.setIcon(
                        FIcon(field_type["icon"], field_type["color"])
                    )

                    self._checkable_items.append(field_name_item)
                    field_name_item.setData(
                        {
                            "name": field,
                            "type": fields[field]["type"],
                            "description": fields[field]["description"],
                        }
                    )

                    descr_item = QStandardItem(field_desc)
                    descr_item.setToolTip(fields[field]["description"])

                    self.appendRow([field_name_item, descr_item])
                    self.fields_loaded.emit()

    def remove_field_from_index(self, index: QModelIndex):

        items_to_update = [self.itemFromIndex(index.siblingAtColumn(0))]

        field_name = index.siblingAtColumn(0).data()
        # To have sample field only, without the sample name
        if self._category == "samples":
            field_name = field_name.split(".")[-1]

            # We want to schedule them all for update, because in the field editor, sample field appears once per sample...
            items_to_update.clear()
            for i in range(self.rowCount()):
                if self.item(i, 0).data(Qt.DisplayRole).split(".")[-1] == field_name:
                    items_to_update.append(self.item(i, 0))

        sql.remove_indexed_field(self.conn, self._category, field_name)

        # Return True on success (i.e. the field is not in the indexed fields anymore)
        success = (self._category, field_name) not in sql.get_indexed_fields(self.conn)

        for item in items_to_update:
            # Weird, but positive success means UserRole should be False (i.e. the field is not indexed anymore)
            item.setData(not success, Qt.UserRole)
            if success:
                font = item.font()
                font.setUnderline(False)
                item.setFont(font)

        return success

    def add_field_to_index(self, index: QModelIndex):
        items_to_update = [self.itemFromIndex(index.siblingAtColumn(0))]

        field_name = index.siblingAtColumn(0).data()
        # To have sample field only, without the sample name
        if self._category == "samples":
            field_name = field_name.split(".")[-1]

            # We want to schedule them all for update, because in the field editor, sample field appears once per sample...
            items_to_update.clear()
            for i in range(self.rowCount()):
                if self.item(i, 0).data(Qt.DisplayRole).split(".")[-1] == field_name:
                    items_to_update.append(self.item(i, 0))

        if self._category == "variants":
            sql.create_variants_indexes(self.conn, {field_name})
        if self._category == "annotations":
            # replace shortcut
            if field_name.startswith("ann."):
                field_name = field_name.replace("ann.", "")
            sql.create_annotations_indexes(self.conn, {field_name})
        if self._category == "samples":
            # replace shortcut
            if field_name.startswith("samples."):
                field_name = field_name.replace("samples.", "")
            sql.create_samples_indexes(self.conn, {field_name})

        # Return True on success (i.e. the field is now in the index field)
        success = (self._category, field_name) in sql.get_indexed_fields(self.conn)

        for item in items_to_update:

            item.setData(success, Qt.UserRole)
            if success:
                font = item.font()
                font.setUnderline(True)
                item.setFont(font)

        return success

    def mimeData(self, indexes: typing.List[QModelIndex]) -> QMimeData:
        fields = [idx.data(Qt.UserRole + 1) for idx in indexes if idx.column() == 0]
        fields = [(f["name"], f["type"]) for f in fields]
        res = QMimeData("cutevariant/typed-json")
        res.setData(
            "cutevariant/typed-json",
            bytes(json.dumps({"type": "fields", "fields": fields}), "utf-8"),
        )
        return res

    def mimeTypes(self) -> typing.List[str]:
        return ["cutevariant/typed-json"]

    def to_file(self, filename: str):
        """Serialize checked fields to a json file

        Args:
            filename (str): a json filename

        TODO: Rename to 'to_json'
        """
        with open(filename, "w") as outfile:
            obj = {"checked_fields": self.checked_fields}
            json.dump(obj, outfile)

    def from_file(self, filename: str):
        """Unserialize checked fields from a json file

        Args:
            filename (str): a json filename
        """
        with open(filename, "r") as infile:
            obj = json.load(infile)
            self.checked_fields = obj.get("checked_fields", [])


class FieldsWidget(QWidget):

    fields_changed = Signal()

    def __init__(self, conn: sqlite3.Connection = None, parent=None):
        super().__init__(parent)
        self.tab_widget = QTabWidget(self)
        self.tab_widget.setTabPosition(QTabWidget.South)
        self.tab_widget.tabBar().setDocumentMode(True)
        self.tab_widget.tabBar().setExpanding(True)

        self.views = []

        # Create the variants widget (the view and its associated filter model)
        self.add_view(conn, "variants")

        # Create the annotations widget (the view and its associated filter model)
        self.add_view(conn, "annotations")

        # Create the samples widget (the view and its associated filter model)
        self.add_view(conn, "samples")

        layout = QVBoxLayout(self)
        layout.addWidget(self.tab_widget)
        layout.setContentsMargins(0, 0, 0, 0)

        self.conn = conn

    def add_view(self, conn, category):
        model = FieldsModel(conn, category)
        view = QTableView()
        view.setContextMenuPolicy(Qt.ActionsContextMenu)

        proxy = QSortFilterProxyModel()
        proxy.setSourceModel(model)

        view.setModel(proxy)
        view.setShowGrid(False)
        view.setIconSize(QSize(24, 24))

        view.setEditTriggers(QAbstractItemView.NoEditTriggers)
        view.setSelectionMode(QAbstractItemView.ExtendedSelection)
        view.setSelectionBehavior(QAbstractItemView.SelectRows)
        view.setAlternatingRowColors(False)
        view.setWordWrap(True)
        view.verticalHeader().hide()

        view.setSortingEnabled(True)
        view.setDragEnabled(True)
        view.horizontalHeader().setStretchLastSection(True)

        proxy.setRecursiveFilteringEnabled(True)
        proxy.setFilterCaseSensitivity(Qt.CaseInsensitive)
        proxy.setFilterKeyColumn(-1)

        model.itemChanged.connect(lambda: self.fields_changed.emit())

        # Setup actions

        # Setup the filter field action. Will filter out NULL values (thus the broom icon)
        filter_field_action = QAction(self.tr("Create filter on null values"), view)
        filter_field_action.triggered.connect(
            functools.partial(self._on_filter_field_clicked, view, proxy, category)
        )
        filter_field_action.setIcon(FIcon(0xF00E2))

        index_field_action = QAction(self.tr("Create index..."), view)
        index_field_action.triggered.connect(
            functools.partial(self._on_index_field_clicked, view, proxy, category)
        )
        index_field_action.setIcon(FIcon(0xF05DB))

        remove_index_action = QAction(self.tr("Remove index..."), view)
        remove_index_action.triggered.connect(
            functools.partial(self._on_remove_index_clicked, view, proxy, category)
        )
        remove_index_action.setIcon(FIcon(0xF0A97))

        view.addActions([filter_field_action, index_field_action, remove_index_action])

        # Update even if the index didn't change
        view.pressed.connect(self._update_actions)

        self.views.append(
            {
                "view": view,
                "proxy": proxy,
                "model": model,
                "name": category,
                "actions": {
                    "filter": filter_field_action,
                    "index": index_field_action,
                    "drop_index": remove_index_action,
                },
            }
        )
        self.tab_widget.addTab(
            view, FIcon(style.FIELD_CATEGORY.get(category, None)["icon"]), category
        )

    def _update_actions(self, current: QModelIndex):
        is_indexed = current.siblingAtColumn(0).data(Qt.UserRole)
        for view in self.views:
            view: dict
            tableview: QTableView = view["view"]
            act_index: QAction = view["actions"].get("index", None)
            act_drop_index: QAction = view["actions"].get("drop_index", None)
            if act_index:
                if is_indexed:
                    tableview.removeAction(act_index)
                else:
                    tableview.addAction(act_index)
            if act_drop_index:
                if is_indexed:
                    tableview.addAction(act_drop_index)
                else:
                    tableview.removeAction(act_drop_index)

    def _on_index_field_clicked(
        self,
        view: QTableView,
        proxy: QSortFilterProxyModel,
        category: str,
    ):
        field_index = view.currentIndex().siblingAtColumn(0)
        field_name = field_index.data()
        if (
            QMessageBox.question(
                self,
                self.tr("Please confirm"),
                self.tr(
                    f"Removing index will make queries on this field slower.\nAre you sure you want to remove {field_name} from indexed fields?"
                ),
            )
            != QMessageBox.Yes
        ):
            return

        model: FieldsModel = proxy.sourceModel()

        if not model.add_field_to_index(proxy.mapToSource(field_index)):
            QMessageBox.warning(
                self,
                self.tr("Indexing failed!"),
                self.tr(f"Could not index column {field_name}!"),
            )
        else:
            QMessageBox.information(
                self,
                self.tr("Done indexing!"),
                self.tr(f"Successfully indexed column {field_name}!"),
            )

    def _on_remove_index_clicked(
        self, view: QTableView, proxy: QSortFilterProxyModel, category: str
    ):
        field_index = view.currentIndex().siblingAtColumn(0)
        field_name = field_index.data()
        if (
            QMessageBox.question(
                self,
                self.tr("Please confirm"),
                self.tr(
                    f"Removing index will make queries on this field slower.\nAre you sure you want to remove {field_name} from indexed fields?"
                ),
            )
            != QMessageBox.Yes
        ):
            return
        if category == "samples":
            field_name = field_name.split(".")[-1]

        model: FieldsModel = proxy.sourceModel()

        if not model.remove_field_from_index(proxy.mapToSource(field_index)):
            QMessageBox.warning(
                self,
                self.tr("Removing index failed!"),
                self.tr(f"Could not remove column {field_name} from indexed fields!"),
            )
        else:
            QMessageBox.information(
                self,
                self.tr("Success!"),
                self.tr(
                    f"Successfully removed column {field_name} from indexed fields!"
                ),
            )

    def _on_filter_field_clicked(
        self, view: QTableView, proxy: QSortFilterProxyModel, category: str
    ):
        """When the user triggers the "filter not null" field action.
        Applies immediately a filter on this field, with a not-null condition

        Args:
            view (QTableView): The view showing a selected field
            category (str): (not used) The category the selected field belongs to
            model (FieldsModel): The actual model containing the data
            proxy (QSortFilterProxyModel): The proxymodel used by the view
        """
        parent: FieldsEditorWidget = self.parent()
        mainwindow: MainWindow = parent.mainwindow
        filters = copy.deepcopy(mainwindow.get_state_data("filters"))
        field_name = view.currentIndex().siblingAtColumn(0).data()

        if category == "annotations":
            field_name = f"ann.{field_name}"
        if category == "samples":
            field_name = f"samples.{field_name}"

        # TODO: filters should start with below expression application-wide...
        if not filters:
            filters = {"$and": []}

        if "$and" in filters:
            filters["$and"].append({field_name: {"$ne": None}})
            mainwindow.set_state_data("filters", filters)
            mainwindow.refresh_plugins(sender=self)

    def update_filter(self, text: str):
        """
        Callback for when the search bar is updated (filter the three models)
        """
        for index, view in enumerate(self.views):
            view["proxy"].setFilterRole(Qt.DisplayRole)
            view["proxy"].setFilterRegExp(text)
            count = view["proxy"].rowCount()
            name = view["name"]
            self.tab_widget.setTabText(index, f"{name} ({count})")

    def show_checked_only(self, active=False):

        for index, view in enumerate(self.views):
            view["proxy"].setFilterRole(Qt.CheckStateRole)
            view["proxy"].setFilterKeyColumn(0)
            # Checked = "2" / Unchecked = "0" / All : ""
            is_checked_str = "2" if active else ""
            view["proxy"].setFilterFixedString(is_checked_str)
            count = view["proxy"].rowCount()
            name = view["name"]
            self.tab_widget.setTabText(index, f"{name} ({count})")

    @property
    def checked_fields(self) -> List[str]:
        """Return checked fields

        Returns:
            List[str] : list of checked fields
        """
        result = []
        for view in self.views:
            result += view["model"].checked_fields
        return result

    @checked_fields.setter
    def checked_fields(self, fields: List[str]):
        """Check fields according name

        Arguments:
            columns (List[str]):
        """
        for view in self.views:
            view["model"].checked_fields = fields

    @property
    def conn(self):
        return self._conn

    @conn.setter
    def conn(self, conn):
        self._conn = conn
        for index, view in enumerate(self.views):
            model = view["model"]
            name = view["name"]
            model.conn = conn
            self.tab_widget.setTabText(index, f"{name} ({model.rowCount()})")
            if conn:
                view["view"].horizontalHeader().setSectionResizeMode(
                    0, QHeaderView.ResizeToContents
                )


class FieldsEditorWidget(plugin.PluginWidget):
    """Display all fields according categories

    Usage:

     view = FieldsWidget
     (conn)
     view.columns = ["chr","pos"]

    """

    ENABLE = True
    REFRESH_STATE_DATA = {"fields"}

    DEFAULT_FIELDS = ["chr", "pos", "ref", "alt"]

    def __init__(self, conn=None, parent=None):
        super().__init__(parent)

        self.setWindowIcon(FIcon(0xF08DF))

        # Create toolbar with search
        self.tool_layout = QHBoxLayout()

        # Setup Toolbar
        # self.toolbar.setIconSize(QSize(16, 16))
        # self.toolbar.setToolButtonStyle(Qt.ToolButtonIconOnly)
        # self.toolbar.layout().setContentsMargins(0, 0, 0, 0)
        # Setup preset combo
        self.presets_combo = QComboBox()
        self.presets_combo.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        self.presets_combo.currentIndexChanged.connect(self.on_select_preset)
        self.tool_layout.addWidget(self.presets_combo)

        # Add button
        add_button = QToolButton()
        add_button.setIcon(FIcon(0xF0415))
        add_button.setText("Add")
        add_button.clicked.connect(self.on_save_preset)
        self.tool_layout.addWidget(add_button)

        # Edit button
        edit_button = QToolButton()
        edit_button.setIcon(FIcon(0xF0900))
        edit_button.setText("edit")
        edit_button.clicked.connect(self.on_edit_preset)
        self.tool_layout.addWidget(edit_button)

        # delete button
        delete_button = QToolButton()
        delete_button.setIcon(FIcon(0xF0156, QColor("red")))
        delete_button.setText("edit")
        delete_button.clicked.connect(self.on_delete_preset)

        self.tool_layout.addWidget(delete_button)
        ## Create fields view
        self.widget_fields = FieldsWidget(conn, parent)

        ## Create search bar
        self.search_edit = QLineEdit()
        self.search_edit.setPlaceholderText(self.tr("Search by keywords... "))
        self.search_edit.textChanged.connect(self.widget_fields.update_filter)
        self.search_edit.setVisible(True)
        clean_action = self.search_edit.addAction(
            FIcon(0xF015A), QLineEdit.TrailingPosition
        )
        clean_action.triggered.connect(self.search_edit.clear)

        ## Create apply button
        self.apply_button = QPushButton(self.tr("Apply"))
        self.apply_button.setIcon(FIcon(0xF0E1E, "white"))
        self.apply_button.setStyleSheet("background-color: #038F6A; color:white")
        self.apply_button.pressed.connect(self.on_apply)

        # setup button_layout
        main_layout = QVBoxLayout(self)
        # layout.setContentsMargins(0, 0, 0, 0)
        main_layout.addLayout(self.tool_layout)
        main_layout.addWidget(self.search_edit)
        main_layout.addWidget(self.widget_fields)
        main_layout.addWidget(self.apply_button)

        self.setFocusPolicy(Qt.ClickFocus)

    def load_presets(self):
        """Refresh self's preset model
        This method should be called by __init__ and on refresh
        """

        self.presets_combo.clear()
        config = Config("fields_editor")
        presets = config["presets"]
        for name, fields in presets.items():
            LOGGER.error(fields)
            self.presets_combo.addItem(name, fields)

    def on_delete_preset(self):
        name = self.presets_combo.currentText()

        ret = QMessageBox.warning(
            self,
            self.tr("Remove preset"),
            self.tr(f"Are you sure you want to delete preset {name}"),
            QMessageBox.Yes | QMessageBox.No,
        )

        if ret == QMessageBox.No:
            return

        config = Config("fields_editor")
        presets = config["presets"]
        if name in presets:
            del presets[name]
            config.save()
            self.load_presets()

    def on_save_preset(self):

        w = PresetsDialog()
        w.preset_name = "No name"
        w.fields = self.widget_fields.checked_fields
        if w.exec_():
            self.load_presets()

    def on_edit_preset(self):

        name = self.presets_combo.currentText()
        if name:
            w = PresetsDialog()
            w.preset_name = name
            w.exec_()

    def toggle_search_bar(self, show=True):
        """Make search bar visible or not

        Args:
            show (bool, optional): If true, search bar is visible
        """
        self.search_edit.setVisible(show)
        if not show:
            self.search_edit.clear()
        else:
            self.search_edit.setFocus(Qt.PopupFocusReason)

    def toggle_checked(self, show=True):
        """Make only checked fields visible or not

        Args:
            show (bool, optional): if true, only checked fields are visibles
        """
        self.widget_fields.show_checked_only(show)

    def on_select_preset(self):
        """Activate when preset has changed from preset_combobox"""
        # TODO Should be
        # self.mainwindow.set_state_data("fields",action.data())
        # self.mainwindow.refresh_plugins(sender=self)

        LOGGER.error(self.presets_combo.currentData())
        self.widget_fields.checked_fields = self.presets_combo.currentData()
        self.on_apply(self.presets_combo.currentData())

    def on_open_project(self, conn):
        """Overrided from PluginWidget"""
        self.widget_fields.conn = conn
        self.on_refresh()

    def on_refresh(self):
        """overrided from PluginWidget"""
        if self.mainwindow:
            self._is_refreshing = True
            self.widget_fields.checked_fields = self.mainwindow.get_state_data("fields")
            self._is_refreshing = False
        self.load_presets()

    def on_apply(self, fields=None):
        if self.mainwindow is None or self._is_refreshing:
            """
            Debugging (no window)
            """
            LOGGER.debug(self.widget_fields.checked_fields)
            return

        fields = self.widget_fields.checked_fields if fields is None else fields

        self.mainwindow.set_state_data("fields", fields)
        self.mainwindow.refresh_plugins(sender=self)

    def to_json(self):
        """override from plugins: Serialize plugin state"""

        return {"checked_fields": self.widget_fields.checked_fields}

    def from_json(self, data):
        """override from plugins: Unzerialize plugin state"""

        if "checked_fields" in data:
            self.widget_fields.checked_fields = data["checked_fields"]


if __name__ == "__main__":
    import sys
    from cutevariant.core.importer import import_reader
    from cutevariant.core.reader import FakeReader

    app = QApplication(sys.argv)

    conn = sql.get_sql_connection(":memory:")
    import_reader(conn, FakeReader())
    # import_file(conn, "examples/test.snpeff.vcf")

    # widget = FieldsEditorWidget()
    # widget.on_open_project(conn)

    # # view.changed.connect(lambda : print(view.columns))

    # widget.show()

    w = PresetsDialog()
    w.show()

    app.exec_()
