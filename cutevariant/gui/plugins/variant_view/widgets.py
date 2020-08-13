import re

from cutevariant.core import command as cmd
from cutevariant.core import vql
import cutevariant.commons as cm

from cutevariant.gui import plugin, FIcon
from cutevariant.gui import formatter

import math

from PySide2.QtWidgets import *
from PySide2.QtCore import *
from PySide2.QtGui import *

LOGGER = cm.logger()


# class VariantCounter(QThread):

#     countChanged = Signal(int)

#     def __init__(self):

#         super().__init__()

#         self.conn = None
#         self.fields = None
#         self.source = None
#         self.filters = None
#         self.group_by = None
#         self.total = 0

#     def run(self):
#         """ override """

#         print("RUN ")
#         self.total = cmd.count_cmd(
#             self.conn,
#             fields=self.fields,
#             source=self.source,
#             filters=self.filters,
#             group_by=self.group_by,
#         )["count"]

#         self.countChanged.emit(self.total)


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
        """Overrided : Return children count of index 
        """
        #  If parent is root

        return len(self.variants)

    def columnCount(self, parent=QModelIndex()):
        """Overrided: Return column count of parent . 

        Parent is not used here. 
        """
        return len(self.headers)

    def data(self, index: QModelIndex(), role=Qt.DisplayRole):
        """ Overrided: return index data according role.
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
            return None

        if self.variants and self.headers:

            column_name = self.headers[index.column()]

            #  ---- Display Role ----
            if role == Qt.DisplayRole and self.formatter is None:
                return str(self.variant(index.row())[column_name])

            if role == Qt.ToolTipRole:
                return (
                    "<font>"
                    + str(self.variant(index.row())[column_name]).replace(",", " ")
                    + "</font>"
                )

            # ------ Other Role -----

            if self.formatter:
                if role in self.formatter.supported_role():
                    value = str(self.variant(index.row())[column_name])
                    return self.formatter.item_data(column_name, value, role)

        return None

    def headerData(self, section, orientation, role=Qt.DisplayRole):
        """Overrided: Return column name 
        This method is called by the Qt view to display vertical or horizontal header data.

        Params:
            section (int): row or column number depending on orientation
            orientation (Qt.Orientation): Qt.Vertical or Qt.Horizontal
            role (Qt.ItemDataRole): https://doc.qt.io/qt-5/qt.html#ItemDataRole-enum

        Examples:
            # return 4th column name 
            column_name = model.headerData(4, Qt.Horizontal)

         """

        # Display columns headers
        if orientation == Qt.Horizontal:
            if role == Qt.DisplayRole:
                return self.headers[section]
        return None

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

        #  Add fields from group by

        for g in self.group_by:
            if g not in self.fields:
                self.fields.append(g)

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

        if self.variants:
            self.headers = list(self.variants[0].keys())

        #  Compute total
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
        except:
            pass
        else:
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
        #     """ Return variant data according index

        return self.variants[row]

        # class QueryDelegate(QStyledItemDelegate):

        # pass
        # """
        # This class specify the aesthetic of the view
        # styles and color of each variant displayed in the view are setup here

        # """

        # def background_color_index(self, index):
        # """ return background color of index """

        # base_brush = qApp.palette("QTableView").brush(QPalette.Base)
        # alternate_brush = qApp.palette("QTableView").brush(QPalette.AlternateBase)

        # if index.parent() == QModelIndex():
        # if index.row() % 2:
        # return base_brush
        # else:
        # return alternate_brush

        # if index.parent().parent() == QModelIndex():
        # return self.background_color_index(index.parent())

        # return base_brush     self.vertical_view_action = self.top_bar.addAction(FIcon())

        # def paint(self, painter, option, index):
        self.vertical_view_action = self.top_bar.addAction(FIcon())


# return super().paint(painter, option, index)


# def sizeHint(self, option, index):
# """Override: Return row height"""

# size = super().sizeHint(option, index)
# size.setHeight(30)
# return size


# super().__init__()


# def focusInEvent(self, event: QFocusEvent):
#     self.setStyleSheet("QTableView{ border: 1px solid palette(highlight)}")
#     self.focusChanged.emit(True)

# def focusOutEvent(self, event: QFocusEvent):
#     self.setStyleSheet("QTableView{ border: 1px solid palette(shadow)}")
#     self.focusChanged.emit(False)


class VariantView(QWidget):

    """A Variant view with controller like pagination
    
    """

    view_clicked = Signal()

    def __init__(self, parent=None):
        super().__init__()

        self.view = QTableView()
        self.bottom_bar = QToolBar()

        # self.view.setFrameStyle(QFrame.NoFrame)
        self.view.setAlternatingRowColors(True)
        self.view.horizontalHeader().setStretchLastSection(True)
        self.view.setSelectionMode(QAbstractItemView.SingleSelection)
        self.view.verticalHeader().hide()

        self.view.setSortingEnabled(True)
        self.view.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.view.setSelectionMode(QAbstractItemView.ContiguousSelection)
        ## self.view.setIndentation(0)
        self.view.setIconSize(QSize(22, 22))
        # self.view.setItemDelegate(self.delegate)
        self.view.horizontalHeader().setSectionsMovable(True)

        # Setup model
        self.model = VariantModel()
        self.view.setModel(self.model)

        #  setup toolbar
        spacer = QWidget()
        spacer.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)

        self.page_box = QComboBox()
        self.page_box.setEditable(True)
        self.page_box.setValidator(QIntValidator())
        self.page_box.setFixedWidth(50)
        self.page_box.setValidator(QIntValidator())

        self.info_label = QLabel()

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

        self.page_box.setCurrentText(str(self.model.page))

    def on_page_changed(self):
        if self.page_box.currentText() != "":
            page = int(self.page_box.currentText())
            self.model.setPage(page)

    def load_page_box(self):
        """Load Bottom toolbar with pagination 
        """
        self.page_box.clear()
        if self.model.pageCount() - 1 == 0:
            self.set_pagging_enabled(False)
        else:
            self.page_box.addItems([str(i) for i in range(self.model.pageCount())])
            self.page_box.validator().setRange(0, self.model.pageCount() - 1)
            self.set_pagging_enabled(True)

        self.info_label.setText(
            "{} row(s) {} page(s)".format(self.model.total, self.model.pageCount())
        )

    def set_pagging_enabled(self, active=True):
        self.page_box.setEnabled(active)
        for action in self.pagging_actions:
            action.setEnabled(active)


class VariantViewWidget(plugin.PluginWidget):
    """Contains the view of query with several controller"""

    variant_clicked = Signal(dict)
    LOCATION = plugin.CENTRAL_LOCATION

    ENABLE = True

    def __init__(self, parent=None):
        super().__init__(parent)

        # Create 2 Pane
        self.splitter = QSplitter(Qt.Vertical)
        self.first_pane = VariantView()
        self.second_pane = VariantView()
        self.second_pane.hide()

        self.splitter.addWidget(self.first_pane)
        self.splitter.addWidget(self.second_pane)

        # Make resizable TODO : ugly ... Make it nicer
        def _resize1_section(l, o, n):
            self.second_pane.view.horizontalHeader().resizeSection(l, n)

        def _resize2_section(l, o, n):
            self.first_pane.view.horizontalHeader().resizeSection(l, n)

        self.first_pane.view.horizontalHeader().sectionResized.connect(_resize1_section)
        self.second_pane.view.horizontalHeader().sectionResized.connect(
            _resize2_section
        )

        # self.second_pane.view.setHorizontalHeader(self.first_pane.view.horizontalHeader())

        #  Common toolbar
        self.top_bar = QToolBar()
        self.top_bar.setToolButtonStyle(Qt.ToolButtonTextBesideIcon)

        self.groupby_act_gp = QActionGroup(self)
        self.groupby_act_gp.setExclusive(True)
        self.groupby_act_gp.setVisible(False)

        # checkable group action
        self.groupby_action = self.top_bar.addAction(
            FIcon(0xF14E0), "Group by", self.on_group_changed,
        )
        self.groupby_action.setCheckable(True)

        # List group action
        self.groupby_actions = []  # List of actions
        self.groupby_act_list = QToolButton()
        self.groupby_act_list.setIcon(FIcon(0xF0756))
        self.groupby_act_list.setToolButtonStyle(Qt.ToolButtonTextBesideIcon)
        self.groupby_act_list.setPopupMode(QToolButton.InstantPopup)
        self._groupby_act_list = QWidgetAction(self)
        self._groupby_act_list.setDefaultWidget(self.groupby_act_list)
        self.top_bar.addAction(self._groupby_act_list)

        # vertical group view button
        self.vertical_view_action = self.top_bar.addAction(
            FIcon(0xF0575, self.palette().color(QPalette.Highlight)),
            "view 1",
            lambda: self.set_view_orientation(Qt.Vertical),
        )
        self.vertical_view_action.setCheckable(True)
        self.vertical_view_action.setChecked(True)  # Default
        self.top_bar.addAction(self.vertical_view_action)
        # horizontal group view button
        self.horizontal_view_action = self.top_bar.addAction(
            FIcon(0xF0BCC, self.palette().color(QPalette.Highlight)),
            "view 2",
            lambda: self.set_view_orientation(Qt.Horizontal),
        )
        self.horizontal_view_action.setCheckable(True)
        self.top_bar.addAction(self.horizontal_view_action)

        self.groupby_act_gp.addAction(self.vertical_view_action)
        self.groupby_act_gp.addAction(self.horizontal_view_action)
        self.groupby_act_gp.addAction(self._groupby_act_list)

        self.first_pane.view.clicked.connect(self.on_variant_clicked)

        #  Formatter tools
        self.top_bar.addSeparator()
        # spacer = QWidget()
        # spacer.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        # self.top_bar.addWidget(spacer)
        self.formatter_combo = QComboBox()
        for i in formatter.find_formatters():
            self.formatter_combo.addItem(i.__name__, i)
        self.top_bar.addWidget(self.formatter_combo)
        self.formatter_combo.currentTextChanged.connect(self.on_formatter_changed)

        #  setup layout
        ## Build stack view

        self.top_bar.addSeparator()
        self.top_bar.addAction(FIcon(0xF0450), "Refresh", self.on_refresh)

        main_layout = QVBoxLayout()
        main_layout.addWidget(self.top_bar)
        main_layout.addWidget(self.splitter)

        self.setLayout(main_layout)

    def on_formatter_changed(self):

        Formatter = self.formatter_combo.currentData()
        self.first_pane.model.formatter = Formatter()
        self.second_pane.model.formatter = Formatter()

    def on_open_project(self, conn):
        """override """
        self.conn = conn
        self.first_pane.conn = self.conn
        self.second_pane.conn = self.conn

        self.on_refresh()
        self.reset()

    def on_refresh(self):
        """ override """

        self.first_pane.fields = self.mainwindow.state.fields
        self.first_pane.source = self.mainwindow.state.source
        self.first_pane.filters = self.mainwindow.state.filters
        self.first_pane.group_by = self.mainwindow.state.group_by

        self.first_pane.model.formatter = next(formatter.find_formatters())()
        self.second_pane.model.formatter = next(formatter.find_formatters())()

        # self.main_view.model.group_by = ["chr","pos","ref","alt"]

        self.first_pane.load()
        self.load_group_fields()

        self.groupby_action.setChecked(bool(self.first_pane.model.group_by))
        self.groupby_act_gp.setVisible(bool(self.first_pane.model.group_by))
        self.set_view_split(self.groupby_action.isChecked())

        # self.show_group_column_only(self.horizontal_view_action.isChecked())

    def on_group_changed(self):

        is_checked = self.groupby_action.isChecked()

        if is_checked:
            checked_fields = [
                action.text() for action in self.groupby_actions if action.isChecked()
            ]

            if not checked_fields:  # By default, add one groupby
                checked_fields = [self.groupby_actions[0].text()]

        else:
            checked_fields = []
            self.reset()

        self.mainwindow.state.group_by = checked_fields
        self.on_refresh()

        #  refresh source editor plugin
        if "vql_editor" in self.mainwindow.plugins:
            plugin = self.mainwindow.plugins["vql_editor"]
            plugin.on_refresh()

    def reset(self):
        self.set_view_split(False)
        self.groupby_act_gp.setVisible(False)
        self.groupby_action.setChecked(False)
        self.first_pane.model.order_by = None

    def load_group_fields(self):
        self.groupby_actions = []
        self.groupby_menu = QMenu()
        self.groupby_menu.setTearOffEnabled(True)
        for field in self.first_pane.model.fields:
            if type(field) == str:  # Avoid tuple ...
                action = self.groupby_menu.addAction(field, self.on_group_changed)
                action.setCheckable(True)
                if field in self.first_pane.model.group_by:
                    action.setChecked(True)
                self.groupby_actions.append(action)

        self.groupby_act_list.setMenu(self.groupby_menu)
        self.groupby_act_list.setText(
            "Group by " + ",".join(self.first_pane.model.group_by)
        )

    def set_view_orientation(self, orientation):
        if orientation == Qt.Vertical:
            self.splitter.setOrientation(Qt.Vertical)
            self.show_group_column_only(False)

        if orientation == Qt.Horizontal:
            self.splitter.setOrientation(Qt.Horizontal)
            self.show_group_column_only(True)

        if "count" in self.first_pane.model.headers:
            self.first_pane.view.setColumnHidden(
                self.first_pane.model.headers.index("count"), orientation == Qt.Vertical
            )

    def set_view_split(self, active=True):

        if active:
            self.second_pane.setVisible(True)
            if self.vertical_view_action.isChecked():
                self.set_view_orientation(Qt.Vertical)
            else:
                self.set_view_orientation(Qt.Horizontal)
        else:
            self.second_pane.setVisible(False)
            self.show_group_column_only(False)

    # def on_group_changed(self):

    #     # TODO : must be user defined

    #     # When Horizontal view is enable, we hide some columns not in GP
    #     # hidden_col = [
    #     #     self.first_pane.model.headers.index(i) for i in GP if i in self.first_pane.model.headers
    #     # ]

    #     self.groupby_act_gp.setVisible(self.groupby_action.isChecked())
    #     self.second_pane.setVisible(self.groupby_action.isChecked())

    #     if self.groupby_action.isChecked() is False:
    #         checked_fields = []
    #     else:
    #         checked_fields = [
    #             action.text() for action in self.groupby_actions if action.isChecked()
    #         ]

    #     self.mainwindow.state.group_by = checked_fields
    #     #  refresh source editor plugin
    #     if "vql_editor" in self.mainwindow.plugins:
    #         plugin = self.mainwindow.plugins["source_editor"]
    #         plugin.on_refresh()

    #     self.on_refresh()

    def show_group_column_only(self, active=True):

        for i, val in enumerate(self.first_pane.model.headers):
            if val not in self.first_pane.model.group_by + ["count"] and active is True:
                self.first_pane.view.setColumnHidden(i, True)
            else:
                self.first_pane.view.setColumnHidden(i, False)

        # hidden_col = [
        #     self.first_pane.model.headers.index(i) for i in GP if i in self.first_pane.model.headers
        # ]

    def on_variant_clicked(self, index: QModelIndex):

        variant = self.first_pane.model.variant(index.row())

        self.second_pane.fields = self.first_pane.model.fields
        self.second_pane.source = self.first_pane.model.source

        and_list = []
        for i in self.first_pane.group_by:
            and_list.append({"field": i, "operator": "=", "value": variant[i]})

        self.second_pane.filters = {"AND": and_list}

        self.second_pane.load()
        self.second_pane.load_page_box()

        #  Refresh plugins when clicked
        self.mainwindow.state.current_variant = variant
        self.mainwindow.refresh_plugins(sender=self)


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

    # w.on_open_project(conn)
    # w.main_view.model.group_by = ["chr","pos","ref","alt"]
    # w.on_refresh()

    w.show()

    app.exec_()
