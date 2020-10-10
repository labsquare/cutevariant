# Standard imports
import functools
import math
import csv
import io
import copy
import string
from logging import DEBUG

# Qt imports
from PySide2.QtWidgets import *
from PySide2.QtCore import *
from PySide2.QtGui import *

# Custom imports
from cutevariant.core.querybuilder import build_complete_query
from cutevariant.core import command as cmd
from cutevariant.gui import plugin, FIcon
from cutevariant.gui.sql_runnable import SqlRunnable
from cutevariant.gui import formatter
from cutevariant.gui.widgets import MarkdownEditor
import cutevariant.commons as cm


LOGGER = cm.logger()


class VariantModel(QAbstractTableModel):
    """
    VariantModel is a Qt model class which contains variants datas from sql.VariantBuilder .
    It loads paginated data from VariantBuilder and create an interface for a Qt view and controllers.
    The model can group variants by (chr,pos,ref,alt) into a tree thanks to VariantBuilder.tree().

    See Qt model/view programming for more information
    https://doc.qt.io/qt-5/model-view-programming.html

    Variants are stored internally as a list of variants. By default, there is only one transcript per row.
    When user expand the row, it will append duplicates variants as children.
    For example, this is a tree with 2 variants , each of them refer to many transcripts.

    """

    loading = Signal(bool)  # emit when data start or stop loading
    load_finished = Signal()  # Emit when data is loaded and ready to be used

    def __init__(self, conn=None, parent=None):
        super().__init__()
        self.limit = 50
        self.page = 0
        self.total = 0
        self.variants = []
        self.headers = []
        self.formatter = None

        # Cache all database fields and their descriptions for tooltips
        # Field names as keys, descriptions as values
        self.fields_descriptions = None

        self.fields = ["chr", "pos", "ref", "alt"]
        self.filters = dict()
        self.source = "variants"
        self.group_by = []
        self.having = {}
        self.order_by = None
        self.order_desc = True
        self.formatter = None
        self.debug_sql = None
        # Keep after all initialization
        self.conn = conn

        # Async stuff
        self.pool = QThreadPool()
        self.is_loading = False
        self.variant_runnable = None
        self.count_runnable = None

    @property
    def conn(self):
        """ Return sqlite connection """
        return self._conn

    @conn.setter
    def conn(self, conn):
        """ Set sqlite connection """
        self._conn = conn
        if conn:
            # Note: model is initialized with None connection during start
            # Cache DB fields descriptions
            self.fields_descriptions = {
                field["name"]: field["description"]
                for field in sql.get_fields(self.conn)
            }

    @property
    def formatter(self):
        return self._formatter

    @formatter.setter
    def formatter(self, formatter):
        self.beginResetModel()
        self._formatter = formatter
        self.endResetModel()

    def rowCount(self, parent=QModelIndex()):
        """Overrided : Return children count of index"""
        # If parent is root

        return len(self.variants)

    def columnCount(self, parent=QModelIndex()):
        """Overrided: Return column count of parent .

        Parent is not used here.
        """
        return len(self.headers)

    def clear(self):
        self.beginResetModel()
        self.variants.clear()
        self.endResetModel()

    def data(self, index: QModelIndex(), role=Qt.DisplayRole):
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
                return str(self.variant(index.row())[column_name])

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
                if self.fields_descriptions and section != 0:
                    field_name = self.fields[section - 1]
                    return self.fields_descriptions.get(field_name)

    def update_variant(self, row: int, variant: dict):
        """Update a variant at the given row with given content

        Update the variant in the GUI AND in the DB.

        Args:
            row (int): Row id of the variant that will be modified
            variant (dict): Dict of fields to be updated
        """
        # Update in database
        left = self.index(row, 0)
        right = self.index(row, self.columnCount() - 1)

        if left.isValid() and right.isValid():
            # Get database id of the variant to allow its update operation
            variant["id"] = self.variants[row]["id"]
            sql.update_variant(self.conn, variant)
            self.variants[row].update(variant)
            self.dataChanged.emit(left, right)

    def _set_loading(self, active=True):
        """Emit the loading status of async queries

        Called before async queries and after their end.

        Signal emitted: loading(bool), captured by VariantView to start/stop
        movie animation.
        """
        self.is_loading = active
        self.loading.emit(active)

    def find_row_id_from_variant_id(self, variant_id: int) -> list:
        """Find the ids of all rows with the same given variant_id

        Args:
            variant_id (int): Variant sql record id
        Returns:
            (list[int]): ids of rows
        """
        return [row_id for row_id, variant in enumerate(self.variants) if variant["id"] == variant_id]

    def load(self):
        """Load variant data into the model from query attributes

        Called by:
            - on_change_query() from the view.
            - load_from_vql(), sort() and setPage() by the model.
        """
        if self.conn is None:
            return

        self._set_loading(True)
        LOGGER.debug("Start loading")

        offset = self.page * self.limit

        # Add fields from group by
        # self.clear()  # Assume variant = []
        self.total = 0

        LOGGER.debug("page: %s", self.page)

        # Store SQL query for debugging purpose
        self.debug_sql = build_complete_query(
            self.conn,
            fields=self.fields,
            source=self.source,
            filters=self.filters,
            limit=self.limit,
            offset=offset,
            order_desc=self.order_desc,
            order_by=self.order_by,
            group_by=self.group_by,
            having=self.having,
        )

        # Create load_func to run asynchronously: load variants
        load_func = functools.partial(
            cmd.select_cmd,
            fields=self.fields,
            source=self.source,
            filters=self.filters,
            limit=self.limit,
            offset=offset,
            order_desc=self.order_desc,
            order_by=self.order_by,
            group_by=self.group_by,
            having=self.having,
        )

        # Create count_func to run asynchronously: count variants
        count_function = functools.partial(
            cmd.count_cmd,
            fields=self.fields,
            source=self.source,
            filters=self.filters,
            group_by=self.group_by,
        )

        # self.sql_thread.terminate()
        self.variant_runnable = SqlRunnable(
            self.conn, lambda conn: list(load_func(conn))
        )
        self.variant_runnable.finished.connect(self.loaded)

        self.count_runnable = SqlRunnable(self.conn, count_function)
        self.count_runnable.finished.connect(self.loaded)

        self.pool.start(self.variant_runnable)
        self.pool.start(self.count_runnable)

    def loaded(self):
        """Called when SQL async queries are done

        - We wait until the 2 requests (variant and count rennable) have finished.
        - self.variants, self.total are set

        Signals:
            - self._is_loading() si called at the end and so loading(true) is emitted
            - load_finished (captured by VariantView to load page_box)
        """
        if not self.variant_runnable or not self.count_runnable:
            return
        if not self.variant_runnable.done or not self.count_runnable.done:
            # One of the runner has not finished his job
            return

        LOGGER.debug("received load data")

        self.beginResetModel()
        self.variants.clear()

        # Add fields from group by
        for g in self.group_by:
            if g not in self.fields:
                self.fields.append(g)

        # Load variants
        self.variants = self.variant_runnable.results
        if self.variants:
            # Set headers of the view
            self.headers = list(self.variants[0].keys())

        # print(self.count_runnable.results["count"])
        self.total = self.count_runnable.results["count"]

        # Reset for next run
        self.variant_runnable = self.count_runnable = None

        # print(self.fields, self.filters, self.group_by)
        self.endResetModel()
        self._set_loading(False)
        self.load_finished.emit()

    def load_from_vql(self, vql):

        try:
            vql_object = vql.parse_one_vql(vql)
            if "select_cmd" in vql_object:
                self.fields = vql_object["fields"]
                self.source = vql_object["source"]
                self.filters = vql_object["filters"]
            self.load()
        except Exception as e:
            LOGGER.exception(e)
            raise e

    def hasPage(self, page: int) -> bool:
        """ Return True if <page> exists otherwise return False """
        return page >= 0 and page * self.limit < self.total

    def setPage(self, page: int):
        """ set the page of the model """
        if self.hasPage(page):
            self.page = page
            self.load()

    def nextPage(self):
        """ Set model to the next page """
        if self.hasPage(self.page + 1):
            self.setPage(self.page + 1)

    def previousPage(self):
        """ Set model to the previous page """
        if self.hasPage(self.page - 1):
            self.setPage(self.page - 1)

    def firstPage(self):
        """ Set model to the first page """
        self.setPage(0)

    def lastPage(self):
        """ Set model to the last page """

        self.setPage(self.pageCount() - 1)

    def pageCount(self):
        """ Return total page count """
        return math.ceil(self.total / self.limit)

    def sort(self, column: int, order):
        """Overrided: Sort data by specified column

        column (int): column id
        order (Qt.SortOrder): Qt.AscendingOrder or Qt.DescendingOrder

        """
        if column < self.columnCount():
            colname = self.headers[column]

            self.order_by = colname
            self.order_desc = order == Qt.DescendingOrder
            self.load()

    def variant(self, row: int) -> dict:
        """Return variant data according index"""
        return self.variants[row]


class VariantDelegate(QStyledItemDelegate):
    """Specify the aesthetic (style and color) of variants displayed on a view"""

    def __init__(self, parent=None):
        super().__init__(parent)

        self.formatter = None

    def paint(self, painter, option, index):
        """Paint with formatter if defined"""

        if self.formatter is None:
            return super().paint(painter, option, index)

        # Draw selections
        if option.state & QStyle.State_Enabled:
            bg = (
                QPalette.Normal
                if option.state & QStyle.State_Active
                else QPalette.Inactive
            )
        else:
            bg = QPalette.Disabled

        if option.state & QStyle.State_Selected:
            painter.fillRect(option.rect, option.palette.color(bg, QPalette.Highlight))

        # Draw formatters
        option.rect = option.rect.adjusted(
            3, 0, 0, 0
        )  # Don't know why I need to adjust the left margin .. .
        self.formatter.paint(painter, option, index)


class LoadingTableView(QTableView):
    """Movie animation displayed on VariantView for long SQL queries executed
    in background.
    """
    def __init__(self, parent=None):
        super().__init__(parent)

        self.movie = QMovie(cm.DIR_ICONS + "loading.gif")

        self.movie.frameChanged.connect(self.update)

    def paintEvent(self, event: QPainter):

        if self.is_loading():
            painter = QPainter(self.viewport())
            rect = self.movie.currentPixmap().rect()
            rect.moveCenter(self.viewport().rect().center())
            painter.drawPixmap(rect.x(), rect.y(), self.movie.currentPixmap())
            self.viewport().update()
        else:
            super().paintEvent(event)

    def start_loading(self):
        self.movie.start()
        self.viewport().update()

    def stop_loading(self):
        self.movie.stop()
        self.viewport().update()

    def is_loading(self):
        return self.movie.state() == QMovie.Running


class VariantView(QWidget):
    """A Variant view with controller like pagination

    Attributes:

        row_to_be_selected (int/None): (optional) Left groupby pane only:
            At the end of the :meth:`loaded` method, the first line is selected
            in order to refresh the current variant in the other pane.
            TL,DR: Select the first row if in grouped mode => refresh the right pane.
    """

    view_clicked = Signal()

    def __init__(self, parent=None, show_popup_menu=True):
        """
        Args:
            parent: parent widget
            show_popup_menu (boolean, optional: If False, disable the context menu
                over variants. For example the group pane should be disable
                in order to avoid partial/false informations to be displayed
                in this menu.
        """
        super().__init__(parent)

        self.parent = parent
        self.show_popup_menu = show_popup_menu
        self.view = LoadingTableView()
        self.bottom_bar = QToolBar()

        self.settings = QSettings()

        # self.view.setFrameStyle(QFrame.NoFrame)
        self.view.setAlternatingRowColors(True)
        self.view.horizontalHeader().setStretchLastSection(True)
        self.view.setSelectionMode(QAbstractItemView.SingleSelection)
        self.view.verticalHeader().hide()

        self.view.setSortingEnabled(True)
        self.view.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.view.setSelectionMode(QAbstractItemView.ExtendedSelection)
        ## self.view.setIndentation(0)
        self.view.setIconSize(QSize(22, 22))
        self.view.horizontalHeader().setSectionsMovable(True)

        # Setup model
        self.model = VariantModel()
        self.view.setModel(self.model)

        # Setup delegate
        self.delegate = VariantDelegate()
        self.view.setItemDelegate(self.delegate)

        # setup toolbar
        spacer = QWidget()
        spacer.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)

        self.page_box = QLineEdit()
        self.page_box.setValidator(QIntValidator())
        self.page_box.setFixedWidth(50)
        self.page_box.setValidator(QIntValidator())

        self.info_label = QLabel()
        self.loading_label = QLabel()
        self.loading_label.setMovie(QMovie(cm.DIR_ICONS + "loading.gif"))
        self.loading_label.movie().setScaledSize(QSize(20, 20))
        self.loading_label.movie().start()

        # TODO: display on debug mode
        self.bottom_bar.addAction(FIcon(0xF0866), "show sql", self.on_show_sql)
        self.bottom_bar.addWidget(self.info_label)
        self.bottom_bar.addWidget(spacer)
        self.bottom_bar.setIconSize(QSize(16, 16))
        self.bottom_bar.setMaximumHeight(30)
        self.bottom_bar.setContentsMargins(0, 0, 0, 0)

        self.pagging_actions = []
        self.pagging_actions.append(
            self.bottom_bar.addAction(FIcon(0xF0600), "<<", self.on_page_clicked)
        )
        self.pagging_actions.append(
            self.bottom_bar.addAction(FIcon(0xF0141), "<", self.on_page_clicked)
        )
        self.bottom_bar.addWidget(self.page_box)
        self.pagging_actions.append(
            self.bottom_bar.addAction(FIcon(0xF0142), ">", self.on_page_clicked)
        )
        self.pagging_actions.append(
            self.bottom_bar.addAction(FIcon(0xF0601), ">>", self.on_page_clicked)
        )
        # self.page_box.returnPressed.connect()

        self.page_box.returnPressed.connect(self.on_page_changed)

        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(0, 0, 0, 0)

        main_layout.addWidget(self.view)
        main_layout.addWidget(self.bottom_bar)
        self.setLayout(main_layout)

        # Async stuff
        # broadcast focus signal
        self.row_to_be_selected = None
        # Get the status of async load: started/finished
        self.model.loading.connect(self._set_loading)
        # Queries are finished (yes its redundant with loading signal...)
        self.model.load_finished.connect(self.loaded)

    def _set_loading(self, active=True):
        """Slot to obtain the status of async load: started/finished

        Start/Stop the movie animation on the view.

        Keyword Args:
            active (bool): True if loaded, False if finished
        """
        self.setDisabled(active)
        if active:
            QTimer.singleShot(1000, self.start_loading_after_delay)
        else:
            self.view.stop_loading()

    def start_loading_after_delay(self):
        self.setDisabled(self.model.is_loading)

        if self.model.is_loading:
            self.view.start_loading()
        else:
            self.view.stop_loading()

    def setModel(self, model: VariantModel):
        self.model = model
        self.view.setModel(model)

    def load(self):
        self.model.page = 0
        self.model.load()

    def loaded(self):
        """Slot called when async queries from the model are finished
        (especially count of variants for page box).
        """
        if self.row_to_be_selected is not None:
            # Left groupby pane only:
            # Select by default the first line in order to refresh the
            # current variant in the other panef
            self.select_row(0)

        self.load_page_box()
        if LOGGER.getEffectiveLevel() != DEBUG:
            self.view.setColumnHidden(0, True)

    def set_formatter(self, formatter):
        self.delegate.formatter = formatter
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

    @property
    def group_by(self):
        return self.model.group_by

    @group_by.setter
    def group_by(self, _group_by):
        self.model.group_by = _group_by

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
        self.view.scrollToTop()

        self.page_box.setText(str(self.model.page))

    def on_page_changed(self):
        """Slot called when page_box is modified and the user has pressed return key

        The validator is ok if this slot is called.
        """
        if self.page_box.text():
            page = int(self.page_box.text())
            self.model.setPage(page)

    def on_show_sql(self):
        """Display debug sql query"""
        msg_box = QMessageBox()
        msg_box.setText(self.model.debug_sql)
        msg_box.exec_()

    def load_page_box(self):
        """Load Bottom toolbar with pagination"""
        self.page_box.clear()
        if self.model.pageCount() - 1 == 0:
            self.set_pagging_enabled(False)
        else:
            # self.page_box.addItems([str(i) for i in range(self.model.pageCount())])
            self.page_box.validator().setRange(0, self.model.pageCount() - 1)
            self.page_box.setText(str(self.model.page))
            self.set_pagging_enabled(True)

        self.info_label.setText(
            self.tr("{} row(s) {} page(s)").format(self.model.total, self.model.pageCount())
        )

    def set_pagging_enabled(self, active=True):
        self.page_box.setEnabled(active)
        for action in self.pagging_actions:
            action.setEnabled(active)

    def contextMenuEvent(self, event: QContextMenuEvent):
        """Override: Show contextual menu over the current variant"""
        if not self.show_popup_menu:
            return

        menu = QMenu(self)
        pos = self.view.viewport().mapFromGlobal(event.globalPos())
        current_index = self.view.indexAt(pos)

        if not current_index.isValid():
            return

        current_variant = self.model.variant(current_index.row())
        full_variant = sql.get_one_variant(self.conn, current_variant["id"])
        # Update variant with currently displayed fields (not in variants table)
        full_variant.update(current_variant)

        # Copy action: Copy the variant reference ID in to the clipboard
        formatted_variant = "{chr}:{pos}-{ref}-{alt}".format(**full_variant)
        menu.addAction(
            FIcon(0xF014C),
            formatted_variant,
            functools.partial(qApp.clipboard().setText, formatted_variant),
        )

        # Create favorite action
        fav_action = menu.addAction(
            self.tr("&Unmark favorite")
            if bool(full_variant["favorite"])
            else self.tr("&Mark as favorite")
        )
        fav_action.setCheckable(True)
        fav_action.setChecked(bool(full_variant["favorite"]))
        fav_action.toggled.connect(self.update_favorites)

        # Create classication action
        class_menu = menu.addMenu(self.tr("Classification"))
        for key, value in cm.CLASSIFICATION.items():

            action = class_menu.addAction(
                FIcon(cm.CLASSIFICATION_ICONS[key]), value
            )
            action.setData(key)
            on_click = functools.partial(
                self.update_classification, current_index, key
            )
            action.triggered.connect(on_click)

        # Create external links
        links_menu = menu.addMenu(self.tr("External links"))
        self.settings.beginGroup("plugins/variant_view/links")
        # Display only external links with placeholders that can be mapped
        for key in self.settings.childKeys():
            format_string = self.settings.value(key)
            # Get placeholders
            field_names = {name for text, name, spec, conv in string.Formatter().parse(format_string)}
            if field_names & full_variant.keys():
                # Full or partial mapping => accepted link
                links_menu.addAction(
                    key,
                    functools.partial(
                        QDesktopServices.openUrl,
                        QUrl(format_string.format(**full_variant), QUrl.TolerantMode)
                    )
                )
        self.settings.endGroup()

        # Comment action
        on_edit = functools.partial(self.edit_comment, current_index)
        menu.addAction(self.tr("&Edit comment ..."), on_edit)

        # Edit menu
        menu.addSeparator()
        menu.addAction(
            FIcon(0xF018F), self.tr("&Copy"), self.copy_to_clipboard, QKeySequence.Copy
        )
        menu.addAction(
            FIcon(0xF0486), self.tr("&Select all"), self.select_all, QKeySequence.SelectAll
        )

        # Display
        menu.exec_(event.globalPos())

    def update_favorites(self, checked: bool):
        """Update favorite status of multiple selected variants

        Warnings:
            BE CAREFUL with this code, we try to limit useless SQL queries as
            much as possible.
        """
        update_data = {"favorite": int(checked)}

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
            self.model.update_variant(index.row(), update_data)

            # JUST update the GUI
            for row_id in self.model.find_row_id_from_variant_id(variant_id):
                self.model.variants[row_id].update(update_data)

    def update_classification(self, index: QModelIndex, value=3):
        """Update classification level of the variant at the given index"""
        if index.isValid():
            update_data = {"classification": int(value)}
            self.model.update_variant(index.row(), update_data)

    def edit_comment(self, index: QModelIndex):
        """Allow a user to add a comment for the selected variant"""
        if not index.isValid():
            return

        # Get comment from DB
        variant_data = sql.get_one_variant(
            self.model.conn, self.model.variant(index.row())["id"]
        )
        comment = variant_data["comment"] if variant_data["comment"] else ""

        editor = MarkdownEditor(default_text=comment)
        if editor.exec_() == QDialog.Accepted:
            # Save in DB
            self.model.update_variant(index.row(), {"comment": editor.toPlainText()})

            # Request a refresh of the variant_info plugin
            self.parent.mainwindow.refresh_plugin("variant_info")

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

    def copy_to_clipboard(self):
        """Copy the selected variant(s) into the clipboard

        The output data is formated in CSV (delimiter is `\t`)
        """
        # In memory file
        output = io.StringIO()
        # Use CSV to securely format the data
        writer = csv.DictWriter(output, delimiter="\t", fieldnames=self.model.fields)
        writer.writeheader()
        for index in self.view.selectionModel().selectedRows():
            # id col is not wanted
            variant = dict(self.model.variant(index.row()))
            if "id" in variant:
                del variant["id"]
            writer.writerow(variant)

        qApp.clipboard().setText(output.getvalue())
        output.close()


class VariantViewWidget(plugin.PluginWidget):
    """Contains the view of query with several controller"""

    variant_clicked = Signal(dict)
    LOCATION = plugin.CENTRAL_LOCATION

    ENABLE = True

    def __init__(self, parent=None):
        super().__init__(parent)

        # Create 2 Panes
        self.splitter = QSplitter(Qt.Horizontal)
        self.main_right_pane = VariantView(parent=self)

        # No popup menu on this one
        self.groupby_left_pane = VariantView(parent=self, show_popup_menu=False)
        self.groupby_left_pane.hide()
        # Force selection of first item after refresh
        self.groupby_left_pane.row_to_be_selected = 0

        self.splitter.addWidget(self.groupby_left_pane)
        self.splitter.addWidget(self.main_right_pane)

        # Make resizable TODO : ugly ... Make it nicer
        # def _resize1_section(l, o, n):
        #     self.groupby_left_pane.view.horizontalHeader().resizeSection(l, n)

        # def _resize2_section(l, o, n):
        #     self.main_right_pane.view.horizontalHeader().resizeSection(l, n)

        # self.main_right_pane.view.horizontalHeader().sectionResized.connect(_resize1_section)
        # self.groupby_left_pane.view.horizontalHeader().sectionResized.connect(
        #     _resize2_section
        # )

        # self.groupby_left_pane.view.setHorizontalHeader(self.main_right_pane.view.horizontalHeader())

        # Top toolbar
        self.top_bar = QToolBar()
        self.top_bar.setToolButtonStyle(Qt.ToolButtonTextBesideIcon)

        # checkable group action
        self.groupby_action = self.top_bar.addAction(
            FIcon(0xF14E0), self.tr("Group by"), self.on_group_changed
        )
        self.groupby_action.setCheckable(True)
        self.groupby_action.setChecked(False)

        # groupbylist
        self.groupbylist_action = self.top_bar.addAction("chr,pos,ref")
        self.groupbylist_action.setVisible(False)
        self.groupbylist_action.triggered.connect(self._show_group_dialog)

        # Formatter tools
        self.top_bar.addSeparator()
        spacer = QWidget()
        spacer.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        self.top_bar.addWidget(spacer)

        # Add formatters to combobox
        self.formatter_combo = QComboBox()
        self.settings = QSettings()
        self.add_available_formatters()

        # Refresh UI button
        self.top_bar.addSeparator()
        self.top_bar.addAction(FIcon(0xF0450), self.tr("Refresh"), self.on_refresh)

        # Setup layout
        main_layout = QVBoxLayout()
        main_layout.addWidget(self.top_bar)
        main_layout.addWidget(self.splitter)

        self.setLayout(main_layout)

        # Make connection
        self.main_right_pane.view.selectionModel().currentRowChanged.connect(
            lambda x, _: self.on_variant_clicked(x)
        )

        self.groupby_left_pane.view.selectionModel().currentRowChanged.connect(
            lambda x, _: self.on_variant_clicked(x)
        )

        # Default group
        self.last_group = ["chr"]

        # Save fields between group/ungroup
        self.save_fields = list()
        self.save_filters = list()

    def add_available_formatters(self):
        """Populate the formatters

        Also recall previously selected formatters via config file.
        Default formatter is "SeqoneFormatter".
        """
        # Get previously selected formatter
        formatter_name = self.settings.value("ui/formatter", "SeqoneFormatter")

        # Add formatters to combobox, a click on it will instantiate the class
        selected_formatter_index = 0
        for index, obj in enumerate(formatter.find_formatters()):
            self.formatter_combo.addItem(obj.DISPLAY_NAME, obj)
            if obj.__name__ == formatter_name:
                selected_formatter_index = index

        self.top_bar.addWidget(self.formatter_combo)
        self.formatter_combo.currentTextChanged.connect(self.on_formatter_changed)

        # Set the previously used/default formatter
        self.formatter_combo.setCurrentIndex(selected_formatter_index)

    def on_formatter_changed(self):
        """Activate the selected formatter

        Called when the current formatter is modified
        """
        formatter_class = self.formatter_combo.currentData()
        self.main_right_pane.set_formatter(formatter_class())
        self.groupby_left_pane.set_formatter(formatter_class())
        # Save formatter setting
        self.settings.setValue("ui/formatter", formatter_class.__name__)

    def on_open_project(self, conn):
        """Overrided from PluginWidget"""
        self.conn = conn
        # Set connections of models
        self.main_right_pane.conn = self.conn
        self.groupby_left_pane.conn = self.conn

        self.on_refresh()

    def on_refresh(self):
        """Overrided from PluginWidget"""
        # Save default data with current query attributes
        # See load(), we use this attr to restore fields after grouping
        self.save_fields = self.mainwindow.state.fields
        self.save_filters = self.mainwindow.state.filters

        self.main_right_pane.fields = self.mainwindow.state.fields
        self.main_right_pane.source = self.mainwindow.state.source
        self.main_right_pane.filters = self.mainwindow.state.filters
        # Set current group_by to left pane
        self._set_groups(self.mainwindow.state.group_by)

        # Set formatter
        formatter_class = next(formatter.find_formatters())
        self.main_right_pane.model.formatter = formatter_class()
        self.groupby_left_pane.model.formatter = formatter_class()
        # Load ui
        self.load()

    def _is_grouped(self) -> bool:
        """Return grouped mode status of the view"""
        # print("is grouped ?")
        # print("left", self.groupby_left_pane.model.group_by)
        # print("right", self.main_right_pane.model.group_by)
        return self.groupby_left_pane.group_by != []

    def load(self):
        """Load all view

        Called by on_refresh, on_group_changed, and _show_group_dialog
        Display/hide groupby_left_pane on user demand.
        """
        is_grouped = self._is_grouped()
        # Left pane and groupbylist are visible in group mode
        self.groupby_left_pane.setVisible(is_grouped)
        self.groupbylist_action.setVisible(is_grouped)

        self.groupby_action.blockSignals(True)
        self.groupby_action.setChecked(is_grouped)
        self.groupby_action.blockSignals(False)

        if is_grouped:
            # Ungrouped => grouped or already grouped
            # Groupby fields become left pane fields
            self.groupby_left_pane.fields = self.groupby_left_pane.group_by
            # Prune right fields with left fields => avoid redundancy of information
            self.main_right_pane.fields = [
                field
                for field in self.save_fields
                if field not in self.groupby_left_pane.group_by
            ]
            self.groupby_left_pane.filters = self.save_filters

            # Refresh models
            self.main_right_pane.load()  # useless, except if we modify fields like above
            self.groupby_left_pane.load()
        else:
            # Grouped => ungrouped
            # Restore fields
            self.main_right_pane.fields = self.save_fields
            # Restore filters
            self.main_right_pane.filters = self.save_filters
            # Refresh model
            self.main_right_pane.load()
            # print("saved right:", self.save_fields)

    def on_group_changed(self):
        """Set group by fields when group by button is clicked"""

        is_checked = self.groupby_action.isChecked()
        is_grouped = self._is_grouped()
        if is_checked and not is_grouped:
            # Group
            # Recall previous/default group
            self._set_groups(self.last_group)
        else:
            # Ungroup
            # Save current group
            self.last_group = self.groupby_left_pane.group_by
        if not is_checked:
            # Reset to default group (chr set in _show_group_dialog)
            self._set_groups([])

        self.load()
        self._refresh_vql_editor()

    def on_variant_clicked(self, index: QModelIndex):
        """React on variant clicked

        Args:
            index (QModelIndex): index into item models derived from
                QAbstractItemModel. U used by item views, delegates, and
                selection models to locate an item in the model.
        """

        if index.model() == self.groupby_left_pane.view.model():
            # Variant clicked on left pane => refresh the right pane
            variant = self.groupby_left_pane.model.variant(index.row())

            if self._is_grouped():
                # Restore fields
                self.groupby_left_pane.source = self.main_right_pane.source

                # Forge a special filter to display the current variant
                # TODO: for key in.. pas for i
                and_list = [
                    {"field": field, "operator": "=", "value": variant[field]}
                    for field in self.groupby_left_pane.group_by
                ]

                if self.save_filters:
                    # Keep and update previous filter
                    filters = copy.deepcopy(self.save_filters)

                    if "AND" in self.save_filters:
                        filters["AND"] += and_list
                    else:
                        filters["AND"] = and_list
                else:
                    # New filter
                    filters = {"AND": and_list}

                self.main_right_pane.filters = filters

                # Update right pane only
                self.main_right_pane.load()

        if index.model() == self.main_right_pane.view.model():
            # Variant clicked on right pane
            variant = self.main_right_pane.model.variant(index.row())

        # Refresh the current variant of mainwindow and plugins
        self.mainwindow.state.current_variant = variant
        self.mainwindow.refresh_plugins(sender=self)

    def _show_group_dialog(self):
        """Show a dialog window to select group fields"""
        dialog = QDialog(self)

        view = QListWidget()
        box = QVBoxLayout()
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        box.addWidget(view)
        box.addWidget(buttons)
        buttons.accepted.connect(dialog.accept)
        buttons.rejected.connect(dialog.reject)

        # Populate the list of fields with their check status
        for field in self.save_fields:
            item = QListWidgetItem()
            item.setText(field)
            if field in self.groupby_left_pane.group_by and isinstance(field, str):
                item.setCheckState(Qt.Checked)
            else:
                item.setCheckState(Qt.Unchecked)

            view.addItem(item)
        dialog.setLayout(box)

        if dialog.exec_() == QDialog.Accepted:

            selected_fields = []
            for i in range(view.count()):
                item = view.item(i)
                if item.checkState() == Qt.Checked:
                    selected_fields.append(item.text())

            # if no group force chr
            if not selected_fields:
                selected_fields = ["chr"]

            # Set current group_by to left pane
            self._set_groups(selected_fields)
            # Reload ui
            self.load()
            self._refresh_vql_editor()

    def _set_groups(self, grouped_fields):
        """Set fields on groupby_left_pane and refresh text on groupby action"""
        self.groupby_left_pane.group_by = grouped_fields
        self.groupbylist_action.setText(",".join(grouped_fields))

    def _refresh_vql_editor(self):
        """Force refresh of vql_editor if loaded"""
        if "vql_editor" in self.mainwindow.plugins:
            self.mainwindow.state.group_by = self.groupby_left_pane.group_by
            plugin_obj = self.mainwindow.plugins["vql_editor"]
            plugin_obj.on_refresh()

    def copy(self):
        """Copy the selected variant(s) into the clipboard

        See Also: VariantView.copy_to_clipboard
        """
        self.main_right_pane.copy_to_clipboard()

    def select_all(self):
        """Select all variants in the view

        See Also: VariantView.select_all
        """
        self.main_right_pane.select_all()


if __name__ == "__main__":
    import sys
    from PySide2.QtWidgets import QApplication
    from cutevariant.core.importer import import_file, import_reader
    from cutevariant.core.reader import FakeReader, VcfReader
    from cutevariant.core import sql

    app = QApplication(sys.argv)

    m = QStringListModel()
    m.setStringList(["salut", "sach"])
    w = LoadingTableView()
    w.setModel(m)
    w.show()

    # conn = sql.get_sql_connexion(":memory:")
    # reader = VcfReader(
    #     open("/home/sacha/Dev/cutevariant/examples/test.snpeff.vcf"), "snpeff"
    # )
    # import_reader(conn, reader)

    # w = VariantViewWidget()
    # w.conn = conn
    # w.main_right_pane.model.conn = conn
    # w.main_right_pane.load()
    # # w.main_view.model.group_by = ["chr","pos","ref","alt"]
    # # w.on_refresh()

    # w.show()

    app.exec_()
