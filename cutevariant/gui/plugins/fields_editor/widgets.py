from typing import List
import sqlite3
import json
import os
import glob
from functools import lru_cache
import typing

from cutevariant.gui import plugin, FIcon, style
from cutevariant.core import sql
from PySide2.QtWidgets import *
from PySide2.QtCore import *
from PySide2.QtGui import *


import cutevariant.commons as cm

LOGGER = cm.logger()


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
                for field in fields:
                    field_name = field
                    if self._category == "annotations":
                        # Remove the ann. prefix (4 characters)
                        field_name = field_name[4:]
                    if self._category == "samples":
                        # Remove the samples. prefix (8 characters)
                        field_name = field_name[8:]

                    field_desc = fields[field]["description"]

                    field_name_item = QStandardItem(field_name)
                    field_name_item.setCheckable(True)
                    font = QFont()
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

    def mimeData(self, indexes: typing.List[QModelIndex]) -> QMimeData:
        field_names = [
            idx.data(Qt.UserRole + 1)["name"] for idx in indexes if idx.column() == 0
        ]
        internal_dict = {"fields": field_names}
        res = QMimeData("application/json")
        res.setText(json.dumps(internal_dict))
        return res

    def mimeTypes(self) -> typing.List[str]:
        return ["application/json"]

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
        proxy = QSortFilterProxyModel()
        proxy.setSourceModel(model)

        view.setModel(proxy)
        view.setShowGrid(False)
        view.horizontalHeader().setStretchLastSection(True)
        view.setIconSize(QSize(16, 16))
        view.setEditTriggers(QAbstractItemView.NoEditTriggers)
        view.setSelectionMode(QAbstractItemView.ExtendedSelection)
        view.setSelectionBehavior(QAbstractItemView.SelectRows)
        view.setAlternatingRowColors(False)
        view.setWordWrap(True)
        view.verticalHeader().hide()
        view.setSortingEnabled(True)

        view.setDragEnabled(True)

        proxy.setRecursiveFilteringEnabled(True)
        proxy.setFilterCaseSensitivity(Qt.CaseInsensitive)
        proxy.setFilterKeyColumn(-1)

        model.itemChanged.connect(lambda: self.fields_changed.emit())

        self.views.append(
            {"view": view, "proxy": proxy, "model": model, "name": category}
        )
        self.tab_widget.addTab(
            view, FIcon(style.FIELD_CATEGORY.get(category, None)["icon"]), category
        )

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
            print(is_checked_str)
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

        self.toolbar = QToolBar(self)
        self.widget_fields = FieldsWidget(conn, parent)

        # Setup Toolbar
        self.toolbar.setIconSize(QSize(16, 16))
        self.toolbar.setToolButtonStyle(Qt.ToolButtonIconOnly)

        # Create search bar
        self.search_edit = QLineEdit()
        self.search_edit.setPlaceholderText(self.tr("Search by keywords... "))
        self.search_edit.textChanged.connect(self.widget_fields.update_filter)
        self.search_edit.setVisible(False)
        clean_action = self.search_edit.addAction(
            FIcon(0xF015A), QLineEdit.TrailingPosition
        )
        clean_action.triggered.connect(self.search_edit.clear)

        # setup button_layout
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.toolbar)
        layout.addWidget(self.widget_fields)
        layout.addWidget(self.search_edit)

        self.search_action = self.toolbar.addAction(FIcon(0xF0349), "Search")
        self.search_action.setCheckable(True)
        self.search_action.setToolTip(self.tr("Search for a fields"))
        self.search_action.toggled.connect(lambda x: self.toggle_search_bar(x))
        self.show_check_action = self.toolbar.addAction(
            FIcon(0xF0C51), "show checked only"
        )
        self.show_check_action.setCheckable(True)
        self.show_check_action.setToolTip(self.tr("Show checked fields only"))
        self.show_check_action.toggled.connect(lambda x: self.toggle_checked(x))
        # Create exclusive actions
        actions = QActionGroup(self)
        actions.addAction(self.search_action)
        actions.addAction(self.show_check_action)
        actions.setExclusionPolicy(QActionGroup.ExclusionPolicy.ExclusiveOptional)

        # Create spacer
        spacer = QWidget()
        spacer.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.toolbar.addWidget(spacer)

        # Create preset combobox with actions
        self.toolbar.addSeparator()
        # Save button
        self.save_action = self.toolbar.addAction(self.tr("Save Preset"))
        self.save_action.setIcon(FIcon(0xF0818))
        self.save_action.triggered.connect(self.on_save_preset)
        self.save_action.setToolTip(self.tr("Save as a new Preset"))

        # Remove button
        self.remove_action = self.toolbar.addAction(self.tr("Remove Preset"))
        self.remove_action.setIcon(FIcon(0xF0B89))
        self.remove_action.triggered.connect(self.on_remove_preset)
        self.remove_action.setToolTip(self.tr("Remove current preset"))
        self.remove_action.setDisabled(True)

        # Preset combobox
        self.preset_combo = QComboBox(self)
        self.preset_combo.currentIndexChanged.connect(self.on_select_preset)
        self.toolbar.addWidget(self.preset_combo)

        self.toolbar.addSeparator()

        # Create apply action
        apply_action = self.toolbar.addAction(self.tr("Apply"))
        self.apply_button = self.toolbar.widgetForAction(apply_action)
        self.apply_button.setIcon(FIcon(0xF0E1E, "white"))
        self.apply_button.setStyleSheet("background-color: #038F6A; color:white")
        self.apply_button.setAutoRaise(False)
        self.apply_button.setToolButtonStyle(Qt.ToolButtonTextBesideIcon)
        self.apply_button.pressed.connect(self.on_apply)

        self.setFocusPolicy(Qt.ClickFocus)
        self.load_presets()

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

    def load_presets(self):
        """
        Loads/updates all saved presets
        """

        self.preset_combo.blockSignals(True)
        self.preset_combo.clear()
        self.preset_combo.addItem(FIcon(0xF1038), "Default", userData="default")

        # get default application directory
        settings = QSettings()
        preset_path = settings.value(
            "preset_path",
            QStandardPaths.writableLocation(QStandardPaths.GenericDataLocation),
        )

        filenames = glob.glob(f"{preset_path}/*.fields.json")
        #  Sort file by date
        filenames.sort(key=os.path.getmtime)

        # Load all user presets
        for filename in filenames:
            with open(filename) as file:
                obj = json.load(file)
                name = obj.get("name", "")
                if name:
                    # we store the filename as data.
                    self.preset_combo.addItem(FIcon(0xF1038), name, filename)
        self.preset_combo.blockSignals(False)

    def on_save_preset(self):
        """Save preset a file into the default directory"""
        settings = QSettings()
        preset_path = settings.value(
            "preset_path",
            QStandardPaths.writableLocation(QStandardPaths.GenericDataLocation),
        )

        name, ok = QInputDialog.getText(
            self,
            self.tr("Input dialog"),
            self.tr("Preset name:"),
            QLineEdit.Normal,
            QDir.home().dirName(),
        )

        if ok:
            with open(f"{preset_path}/{name}.fields.json", "w") as file:
                obj = self.to_json()
                obj["name"] = name
                json.dump(obj, file)

            self.load_presets()
            # set last presets
            if self.preset_combo.count() > 0:
                self.preset_combo.setCurrentIndex(self.preset_combo.count() - 1)

    def on_remove_preset(self):

        filename = self.preset_combo.currentData()
        if os.path.exists(filename):
            reply = QMessageBox.question(
                self,
                self.tr("Remove preset ..."),
                self.tr(f"Do you want to remove the preset {filename}?"),
                QMessageBox.Yes | QMessageBox.No,
            )

            if reply == QMessageBox.Yes:
                os.remove(filename)
                self.load_presets()

    def on_select_preset(self):
        """Activate when preset has changed from preset_combobox"""
        filename = self.preset_combo.currentData()

        if filename == "default":
            self.widget_fields.checked_fields = self.DEFAULT_FIELDS
            self.remove_action.setDisabled(True)

        elif os.path.exists(filename):
            self.remove_action.setDisabled(False)
            with open(filename) as file:
                self.from_json(json.load(file))

        self.on_apply()

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

    def on_apply(self):
        if self.mainwindow is None or self._is_refreshing:
            """
            Debugging (no window)
            """
            print(self.widget_fields.checked_fields)
            return

        self.mainwindow.set_state_data("fields", self.widget_fields.checked_fields)
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

    widget = FieldsEditorWidget()
    widget.on_open_project(conn)

    # view.changed.connect(lambda : print(view.columns))

    widget.show()

    app.exec_()
