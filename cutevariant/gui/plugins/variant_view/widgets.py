# Standard imports
import functools
import math
import csv
import io
import re
import sqlite3
import time
import datetime
from collections import defaultdict
import copy
import sys
import string
import urllib.request  # STRANGE: CANNOT IMPORT URLLIB ALONE
from logging import DEBUG, Logger
import typing
import jinja2
import getpass

# dependency
import cachetools

# Qt imports
from PySide6.QtWidgets import *
from PySide6.QtCore import *
from PySide6.QtGui import *
from cutevariant.core import querybuilder

# Custom imports
from cutevariant.core.querybuilder import build_sql_query
from cutevariant.core import sql
from cutevariant.core import command as cmd

from cutevariant.gui import mainwindow, plugin, FIcon, formatter, style
from cutevariant.gui.formatters.cutestyle import CutestyleFormatter
from cutevariant.gui.widgets import GroupbyDialog
from cutevariant.gui.sql_thread import SqlThread
from cutevariant.gui.widgets import (
    MarkdownDialog,
    VariantDialog,
    FilterDialog,
    SampleVariantDialog,
)

from cutevariant.config import Config
from cutevariant import LOGGER
import cutevariant.constants as cst
import cutevariant.commons as cm
from cutevariant.core.querybuilder import filters_to_flat

from cutevariant.gui import tooltip as toolTip


class VariantVerticalHeader(QHeaderView):
    def __init__(self, parent=None):
        super().__init__(Qt.Vertical, parent)

    def sizeHint(self):
        return QSize(30, super().sizeHint().height())

    def paintSection(self, painter: QPainter, rect: QRect, section: int):

        if painter is None:
            return

        painter.save()
        super().paintSection(painter, rect, section)

        try:

            favorite = self.model().variant(section).get("favorite", False)
            number = self.model().variant(section).get("classification", 0)

            painter.restore()

            classification = next(i for i in self.model().classifications if i["number"] == number)

            color = classification.get("color")
            icon = 0xF0130

            icon_favorite = 0xF0133

            pen = QPen(QColor(classification.get("color")))
            pen.setWidth(6)
            painter.setPen(pen)
            painter.setBrush(QBrush(classification.get("color")))
            painter.drawLine(rect.left(), rect.top() + 1, rect.left(), rect.bottom() - 1)

            target = QRect(0, 0, 20, 20)
            pix = FIcon(icon_favorite if favorite else icon, color).pixmap(target.size())
            target.moveCenter(rect.center() + QPoint(1, 1))

            painter.drawPixmap(target, pix)

        except Exception as e:
            LOGGER.debug("Cannot draw classification: " + str(e))


class VariantModel(QAbstractTableModel):
    """VariantModel is a Qt model class which contains variant data from SQL DB.

    It loads paginated data and create an interface for Qt views and controllers.
    The model can group variants by (chr,pos,ref,alt).

    See Qt model/view programming for more information
    https://doc.qt.io/qt-5/model-view-programming.html

    Variants are stored internally as a list of variants.
    By default, there is only one variant per row until a user selects a field
    from annotations or from multiple samples.
    Duplicated variants will be displayed in this case. It is advised to use the
    button "group" in the GUI to easily split between specific fields and common
    fields.

    Signals:
        variant_loaded(bool): Emit when variant are loaded
        count_loaded(bool): Emit when total count are loaded
        error_raised(str): Emit message when threads or something else encounter errors
    """

    # emit when variant results is loaded
    variant_loaded = Signal()
    variant_is_loading = Signal(bool)

    # emit when toutal count is loaded
    count_loaded = Signal()
    count_is_loading = Signal(bool)

    # Emit when all load has started
    load_started = Signal()

    # Emit when all data ( count + variant) has finished
    load_finished = Signal()

    error_raised = Signal(str)
    interrupted = Signal()

    sort_changed = Signal(str, bool)

    def __init__(self, conn=None, parent=None):
        super().__init__()
        self.limit = 50
        self.memory_cache = 32
        self.page = 1  #
        self.total = 0
        self.variants = []
        self.headers = []

        self.classifications = []

        # Cache all database fields and their descriptions for tooltips
        # Field names as keys, descriptions as values
        self.fields_descriptions = None

        self.fields = ["chr", "pos", "ref", "alt", "ann.gene"]
        self._extra_fields = ["classification", "favorite"]

        self.filters = dict()
        self.source = "variants"
        self.group_by = []
        self.having = {}
        self.order_by = []
        self.formatter = None
        self.debug_sql = None
        # Keep after all initialization
        self.conn = conn

        self.mutex = QMutex()

        # Thread (1 for getting variant, 1 for getting count variant )
        self._load_variant_thread = SqlThread(self.conn)
        self._load_count_thread = SqlThread(self.conn)

        self._load_variant_thread.started.connect(lambda: self.variant_is_loading.emit(True))
        self._load_variant_thread.finished.connect(lambda: self.variant_is_loading.emit(False))
        self._load_variant_thread.result_ready.connect(self.on_variant_loaded)
        self._load_variant_thread.error.connect(self.error_raised)

        self._load_count_thread.started.connect(lambda: self.count_is_loading.emit(True))
        self._load_count_thread.finished.connect(lambda: self.count_is_loading.emit(False))
        self._load_count_thread.result_ready.connect(self.on_count_loaded)

        self._finished_thread_count = 0
        self._user_has_interrupt = False

        # Create results cache because Thread doesn't use the memoization cache from command.py.
        # This is because Thread create a new connection and change the function signature used by the cache.
        self.set_cache(32)

    @property
    def conn(self):
        """Return sqlite connection"""
        return self._conn

    @conn.setter
    def conn(self, conn):
        """Set sqlite connection"""
        self._conn = conn
        if conn:
            # Note: model is initialized with None connection during start
            # Cache DB fields descriptions
            self.fields_descriptions = {}
            for field in sql.get_fields(self.conn):
                key = field["name"]
                desc = field["description"]

                if field["category"] == "annotations":
                    key = "ann." + key

                if field["category"] == "samples":
                    key = "samples." + key

                self.fields_descriptions[key] = desc

            LOGGER.debug("Init async thread")

            # Clear cache with new connection
            self.clear_all_cache()

            # Init Runnables (1 for each query type)
            self._load_variant_thread.conn = conn
            self._load_count_thread.conn = conn

            # self._load_count_thread.error.connect(self._on_error)

    def rowCount(self, parent=QModelIndex()):
        """Overrided : Return children count of index"""
        # If parent is root
        if parent == QModelIndex():
            return len(self.variants)
        else:
            return 0

    def columnCount(self, parent=QModelIndex()):
        """Overrided: Return column count of parent .

        Parent is not used here
        """

        #  Check integrity for unit test
        if parent == QModelIndex():
            return len(self.headers)
        return 0

    def clear_all_cache(self):
        """clear cache"""
        self.clear_count_cache()
        self.clear_variant_cache()

    def clear_variant_cache(self):
        self._load_variant_cache.clear()

    def clear_count_cache(self):
        self._load_count_cache.clear()

    def set_cache(self, cachesize=32):

        if hasattr(self, "_load_variant_cache"):
            self._load_variant_cache.clear()

        if hasattr(self, "_load_count_cache"):
            self._load_count_cache.clear()

        self._load_variant_cache = cachetools.LFUCache(
            maxsize=cachesize * 1_048_576, getsizeof=sys.getsizeof
        )
        self._load_count_cache = cachetools.LFUCache(maxsize=1000)

    def cache_size(self):
        """Return total cache size"""
        return self._load_variant_cache.currsize

    def max_cache_size(self):
        return self._load_variant_cache.maxsize

    def clear(self):
        """Reset the current model

        - clear variants list
        - total of variants is set to 0
        - emit variant_loaded signal
        """
        self.beginResetModel()
        self.variants.clear()
        self.total = 0
        self.endResetModel()
        self.variant_loaded.emit()

    def data(self, index: QModelIndex, role=Qt.DisplayRole):
        """Overrided: return index data according role.
        This method is called by the Qt view to get data to display according Qt role.

        Params:
            index (QModelIndex): index from where your want to get data
            role (Qt.ItemDataRole): https://doc.qt.io/qt-5/qt.html#ItemDataRole-enum

        Examples:
            index = model.index(row=10, column = 1)
            chromosome_value = model.data(index)
        """

        # Avoid error
        if not index.isValid():
            return

        if self.variants and self.headers:

            column_name = self.headers[index.column()]

            # ---- Display Role ----
            if role == Qt.DisplayRole:
                value = self.variant(index.row())[column_name]
                if value is None:
                    return "NULL"
                else:
                    return str(self.variant(index.row())[column_name])

            if role == Qt.ToolTipRole:
                value = str(self.variant(index.row())[column_name])
                return value

            if role == Qt.DecorationRole:
                if column_name == "tags":
                    return QColor("red")

            if role == Qt.BackgroundRole:
                class_number = self.variant(index.row())["classification"]
                if class_number > 0:
                    classification = self.classification_to_name(class_number)
                    col = QColor(classification.get("color", "lightgray"))
                    col.setAlpha(50)
                    brush = QBrush(col)
                    return brush

        return None

    def classification_to_name(self, number: int):
        return next(i for i in self.classifications if i["number"] == number)

    def headerData(self, section, orientation=Qt.Horizontal, role=Qt.DisplayRole):
        """Overrided: Return column name and display tooltips on headers

        This method is called by the Qt view to display vertical or horizontal header data.

        Params:
            section (int): row or column number depending on orientation
            orientation (Qt.Orientation): Qt.Vertical or Qt.Horizontal
            role (Qt.ItemDataRole): https://doc.qt.io/qt-5/qt.html#ItemDataRole-enum

        Examples:
            # return 4th column name
            column_name = model.headerData(4, Qt.Horizontal)

        Warnings:
            Return nothing if orientation is != from Qt.Horizontal,
            and role != Qt.DisplayRole
        """
        # Display columns headers

        if orientation == Qt.Horizontal:
            if role == Qt.DisplayRole:
                return self.headers[section]

            if role == Qt.ToolTipRole:
                # Field descriptions on headers
                # Note: fields are set in load()
                if self.fields_descriptions:
                    field_name = self.fields[section]

                    if field_name.startswith("samples."):
                        # Remove sample name to get descriptionield_name.split(".")
                        k = field_name.split(".")
                        field_name = k[0] + "." + k[2]

                    return self.fields_descriptions.get(field_name)

            if role == Qt.SizeHintRole:
                return QSize(0, 20)

        if orientation == Qt.Horizontal:
            field_name = self.fields[section]
            flattened_filters = filters_to_flat(self.filters)
            col_filtered = any(field_name in f for f in flattened_filters)
            if role == Qt.DecorationRole:
                return QIcon(FIcon(0xF10E5)) if col_filtered else QIcon(FIcon(0xF0233))
            if role == Qt.FontRole:
                font = QFont()
                font.setBold(col_filtered)
                return font

        # vertical header
        if role == Qt.ToolTipRole and orientation == Qt.Vertical:
            variant = self.variant(section)
            variant = variant | dict(
                sql.get_variant(
                    conn=self.conn,
                    variant_id=variant["id"],
                    with_annotations=True,
                    with_samples=True,
                )
            )
            variant_tooltip = toolTip.variant_tooltip(
                data=variant, conn=self.conn, fields=self.fields
            )
            return variant_tooltip

    def update_variant(self, row: int, variant: dict):
        """Update a variant at the given row with given content

        Update the variant in the GUI AND in the DB.

        Args:
            row (int): Row id of the variant that will be modified
            variant (dict): Dict of fields to be updated
        """
        # Update in database
        # if tuple(self.conn.execute("PRAGMA data_version").fetchone())[0] > 1:
        #     print(tuple(self.conn.execute("PRAGMA data_version").fetchone())[0])
        #     ret = QMessageBox.warning(None, "Database has been modified", "Do you want to overwrite value?", QMessageBox.Yes | QMessageBox.No)
        #     if ret == QMessageBox.No:
        #         return
        variant_id = self.variants[row]["id"]

        # find index
        left = self.index(row, 0)
        right = self.index(row, self.columnCount() - 1)

        editable_fields = ["classification", "favorite", "comment", "tags"]

        # Current data
        sql_variant = {
            k: v for k, v in sql.get_variant(self.conn, variant_id).items() if k in editable_fields
        }

        # SQL data
        model_variant = {k: v for k, v in self.variants[row].items() if k in editable_fields}

        # Is there a difference between model and sql ? Which one ?

        difference = set(model_variant.items()) - set(sql_variant.items())

        if difference:

            diff_fields = ",".join([f"{key}" for key, value in difference])

            box = QMessageBox(None)
            box.setWindowTitle("Database has been modified from another place")
            box.setText(
                f"The fields <b>{diff_fields}</b> have been modified from another place.\nDo you want to overwrite value?"
            )
            box.setStandardButtons(QMessageBox.Yes | QMessageBox.No)
            box.setDetailedText(f"{variant=}\n{sql_variant=} \n {model_variant}")
            box.setIcon(QMessageBox.Warning)

            if box.exec_() == QMessageBox.No:

                return

        # Update all variant with same variant_id
        # Use case : When several transcript are displayed
        for row in self.find_row_id_from_variant_id(variant_id):

            if left.isValid() and right.isValid():
                # Get database id of the variant to allow its update operation
                variant["id"] = self.variants[row]["id"]
                sql.update_variant(self.conn, variant)
                self.variants[row].update(variant)
                self.dataChanged.emit(left, right)
                self.headerDataChanged.emit(Qt.Vertical, left, right)

        # Log modification

        with open("user.log", "a") as file:

            username = getpass.getuser()
            timestamp = str(datetime.datetime.now())
            del variant["id"]

            file.write(
                f"{username} updated {', '.join(variant.keys())} for {variant_id=} with {', '.join(str(v) for v in variant.values())} at {timestamp} \n"
            )

    def find_row_id_from_variant_id(self, variant_id: int) -> list:
        """Find the ids of all rows with the same given variant_id

        Args:
            variant_id (int): Variant sql record id
        Returns:
            (list[int]): ids of rows
        """
        return [
            row_id for row_id, variant in enumerate(self.variants) if variant["id"] == variant_id
        ]

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

        if self._load_count_thread:
            if self._load_count_thread.isRunning():
                self._user_has_interrupt = True
                self._load_count_thread.interrupt()
                self._load_count_thread.wait(1000)
                interrupted = True

        if self._load_variant_thread:
            if self._load_variant_thread.isRunning():
                self._user_has_interrupt = True
                self._load_variant_thread.interrupt()
                self._load_variant_thread.wait(1000)
                interrupted = True

        if interrupted:
            self.interrupted.emit()

        # # Wait for exception ...
        # if loop:
        #     self.error_raised.connect(loop.quit)
        #     loop.exec_()

    def is_running(self):
        if self._load_variant_thread and self._load_count_thread:
            return self._load_variant_thread.isRunning() or self._load_count_thread.isRunning()

        return False

    def load(self):
        """Start async queries to get variants and variant count

        Called by:
            - on_change_query() from the view.
            - sort() and setPage() by the model.

        See Also:
            :meth:`loaded`
        """
        if self.conn is None:
            return

        if self.is_running():
            LOGGER.debug("Cannot load data. Thread is not finished. You can call interrupt() ")
            return

        LOGGER.debug("Start loading")
        self.mutex.lock()
        offset = (self.page - 1) * self.limit

        # Add fields from group by
        # self.clear()  # Assume variant = []
        self.total = 0
        self._finished_thread_count = 0
        # LOGGER.debug("Page queried: %s", self.page)

        query_fields = set(self.fields + self._extra_fields)

        # Store SQL query for debugging purpose
        self.debug_sql = build_sql_query(
            self.conn,
            fields=query_fields,
            source=self.source,
            filters=self.filters,
            limit=self.limit,
            offset=offset,
            order_by=self.order_by,
        )

        LOGGER.debug(self.debug_sql)
        # Create load_func to run asynchronously: load variants
        load_func = functools.partial(
            cmd.select_cmd,
            fields=query_fields,
            source=self.source,
            filters=self.filters,
            limit=self.limit,
            offset=offset,
            order_by=self.order_by,
        )

        # Create count_func to run asynchronously: count variants
        count_function = functools.partial(
            cmd.count_cmd,
            fields=query_fields,
            source=self.source,
            filters=self.filters,
        )

        # Start the run
        self._start_timer = time.perf_counter()

        # Create function HASH for CACHE
        self._count_hash = hash(count_function.func.__name__ + str(count_function.keywords))
        self._variant_hash = hash(load_func.func.__name__ + str(load_func.keywords))

        self.load_started.emit()

        # Launch the first thread "count" or by pass it using the cache
        if self._count_hash in self._load_count_cache:
            self._load_count_thread.results = self._load_count_cache[self._count_hash]
            self.on_count_loaded()
        else:
            self._load_count_thread.start_function(count_function)

        # Launch the second thread "count" or by pass it using the cache
        if self._variant_hash in self._load_variant_cache:
            self._load_variant_thread.results = self._load_variant_cache[self._variant_hash]
            self.on_variant_loaded()

        else:
            self._load_variant_thread.start_function(lambda conn: list(load_func(conn)))

        self.mutex.unlock()

    def on_variant_loaded(self):
        """
        Triggered when variant_thread is finished

        """

        #  Compute time elapsed since loading

        self.beginResetModel()
        self.variants.clear()

        # Save cache
        self._load_variant_cache[self._variant_hash] = self._load_variant_thread.results.copy()

        # Load variants
        self.variants = self._load_variant_thread.results
        if self.variants:
            # Set headers of the view
            self.headers = list(self.variants[0].keys())
            # Hide extra fields
            self.headers = self.fields

        # self.total = self._load_count_thread.results["count"]

        self.endResetModel()
        self.variant_loaded.emit()

        #  Test if both thread are finished
        self._finished_thread_count += 1
        if self._finished_thread_count == 2:
            self._end_timer = time.perf_counter()
            self.elapsed_time = self._end_timer - self._start_timer
            self.load_finished.emit()

    def on_count_loaded(self):
        """
        Triggered when count_threaed is finished
        """

        # Save cache
        self._load_count_cache[self._count_hash] = self._load_count_thread.results.copy()

        self.total = self._load_count_thread.results["count"]
        self.count_loaded.emit()

        #  Test if both thread are finished
        self._finished_thread_count += 1
        if self._finished_thread_count == 2:
            self._end_timer = time.perf_counter()
            self.elapsed_time = self._end_timer - self._start_timer
            self.load_finished.emit()

    def hasPage(self, page: int) -> bool:
        """Return True if <page> exists otherwise return False"""
        return (page - 1) >= 0 and (page - 1) * self.limit < self.total

    def setPage(self, page: int):
        """set the page of the model"""
        if self.hasPage(page):
            self.page = page

    def nextPage(self):
        """Set model to the next page"""
        if self.hasPage(self.page + 1):
            self.setPage(self.page + 1)

    def previousPage(self):
        """Set model to the previous page"""
        if self.hasPage(self.page - 1):
            self.setPage(self.page - 1)

    def firstPage(self):
        """Set model to the first page"""
        self.setPage(1)

    def lastPage(self):
        """Set model to the last page"""

        self.setPage(self.pageCount())

    def pageCount(self):
        """Return total page count"""
        return math.ceil(self.total / self.limit)

    def sort(self, column: int, order):
        """Overrided: Sort data by specified column

        column (int): column id
        order (Qt.SortOrder): Qt.AscendingOrder or Qt.DescendingOrder

        """

        if column < self.columnCount():
            field = self.fields[column]

            ascending = True if order == Qt.AscendingOrder else False

            # remove if already in
            new_order_by = [(field, ascending)]
            self.order_by = new_order_by

            self.load()

    def variant(self, row: int) -> dict:
        """Return variant data according index"""
        return self.variants[row]

    def is_variant_loading(self):
        if self._load_variant_thread:
            return self._load_variant_thread.isRunning()
        else:
            return False

    def is_count_loading(self):
        if self._load_count_thread:
            return self._load_count_thread.isRunning()
        else:
            return False

    def removeColumn(self, column: int, parent: QModelIndex = QModelIndex()) -> bool:
        self.beginRemoveColumns(parent, column, column)
        self.fields = self.fields[:column] + self.fields[column + 1 :]
        self.endRemoveColumns()


class LoadingTableView(QTableView):
    """Movie animation displayed on VariantView for long SQL queries executed
    in background.
    """

    def __init__(self, parent=None):
        super().__init__(parent)

        self._is_loading = False
        self.horizontalHeader().setHighlightSections(False)

    def paintEvent(self, event: QPainter):

        if self.is_loading():
            painter = QPainter(self.viewport())

            painter.drawText(self.viewport().rect(), Qt.AlignCenter, self.tr("Loading ..."))

        else:
            super().paintEvent(event)

    def start_loading(self):
        self._is_loading = True
        self.viewport().update()

    def stop_loading(self):
        self._is_loading = False
        self.viewport().update()

    def is_loading(self):
        return self._is_loading


class VariantView(QWidget):
    """A Variant view with controller like pagination

    Signals:
        error_raised (str): Emit message when async runnables encounter errors
        variant_clicked(QModelIndex): Emit when user clicked on a v ariant
        load_finished : Emit when data is loaded
    """

    error_raised = Signal(str)
    variant_clicked = Signal(QModelIndex)
    load_finished = Signal()

    # Header action
    filter_add = Signal(str)
    filter_remove = Signal(str)
    field_remove = Signal(str)

    # Shortcut plugin action
    fields_btn_clicked = Signal()
    source_btn_clicked = Signal()
    filters_btn_clicked = Signal()

    def __init__(self, parent=None):
        """
        Args:
            parent: parent widget
        """
        super().__init__(parent)

        self.parent = parent  # used to access parent.mainwindow
        self.view = LoadingTableView()

        self.bottom_bar = QToolBar()
        self.top_bar = QToolBar()

        # Log edit
        self.log_edit = QLabel()
        self.log_edit.setMaximumHeight(30)
        self.log_edit.hide()
        self.log_edit.setFrameStyle(QFrame.StyledPanel | QFrame.Raised)
        self.log_edit.setStyleSheet(
            "QWidget{{background-color:'{}'; color:'{}'}}".format("orange", "black")
        )

        # Setup model
        self.model = VariantModel()
        self.delegate = formatter.FormatterDelegate()
        self.delegate.set_formatter(CutestyleFormatter())

        # Setup view
        self.view.setAlternatingRowColors(True)
        self.view.horizontalHeader().setStretchLastSection(True)
        self.view.setSelectionMode(QAbstractItemView.SingleSelection)

        self.view.setVerticalHeader(VariantVerticalHeader())
        self.view.verticalHeader().setSectionsClickable(True)
        self.view.verticalHeader().sectionDoubleClicked.connect(self.on_double_clicked_vertical_header)

        self.view.setSortingEnabled(True)
        self.view.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.view.setSelectionMode(QAbstractItemView.ExtendedSelection)
        self.view.setIconSize(QSize(16, 16))
        self.view.horizontalHeader().setSectionsMovable(True)
        self.view.setModel(self.model)

        self.view.setItemDelegate(self.delegate)
        # setup bottom bar toolbar
        spacer = QWidget()
        spacer.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)

        self.page_box = QLineEdit()
        self.page_box.setValidator(QIntValidator())
        self.page_box.setFixedWidth(50)
        self.page_box.setValidator(QIntValidator())
        self.page_box.setFocusPolicy(Qt.NoFocus)

        # Display nb of variants/groups and pages
        self.info_label = QLabel()
        self.time_label = QLabel()
        self.cache_label = QLabel()
        self.loading_label = QLabel()
        self.loading_label.setMovie(QMovie(cst.DIR_ICONS + "loading.gif"))

        self.top_bar.setToolButtonStyle(Qt.ToolButtonTextBesideIcon)
        self.top_bar.setIconSize(QSize(16, 16))

        self.bottom_bar.addAction(FIcon(0xF0A30), "Show SQL query", self.on_show_sql)
        self.bottom_bar.addAction(FIcon(0xF10A6), "clear all cache", self.on_clear_cache)

        self.bottom_bar.addWidget(self.time_label)
        self.bottom_bar.addWidget(self.cache_label)
        self.bottom_bar.addSeparator()
        self.bottom_bar.setIconSize(QSize(16, 16))
        self.bottom_bar.addWidget(spacer)

        # Add loading action and store action
        self.bottom_bar.addWidget(self.info_label)
        self.bottom_bar.setContentsMargins(0, 0, 0, 0)
        self.loading_action = self.bottom_bar.addWidget(self.loading_label)

        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        main_layout.addWidget(self.top_bar)
        main_layout.addWidget(self.view)
        main_layout.addWidget(self.bottom_bar)
        main_layout.addWidget(self.log_edit)
        self.setLayout(main_layout)

        # Connection
        self.model.variant_loaded.connect(self.on_variant_loaded)
        self.model.count_loaded.connect(self.on_count_loaded)
        self.model.load_finished.connect(self.on_load_finished)
        self.model.count_is_loading.connect(self.set_tool_loading)
        self.model.variant_is_loading.connect(self.set_view_loading)

        # Connect errors from async runnables
        self.model.error_raised.connect(self.set_message)
        self.view.doubleClicked.connect(self.on_double_clicked)
        self.view.selectionModel().currentChanged.connect(self.on_variant_clicked)

        self._setup_actions()

    def _setup_actions(self):
        # ## SETUP TOP BAR
        # -----------Favorite action ----------
        self.favorite_action = QAction(self.tr("Favorite"))
        favicon = QIcon()
        favicon.addPixmap(FIcon(0xF00C3).pixmap(22, 22), QIcon.Normal, QIcon.Off)
        favicon.addPixmap(FIcon(0xF00C0).pixmap(22, 22), QIcon.Normal, QIcon.On)
        self.favorite_action.setIcon(favicon)
        self.favorite_action.setCheckable(True)
        self.favorite_action.toggled.connect(lambda x: self.update_favorites(x))
        self.favorite_action.setShortcut(QKeySequence(Qt.Key_Space))
        self.favorite_action.setShortcutContext(Qt.WidgetWithChildrenShortcut)
        self.favorite_action.setToolTip(
            self.tr(
                "Toggle the selected variant as favorite (%s). The field `favorite` must be selected."
                % self.favorite_action.shortcut().toString()
            )
        )
        self.addAction(self.favorite_action)

        # -----------Comment action ----------
        self.comment_action = QAction(FIcon(0xF0182), self.tr("Comments"))
        self.comment_action.setToolTip(self.tr("Edit comment of selected variant ..."))
        self.comment_action.triggered.connect(
            lambda x: self.edit_comment(self.view.selectionModel().selectedRows()[0])
        )
        self.addAction(self.comment_action)

        self.fields_button = self.top_bar.addAction(FIcon(0xF08DF), "Fields")
        self.fields_button.triggered.connect(self.fields_btn_clicked)
        self.fields_button.setToolTip("Edit Fields ")
        self.source_button = self.top_bar.addAction(FIcon(0xF04EB), "Source")
        self.source_button.triggered.connect(self.source_btn_clicked)
        self.source_button.setToolTip("Edit Source ")
        self.filters_button = self.top_bar.addAction(FIcon(0xF0232), "Filters")
        self.filters_button.triggered.connect(self.filters_btn_clicked)
        self.filters_button.setToolTip("Edit Filters ")

        spacer = QWidget()
        spacer.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.top_bar.addWidget(spacer)

        self.source_label = QLabel("source")
        self.top_bar.addWidget(self.source_label)

        spacer = QWidget()
        spacer.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.top_bar.addWidget(spacer)
        # -----------Resize action ----------

        self.resize_action = self.top_bar.addAction(FIcon(0xF142A), self.tr("Auto resize"))
        self.resize_action.setToolTip(self.tr("Adjust columns size to content"))
        self.resize_action.triggered.connect(self.auto_resize)

        # -----------Refresh action ----------
        self.refresh_action = self.top_bar.addAction(
            FIcon(0xF0450), self.tr("Refresh"), lambda: self.load(reset_page=True)
        )
        self.refresh_action.setToolTip(self.tr("Refresh the current list of variants"))

        # -----------Interrupt action ----------

        self.interrupt_action = self.top_bar.addAction(
            FIcon(0xF04DB), self.tr("Stop"), lambda: self.model.interrupt()
        )
        self.interrupt_action.setToolTip(self.tr("Stop current query"))

        ## SETUP BOTTOM BAR
        # group action to make it easier disabled
        self.pagging_actions = QActionGroup(self)
        # First page action  <<
        action = self.bottom_bar.addAction(FIcon(0xF0600), "<<", self.on_page_clicked)
        action.setShortcut(Qt.CTRL + Qt.Key_Left)
        action.setAutoRepeat(False)
        action.setToolTip(self.tr("First page (%s)" % action.shortcut().toString()))
        self.pagging_actions.addAction(action)

        # Previous page action <
        action = self.bottom_bar.addAction(FIcon(0xF0141), "<", self.on_page_clicked)
        action.setShortcut(QKeySequence(Qt.Key_Left))
        # action.setShortcutContext(Qt.WindowShortcut)
        action.setAutoRepeat(False)
        action.setToolTip(self.tr("Previous page (%s)" % action.shortcut().toString()))
        self.pagging_actions.addAction(action)

        # Add count widget
        self.bottom_bar.addWidget(self.page_box)
        self.page_box.returnPressed.connect(self.on_page_changed)

        # Next page action >
        action = self.bottom_bar.addAction(FIcon(0xF0142), ">", self.on_page_clicked)
        action.setShortcut(QKeySequence(Qt.Key_Right))
        # action.setShortcutContext(Qt.WindowShortcut)
        action.setAutoRepeat(False)
        action.setToolTip(self.tr("Next page (%s)" % action.shortcut().toString()))
        self.pagging_actions.addAction(action)

        # End page action >>
        action = self.bottom_bar.addAction(FIcon(0xF0601), ">>", self.on_page_clicked)
        action.setShortcut(Qt.CTRL + Qt.Key_Right)
        action.setAutoRepeat(False)
        action.setToolTip(self.tr("Last page (%s)" % action.shortcut().toString()))
        self.pagging_actions.addAction(action)

    def auto_resize(self):
        """Resize columns to content"""
        self.view.resizeColumnsToContents()
        self.view.horizontalHeader().setSectionResizeMode(QHeaderView.Interactive)
        self.view.horizontalHeader().setStretchLastSection(True)

    def set_message(self, message: str):
        """Show message error at the bottom of the view

        Args:
            message (str): Error message
        """

        if self.log_edit.isHidden():
            self.log_edit.show()

        icon_64 = FIcon(0xF0027, "black").to_base64(18, 18)

        self.log_edit.setText(
            """<div height=100%>
            <img src="data:image/png;base64,{}" align="left"/>
             <span> {} </span>
            </div>""".format(
                icon_64, message
            )
        )

    def load(self, reset_page: bool = False):
        """Load the view

        If reset_page is set to True, also reset the page to 1

        Args:
            reset_page (bool, optional):
        """
        if reset_page:
            self.model.page = 1
            # self.model.order_by = None

        self.log_edit.hide()
        self.model.interrupt()
        self.model.load()

        self.source_label.setText(self.model.source)

        # display sort indicator
        order_by = self.model.order_by
        if order_by:
            ordered_field = order_by[0][0]
            order = Qt.AscendingOrder if order_by[0][1] else Qt.DescendingOrder
            if ordered_field in self.model.fields:
                index = self.model.fields.index(ordered_field)
                self.view.horizontalHeader().setSortIndicator(index, order)

    def on_variant_loaded(self):
        """Slot called when async queries from the model are finished
        (especially count of variants for page box).

        Signals:
            Emits no_variant signal.
        """
        # if self.row_to_be_selected is not None:
        #     # Left groupby pane only:
        #     # Select by default the first line in order to refresh the
        #     # current variant in the other pane
        #     if self.model.rowCount():
        #         self.select_row(0)
        #     else:
        #         self.no_variant.emit()
        cache = cm.bytes_to_readable(self.model.cache_size())
        max_cache = cm.bytes_to_readable(self.model.max_cache_size())
        self.cache_label.setText(str(" Cache {} of {}".format(cache, max_cache)))

        self.view.scrollToTop()

        #  Select first row
        if self.model.rowCount():
            self.select_row(0)

    def on_count_loaded(self):

        self.page_box.clear()
        if self.model.pageCount() - 1 == 0:
            self.set_pagging_enabled(False)
        else:
            # self.page_box.addItems([str(i) for i in range(self.model.pageCount())])
            self.page_box.validator().setRange(1, self.model.pageCount())
            self.page_box.setText(str(self.model.page))
            self.set_pagging_enabled(True)

        text = self.tr("{} line(s) Page {} on {}")
        text = text.format(self.model.total, self.model.page, self.model.pageCount())
        self.info_label.setText(text)

        #  Set focus to view ! Otherwise it stay on page_box
        self.view.setFocus(Qt.ActiveWindowFocusReason)

    def on_load_finished(self):
        self.time_label.setText(str(" Executed in %.2gs " % (self.model.elapsed_time)))
        self.load_finished.emit()

    def set_formatter(self, formatter_class):

        self.delegate.set_formatter(formatter_class)
        self.view.reset()

    @property
    def conn(self):
        return self.model.conn

    @conn.setter
    def conn(self, _conn):
        self.model.conn = _conn

    @property
    def fields(self):
        return self.model.fields

    @fields.setter
    def fields(self, _fields):
        self.model.fields = _fields

    @property
    def source(self):
        return self.model.source

    @source.setter
    def source(self, _source):
        self.model.source = _source

    @property
    def filters(self):
        return self.model.filters

    @filters.setter
    def filters(self, _filters):
        self.model.filters = _filters

    def on_page_clicked(self):

        action_text = self.sender().text()

        if action_text == "<<":
            fct = self.model.firstPage

        if action_text == ">>":
            fct = self.model.lastPage

        if action_text == "<":
            fct = self.model.previousPage

        if action_text == ">":
            fct = self.model.nextPage

        fct()
        self.load()

    def on_page_changed(self):
        """Slot called when page_box is modified and the user has pressed return key

        The validator is ok if this slot is called.
        """
        if self.page_box.text():
            page = int(self.page_box.text())
            self.model.setPage(page)
            self.load()

    def on_variant_clicked(self, index: QModelIndex):
        variant = self.model.variant(index.row())
        full_variant = sql.get_variant(self.conn, variant["id"])
        self.favorite_action.blockSignals(True)
        self.favorite_action.setChecked(bool(full_variant["favorite"]))
        self.favorite_action.blockSignals(False)

    def on_clear_cache(self):

        self.model.clear_all_cache()
        self.load()

    def on_show_sql(self):
        """Display debug sql query"""
        msg_box = QMessageBox()
        msg_box.setWindowTitle("SQL debug")
        msg_box.setText(self.model.debug_sql)
        explain_query = []
        for rec in self.conn.execute("EXPLAIN QUERY PLAN " + self.model.debug_sql):
            explain_query.append(str(dict(rec)))

        msg_box.setDetailedText("\n".join(explain_query))

        msg_box.exec_()

    def set_pagging_enabled(self, active=True):
        self.page_box.setEnabled(active)
        self.pagging_actions.setEnabled(active)

    def set_view_loading(self, active=True):
        self.view.setDisabled(active)

        def show_loading_if_loading():
            if self.model.is_variant_loading():
                self.view.start_loading()

        if active:
            QTimer.singleShot(2000, show_loading_if_loading)
        else:
            self.view.stop_loading()
            self.view.setFocus(Qt.OtherFocusReason)

    def set_tool_loading(self, active=True):

        if active:
            self.info_label.setText(self.tr("Counting all variants. This can take a while ... "))
            self.loading_action.setVisible(True)
            self.loading_label.movie().start()
        else:
            self.loading_label.movie().stop()
            self.loading_action.setVisible(False)
            # self.info_label.setText("")

        self.bottom_bar.setDisabled(active)

    def set_loading(self, active=True):

        self.set_view_loading(active)
        self.set_tool_loading(active)

    def _get_links(self) -> list:
        """Get links from settings

        Return list of links from QSettings

        Exemples:
            {
            "name":"google",
            "url": "http://www.google.fr/q={}",
            "is_browser": True   # Open with browser
            "is_default": True   # is a default action
            }

        """
        config = Config("variant_view")
        links = config.get("links", [])

        return links

    def _show_variant_dialog(self):

        current_index = self.view.selectionModel().currentIndex()

        if current_index.isValid():
            current_variant = self.model.variant(current_index.row())

            dialog = VariantDialog(self.conn, current_variant["id"])
            if dialog.exec() == QDialog.Accepted:
                self.parent.mainwindow.refresh_plugin("variant_view")
                self.parent.mainwindow.refresh_plugin("sample_view")

    def _show_sample_variant_dialog(self):

        # current index
        index = self.view.currentIndex()

        # find variant_id
        variant_id = None
        current_variant = self.model.variant(index.row())
        variant_id = current_variant["id"]

        # find sample_id
        sample_id = None
        _header_name = self.model.headers[index.column()]
        match = re.findall(r"^samples.(\w+)\.(.*)$", _header_name)
        if match:
            sample_name = match[0][0]
            sample_infos = sql.search_samples(self.conn, name=sample_name)
            for sample_info in sample_infos:
                sample_id = sample_info["id"]

        # validation dialog
        if variant_id and sample_id:
            dialog = SampleVariantDialog(self.conn, sample_id, variant_id)
            if dialog.exec_() == QDialog.Accepted:
                self.on_refresh()

    def _create_header_menu(self, column: int) -> QMenu:
        """Create a menu when clicking on a header"""

        menu = QMenu()
        field = self.model.headerData(column, Qt.Horizontal, Qt.DisplayRole)

        menu.addAction(
            QIcon(FIcon(0xF0EF1)),
            f"Create Filter for {field}",
            functools.partial(lambda x: self.filter_add.emit(x), field),
        )

        menu.addAction(
            QIcon(FIcon(0xF0235)),
            f"Clear all filters for {field}",
            functools.partial(lambda x: self.filter_remove.emit(x), field),
        )

        menu.addAction(
            FIcon(0xF04EE),
            f"Remove columns",
            functools.partial(lambda x: self.field_remove.emit(x), field),
        )

        menu.addAction(
            FIcon(0xF1860),
            self.tr("Show unique values for this column"),
            functools.partial(self.show_unique_values, field),
        )

        return menu

    def _create_variant_menu(self, index: QModelIndex) -> QMenu:
        """Create a menu when clicking on a variant line"""
        menu = QMenu(self)

        current_variant = self.model.variant(index.row())

        # Get variant name
        variant_name = cm.find_variant_name(conn=self.conn, variant_id=current_variant["id"], troncate=True)

        menu.addAction(
            FIcon(0xF064F),
            f"Edit Variant '{variant_name}'",
            self._show_variant_dialog,
        )

        # action menu

        # Classification menu

        menu.addMenu(self.create_classification_menu(index))
        menu.addMenu(self.create_tags_menu(index))
        menu.addMenu(self.create_external_links_menu())

        menu.addAction(self.favorite_action)
        menu.addAction(self.comment_action)

        # Validation menu

        # Find variant id
        variant_id = current_variant["id"]

        # Find sample id
        sample_name = None
        sample_id = None
        sample_valid = None
        header_name = self.model.headers[index.column()]
        header_name_match_sample = re.findall(r"^samples.(\w+)\.(.*)$", header_name)
        if header_name_match_sample:
            sample_name = header_name_match_sample[0][0]
            sample_infos = sql.search_samples(self.conn, name=sample_name)
            for sample_info in sample_infos:
                sample_id = sample_info["id"]
                sample_valid = sample_info["classification"]

        # Menu Validation for sample
        if sample_id and sample_name and variant_id:

            # find genotype
            genotype = sql.get_sample_annotations(self.conn, variant_id, sample_id)

            # find sample lock/unlock
            validation_menu_lock = False
            validation_menu_text = f"Sample {sample_name} Genotype..."

            if self.is_locked(sample_id):
                validation_menu_lock = True
                validation_menu_text = f"Sample {sample_name} locked"

            menu.addSeparator()

            sample_validation_menu = QMenu(self.tr(f"{validation_menu_text}"))
            menu.addMenu(sample_validation_menu)

            sample_validation_menu.setIcon(FIcon(0xF0009))
            sample_validation_menu.addAction(f"Edit Genotype", self._show_sample_variant_dialog)

            if not validation_menu_lock:
                sample_validation_menu.addMenu(self.create_validation_menu(genotype))

            # menu.addMenu(sample_validation_menu)

        # Edit menu
        menu.addSeparator()
        menu.addAction(FIcon(0xF018F), self.tr("&Copy"), self.copy_to_clipboard, QKeySequence.Copy)
        menu.addAction(
            FIcon(0xF018F),
            self.tr("Copy cell value"),
            self.copy_cell_to_clipboard,
        )
        menu.addAction(
            FIcon(0xF0486),
            self.tr("&Select all"),
            self.select_all,
            QKeySequence.SelectAll,
        )

        return menu

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

    def contextMenuEvent(self, event: QContextMenuEvent):
        """Override: Show contextual menu over the current variant"""

        menu = QMenu(self)

        # Menu header
        if self.view.horizontalHeader().underMouse():
            pos = self.view.horizontalHeader().viewport().mapFromGlobal(event.globalPos())
            column = self.view.horizontalHeader().logicalIndexAt(pos)

            menu = self._create_header_menu(column)
            menu.exec_(event.globalPos())

        # Menu Variant
        if self.view.viewport().underMouse():
            pos = self.view.viewport().mapFromGlobal(event.globalPos())
            current_index = self.view.indexAt(pos)
            if not current_index.isValid():
                return

            menu = self._create_variant_menu(current_index)
            menu.exec_(event.globalPos())

    def _open_url(self, url_template: str, in_browser=False):

        config = Config("variant_view")

        batch_open = False

        if "batch_open_links" in config:
            batch_open = bool(config["batch_open_links"])

        # To avoid code repeating, iterate through list, even if it has only one element
        if batch_open:
            indexes = self.view.selectionModel().selectedRows(0)
        else:
            indexes = [self.view.currentIndex().siblingAtColumn(0)]

        for row_index in indexes:

            variant = self.model.variant(row_index.row())
            variant_id = variant["id"]
            full_variant = sql.get_variant(self.conn, variant_id, True, False)

            url = self._create_url(url_template, full_variant)

            if in_browser:
                QDesktopServices.openUrl(url)

            else:
                try:
                    urllib.request.urlopen(url.toString(), timeout=10)
                except Exception as e:
                    LOGGER.error(
                        "Error while trying to access " + url.toString() + "\n%s" * len(e.args),
                        *e.args,
                    )
                    cr = "\n"
                    QMessageBox.critical(
                        self,
                        self.tr("Error !"),
                        self.tr(
                            f"Error while trying to access {url.toString()}:{cr}{cr.join([str(a) for a in e.args])}"
                        ),
                    )

    def _create_url(self, format_string: str, variant: dict) -> QUrl:
        """Create a link from a format string and a variant data

        Args:
            format_string (str): a string with format group like : http://www.google.fr?q={chr}
            variant (dict): a variant dict returned by sql.get_one_variant.

        Returns:
            QUrl: return url or return None

        """
        env = jinja2.Environment()

        try:
            return QUrl(env.from_string(format_string).render(variant))

        except Exception as e:
            Logger.warning(e)
            return QUrl()

    def update_favorites(self, checked: bool = None):
        """Update favorite status of multiple selected variants

        if checked is None, toggle favorite

        Warnings:
            BE CAREFUL with this code, we try to limit useless SQL queries as
            much as possible.
        """

        # Do not update the same variant multiple times
        unique_ids = set()

        for index in self.view.selectionModel().selectedRows():
            if not index.isValid():
                continue

            # Get variant id
            variant = self.model.variants[index.row()]
            variant_id = variant["id"]

            if variant_id in unique_ids:
                continue
            unique_ids.add(variant_id)

            # Update GUI + DB
            if checked is None:
                #  Toggle checked box
                update_data = {"favorite": int(not bool(variant["favorite"]))}
            else:
                update_data = {"favorite": int(checked)}

            self.model.update_variant(index.row(), update_data)
            self.parent.mainwindow.refresh_plugin("variant_edit")

    def update_classification(self, value: int = 3):
        """Update classification level of the variant at the given index
        This function applies the same level to all the variants selected in the view

        Args:
            value (int, optional): ACMG classification value to apply. Defaults to 3.
        """

        # Do not update the same variant multiple times
        unique_ids = set()
        for index in self.view.selectionModel().selectedRows():
            if not index.isValid():
                continue

            # Get variant id
            variant = self.model.variants[index.row()]
            variant_id = variant["id"]

            if variant_id in unique_ids:
                continue
            unique_ids.add(variant_id)
            update_data = {"classification": int(value)}
            self.model.update_variant(index.row(), update_data)
            self.parent.mainwindow.refresh_plugin("variant_edit")

    def update_validation(self, value: int = 0):
        """Update validation of the variant for a given sample ID
        This function applies the same level to all the variants selected in the view
        Args:
            value (int, optional): Sample Variant classification value to apply. Defaults to 0.
            sample_id (int, optional): Sample ID. Defaults to None.
        """

        # current index
        index = self.view.currentIndex()

        # find sample_id
        sample_id = None
        _header_name = self.model.headers[index.column()]
        match = re.findall(r"^samples.(\w+)\.(.*)$", _header_name)
        if match:
            sample_name = match[0][0]
            sample_infos = sql.search_samples(self.conn, name=sample_name)
            for sample_info in sample_infos:
                sample_id = sample_info["id"]

        # Do not update the same variant multiple times
        unique_ids = set()
        for index in self.view.selectionModel().selectedRows():
            if not index.isValid():
                continue

            # Get variant id
            variant = self.model.variants[index.row()]
            variant_id = variant["id"]

            if variant_id in unique_ids:
                continue
            unique_ids.add(variant_id)

            data = {}
            data["variant_id"] = variant_id
            data["sample_id"] = sample_id
            data["classification"] = value

            sql.update_genotypes(self.conn, data)

            if "genotypes" in self.parent.mainwindow.plugins:
                self.parent.mainwindow.refresh_plugin("genotypes")

            if "samples" in self.parent.mainwindow.plugins:
                self.parent.mainwindow.refresh_plugin("samples")

    def update_tags(self, tags: list = []):
        """Update tags of the variant

        Args:
            tags(list): A list of tags

        """

        for index in self.view.selectionModel().selectedRows():

            # current variant
            row = index.row()
            variant = self.model.variants[row]
            variant_id = variant["id"]

            # current varaint tags
            current_variant = sql.get_variant(self.conn, variant_id)
            current_tags_text = current_variant.get("tags", None)
            if current_tags_text:
                current_tags = current_tags_text.split(cst.HAS_OPERATOR)
            else:
                current_tags = []

            # append tags
            for tag in tags:
                current_tags.append(tag) if tag not in current_tags else current_tags

            # update tags
            self.model.update_variant(row, {"tags": cst.HAS_OPERATOR.join(current_tags)})

    def edit_comment(self, index: QModelIndex):
        """Allow a user to add a comment for the selected variant"""
        if not index.isValid():
            return

        # Get comment from DB
        variant_data = sql.get_variant(self.model.conn, self.model.variant(index.row())["id"])
        comment = variant_data["comment"] if variant_data["comment"] else ""

        editor = MarkdownDialog()
        editor.widget.setPlainText(comment)
        if editor.exec_() == QDialog.Accepted:
            # Save in DB
            self.model.update_variant(index.row(), {"comment": editor.widget.toPlainText()})

            # Request a refresh of the variant_edit plugin
            self.parent.mainwindow.refresh_plugin("variant_edit")

    def select_all(self):
        """Select all variants in the view"""
        self.view.selectAll()

    def select_row(self, row):
        """Select the row with the given index

        Called for left pane by :meth:`loaded`.
        """
        index = self.view.model().index(row, 0)
        self.view.selectionModel().setCurrentIndex(
            index, QItemSelectionModel.SelectCurrent | QItemSelectionModel.Rows
        )

    def keyPressEvent(self, event: QKeyEvent):
        """
        Handles key press events on the VariantView
        Can be used to filter out unexpected behavior with KeySequence conflicts
        """
        if event.matches(
            QKeySequence.Copy
        ):  # Default behavior from QTableView only copies the index that the mouse hovers
            self.copy_to_clipboard()  # So copy to clipboard to get the expected behavior in contextMenuEvent
            event.accept()  # Accept the event before the QTableView handles it in a terrible way

    def copy_to_clipboard(self):
        """Copy the selected variant(s) into the clipboard

        The output data is formated in CSV (delimiter is `\t`)
        """
        # In memory file
        output = io.StringIO()
        # Use CSV to securely format the data
        writer = csv.DictWriter(output, delimiter="\t", fieldnames=self.model.headers)
        writer.writeheader()
        for index in self.view.selectionModel().selectedRows():
            # id col is not wanted
            variant = dict(self.model.variant(index.row()))
            if "id" in variant:
                del variant["id"]
            writer.writerow(variant)

        QApplication.instance().clipboard().setText(output.getvalue())
        output.close()

    def copy_cell_to_clipboard(self):
        index = self.view.currentIndex()
        if not index:
            return
        data = index.data()
        QApplication.instance().clipboard().setText(data)

    def _open_default_link(self, index: QModelIndex):

        #  get default link
        link = [i for i in self._get_links() if i["is_default"] is True]
        if not link:
            return

        link = link[0]

        if link:
            self._open_url(link["url"], link["is_browser"])

    def on_double_clicked(self, index: QModelIndex):
        """
        Action on default doubleClick
        """
        self.open_editor(index)

    def on_double_clicked_vertical_header(self, index: QModelIndex):
        """
        Action on doubleClick on verticalHeader
        """
        self.open_editor(index)

    def open_editor(self, index: QModelIndex):
        """
        Open Editor
        Either Variant Editor (if variant column) or Genotype Editor (if genotype column)
        """

        header_name_match_sample = False
        validation_menu_lock = False
        no_genotype = False
        sample_name = "unknown"

        # Check if Edit Genotype
        if type(index) is not int:
            # Double click on horizontal header
            header_name = self.model.headers[index.column()]
            header_name_match_sample = re.findall(r"^samples.(\w+)\.(.*)$", header_name)
            validation_menu_lock = False
            no_genotype = False
            sample_name = "unknown"
            if header_name_match_sample:
                sample_name = header_name_match_sample[0][0]
                sample_infos = next(sql.search_samples(self.conn, name=sample_name))
                if self.is_locked(sample_infos.get("id", 0)):
                    validation_menu_lock = True
                if index.data() == "NULL":
                    no_genotype = True

        # Menu Validation for sample
        if header_name_match_sample:
            if validation_menu_lock:
                QMessageBox.information(
                    self, "Sample locked", self.tr(f"Sample '{sample_name}' is locked, genotype can not be changed")
                )
            elif no_genotype:
                QMessageBox.information(
                    self, "No genotype", self.tr(f"Sample '{sample_name}' does not have genotype for this variant")
                )
            else:
                self._show_sample_variant_dialog()
        else:
            self._show_variant_dialog()

    def create_classification_menu(self, index: QModelIndex):
        # Create classication action
        class_menu = QMenu(self.tr("Classification"))

        variant = self.model.variant(index.row())

        for item in self.model.classifications:

            if variant["classification"] == item["number"]:
                icon = 0xF0133
                # class_menu.setIcon(FIcon(icon, item["color"]))
            else:
                icon = 0xF012F

            action = class_menu.addAction(FIcon(icon, item["color"]), item["name"])
            action.setData(item["number"])
            on_click = functools.partial(self.update_classification, item["number"])
            action.triggered.connect(on_click)

        return class_menu

    def create_tags_menu(self, index: QModelIndex):
        # Create classication action
        tags_menu = QMenu(self.tr("Tags"))

        variant = self.model.variant(index.row())

        tags_preset = Config("tags")

        for item in tags_preset.get("variants", []):

            icon = 0xF04F9

            action = tags_menu.addAction(FIcon(icon, item["color"]), item["name"])
            action.setData(item["name"])
            on_click = functools.partial(self.update_tags, [item["name"]])
            action.triggered.connect(on_click)

        return tags_menu

    def create_validation_menu(self, genotype):
        # Create classication action
        validation_menu = QMenu(self.tr(f"Genotype Classification"))

        config = Config("classifications")
        genotypes_classifications = config.get("genotypes", [])

        for item in genotypes_classifications:

            if genotype["classification"] == item["number"]:
                icon = 0xF0133
                # validation_menu.setIcon(FIcon(icon, item["color"]))
            else:
                icon = 0xF012F

            action = validation_menu.addAction(FIcon(icon, item["color"]), item["name"])
            action.setData(item["number"])
            on_click = functools.partial(self.update_validation, value=item["number"])
            action.triggered.connect(on_click)

        return validation_menu

    def create_external_links_menu(self):
        menu = QMenu(self.tr("Browse to ..."))
        for link in self._get_links():
            func_slot = functools.partial(self._open_url, link["url"], link["is_browser"])
            action = menu.addAction(link["name"], func_slot)
            action.setIcon(FIcon(0xF0866))
        return menu

    def show_unique_values(self, field: str):
        groupby_dialog = GroupbyDialog(self.conn, self)
        groupby_dialog.load(field, self.model.fields, self.model.source, self.model.filters)
        if groupby_dialog.exec() == QDialog.Accepted:
            selected_values = groupby_dialog.get_selected_values()
            if selected_values:
                self.add_condition_to_filters(
                    {groupby_dialog.view.groupby_model.get_field_name(): {"$in": selected_values}}
                )

    def add_condition_to_filters(self, condition: dict):
        filters = copy.deepcopy(self.parent.mainwindow.get_state_data("filters"))

        if "$and" in filters:
            for index, cond in enumerate(filters["$and"]):
                if list(cond.keys())[0] == list(condition.keys())[0]:
                    filters["$and"][index] = condition
                    break
            else:
                filters["$and"].append(condition)
        else:
            filters = {"$and": [condition]}

        self.parent.mainwindow.set_state_data("filters", filters)
        self.parent.mainwindow.refresh_plugins(sender=self)


class VariantViewWidget(plugin.PluginWidget):
    """
    A plugin table of all variants
    """

    # Plugin class parameter
    LOCATION = plugin.CENTRAL_LOCATION
    ENABLE = True
    REFRESH_STATE_DATA = {"fields", "filters", "source", "order_by"}

    def __init__(self, parent=None):
        super().__init__(parent)

        # Create the variant view
        self.view = VariantView(parent=self)

        # Setup layout
        main_layout = QVBoxLayout(self)
        main_layout.addWidget(self.view)

        # Make connection
        self.view.view.selectionModel().currentRowChanged.connect(
            lambda x, _: self.on_variant_clicked(x)
        )

        self.view.load_finished.connect(self.on_load_finished)

        self.view.filter_add.connect(self.on_filter_added)
        self.view.filter_remove.connect(self.on_filter_removed)
        self.view.field_remove.connect(self.on_field_removed)

        self.view.fields_btn_clicked.connect(lambda: self.show_plugin("fields_editor"))
        self.view.source_btn_clicked.connect(lambda: self.show_plugin("source_editor"))
        self.view.filters_btn_clicked.connect(lambda: self.show_plugin("filters_editor"))

    def show_plugin(self, name: str):

        if name in self.mainwindow.plugins:
            print("YOO ", name)
            dock = self.mainwindow.plugins[name].parent()
            dock.setVisible(not dock.isVisible())

    def on_load_finished(self):
        """Triggered when variant load is finished
        Notify all plugins registered to "executed_query_data"

        """

        executed_query_data = {
            "count": self.view.model.total,
            "elapsed_time": self.view.model.elapsed_time,
        }

        self.mainwindow.set_state_data("executed_query_data", executed_query_data)
        self.mainwindow.set_state_data("order_by", self.view.model.order_by)
        self.mainwindow.refresh_plugins()

    def on_field_removed(self, field: str):

        # TODO: Refactor to remove column based on field name...
        fields = self.view.model.fields
        field_index = fields.index(field)
        self.view.model.removeColumn(field_index)
        self.view.load()
        fields = self.view.model.fields
        self.mainwindow.set_state_data("fields", fields)
        self.mainwindow.refresh_plugins(sender=self)

    def on_filter_added(self, field: str):

        dialog = FilterDialog(self.conn)
        dialog.set_field(field)

        if dialog.exec():

            one_filter = dialog.get_filter()
            filters = copy.deepcopy(self.view.model.filters)

            print("ONE filter", one_filter)

            if not filters:
                filters = {"$and": []}

            if "$and" in filters:
                filters["$and"].append(one_filter)
            if "$or" in filters:
                filters["$or"].append(one_filter)

            self.view.model.filters = filters
            self.view.load()
            self.mainwindow.set_state_data("filters", filters)
            self.mainwindow.refresh_plugins(sender=self)

    def on_filter_removed(self, field: str):
        filters = self.view.model.filters
        new_filters = querybuilder.remove_field_in_filter(filters, field)

        self.view.model.filters = new_filters
        self.view.load()

        self.mainwindow.set_state_data("filters", new_filters)
        self.mainwindow.refresh_plugins(sender=self)

    def on_open_project(self, conn):
        """Overrided from PluginWidget"""
        self.conn = conn
        self.view.conn = self.conn

        # Setup config
        config = self.create_config()
        self.view.model.limit = config.get("rows_per_page", 50)
        self.view.model.set_cache(config.get("memory_cache", 32))

        config = Config("classifications")
        self.view.model.classifications = list(config.get("variants", []))

        self.on_refresh()

    def on_close_project(self):
        self.view.model.clear()

    def on_refresh(self):
        """Overrided from PluginWidget"""
        # Save default data with current query attributes
        # See load(), we use this attr to restore fields after grouping

        if self.mainwindow:

            self.view.model.clear_variant_cache()
            self.view.fields = self.mainwindow.get_state_data("fields")
            self.view.filters = self.mainwindow.get_state_data("filters")
            self.view.model.order_by = self.mainwindow.get_state_data("order_by")
            self.view.model.source = self.mainwindow.get_state_data("source")

            self.view.load(reset_page=True)

    def on_variant_clicked(self, index: QModelIndex):
        """React on variant clicked

        Args:
            index (QModelIndex): index into item models derived from
                QAbstractItemModel. U used by item views, delegates, and
                selection models to locate an item in the model.
        """

        if index.model() == self.view.view.model():
            # Variant clicked on right pane

            # TODO Make current_variant state data take the value of the whole variant (with annotations and samples!)
            variant = self.view.model.variant(index.row())

        if self.mainwindow:
            self.mainwindow.set_state_data("current_variant", variant)
            # Request a refresh of the variant_info plugin
            self.mainwindow.refresh_plugins(self)


if __name__ == "__main__":
    import sys
    from PySide6.QtWidgets import QApplication
    from cutevariant.core.importer import import_file, import_reader
    from cutevariant.core.reader import FakeReader, VcfReader
    from cutevariant.core import sql

    app = QApplication(sys.argv)

    conn = sql.get_sql_connection("/home/sacha/Dev/cutevariant/corpos3.db")

    w = VariantViewWidget()
    w.conn = conn
    w.view.model.conn = conn
    w.view.load()
    # w.main_view.model.group_by = ["chr","pos","ref","alt"]
    # w.on_refresh()

    w.show()

    app.exec_()
    w.on_refresh()

    w.show()

    app.exec_()
