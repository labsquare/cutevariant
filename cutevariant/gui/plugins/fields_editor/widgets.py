from typing import List
import sqlite3
import json
from functools import lru_cache


from cutevariant.gui import plugin, FIcon, style
from cutevariant.core import sql
from PySide2.QtWidgets import *
from PySide2.QtCore import *
from PySide2.QtGui import *


import cutevariant.commons as cm

LOGGER = cm.logger()


@lru_cache()
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
    def __init__(
        self, category="variants", conn: sqlite3.Connection = None, parent=None
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

        Todo:
            Bug : What if 2 name are in different categories
        """

        for item in self._checkable_items:
            item.setCheckState(Qt.Unchecked)
            if item.data()["name"] in fields:
                item.setCheckState(Qt.Checked)

    def load(self):
        """Load all fields from the model"""

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
                    self.appendRow([field_name_item, descr_item])

    def to_file(self, filename: str):
        """Serialize checked fields to a json file

        Args:
            filename (str): a json filename
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

        # Create the variants widget (the view and its associated filter model)
        self.variants_fields_view = QTableView()
        self.variants_fields_model = FieldsModel("variants", conn)
        self.variants_fields_filter = QSortFilterProxyModel(self)
        self.init_all(
            self.variants_fields_model,
            self.variants_fields_filter,
            self.variants_fields_view,
        )

        # Create the annotations widget (the view and its associated filter model)
        self.annotations_fields_view = QTableView()
        self.annotations_fields_model = FieldsModel("annotations", conn)
        self.annotations_fields_filter = QSortFilterProxyModel(self)
        self.init_all(
            self.annotations_fields_model,
            self.annotations_fields_filter,
            self.annotations_fields_view,
        )

        # Create the samples widget (the view and its associated filter model)
        self.samples_fields_view = QTableView()
        self.samples_fields_model = FieldsModel("samples", conn)
        self.samples_fields_filter = QSortFilterProxyModel(self)
        self.init_all(
            self.samples_fields_model,
            self.samples_fields_filter,
            self.samples_fields_view,
        )

        self.tab_widget.addTab(self.variants_fields_view, self.tr("variants"))
        self.tab_widget.addTab(self.annotations_fields_view, self.tr("annotations"))
        self.tab_widget.addTab(self.samples_fields_view, self.tr("samples"))

        layout = QVBoxLayout(self)
        layout.addWidget(self.tab_widget)

        self.conn = conn

    def init_all(
        self, model: FieldsModel, proxy: QSortFilterProxyModel, view: QTableView
    ):
        proxy.setSourceModel(model)
        view.setModel(proxy)
        view.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeToContents)
        view.setIconSize(QSize(16, 16))
        view.setEditTriggers(QAbstractItemView.NoEditTriggers)
        proxy.setRecursiveFilteringEnabled(True)

        proxy.setFilterCaseSensitivity(Qt.CaseInsensitive)
        proxy.setFilterKeyColumn(-1)

        model.itemChanged.connect(lambda: self.fields_changed.emit())

    def update_filter(self, text: str):
        """
        Callback for when the search bar is updated (filter the three models)
        """
        self.variants_fields_filter.setFilterRegExp(text)
        self.annotations_fields_filter.setFilterRegExp(text)
        self.samples_fields_filter.setFilterRegExp(text)

    @property
    def checked_fields(self) -> List[str]:
        """Return checked fields

        Returns:
            List[str] : list of checked fields
        """
        return (
            self.variants_fields_model.checked_fields
            + self.annotations_fields_model.checked_fields
            + self.samples_fields_model.checked_fields
        )

    @checked_fields.setter
    def checked_fields(self, fields: List[str]):
        """Check fields according name

        Arguments:
            columns (List[str]):
        """
        self.variants_fields_model.checked_fields = fields
        self.annotations_fields_model.checked_fields = fields
        self.samples_fields_model.checked_fields = fields

    @property
    def conn(self):
        return self._conn

    @conn.setter
    def conn(self, conn):
        prepare_fields_for_editor.cache_clear()
        self._conn = conn
        self.variants_fields_model.conn = conn
        self.annotations_fields_model.conn = conn
        self.samples_fields_model.conn = conn


class FieldsEditorWidget(plugin.PluginWidget):
    """Display all fields according categorie

    Usage:

     view = FieldsWidget
     (conn)
     view.columns = ["chr","pos"]

    """

    ENABLE = True

    # @property
    # def conn(self):
    #     return self._conn

    # @conn.setter
    # def conn(self, conn):
    #     self._conn = conn
    #     self.widget_fields.conn = conn

    def __init__(self, conn=None, parent=None):
        super().__init__(parent)

        self.setWindowTitle(self.tr("Columns"))

        self.toolbar = QToolBar(self)
        self.widget_fields = FieldsWidget(conn, parent)
        self.search_edit = QLineEdit()

        layout = QVBoxLayout(self)

        layout.addWidget(self.toolbar)
        layout.addWidget(self.widget_fields)
        layout.addWidget(self.search_edit)

        layout.setContentsMargins(0, 0, 0, 0)

        self.widget_fields.fields_changed.connect(self.on_fields_changed)

        # Setup toolbar
        self.toolbar.setIconSize(QSize(16, 16))

        # setup search edit
        self.setFocusPolicy(Qt.ClickFocus)

        self.search_act = QAction(FIcon(0xF0969), self.tr("Search by keywords..."))
        self.search_act.setCheckable(True)
        self.search_act.toggled.connect(self.on_search_pressed)
        self.search_act.setShortcutContext(Qt.WidgetShortcut)
        self.search_act.setShortcut(QKeySequence.Find)

        self.toolbar.addAction(self.search_act)

        self.search_edit.setVisible(False)
        self.search_edit.setPlaceholderText(self.tr("Search by keywords... "))

        self.search_edit.textChanged.connect(self.widget_fields.update_filter)

        self.auto_refresh = True

        self._is_refreshing = (
            False  # Help to avoid loop between on_refresh and on_fields_changed
        )

        self.conn = conn

    def on_search_pressed(self, checked: bool):
        self.search_edit.setVisible(checked)
        self.search_edit.setFocus(Qt.MenuBarFocusReason)

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

    def on_fields_changed(self):
        if self.mainwindow is None or self._is_refreshing:
            """
            Debugging (no window)
            """
            print(self.widget_fields.checked_fields)
            return

        self.mainwindow.state.fields = self.widget_fields.checked_fields
        if self.auto_refresh:
            self.mainwindow.refresh_plugins(sender=self)


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
