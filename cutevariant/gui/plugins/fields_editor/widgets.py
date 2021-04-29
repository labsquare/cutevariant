from typing import List
import sqlite3
import json
import os
import glob
from functools import lru_cache

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
                        FIcon(field_type["icon"], "white", field_type["color"])
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
        view.horizontalHeader().setStretchLastSection(True)
        view.setIconSize(QSize(16, 16))
        view.setEditTriggers(QAbstractItemView.NoEditTriggers)
        view.setSelectionMode(QAbstractItemView.SingleSelection)
        view.setSelectionBehavior(QAbstractItemView.SelectRows)
        view.setAlternatingRowColors(True)
        view.setWordWrap(True)
        view.verticalHeader().hide()
        view.setSortingEnabled(True)

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
        # TODO : this is not working .. Charles
        for index, view in enumerate(self.views):
            view["proxy"].setFilterRole(Qt.CheckStateRole)
            view["proxy"].setFilterKeyColumn(0)

            # view["proxy"].setFilterFixedString("1")
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


class FieldsPresetsEditorDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle(self.tr("Presets Editor"))
        self.caption_label = QLabel(self.tr("Edit fields presets"))
        self.presets_model = QStandardItemModel(0, 0)
        self.presets_view = QListView(self)
        self.presets_view.setSelectionMode(QAbstractItemView.ExtendedSelection)
        self.presets_view.setModel(self.presets_model)

        # self.toolbar = QToolBar(self)
        # self.delete_action = self.toolbar.addAction(
        #     FIcon(0xF01B4), self.tr("Delete selected presets"), self.on_remove_presets
        # )

        #        self.delete_action.setShortcut(QKeySequence.Delete)

        del_button = QPushButton(self.tr("Delete"))
        ok_button = QPushButton(self.tr("Ok"))

        ok_button.clicked.connect(self.close)
        del_button.clicked.connect(self.on_remove_presets)

        button_layout = QHBoxLayout()
        button_layout.addWidget(del_button)
        button_layout.addWidget(ok_button)

        layout = QVBoxLayout(self)
        layout.addWidget(self.presets_view)
        layout.addLayout(button_layout)

        self.load_presets()

    def on_remove_presets(self):
        # Retrieve selected presets (scheduled for deletion)
        selected_preset_indexes = self.presets_view.selectionModel().selectedIndexes()
        if not selected_preset_indexes:
            # Don't even ask, nothing will be deleted !
            return

        confirmation = QMessageBox.question(
            self,
            self.tr("Please confirm"),
            self.tr(
                f"Do you really want to remove selected presets ?\n {len(selected_preset_indexes)} presets would be definitely lost !"
            ),
        )
        if confirmation == QMessageBox.Yes:
            selected_items = [
                self.presets_model.item(selected.row())
                for selected in selected_preset_indexes
            ]
            for selected_item in selected_items:
                preset_file_name = selected_item.data()
                os.remove(preset_file_name)
            # After we removed all selected presets from the disk, let's reload the model
            self.load_presets()

    def load_presets(self):

        self.presets_model.clear()
        settings = QSettings()
        preset_path = settings.value(
            "preset_path",
            QStandardPaths.writableLocation(QStandardPaths.GenericDataLocation),
        )

        filenames = glob.glob(f"{preset_path}/*.fields.json")
        #  Sort file by date
        filenames.sort(key=os.path.getmtime)

        for filename in filenames:
            with open(filename) as file:
                obj = json.load(file)
                preset_item = QStandardItem(obj.get("name", ""))

                # All we need from the preset is its name (the item title) and the path to the file where it is stored
                preset_item.setData(filename)
                self.presets_model.appendRow([preset_item])


class FieldsEditorWidget(plugin.PluginWidget):
    """Display all fields according categories

    Usage:

     view = FieldsWidget
     (conn)
     view.columns = ["chr","pos"]

    """

    ENABLE = True

    def __init__(self, conn=None, parent=None):
        super().__init__(parent)
        self.setWindowIcon(FIcon(0xF08DF))

        self.toolbar = QToolBar(self)
        self.widget_fields = FieldsWidget(conn, parent)

        # Create search bar
        self.search_edit = QLineEdit()
        self.search_edit.setPlaceholderText(self.tr("Search by keywords... "))
        self.search_edit.textChanged.connect(self.widget_fields.update_filter)
        self.search_edit.setVisible(False)
        # setup button_layout
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.toolbar)
        layout.addWidget(self.search_edit)

        layout.addWidget(self.widget_fields)

        # Create search action
        self.search_action = self.toolbar.addAction(FIcon(0xF0349), "Search ...")
        self.search_action.setCheckable(True)
        self.search_action.triggered.connect(lambda x: self.toggle_search_bar(x))

        # self.show_check_action = self.toolbar.addAction(FIcon(0xF0C51), "show checked")
        # self.show_check_action.setCheckable(True)
        # self.show_check_action.triggered.connect(lambda x: self.toggle_checked(x))

        spacer = QWidget()
        spacer.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.toolbar.addWidget(spacer)
        # Create apply button
        self.apply_fields = QPushButton(FIcon(0xF0E1E), self.tr("Apply"))
        self.apply_fields.pressed.connect(self.on_apply_fields_pressed)

        # Setup toolbar
        self.toolbar.setIconSize(QSize(16, 16))
        self.toolbar.setToolButtonStyle(Qt.ToolButtonTextBesideIcon)

        # Create preset button
        self.presets_button = QPushButton(self.tr("Default preset"))
        self.presets_button.setFlat(True)
        self.presets_button.setIcon(FIcon(0xF035C))

        self.toolbar.addWidget(self.presets_button)
        self.toolbar.addAction(FIcon(0xF0E1E), "Apply", self.on_apply_fields_pressed)

        self.menu = QMenu(self)

        self.load_preset_menu()

        self.presets_button.setMenu(self.menu)
        self.setFocusPolicy(Qt.ClickFocus)

        self.auto_refresh = True

        self._is_refreshing = (
            False  # Help to avoid loop between on_refresh and on_fields_changed
        )

    def toggle_search_bar(self, show=True):
        self.search_edit.setVisible(show)
        if not show:
            self.search_edit.clear()
        else:
            self.search_edit.setFocus(Qt.PopupFocusReason)

    def toggle_checked(self, show=True):
        # TODO : this is not working .. Charles
        self.widget_fields.show_checked_only(True)

    def load_preset_menu(self):
        """
        Loads/updates all saved presets
        When called, the default preset will be selected and applied, to avoid any confusion
        """
        settings = QSettings()
        preset_path = settings.value(
            "preset_path",
            QStandardPaths.writableLocation(QStandardPaths.GenericDataLocation),
        )

        self.menu.clear()

        filenames = glob.glob(f"{preset_path}/*.fields.json")
        #  Sort file by date
        filenames.sort(key=os.path.getmtime)

        for filename in filenames:
            with open(filename) as file:
                obj = json.load(file)
                action = self.menu.addAction(obj.get("name", ""))
                action.setData(obj)
                action.setIcon(FIcon(0xF103B))
                action.triggered.connect(self.on_preset_clicked)

        self.menu.addSeparator()
        default_preset = self.menu.addAction(self.tr("Default preset"))

        # Hard-coded default preset
        default_preset.setData(
            {
                "name": self.tr("Default preset"),
                "checked_fields": [
                    "favorite",
                    "classification",
                    "chr",
                    "pos",
                    "ref",
                    "alt",
                    "qual",
                ],
            }
        )
        default_preset.triggered.connect(self.on_preset_clicked)

        self.menu.addAction(FIcon(0xF0193), "Save...", self.on_save_preset)
        self.menu.addAction(FIcon(0xF11E7), "Edit...", self.on_edit_preset_pressed)

        default_preset.trigger()

    def on_preset_clicked(self):

        action = self.sender()
        data = action.data()
        if "name" in data:
            self.presets_button.setText(data["name"])
        else:
            self.presets_button.setText("")
        self.from_json(data)

        self.on_apply_fields_pressed()

    def on_save_preset(self):

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

            self.load_preset_menu()

            # Fakes the selection of that preset that just got created...
            self.presets_button.setText(name)

    def on_edit_preset_pressed(self):
        edit_dialog = FieldsPresetsEditorDialog(self)
        edit_dialog.exec_()

        # Reload the preset menu again, in case the user deleted some
        self.load_preset_menu()
        # Dialog should be out of scope, but doesn't get deleted !

    def on_open_project(self, conn):
        """ Overrided from PluginWidget """
        self.widget_fields.conn = conn
        self.on_refresh()

    def on_refresh(self):
        """ overrided from PluginWidget """
        if self.mainwindow:
            self._is_refreshing = True
            self.widget_fields.checked_fields = self.mainwindow.state.fields
            self._is_refreshing = False

    def on_apply_fields_pressed(self):
        if self.mainwindow is None or self._is_refreshing:
            """
            Debugging (no window)
            """
            print(self.widget_fields.checked_fields)
            return

        self.mainwindow.state.fields = self.widget_fields.checked_fields
        self.mainwindow.refresh_plugins(sender=self)

    def to_json(self):
        """ override from plugins: Serialize plugin state """

        return {"checked_fields": self.widget_fields.checked_fields}

    def from_json(self, data):
        """ override from plugins: Unzerialize plugin state """

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
