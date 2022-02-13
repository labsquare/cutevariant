"""Plugin to Display genotypes variants 
"""
import typing
from functools import cmp_to_key, partial
import time
import copy
import re

# Qt imports
from PySide2.QtWidgets import *
from PySide2.QtCore import *
from PySide2.QtGui import *


# Custom imports
from cutevariant.core import sql, command
from cutevariant.core.reader import BedReader
from cutevariant.gui import plugin, FIcon, style
from cutevariant.commons import DEFAULT_SELECTION_NAME

from cutevariant.gui.widgets import ChoiceWidget, create_widget_action, SampleDialog


from cutevariant import LOGGER
from cutevariant.gui.sql_thread import SqlThread

from cutevariant.gui.style import GENOTYPE


from PySide2.QtWidgets import *
import sys
from functools import partial


class SamplesModel(QAbstractTableModel):

    samples_are_loading = Signal(bool)
    error_raised = Signal(str)
    load_started = Signal()
    load_finished = Signal()
    interrupted = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.conn = None
        self.items = []
        self.fields = []

        self.selected_samples = []
        self.selected_families = []
        self.selected_genotypes = []
        self.selected_tags = []

        self._headers = []
        self.fields_descriptions = {}

        # Creates the samples loading thread
        self._load_samples_thread = SqlThread(self.conn)

        # Connect samples loading thread's signals (started, finished, error, result ready)
        self._load_samples_thread.started.connect(
            lambda: self.samples_are_loading.emit(True)
        )
        self._load_samples_thread.finished.connect(
            lambda: self.samples_are_loading.emit(False)
        )
        self._load_samples_thread.result_ready.connect(self.on_samples_loaded)
        self._load_samples_thread.error.connect(self.error_raised)

        self._user_has_interrupt = False

    def rowCount(self, parent: QModelIndex = QModelIndex) -> int:
        """override"""
        return len(self.items)

    def columnCount(self, parent: QModelIndex = QModelIndex) -> int:
        """override"""
        return len(self._headers)

    def item(self, row: int):
        return self.items[row]

    def data(self, index: QModelIndex, role: Qt.ItemDataRole) -> typing.Any:
        """override"""
        if not index.isValid():
            return None

        item = self.items[index.row()]
        key = self._headers[index.column()]

        if role == Qt.DisplayRole and key != "valid":
            return item[key]

        if role == Qt.DecorationRole:
            if key == "valid":
                hex_icon = 0xF139A if item[key] == 1 else 0xF0FC7
                return QIcon(FIcon(hex_icon))

        # if role == Qt.DecorationRole:
        #     if index.column() == 0:
        #         return QIcon(FIcon(SEX_ICON.get(item["sex"], 0xF02D6)))
        #     if field == "gt":
        #         icon = style.GENOTYPE.get(item[field], style.GENOTYPE[-1])["icon"]
        #         return QIcon(FIcon(icon))

        # if role == Qt.ToolTipRole:
        #     if index.column() == 0:
        #         return f"""{item['name']} (<span style="color:{PHENOTYPE_COLOR.get(item['phenotype'],'lightgray')}";>{PHENOTYPE_STR.get(item['phenotype'],'Unknown phenotype')}</span>)"""

        #     else:
        #         description = self.fields_descriptions.get(field, "")
        #         return f"<b>{field}</b><br/> {description} "

        # if role == Qt.ForegroundRole and index.column() == 0:
        #     phenotype = self.items[index.row()]["phenotype"]
        #     return QColor(PHENOTYPE_COLOR.get(phenotype, "#FF00FF"))

    def headerData(self, section: int, orientation: Qt.Orientation, role: int):

        if orientation == Qt.Horizontal and role == Qt.DisplayRole:
            if section == 0:
                return ""

            if section < len(self._headers):
                return self._headers[section]

        return None

    def on_samples_loaded(self):

        self.beginResetModel()
        self.items.clear()

        self.items = self._load_samples_thread.results

        if len(self.items) > 0:
            self._headers = [i for i in self.items[0].keys() if i != "id"]

        self.endResetModel()

        # # Save cache
        # self._load_variant_cache[
        #     self._sample_hash
        # ] = self._load_variant_thread.results.copy()

        self._end_timer = time.perf_counter()
        self.elapsed_time = self._end_timer - self._start_timer
        self.load_finished.emit()

    def load(self, variant_id):
        """Start async queries to get sample fields for the selected variant

        Called by:
            - on_change_query() from the view.
            - sort() and setPage() by the model.

        See Also:
            :meth:`on_samples_loaded`
        """
        if self.conn is None:
            return

        if self.is_running():
            LOGGER.debug(
                "Cannot load data. Thread is not finished. You can call interrupt() "
            )
            self.interrupt()

        # Create load_func to run asynchronously: load samples
        load_samples_func = partial(
            sql.get_sample_annotations_by_variant,
            variant_id=variant_id,
            fields=self.fields,
            samples=self.selected_samples,
            families=self.selected_families,
            genotypes=self.selected_genotypes,
        )

        # Start the run
        self._start_timer = time.perf_counter()

        # # Create function HASH for CACHE
        # self._sample_hash = hash(load_samples_func.func.__name__ + str(load_samples_func.keywords))

        self.load_started.emit()

        # # Launch the first thread "count" or by pass it using the cache
        # if self._sample_hash in self._load_count_cache:
        #     self._load_variant_thread.results = self._load_count_cache[self._count_hash]
        #     self.on_samples_loaded()
        # else:
        self._load_samples_thread.conn = self.conn
        self._load_samples_thread.start_function(
            lambda conn: list(load_samples_func(conn))
        )

    def sort(self, column: int, order: Qt.SortOrder) -> None:
        self.beginResetModel()

        sorting_key = self.headerData(column, Qt.Horizontal, Qt.DisplayRole)

        # Compare items from self.items based on the sorting key given by the header
        def field_sort(i1, i2):
            # The one of i1 or i2 that is None should always be considered lower
            if i1[sorting_key] is None:
                return -1
            if i2[sorting_key] is None:
                return 1

            if i1[sorting_key] < i2[sorting_key]:
                return -1
            elif i1[sorting_key] == i2[sorting_key]:
                return 0
            else:
                return 1

        self.items = sorted(
            self.items,
            key=cmp_to_key(field_sort),
            reverse=order == Qt.DescendingOrder,
        )
        self.endResetModel()

    def interrupt(self):
        """Interrupt current query if active

        This is a blocking function...

        call interrupt and wait for the error_raised signals ...
        If nothing happen after 1000 ms, by pass and continue
        If I don't use the dead time, it is waiting for an infinite time
        at startup ... Because at startup, loading is called 2 times.
        One time by the register_plugin and a second time by the plugin.show_event
        """

        interrupted = False

        if self._load_samples_thread:
            if self._load_samples_thread.isRunning():
                self._user_has_interrupt = True
                self._load_samples_thread.interrupt()
                self._load_samples_thread.wait(1000)
                interrupted = True

        if interrupted:
            self.interrupted.emit()

    def is_running(self):
        if self._load_samples_thread:
            return self._load_samples_thread.isRunning()
        return False


class SamplesWidget(plugin.PluginWidget):
    """Widget displaying the list of avaible selections.
    User can select one of them to update Query::selection
    """

    ENABLE = True
    REFRESH_STATE_DATA = {"current_variant"}

    def __init__(self, parent=None, conn=None):
        """
        Args:
            parent (QWidget)
            conn (sqlite3.connexion): sqlite3 connexion
        """
        super().__init__(parent)

        self.toolbar = QToolBar()
        self.toolbar.setIconSize(QSize(16, 16))
        self.view = QTableView()
        self.view.setShowGrid(False)
        self.view.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.view.setSortingEnabled(True)
        self.view.setIconSize(QSize(16, 16))
        self.view.horizontalHeader().setHighlightSections(False)
        self.model = SamplesModel()

        self.error_label = QLabel()
        self.error_label.setStyleSheet(
            "QWidget{{background-color:'{}'; color:'{}'}}".format(
                style.WARNING_BACKGROUND_COLOR, style.WARNING_TEXT_COLOR
            )
        )

        self.field_selector = ChoiceWidget()
        self.field_selector.accepted.connect(self.on_refresh)
        self.sample_selector = ChoiceWidget()
        self.sample_selector.accepted.connect(self.on_refresh)
        self.family_selector = ChoiceWidget()
        self.family_selector.accepted.connect(self.on_refresh)
        self.tag_selector = ChoiceWidget()
        self.tag_selector.accepted.connect(self.on_refresh)
        self.geno_selector = ChoiceWidget()
        self.geno_selector.accepted.connect(self.on_refresh)

        self.setWindowIcon(FIcon(0xF0A8C))

        self.view.setModel(self.model)

        vlayout = QVBoxLayout()
        vlayout.setContentsMargins(0, 0, 0, 0)
        vlayout.addWidget(self.toolbar)
        vlayout.addWidget(self.view)
        vlayout.addWidget(self.error_label)
        vlayout.setSpacing(0)
        self.setLayout(vlayout)

        self.view.doubleClicked.connect(self._on_double_clicked)
        self.model.error_raised.connect(self.show_error)
        self.model.load_finished.connect(self.on_load_finished)

        self.setup_actions()

    def setup_actions(self):

        # Fields action
        field_action = create_widget_action(self.toolbar, self.field_selector)
        field_action.setIcon(FIcon(0xF0835))
        field_action.setText("Fields")
        field_action.setToolTip("Select fields to display")

        # sample action
        sample_action = create_widget_action(self.toolbar, self.sample_selector)
        sample_action.setIcon(FIcon(0xF0013))
        sample_action.setText("Samples ")
        sample_action.setToolTip("Filter by samples")

        # family action
        fam_action = create_widget_action(self.toolbar, self.family_selector)
        fam_action.setIcon(FIcon(0xF0B58))
        fam_action.setText("Family")
        fam_action.setToolTip("Filter by family")

        # tags action
        tag_action = create_widget_action(self.toolbar, self.tag_selector)
        tag_action.setIcon(FIcon(0xF04FC))
        tag_action.setText("Tags ")
        tag_action.setToolTip("Filter by tags")

        # only genotype action

        # geno action
        geno_action = create_widget_action(self.toolbar, self.geno_selector)
        geno_action.setIcon(FIcon(0xF0902))
        geno_action.setText("Genotype")
        geno_action.setToolTip("Filter by genotype")

        # Menu action

        spacer = QWidget()
        spacer.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

        self.toolbar.addWidget(spacer)
        menu_action = self.toolbar.addAction(FIcon(0xF035C), "menu")
        self.toolbar.widgetForAction(menu_action).setPopupMode(QToolButton.InstantPopup)
        self.general_menu = QMenu()

        self.clear_filters = self.general_menu.addAction(
            FIcon(0xF14F0), self.tr("Clear all filters"), self._on_clear_filters
        )

        self.general_menu.addAction(self.tr("Save preset"))
        self.general_menu.addAction(self.tr("Edit preset ..."))
        menu_action.setMenu(self.general_menu)

    def contextMenuEvent(self, event: QContextMenuEvent):

        menu = QMenu(self)
        menu.addAction(QIcon(), "Edit sample ...", self._show_sample_dialog)
        menu.exec_(event.globalPos())

    def _show_sample_dialog(self):

        row = self.view.selectionModel().currentIndex().row()
        sample = self.model.item(row)
        if sample:

            dialog = SampleDialog(self._conn, sample["id"])

            if dialog.exec_() == QDialog.Accepted:
                self.on_refresh()

    def _toggle_column(self, col: int, show: bool):
        """hide/show columns"""
        if show:
            self.view.showColumn(col)
        else:
            self.view.hideColumn(col)

    def _on_clear_filters(self):

        self.sample_selector.uncheck_all()
        self.family_selector.uncheck_all()
        self.geno_selector.uncheck_all()
        self.tag_selector.uncheck_all()

        self.on_refresh()

    def _on_double_clicked(self, index: QModelIndex):

        sample_name = index.siblingAtColumn(0).data()

        if sample_name:
            filters = copy.deepcopy(self.mainwindow.get_state_data("filters"))
            key = f"samples.{sample_name}.gt"
            condition = {key: {"$gte": 1}}

            if "$and" in filters:
                for index, field in enumerate(filters["$and"]):
                    if re.match(r"samples\.\w+\.gt", list(field.keys())[0]):
                        filters["$and"][index] = condition
                        break
                else:
                    filters["$and"].append(condition)
            else:
                filters = {"$and": [condition]}

            print("FILTERS", filters)
            self.mainwindow.set_state_data("filters", filters)
            self.mainwindow.refresh_plugins(sender=self)

    def on_open_project(self, conn):
        self._conn = conn
        self.model.conn = conn
        self.load_samples()
        self.load_tags()
        self.load_fields()
        self.load_family()
        self.load_genotype()

    def _is_selectors_checked(self):
        """Return False if selectors is not checked"""

        return (
            self.sample_selector.checked()
            or self.family_selector.checked()
            or self.tag_selector.checked()
        )

    def load_samples(self):

        self.sample_selector.clear()
        for sample in sql.get_samples(self._conn):
            self.sample_selector.add_item(
                FIcon(0xF0B55), sample["name"], data=sample["name"]
            )

    def load_tags(self):

        self.tag_selector.clear()
        for tag in ["#hemato", "#cancero", "#exome"]:
            self.tag_selector.add_item(FIcon(0xF04FD), tag, data=tag)

    def load_fields(self):
        self.field_selector.clear()
        for field in sql.get_field_by_category(self._conn, "samples"):
            self.field_selector.add_item(
                FIcon(0xF0835), field["name"], field["description"], data=field["name"]
            )

    def load_family(self):
        self.family_selector.clear()
        for fam in sql.get_samples_family(self._conn):
            self.family_selector.add_item(FIcon(0xF036E), fam, data=fam)

    def load_genotype(self):
        self.geno_selector.clear()

        for key, value in GENOTYPE.items():
            self.geno_selector.add_item(FIcon(value["icon"]), value["name"], data=key)

    def on_refresh(self):

        # Get fields
        self.current_variant = self.mainwindow.get_state_data("current_variant")
        variant_id = self.current_variant["id"]

        self.model.fields = [i["name"] for i in self.field_selector.selected_items()]

        self.model.selected_samples = [
            i["name"] for i in self.sample_selector.selected_items()
        ]
        self.model.selected_families = [
            i["name"] for i in self.family_selector.selected_items()
        ]
        self.model.selected_genotypes = [
            i["data"] for i in self.geno_selector.selected_items()
        ]

        self.model.load(variant_id)

        # self.view.horizontalHeader().setSectionResizeMode(
        #     0, QHeaderView.ResizeToContents
        # )
        # self.view.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeToContents)
        # self.view.horizontalHeader().setSectionResizeMode(0, QHeaderView.Minimum)
        # self.view.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)

    def show_error(self, message):
        self.error_label.setText(message)
        self.error_label.setVisible(bool(message))

    def on_load_finished(self):
        self.show_error("")

        self.view.horizontalHeader().setSectionResizeMode(QHeaderView.Interactive)
        self.view.horizontalHeader().setSectionResizeMode(
            0, QHeaderView.ResizeToContents
        )
        self.view.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)


if __name__ == "__main__":

    import sqlite3
    import sys
    from PySide2.QtWidgets import QApplication

    app = QApplication(sys.argv)

    conn = sqlite3.connect("/home/sacha/test3.db")
    conn.row_factory = sqlite3.Row

    view = SamplesWidget()
    view.on_open_project(conn)
    view.show()

    app.exec_()
