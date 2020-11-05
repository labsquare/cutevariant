from cutevariant.gui import plugin, FIcon
from cutevariant.core import sql
from PySide2.QtWidgets import *
from PySide2.QtCore import *
from PySide2.QtGui import *


class FieldsModel(QStandardItemModel):
    """Model to store all fields available for variants, annotations and samples"""

    def __init__(self, conn=None):
        super().__init__()
        self.checkable_items = []
        self.conn = conn

    def columnCount(self, index=QModelIndex()):
        return 2

    def headerData(self, section, orientation, role):

        if role != Qt.DisplayRole:
            return None

        if orientation == Qt.Horizontal:
            if section == 0:
                return "Name"

        return None

    @property
    def fields(self):
        """Return checked columns

        Returns:
            list -- list of columns
        """
        selected_fields = []
        for item in self.checkable_items:
            if item.checkState() == Qt.Checked:
                selected_fields.append(item.data()["name"])
        return selected_fields

    @fields.setter
    def fields(self, columns):
        """Check items which name is in columns

        Arguments:
            columns {list} -- list of columns
        """

        for item in self.checkable_items:
            item.setCheckState(Qt.Unchecked)
            if item.data()["name"] in columns:
                item.setCheckState(Qt.Checked)

    def load(self):
        """Load all columns avaible into the model"""
        self.clear()
        self.checkable_items.clear()

        self.appendRow(self.load_fields("variants"))
        self.appendRow(self.load_fields("annotations"))

        samples_items = QStandardItem("samples")
        samples_items.setIcon(FIcon(0xF0B9C))
        font = QFont()

        samples_items.setFont(font)

        for sample in sql.get_samples(self.conn):
            sample_item = self.load_fields("samples", parent_name=sample["name"])
            sample_item.setText(sample["name"])
            sample_item.setIcon(FIcon(0xF0B9C))
            samples_items.appendRow(sample_item)

        self.appendRow(samples_items)

    def load_fields(self, category, parent_name=None):
        root_item = QStandardItem(category)
        root_item.setColumnCount(2)
        root_item.setIcon(FIcon(0xF0256))
        font = QFont()
        root_item.setFont(font)

        type_icons = {"int": 0xF03A0, "str": 0xF100D, "float": 0xF03A0, "bool": 0xF023B}

        for field in sql.get_field_by_category(self.conn, category):
            field_name = QStandardItem(field["name"])
            descr = QStandardItem(field["description"])
            descr.setToolTip(field["description"])

            field_name.setCheckable(True)

            if field["type"] in type_icons.keys():
                field_name.setIcon(FIcon(type_icons[field["type"]]))

            root_item.appendRow([field_name, descr])
            self.checkable_items.append(field_name)

            if category == "samples":
                field_name.setData({"name": ("sample", parent_name, field["name"])})
            else:
                field_name.setData(field)

        return root_item


class FieldsEditorWidget(plugin.PluginWidget):
    """Display all fields according categorie

    Usage:

     view = FieldsWidget
     (conn)
     view.columns = ["chr","pos"]

    """

    ENABLE = True

    def __init__(self, conn=None, parent=None):
        super().__init__(parent)

        self.setWindowTitle(self.tr("Columns"))
        self.view = QTreeView()
        self.toolbar = QToolBar()
        # conn is always None here but initialized in on_open_project()
        self.model = FieldsModel(conn)

        # setup proxy ( for search option )
        self.proxy_model = QSortFilterProxyModel()
        self.proxy_model.setSourceModel(self.model)
        self.proxy_model.setRecursiveFilteringEnabled(True)
        # Search is case insensitive
        self.proxy_model.setFilterCaseSensitivity(Qt.CaseInsensitive)
        # Search in all columns
        self.proxy_model.setFilterKeyColumn(-1)

        self.view.setModel(self.proxy_model)
        self.view.setIconSize(QSize(16, 16))
        self.view.header().setSectionResizeMode(QHeaderView.ResizeToContents)
        self.view.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.view.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.search_edit = QLineEdit()
        # self.view.setIndentation(0)
        self.view.header().setVisible(False)
        layout = QVBoxLayout()

        layout.addWidget(self.search_edit)
        layout.addWidget(self.view)
        layout.addWidget(self.toolbar)

        layout.setContentsMargins(0, 0, 0, 0)
        self.setLayout(layout)
        self.model.itemChanged.connect(self.on_fields_changed)

        # Setup toolbar
        self.toolbar.setIconSize(QSize(16, 16))
        self.toolbar.addAction(
            FIcon(0xF0615), self.tr("Collapse"), self.view.collapseAll
        )
        self.toolbar.addAction(FIcon(0xF0616), self.tr("Expand"), self.view.expandAll)

        # setup search edit
        search_act = self.toolbar.addAction(
            FIcon(0xF0969), self.tr("Search fields by keywords...")
        )
        search_act.setCheckable(True)
        search_act.toggled.connect(self.on_search_pressed)
        search_act.setShortcut(QKeySequence.Find)
        self.search_edit.setVisible(False)
        self.search_edit.setPlaceholderText(self.tr("Search by keywords... "))

        self.search_edit.textChanged.connect(self.proxy_model.setFilterRegExp)

        self._is_refreshing = (
            False  # Help to avoid loop between on_refresh and on_fields_changed
        )

    def on_search_pressed(self, checked: bool):
        self.search_edit.setVisible(checked)
        self.search_edit.setFocus(Qt.MenuBarFocusReason)

    def on_open_project(self, conn):
        """ Overrided from PluginWidget """
        self.model.conn = conn
        self.model.load()
        self.on_refresh()

    def on_refresh(self):
        """ overrided from PluginWidget """
        self._is_refreshing = True
        self.model.fields = self.mainwindow.state.fields
        self._is_refreshing = False

    def on_fields_changed(self):

        if self.mainwindow is None or self._is_refreshing:
            return

        self.mainwindow.state.fields = self.model.fields
        self.mainwindow.refresh_plugins(sender=self)


if __name__ == "__main__":
    import sys
    from cutevariant.core.importer import import_reader
    from cutevariant.core.reader import FakeReader

    app = QApplication(sys.argv)

    conn = sql.get_sql_connection(":memory:")
    import_reader(conn, FakeReader())
    # import_file(conn, "examples/test.snpeff.vcf")

    view = FieldsEditorWidget()

    view.conn = conn
    view.fields = ["chr", "pos"]

    # view.changed.connect(lambda : print(view.columns))

    view.show()

    app.exec_()
