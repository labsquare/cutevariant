"""Plugin to show all characteristics of a selected variant

VariantInfoWidget is showed on the GUI, it uses VariantPopupMenu to display a
contextual menu about the variant which is selected.
VariantPopupMenu is also used in viewquerywidget for the same purpose.
"""
from logging import DEBUG

# Qt imports
from PySide6.QtCore import QModelIndex, Qt, Slot, QSize
from PySide6.QtWidgets import *
from PySide6.QtGui import QFont, QColor

# Custom imports
from cutevariant.gui import FIcon, style
from cutevariant.core import sql, get_sql_connection
from cutevariant.gui.plugin import PluginWidget
from cutevariant import constants as cst

from cutevariant.gui.widgets import DictWidget


from cutevariant.gui.widgets.qjsonmodel import QJsonModel, QJsonTreeItem

from cutevariant import LOGGER


class VariantInfoModel(QJsonModel):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._headers = ["Fields", "Value"]
        self.fields_descriptions = {}

    @property
    def conn(self):
        return self._conn

    @conn.setter
    def conn(self, conn):
        self._conn = conn
        self.fields_descriptions = {f["name"]: f["description"] for f in sql.get_fields(conn)}

    def data(self, index: QModelIndex, role: Qt.ItemDataRole):

        item: QJsonTreeItem = index.internalPointer()
        value = item.value

        # if role == Qt.ForegroundRole and index.column() == 1:

        #     if value == "":
        #         return Qt.gray

        #     value_type = type(value).__name__
        #     if value_type in style.FIELD_TYPE:
        #         col = QColor(style.FIELD_TYPE[value_type]["color"])
        #         return col

        if role == Qt.SizeHintRole:
            return QSize(30, 30)

        if role == Qt.ToolTipRole:

            if index.column() == 0:
                # Return fields description
                key = super().data(index, Qt.DisplayRole)
                description = self.fields_descriptions.get(key, "")
                return f"<b>{key}</b><br/>{description}"

            if index.column() == 1:
                # Return key values
                return str(value)

        if role == Qt.DisplayRole and index.column() == 1:
            if value == "":
                return item.childCount()

        if role == Qt.FontRole and index.column() == 0:
            font = QFont()
            font.setBold(True)
            return font

        return super().data(index, role)

    def flags(self, index):
        return Qt.ItemIsEnabled | Qt.ItemIsSelectable


class VariantInfoWidget(PluginWidget):
    """Plugin to show all annotations of a selected variant"""

    ENABLE = False
    REFRESH_STATE_DATA = {"current_variant"}

    def __init__(self, parent=None):
        super().__init__(parent)

        # Current variant => set by on_refresh and on_open_project
        self.current_variant = None

        self.model = VariantInfoModel()

        self.proxy_model = QSortFilterProxyModel()
        self.proxy_model.setSourceModel(self.model)
        self.proxy_model.setRecursiveFilteringEnabled(True)

        self.view = QTreeView()
        self.view.setModel(self.proxy_model)
        self.view.setAlternatingRowColors(True)

        self.search_bar = QLineEdit()
        self.search_bar.textChanged.connect(self.proxy_model.setFilterFixedString)
        self.search_bar.setPlaceholderText(self.tr("Search by keywords... "))
        self.search_bar.addAction(FIcon(0xF015A), QLineEdit.TrailingPosition).triggered.connect(
            self.search_bar.clear
        )

        vlayout = QVBoxLayout()
        vlayout.addWidget(self.view)
        vlayout.addWidget(self.search_bar)
        vlayout.setContentsMargins(0, 0, 0, 0)

        self.setLayout(vlayout)
        self.setWindowIcon(FIcon(0xF0B73))

    #     self.view = QTabWidget()
    #     self.toolbar = QToolBar()
    #     # self.toolbar.setIconSize(QSize(16, 16))

    #     # Build comments tab
    #     self.edit_panel = EditPanel()
    #     self.edit_panel.saved.connect(self.on_save_variant)
    #     self.view.addTab(self.edit_panel, self.tr("User"))

    #     # Build variant tab
    #     self.variant_view = DictWidget()
    #     self.variant_view.set_header_visible(True)

    #     self.view.addTab(self.variant_view, self.tr("Variant"))

    #     # Build transcript tab
    #     self.transcript_combo = QComboBox()
    #     self.transcript_view = DictWidget()
    #     self.transcript_view.set_header_visible(True)
    #     tx_layout = QVBoxLayout()
    #     tx_layout.addWidget(self.transcript_combo)
    #     tx_layout.addWidget(self.transcript_view)
    #     tx_widget = QWidget()
    #     tx_widget.setLayout(tx_layout)
    #     self.view.addTab(tx_widget, self.tr("Transcripts"))
    #     self.transcript_combo.currentIndexChanged.connect(self.on_transcript_changed)

    #     # Build Samples tab
    #     self.sample_combo = QComboBox()
    #     self.sample_view = DictWidget()
    #     self.sample_view.set_header_visible(True)

    #     tx_layout = QVBoxLayout()
    #     tx_layout.addWidget(self.sample_combo)
    #     tx_layout.addWidget(self.sample_view)
    #     tx_widget = QWidget()
    #     tx_widget.setLayout(tx_layout)
    #     self.view.addTab(tx_widget, self.tr("Samples"))
    #     self.sample_combo.currentIndexChanged.connect(self.on_sample_changed)

    #     # Build genotype tab
    #     self.genotype_view = QListWidget()
    #     # self.genotype_view.setIconSize(QSize(20, 20))
    #     self.view.addTab(self.genotype_view, self.tr("Genotypes"))

    #     v_layout = QVBoxLayout()
    #     v_layout.setContentsMargins(0, 0, 0, 0)
    #     v_layout.addWidget(self.view)
    #     self.setLayout(v_layout)

    #     # # Create menu
    #     # TODO: restore this
    #     # self.context_menu = VariantPopupMenu()
    #     # # Ability to trigger the menu
    #     # self.view.setContextMenuPolicy(Qt.CustomContextMenu)
    #     # self.view.customContextMenuRequested.connect(self.show_menu)
    #     # self.add_tab("variants")

    #     # Cache all database fields and their descriptions for tooltips
    #     # Field names as keys, descriptions as values
    #     self.fields_descriptions = None

    #     # Cache genotype icons
    #     # Values in gt field as keys (str), FIcon as values
    #     self.genotype_icons = {
    #         key: FIcon(val) for key, val in cst.GENOTYPE_ICONS.items()
    #     }

    # def clear(self):
    #     """ Clear all view """
    #     self.variant_view.clear()
    #     self.transcript_view.clear()
    #     self.sample_view.clear()
    #     self.genotype_view.clear()
    #     self.edit_panel.clear()

    # def on_save_variant(self):

    #     # if view is visible
    #     if "variant_view" in self.mainwindow.plugins:
    #         variant_view = self.mainwindow.plugins["variant_view"]

    #         update_data = self.edit_panel.get_data()

    #         index = variant_view.main_right_pane.view.currentIndex()
    #         variant_view.main_right_pane.model.update_variant(index.row(), update_data)

    #         # variant_view.main_right_pane.model.update_variant(index.row(), update_data)

    #     else:
    #         # TODO BUT UNNECESSARY because we always have a variant_viex ...
    #         # Save directly in database ?
    #         pass

    def on_open_project(self, conn):
        self.conn = conn
        self.model.conn = conn

    def on_refresh(self):
        """Set the current variant by the variant displayed in the GUI"""
        self.current_variant = self.mainwindow.get_state_data("current_variant")

        results = sql.get_variant(self.conn, self.current_variant["id"], True, True)

        self.model.load(results)
        self.view.expandAll()
        self.view.header().setSectionResizeMode(0, QHeaderView.Stretch)
        # self.view.header().setSectionResizeMode(1, QHeaderView.Fixed)

    # @Slot()
    # def on_save_clicked(self):
    #     """Save button
    #     """
    #     classification = self.classification_box.currentIndex()
    #     favorite = self.favorite_checkbox.isChecked()
    #     comment = self.comment_input.toPlainText()

    #     updated = {
    #         "classification": classification,
    #         "favorite": favorite,
    #         "comment": comment,
    #     }

    #     if "variant_view" in self.mainwindow.plugins:
    #         main_view = self.mainwindow.plugins["variant_view"]
    #         print(main_view)

    # sql.update_variant(self.conn, updated)

    # def show_menu(self, pos: QPoint):
    #     """Show context menu associated to the current variant"""
    #     if not self.current_variant:
    #         return
    #     self.context_menu.popup(self.current_variant, self.view.mapToGlobal(pos))


if __name__ == "__main__":
    import sys

    app = QApplication(sys.argv)

    conn = get_sql_connection("/home/schutz/Dev/cutevariant/examples/test.db")

    w = VariantInfoWidget()
    w.conn = conn

    variant = sql.get_variant(conn, 1)

    w.current_variant = variant

    w.show()

    app.exec_()
