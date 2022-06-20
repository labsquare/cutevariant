"""Plugin to Display genotypes variants 
"""
from dataclasses import replace
import typing
from functools import cmp_to_key, partial
import functools
import time
import copy
import re
import sqlite3

# Qt imports
from PySide6.QtWidgets import *
from PySide6.QtCore import *
from PySide6.QtGui import *


# Custom imports
from cutevariant.core import sql, command
from cutevariant.core.reader import BedReader
from cutevariant.gui import plugin, FIcon, style
from cutevariant.constants import DEFAULT_SELECTION_NAME
from cutevariant.config import Config
import cutevariant.commons as cm


from cutevariant.gui.widgets import (
    ChoiceButton,
    SampleDialog,
    SampleVariantDialog,
    PresetAction,
)

from cutevariant.gui import tooltip as toolTip
from cutevariant import LOGGER
from cutevariant.gui.sql_thread import SqlThread

from cutevariant.gui import FormatterDelegate
from cutevariant.gui.formatters.cutestyle import CutestyleFormatter

import cutevariant.constants as cst

from PySide6.QtWidgets import *
import sys
from functools import partial


class GenotypeVerticalHeader(QHeaderView):

    # COLOR = {0: "gray", 1: "orange", 2: "green"}

    def __init__(self, parent=None):
        super().__init__(Qt.Vertical, parent)

    def sizeHint(self):
        return QSize(30, super().sizeHint().height())

    def paintSection(self, painter: QPainter, rect: QRect, section: int):

        painter.setBrush(QBrush(QColor("red")))

        painter.save()
        super().paintSection(painter, rect, section)
        painter.restore()
        # default color
        default_color = "lightgray"

        # classification color
        number = self.model().get_genotype(section).get("classification")
        if number:
            classification = next(i for i in self.model().classifications if i["number"] == number)
            color = classification.get("color", default_color)
        else:
            color = default_color

        # genotype icon
        GENOTYPE_ICONS = {key: FIcon(val) for key, val in cst.GENOTYPE_ICONS.items()}
        genotype_sample_name = self.model().get_genotype(section)["name"]
        genotype_variant_id = self.model().get_genotype(section)["variant_id"]

        genotype = ""
        if genotype_variant_id and genotype_sample_name:
            genotype_infos = next(
                sql.get_genotypes(
                    self.model().conn,
                    genotype_variant_id,
                    ["gt"],
                    [genotype_sample_name],
                )
            )
            genotype = genotype_infos["gt"]
        if genotype:
            genotype_int = int(genotype)
        else:
            genotype_int = -1
        pix_icon = GENOTYPE_ICONS.get(genotype_int)  # , GENOTYPE_ICONS[-1])
        pix_icon.engine.setColor(color)

        # painter
        pen = QPen(QColor(color))
        pen.setWidth(6)
        painter.setPen(pen)
        painter.setBrush(QBrush(color))
        painter.drawLine(rect.left(), rect.top() + 1, rect.left(), rect.bottom() - 1)

        target = QRect(0, 0, 20, 20)
        pix = pix_icon.pixmap(target.size())
        target.moveCenter(rect.center() + QPoint(1, 1))

        painter.drawPixmap(target, pix)


class GenotypeModel(QAbstractTableModel):

    """

    model = GenotypeModel()

    model.set_fields(["gt","dp","truc"])
    model.set_samples(["boby","raymond"])
    model.set_variant_id(324)

    model.load()

    """

    samples_are_loading = Signal(bool)
    error_raised = Signal(str)
    load_started = Signal()
    load_finished = Signal()
    interrupted = Signal()

    def __init__(self, conn: sqlite3.Connection = None, parent=None):
        super().__init__(parent)

        self.conn = conn

        # Inner Data
        self._genotypes = []

        # Selected fields
        self._fields = set()

        # Selected samples
        self._samples = set()

        # Current variant
        self._variant_id = 0

        self._headers = []
        self.fields_descriptions = {}

        # FROM config("classification"), see on_project_data
        self.classifications = []

        # Creates the samples loading thread
        self._load_samples_thread = SqlThread(self.conn)

        # Connect samples loading thread's signals (started, finished, error, result ready)
        self._load_samples_thread.started.connect(lambda: self.samples_are_loading.emit(True))
        self._load_samples_thread.finished.connect(lambda: self.samples_are_loading.emit(False))
        self._load_samples_thread.result_ready.connect(self.on_samples_loaded)
        self._load_samples_thread.error.connect(self.error_raised)

        self._user_has_interrupt = False

    def rowCount(self, parent: QModelIndex = QModelIndex()) -> int:
        """override"""
        if parent == QModelIndex():
            return len(self._genotypes)
        else:
            return 0

    def columnCount(self, parent: QModelIndex = QModelIndex()) -> int:
        """override"""
        if parent == QModelIndex():
            return len(self._headers)
        else:
            return 0

    def get_genotype(self, row: int) -> dict:
        return self._genotypes[row]

    def get_samples(self) -> typing.List[str]:
        return self._samples

    def set_samples(self, samples: typing.List[str]):
        self._samples = list(set(samples))

    def get_fields(self) -> typing.List[str]:
        return self._fields

    def set_fields(self, fields: typing.List[str]):
        self._fields = list(set(fields))

    def set_variant_id(self, variant_id: int):
        self._variant_id = variant_id

    def get_variant_id(self) -> int:
        return self._variant_id

    def data(self, index: QModelIndex, role: Qt.ItemDataRole) -> typing.Any:
        """override"""
        if not index.isValid():
            return None

        item = self._genotypes[index.row()]
        key = self._headers[index.column()]

        if role == Qt.DisplayRole:
            return item[key] or "NULL"

        if role == Qt.ToolTipRole:
            return self.get_tooltip(index.row())

    def get_tooltip(self, row: int):
        """Return all samples info as a formatted text"""

        return toolTip.genotype_tooltip(data=self.get_genotype(row), conn=self.conn)

    def headerData(self, section: int, orientation: Qt.Orientation, role: int):

        if orientation == Qt.Horizontal and role == Qt.DisplayRole:
            if section < len(self._headers):
                return self._headers[section]

        # vertical header
        if role == Qt.ToolTipRole and orientation == Qt.Vertical:
            genotype = self.get_genotype(section)
            genotype_tooltip = toolTip.genotype_tooltip(data=genotype, conn=self.conn)
            return genotype_tooltip

        return None

    def on_samples_loaded(self):

        self.beginResetModel()

        self._genotypes = self._load_samples_thread.results

        if len(self._genotypes) > 0:
            self._headers = [
                i for i in self._genotypes[0].keys() if i not in ("sample_id", "variant_id")
            ]

        if "classification" not in self._fields:
            self._headers.remove("classification")

        self.endResetModel()

        self._end_timer = time.perf_counter()
        self.elapsed_time = self._end_timer - self._start_timer
        self.load_finished.emit()

    def load(self):
        """Start async queries to get sample fields for the selected variant

        Called by:
            - on_change_query() from the view.
            - sort() and setPage() by the model.

        See Also:
            :meth:`on_samples_loaded`
        """
        if self.conn is None:
            return

        if not self.get_samples():
            self.clear()
            return

        if self.is_running():
            LOGGER.debug("Cannot load data. Thread is not finished. You can call interrupt() ")
            self.interrupt()

        # mandatory field

        # Create load_func to run asynchronously: load samples

        used_fields = copy.deepcopy(self.get_fields()) or ["gt"]
        if "classification" not in used_fields:
            used_fields.append("classification")

        load_samples_func = partial(
            sql.get_genotypes,
            variant_id=self.get_variant_id(),
            fields=used_fields,
            samples=self.get_samples(),
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
        self._load_samples_thread.start_function(lambda conn: list(load_samples_func(conn)))

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

        self._genotypes = sorted(
            self._genotypes,
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

    def edit(self, rows: list, data: dict):
        """Edit current item
        Args:
            row (int): Description
            data (dict): Description
        """

        # change from memory
        rows = sorted(rows, reverse=True)
        for row in rows:

            self._genotypes[row].update(data)

            new_data = copy.deepcopy(self._genotypes[row])
            del new_data["name"]

            sql.update_genotypes(self.conn, new_data)
            self.dataChanged.emit(self.index(row, 0), self.index(row, self.columnCount()))
            self.headerDataChanged.emit(Qt.Vertical, row, row)

    def clear(self):

        self.beginResetModel()
        self._genotypes.clear()
        self.endResetModel()
        self.load_finished.emit()


# class SamplesView(QTableView):
#     def __init__(self, parent=None):
#         super().__init__(parent)

#         self.delegate = FormatterDelegate()
#         self.delegate.set_formatter(CutestyleFormatter())

#         # self.setItemDelegate(self.delegate)


class GenotypesWidget(plugin.PluginWidget):
    """Widget displaying the list of avaible selections.
    User can select one of them to update Query::selection
    """

    ENABLE = True
    REFRESH_STATE_DATA = {"current_variant", "samples"}

    def __init__(self, parent=None, conn=None):
        """
        Args:
            parent (QWidget)
            conn (sqlite3.connexion): sqlite3 connexion
        """
        super().__init__(parent)

        self.toolbar = QToolBar()
        self.toolbar.setIconSize(QSize(16, 16))
        self.delegate = FormatterDelegate()
        self.delegate.set_formatter(CutestyleFormatter())
        self.model = GenotypeModel()
        self.view = QTableView()
        self.view.setShowGrid(False)
        self.view.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.view.setSortingEnabled(True)
        self.view.setIconSize(QSize(16, 16))
        self.view.horizontalHeader().setHighlightSections(False)
        self.view.setModel(self.model)

        self.view.setVerticalHeader(GenotypeVerticalHeader())
        self.view.verticalHeader().setSectionsClickable(True)
        self.view.verticalHeader().sectionDoubleClicked.connect(self._on_double_clicked_vertical_header)

        self.view.setItemDelegate(self.delegate)

        self.add_sample_button = QPushButton(self.tr("Add samples ..."))
        self.add_sample_button.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)

        empty_widget = QFrame()
        empty_widget.setFrameStyle(QFrame.StyledPanel | QFrame.Plain)
        empty_widget.setBackgroundRole(QPalette.Base)
        empty_widget.setAutoFillBackground(True)
        empty_layout = QVBoxLayout(empty_widget)
        empty_layout.setAlignment(Qt.AlignCenter)

        empty_layout.addWidget(QLabel("Add samples to display genotypes ..."))

        self.label = QLabel()
        self.label.setFrameStyle(QFrame.StyledPanel | QFrame.Raised)
        self.label.setAlignment(Qt.AlignCenter)
        self.label.setMinimumHeight(30)

        font = QFont()
        font.setBold(True)
        self.label.setFont(font)

        self.error_label = QLabel()
        self.error_label.hide()
        self.error_label.setStyleSheet(
            "QWidget{{background-color:'{}'; color:'{}'}}".format("orange", "black")
        )

        self.setWindowIcon(FIcon(0xF0AA1))

        self.stack_layout = QStackedLayout()
        self.stack_layout.addWidget(empty_widget)
        self.stack_layout.addWidget(self.view)

        vlayout = QVBoxLayout()
        vlayout.setContentsMargins(0, 0, 0, 0)
        vlayout.addWidget(self.toolbar)
        vlayout.addLayout(self.stack_layout)
        vlayout.addWidget(self.error_label)
        vlayout.addWidget(self.label)
        vlayout.setSpacing(0)
        self.setLayout(vlayout)

        self.view.doubleClicked.connect(self._on_double_clicked)
        self.model.error_raised.connect(self.show_error)
        self.model.load_finished.connect(self.on_load_finished)
        self.model.modelReset.connect(self.on_model_reset)
        self.setup_actions()

    def on_model_reset(self):
        if self.model.rowCount() > 0:
            self.stack_layout.setCurrentIndex(1)
            self.view.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeToContents)
            self.view.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        else:
            self.stack_layout.setCurrentIndex(0)

        # self.view.horizontalHeader().setSectionResizeMode(QHeaderView.AdjustToContents)

    def setup_actions(self):

        # Fields to display
        # field_action = create_widget_action(self.toolbar, self.field_selector)
        # field_action.setIcon(FIcon(0xF0756))
        # field_action.setText("Fields")
        # field_action.setToolTip("Select fields to display")
        # Spacer

        self.fields_button = ChoiceButton()
        self.fields_button.prefix = "Fields"
        self.fields_button.empty_message = "gt"
        self.fields_button.setFixedWidth(100)
        self.fields_button.item_changed.connect(self.on_refresh)
        self.toolbar.addWidget(self.fields_button)

        self.toolbar.addAction(QIcon(), "Clear Fields", self.fields_button.uncheck_all)

        spacer = QWidget()
        spacer.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.toolbar.addWidget(spacer)

        # Presets list
        self.preset_menu = QMenu()
        self.preset_button = QPushButton()
        self.preset_button.setToolTip(self.tr("Presets"))
        self.preset_button.setIcon(FIcon(0xF035C))
        self.preset_button.setMenu(self.preset_menu)
        self.preset_button.setFlat(True)
        self.toolbar.addWidget(self.preset_button)

        self.load_presets()

    def load_presets(self):

        self.preset_menu.clear()

        config = Config("samples")

        self.preset_menu.addAction("Save preset", self.save_preset)
        self.preset_menu.addSeparator()

        if "presets" in config:
            presets = config["presets"]
            for name, fields in presets.items():
                action = PresetAction(name, name, self)
                action.set_close_icon(FIcon(0xF05E8, "red"))
                action.triggered.connect(self._on_select_preset)
                action.removed.connect(self.delete_preset)

                self.preset_menu.addAction(action)

        self.preset_menu.addSeparator()
        self.preset_menu.addAction("Reload presets", self.load_presets)

    def delete_preset(self):
        if not self.sender():
            return

        name = self.sender().data()

        ret = QMessageBox.warning(
            self,
            self.tr("Remove preset"),
            self.tr(f"Are you sure you want to delete preset {name}"),
            QMessageBox.Yes | QMessageBox.No,
        )

        if ret == QMessageBox.No:
            return

        config = Config("samples")
        presets = config["presets"]
        if name in presets:
            del presets[name]
            config.save()
            self.load_presets()

    def save_preset(self):
        name, success = QInputDialog.getText(
            self, self.tr("Create new preset"), self.tr("Preset name:")
        )

        if success and name:
            config = Config("samples")
            presets = config["presets"] or {}
            # if preset name exists ...
            if name in presets:
                ret = QMessageBox.warning(
                    self,
                    self.tr("Overwrite preset"),
                    self.tr(f"Preset {name} already exists. Do you want to overwrite it ?"),
                    QMessageBox.Yes | QMessageBox.No,
                )

                if ret == QMessageBox.No:
                    return

            presets[name] = self.model._fields
            config["presets"] = presets

            config.save()

        self.load_presets()

    def _on_select_preset(self):
        config = Config("samples")
        presets = config["presets"]
        key = self.sender().data()
        if key in presets:
            self.fields_button.set_checked(presets[key])

        self.on_refresh()

    def _on_double_clicked(self):
        self._show_sample_variant_dialog()

    def _on_double_clicked_vertical_header(self):
        self._show_sample_variant_dialog()

    def contextMenuEvent(self, event: QContextMenuEvent):

        row = self.view.selectionModel().currentIndex().row()

        genotype = self.model.get_genotype(row)

        menu = QMenu(self)

        # Add section Sample
        sample_name = genotype.get("name", "unknown")

        # Add section Variant
        variant_id = genotype.get("variant_id", 0)
        variant_name = cm.find_variant_name(conn=self.conn, variant_id=variant_id, troncate=True)

        # Validation
        if genotype["sample_id"] and genotype["variant_id"]:

            # find sample lock/unlock
            if self.is_locked(genotype.get("sample_id", 0)):
                validation_menu_enable = False
                validation_menu_title = "Classification (locked)"
                tags_menu_title = "Tags (locked)"
            else:
                validation_menu_enable = True
                validation_menu_title = "Classification"
                tags_menu_title = "Tags"

            menu.addAction(
                FIcon(0xF064F),
                f"Edit Genotype '{sample_name}' - '{variant_name}'",
                self._show_sample_variant_dialog,
            )

            # Classification menu
            cat_menu = menu.addMenu(validation_menu_title)
            cat_menu.setEnabled(validation_menu_enable)

            for item in self.model.classifications:

                if genotype["classification"] == item["number"]:
                    icon = 0xF0133
                    # cat_menu.setIcon(FIcon(icon, item["color"]))
                else:
                    icon = 0xF012F

                action = cat_menu.addAction(FIcon(icon, item["color"]), item["name"])
                action.setData(item["number"])
                action.triggered.connect(self._on_classification_changed)

            # tags menu
            tags_menu = menu.addMenu(tags_menu_title)
            tags_menu.setEnabled(validation_menu_enable)

            tags_preset = Config("tags")

            for item in tags_preset.get("genotypes",[]):

                icon = 0xF04F9

                action = tags_menu.addAction(FIcon(icon, item["color"]), item["name"])
                action.setData(item["name"])
                on_click = functools.partial(self._on_tags_changed, [item["name"]])
                action.triggered.connect(on_click)

            menu.exec_(event.globalPos())

    def is_locked(self, sample_id: int):
        """Prevents editing genotype if sample is classified as locked
        A sample is considered locked if its classification has the boolean "lock: true" set in the Config (yml) file.

        Args:
            sample_id (int): sql sample id

        Returns:
            locked (bool) : lock status of sample attached to current genotype
        """
        config_classif = Config("classifications").get("samples", None)
        sample = sql.get_sample(self.conn, sample_id)
        sample_classif = sample.get("classification", None)

        if config_classif == None or sample_classif == None:
            return False

        locked = False
        for config in config_classif:
            if config["number"] == sample_classif and "lock" in config:
                if config["lock"] == True:
                    locked = True
        return locked

    def _show_sample_dialog(self):

        row = self.view.selectionModel().currentIndex().row()
        sample = self.model.get_genotype(row)
        if sample:

            dialog = SampleDialog(self.conn, sample["sample_id"])

            if dialog.exec_() == QDialog.Accepted:
                # self.load_all_filters()
                self.on_refresh()

    def _show_sample_variant_dialog(self):

        row = self.view.selectionModel().currentIndex().row()
        sample = self.model.get_genotype(row)

        sample_name = sample.get("name", "unknown")
        sample_id = sample.get("sample_id", None)
        variant_id = sample.get("variant_id", None)

        if sample and sample_id is not None and variant_id is not None:

            dialog = SampleVariantDialog(self.conn, sample["sample_id"], self.current_variant["id"])

            if dialog.exec_() == QDialog.Accepted:
                # self.load_all_filters()
                self.on_refresh()

        else:
            QMessageBox.information(
                self, "No genotype", self.tr(f"Sample '{sample_name}' does not have genotype for this variant")
            )


    def _toggle_column(self, col: int, show: bool):
        """hide/show columns"""
        if show:
            self.view.showColumn(col)
        else:
            self.view.hideColumn(col)

    def _on_classification_changed(self):
        """triggered from menu"""
        if not self.sender():
            return

        value = self.sender().data()
        text = self.sender().text()

        rows = [i.row() for i in self.view.selectionModel().selectedRows()]
        self.model.edit(rows, {"classification": value})

        if "samples" in self.mainwindow.plugins:
            self.mainwindow.refresh_plugin("samples")

    def _on_tags_changed(self, tags: list = []):
        """triggered from menu"""

        for index in self.view.selectionModel().selectedRows():
            
            # current variant sample
            row = index.row()
            genotype = self.model.get_genotype(row)
            genotype_variant_id = genotype["variant_id"]
            genotype_sample_name = genotype["name"]

            # current variant tags
            current_genotype = next(sql.get_genotypes(
                    self.conn,
                    genotype_variant_id,
                    ["tags"],
                    [genotype_sample_name],
                ))
            current_tags_text = current_genotype.get("tags", None)
            if current_tags_text:
                current_tags = current_tags_text.split(cst.HAS_OPERATOR)
            else:
                current_tags = []

            # append tags
            for tag in tags:
                current_tags.append(tag) if tag not in current_tags else current_tags

            # update tags
            self.model.edit([row], {"tags": cst.HAS_OPERATOR.join(current_tags)})

    def _on_clear_filters(self):

        self.on_refresh()

    def _create_filters(self, copy_existing_filters: bool = True) -> dict:
        """
        The function creates a dictionary of filters based on a list of filters and existing filters (or not)

        Args:
            copy_existing_filters (bool, optional)

        Returns:
            dict: A dictionary of filters
        """

        indexes = self.view.selectionModel().selectedRows()
        if copy_existing_filters:
            filters = copy.deepcopy(self.mainwindow.get_state_data("filters"))
        else:
            filters = {}

        if not filters:
            root = "$or"
            filters["$or"] = []

        else:
            root = list(filters.keys())[0]
            filters[root] = [
                i for i in filters[root] if not list(i.keys())[0].startswith("samples")
            ]

        for index in indexes:
            # sample_name = index.siblingAtColumn(1).data()
            sample_name = index.siblingAtColumn(0).data()
            if sample_name:
                key = f"samples.{sample_name}.gt"
                condition = {key: {"$gte": 1}}
                filters[root].append(condition)

        return filters

    def on_add_source(self):
        """
        This function is called when the user clicks on the "Add Source" button in the "Source" tab
        """

        name, success = QInputDialog.getText(
            self, self.tr("Source Name"), self.tr("Get a source name ")
        )

        # if not name:
        #     return

        if success and name:

            sql.insert_selection_from_source(
                self.conn, name, "variants", self._create_filters(False)
            )

            if "source_editor" in self.mainwindow.plugins:
                self.mainwindow.refresh_plugin("source_editor")

        else:

            return

    def on_add_filter(self):
        """
        This function is called when the user clicks on the "Add Filter" button
        """

        self.mainwindow.set_state_data("filters", self._create_filters())
        self.mainwindow.refresh_plugins(sender=self)

    def on_open_project(self, conn):
        self.conn = conn
        self.model.conn = conn
        self.model.clear()
        self.load_all_filters()

        config = Config("classifications")
        self.model.classifications = config.get("genotypes", [])

    def _is_selectors_checked(self):
        """Return False if selectors is not checked"""

        return (
            self.sample_selector.checked()
            or self.family_selector.checked()
            or self.tag_selector.checked()
        )

    def load_all_filters(self):
        self.load_fields()

    def load_samples(self):

        self.sample_selector.clear()
        for sample in sql.get_samples(self.conn):
            self.sample_selector.add_item(FIcon(0xF0B55), sample["name"], data=sample["name"])

    def load_fields(self):
        self.fields_button.clear()
        for field in sql.get_field_by_category(self.conn, "samples"):
            self.fields_button.add_item(
                FIcon(0xF0835),
                field["name"],
                field["description"],
                data=field["name"],
            )

    def on_refresh(self):

        # variant id
        self.current_variant = self.mainwindow.get_state_data("current_variant")
        if self.current_variant and "id" in self.current_variant:
            variant_id = self.current_variant["id"]
        else:
            variant_id = None

        # variant name
        variant_name = cm.find_variant_name(conn=self.conn, variant_id=variant_id, troncate=True)

        # fields
        fields = self.fields_button.get_checked()

        # samples
        samples = self.mainwindow.get_state_data("samples")

        # Change variant name
        self.label.setText(variant_name)

        self.model.set_fields(fields)
        self.model.set_variant_id(variant_id)
        self.model.set_samples(samples)
        self.model.load()

        # self.view.horizontalHeader().setSectionResizeMode(
        #     0, QHeaderView.ResizeToContents
        # )
        # self.view.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeToContents)
        # self.view.horizontalHeader().setSectionResizeMode(0, QHeaderView.Minimum)
        # self.view.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)

    def on_close_project(self):
        self.model.clear()

    def show_error(self, message):
        self.error_label.setText(message)
        self.error_label.setVisible(bool(message))

    def on_load_finished(self):
        self.show_error("")


# self.view.horizontalHeader().setSectionResizeMode(
#     0, QHeaderView.ResizeToContents
# )
# self.view.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)


if __name__ == "__main__":

    import sqlite3
    import sys
    from PySide6.QtWidgets import QApplication

    app = QApplication(sys.argv)

    conn = sqlite3.connect("/home/sacha/test3.db")
    # conn = sqlite3.connect("C:/Users/Ichtyornis/Projects/cutevariant/test2.db")
    conn.row_factory = sqlite3.Row

    view = GenotypesWidget()
    view.on_open_project(conn)
    view.show()

    app.exec()
