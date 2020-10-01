# Standard imports
import functools
import math
import csv
import io

# Qt imports
from PySide2.QtWidgets import *
from PySide2.QtCore import *
from PySide2.QtGui import *

# Custom imports
from cutevariant.core.querybuilder import build_complete_query
from cutevariant.core import command as cmd
from cutevariant.gui import plugin, FIcon
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

    changed = Signal()

    def __init__(self, conn=None, parent=None):
        super().__init__()
        self.limit = 50
        self.page = 0
        self.total = 0
        self.variants = []
        self.headers = []
        self.formatter = None

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

    @property
    def conn(self):
        """ Return sqlite connection """
        return self._conn

    @conn.setter
    def conn(self, conn):
        """ Set sqlite connection """
        self._conn = conn
        self.emit_changed = True

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

            if role == Qt.ToolTipRole:
                return (
                    "<font>"
                    + str(self.variant(index.row())[column_name]).replace(",", " ")
                    + "</font>"
                )

    def headerData(self, section, orientation=Qt.Horizontal, role=Qt.DisplayRole):
        """Overrided: Return column name
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

    def update_variant(self, row: int, variant={}):
        """Update a row

        Args:
            row (int): Description
        """

        # Update in database
        left = self.index(row, 0)
        right = self.index(row, self.columnCount() - 1)

        if left.isValid() and right.isValid():
            # Set id
            variant["id"] = self.variants[row]["id"]
            sql.update_variant(self.conn, variant)
            self.variants[row].update(variant)
            self.dataChanged.emit(left, right)

    def load(self, emit_changed=True, reset_page=False):
        """Load variant data into the model from query attributes

        Args:
            emit_changed (bool): emit the signal changed()

        Called by:
            - on_change_query() from the view.
            - sort() and setPage() by the model.
        """

        if self.conn is None:
            return

        self.beginResetModel()

        offset = self.page * self.limit

        self.variants.clear()

        # Add fields from group by

        for g in self.group_by:
            if g not in self.fields:
                self.fields.append(g)

        #  Store SQL query for debugging purpose
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

        #  Load variants
        self.variants = list(
            cmd.select_cmd(
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
        )

        # # Keep favorite and remove vrom data
        # self.favorite = [i["favorite"] for i in self.variants]
        # for i in self.variants:
        #     i.pop("favorite")

        if self.variants:
            self.headers = list(self.variants[0].keys())

        # Compute total
        if emit_changed:
            self.changed.emit()
            # Probably need to compute total ==> >Must be async !
            # But sqlite cannot be async ? Does it ?
            self.total = cmd.count_cmd(
                self.conn,
                fields=self.fields,
                source=self.source,
                filters=self.filters,
                group_by=self.group_by,
            )["count"]

        self.endResetModel()

    def load_from_vql(self, vql):

        try:
            vql_object = vql.parse_one_vql(vql)
            if "select_cmd" in vql_object:
                self.fields = vql_object["fields"]
                self.source = vql_object["source"]
                self.filters = vql_object["filters"]
        except Exception as e:
            raise e
        finally:
            self.load()

    def hasPage(self, page: int) -> bool:
        """ Return True if <page> exists otherwise return False """
        return page >= 0 and page * self.limit < self.total

    def setPage(self, page: int):
        """ set the page of the model """
        if self.hasPage(page):
            self.page = page
            self.load(emit_changed=False)

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
            self.load(emit_changed=False)

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


class VariantView(QWidget):
    """A Variant view with controller like pagination"""

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
        self.view = QTableView()
        self.bottom_bar = QToolBar()

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

        self.page_box = QComboBox()
        self.page_box.setEditable(True)
        self.page_box.setValidator(QIntValidator())
        self.page_box.setFixedWidth(50)
        self.page_box.setValidator(QIntValidator())

        self.info_label = QLabel()

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

        self.page_box.currentTextChanged.connect(self.on_page_changed)

        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(0, 0, 0, 0)

        main_layout.addWidget(self.view)
        main_layout.addWidget(self.bottom_bar)
        self.setLayout(main_layout)

        # broadcast focus signal

    def setModel(self, model: VariantModel):
        self.model = model
        self.view.setModel(model)

    def load(self):
        self.model.load()
        self.load_page_box()

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

        self.page_box.setCurrentText(str(self.model.page))

    def on_page_changed(self):
        if self.page_box.currentText() != "":
            page = int(self.page_box.currentText())
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
            self.set_pagging_enabled(True)

        self.info_label.setText(
            "{} row(s) {} page(s)".format(self.model.total, self.model.pageCount())
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
        current_variant = self.model.variant(current_index.row())

        if current_index.isValid():

            full_variant = sql.get_one_variant(self.conn, current_variant["id"])

            # Copy action: Copy the variant reference ID in to the clipboard
            formatted_variant = "{chr}:{pos}-{ref}-{alt}".format(**full_variant)
            menu.addAction(
                FIcon(0xF014C),
                formatted_variant,
                functools.partial(qApp.clipboard().setText, formatted_variant),
            )

            # Create favorite action
            fav_action = menu.addAction(self.tr("&Mark as favorite"))
            fav_action.setCheckable(True)
            fav_action.setChecked(bool(full_variant["favorite"]))
            fav_action.toggled.connect(lambda x: self.update_favorite(current_index, x))

            # Create classication action
            class_menu = menu.addMenu("Classification")
            for key, value in cm.CLASSIFICATION.items():

                action = class_menu.addAction(
                    FIcon(cm.CLASSIFICATION_ICONS[key]), value
                )
                action.setData(key)
                on_click = functools.partial(
                    self.update_classification, current_index, key
                )
                action.triggered.connect(on_click)

            # Comment action
            on_edit = functools.partial(self.edit_comment, current_index)
            menu.addAction(self.tr("&Edit comment ..."), on_edit)

            # Edit menu
            menu.addSeparator()
            menu.addAction(
                FIcon(0xF018F), "&Copy", self.copy_to_clipboard, QKeySequence.Copy
            )
            menu.addAction(
                FIcon(0xF0486), "&Select all", self.select_all, QKeySequence.SelectAll
            )

            # Display
            menu.exec_(event.globalPos())

    def update_favorite(self, index: QModelIndex, value=1):

        if index.isValid():
            update = {"favorite": int(value)}
            self.model.update_variant(index.row(), update)

    def update_classification(self, index: QModelIndex, value=3):

        if index.isValid():
            update = {"classification": int(value)}
            self.model.update_variant(index.row(), update)

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
        """Select the column with the given index"""
        index = self.view.model().index(row, 0)
        self.view.selectionModel().setCurrentIndex(
            index,
            QItemSelectionModel.SelectCurrent | QItemSelectionModel.Rows
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
        self.main_right_pane.conn = self.conn
        self.groupby_left_pane.conn = self.conn

        self.on_refresh()

    def on_refresh(self):
        """Overrided from PluginWidget"""
        # Save default data with current query attributes
        # See load(), we use this attr to restore fields after grouping
        self.save_fields = self.mainwindow.state.fields
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
        #print("left", self.groupby_left_pane.model.group_by)
        #print("right", self.main_right_pane.model.group_by)
        return self.groupby_left_pane.model.group_by != []

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
            # Groupby fields become left pane fields
            self.groupby_left_pane.model.fields = self.groupby_left_pane.model.group_by
            # Prune right fields with left fields => avoid redundancy of information
            self.main_right_pane.model.fields = [
                field for field in self.main_right_pane.model.fields
                if field not in self.groupby_left_pane.model.group_by
            ]
            # Refresh models
            self.main_right_pane.load()  # useless, except if we modify fields
            self.groupby_left_pane.load()
        else:
            # Restore fields
            self.main_right_pane.model.fields = self.save_fields
            # Refresh model
            self.main_right_pane.load()

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
            self.last_group = self.groupby_left_pane.model.group_by
        if not is_checked:
            # Reset to default group (chr set in _show_group_dialog)
            self._set_groups([])

        self.load()
        self._refresh_vql_editor()

        if not is_grouped:
            # Select the first row if grouped => refresh the right pane
            self.groupby_left_pane.select_row(0)

    def on_variant_clicked(self, index: QModelIndex):
        """React on variant clicked

        TODO : ugly...

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
                # self.groupby_left_pane.fields = self.save_fields
                self.groupby_left_pane.source = self.main_right_pane.model.source # laissé

                and_list = []
                for i in self.groupby_left_pane.group_by:
                    and_list.append({"field": i, "operator": "=", "value": variant[i]})

                self.main_right_pane.filters = {"AND": and_list}

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
            if field in self.groupby_left_pane.model.group_by and type(field) == str:
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

            self._set_groups(selected_fields)
            self.load()
            self._refresh_vql_editor()

            # Auto select first item of group by
            self.groupby_left_pane.select_row(0)

    def _set_groups(self, grouped_fields):
        """Set fields on groupby_left_pane and refresh text on groupby action"""
        self.groupby_left_pane.model.group_by = grouped_fields
        self.groupbylist_action.setText(",".join(grouped_fields))

    def _refresh_vql_editor(self):
        """Force refresh of vql_editor if loaded"""
        if "vql_editor" in self.mainwindow.plugins:
            self.mainwindow.state.group_by = self.groupby_left_pane.model.group_by
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

    conn = sql.get_sql_connexion(":memory:")
    reader = VcfReader(
        open("/home/sacha/Dev/cutevariant/examples/test.snpeff.vcf"), "snpeff"
    )
    import_reader(conn, reader)

    w = VariantViewWidget()

    w.conn = conn
    w.main_right_pane.model.conn = conn
    w.main_right_pane.load()
    # w.main_view.model.group_by = ["chr","pos","ref","alt"]
    # w.on_refresh()

    w.show()

    app.exec_()
