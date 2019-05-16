"""Widget to display variants from a query in the GUI.

ViewQueryWidget class is added to a QTabWidget and is seen by the user;
it uses QueryModel class as a model that handles records from the database.
QueryDelegate class handles the aesthetic of the view.
"""

# Standard imports
import copy
import csv

# Qt imports
from PySide2.QtWidgets import *
from PySide2.QtCore import *
from PySide2.QtGui import *

# Custom imports
from cutevariant.gui.ficon import FIcon
from .plugin import QueryPluginWidget
from cutevariant.core import Query
from cutevariant.core import sql
from cutevariant.gui import style
from cutevariant.gui.infovariantwidget import VariantPopupMenu
from cutevariant.commons import logger
from cutevariant.commons import GENOTYPE_ICONS

LOGGER = logger()


class QueryModel(QAbstractItemModel):
    """
    QueryModel is the base class to display variant in the view.
    It can load paginated data using limit and page attribute.

    Attributes:
        limit(int): Variant count to display. See SQL LIMIT
        page(int): current page to display. See SQL OFFSET
        total(int): Total variant count
        variants(list): Internal data to store variants

    """

    def __init__(self, parent=None):
        super().__init__()
        self.limit = 50
        self.page = 0
        self.total = 0
        self._query = None
        self.variants = []

    def is_root(self, index: QModelIndex) -> bool:
        """
        Return True if the parent of index is the invisible root index
        """
        return index == QModelIndex()

    def rowCount(self, parent=QModelIndex()):
        """
        Overrided : Return model row count
        """
        #  If parent is root

        if parent == QModelIndex():
            return len(self.variants)

        if parent.parent() == QModelIndex():
            return len(self.variants[parent.row()]) - 1  # Omit first

        # Get parent variant row ID and return children count
        # if self.row_id(parent) in self.children:
        #     return len(self.children[parent.row()])
        # else:
        # return 0

    def columnCount(self, parent=QModelIndex()):
        """Overrided: Return column count """

        # If no query is defined
        if not self._query:
            return 0

        return len(self._query.columns) + 1  #  show children count for the first col

    def index(self, row, column, parent=QModelIndex()):
        """Overrided: Return index """

        if not self.hasIndex(row, column, parent):
            return QModelIndex()

        # if parent is root
        if parent == QModelIndex():
            return self.createIndex(row, column, None)

        # if parent is first level
        if parent.parent() == QModelIndex():
            return self.createIndex(row, column, parent.row())

    def parent(self, child):
        """Overrided: Return parent of child """

        if not child.isValid():
            return QModelIndex()

        if child.internalId() == None:
            return QModelIndex()

        else:
            return self.index(child.internalId(), 0, QModelIndex())

    def data(self, index, role=Qt.DisplayRole):
        """ Overrided: return value of index according role  """

        if not index.isValid():
            return None

        #  ---- DISPLAY ROLE ----
        if role == Qt.DisplayRole:
            #  Display the first level
            if index.parent() == QModelIndex():
                if index.column() == 0:
                    # First column display children count
                    return str(self.children_count(index))
                elif index.column() not in self.indexes_in_group_by:
                    # Mask columns not concerned by the group by
                    # These columns have an arbitrary value choosen among all retrieved values
                    # ..seealso:: load()
                    return "..."
                else:
                    # Other display variant data
                    return str(self.variants[index.row()][0][index.column()])

            #  Display the second level ( children )
            if index.parent().parent() == QModelIndex():
                if index.column() == 0 or index.column() in self.indexes_in_group_by:
                    # No children for the first columns
                    # Don't show redondant data for columns that are in the group by
                    return ""
                else:
                    #  Display children data
                    return str(
                        self.variants[index.parent().row()][index.row()][index.column()]
                    )

        #  ----- ICON ROLE ---
        if role == Qt.DecorationRole:
            if (
                index.parent() == QModelIndex()
                and index.column() == 0
                and self.hasChildren(index)
            ):
                return self._draw_children_count_icon(self.variants[index.row()][0][-1])

        return None

    def headerData(self, section, orientation, role=Qt.DisplayRole):
        """Overrided: Return column name as header data """

        #  Display columns headers
        if orientation == Qt.Horizontal:
            if role == Qt.DisplayRole:
                if section == 0:
                    return "children"
                else:
                    col = self._query.columns[section - 1]
                    if type(col) == tuple and len(col) == 3:  #  show functions
                        fct, arg, field = col
                        return f"{fct}({arg}).{field}"
                    else:
                        return self._query.columns[section - 1]

        return None

    def hasChildren(self, parent: QModelIndex) -> bool:
        # return False
        """Overrided: Return True if parent has children """
        # if invisible root node, always return True
        if parent == QModelIndex():
            return True

        if parent.parent() == QModelIndex():
            children_count = self.children_count(parent)
            return children_count > 1

        return False

        # if parent.parent() == QModelIndex():
        #     return self._children_count(parent) > 1

    def canFetchMore(self, parent: QModelIndex) -> bool:
        """ Overrided """
        return self.hasChildren(parent)

    def fetchMore(self, parent: QModelIndex):
        """
        Overrided

        Fetch more annotation when row is expand

        """
        if parent == QModelIndex():
            return

        #  get sql variant id
        variant_id = self.variants[parent.row()][0][0]

        columns = ",".join(self._query.get_columns(do_not_add_default_things=True))
        joints = self._query.get_joints()

        #  TODO : need to put this into QUERY
        # TODO: add filter into left join annotations ... instead in where
        sub_query = f"""SELECT variants.id, {columns} FROM variants
        {joints}
        WHERE annotations.variant_id = {variant_id}"""
        print("SUB QUERY", sub_query)

        records = list(self._query.conn.cursor().execute(sub_query).fetchall())

        # Insert children
        self.beginInsertRows(parent, 0, len(records))

        # Clear pevious children
        self.variants[parent.row()][1:] = []

        for idx, record in enumerate(records):  # skip first records
            self.variants[parent.row()].append(tuple(record))

        self.endInsertRows()

    def children_count(self, index: QModelIndex):
        """Return children count from variant

        This one is the last value of sql record output and correspond to the COUNT(annotation)
        of the GROUP BY
        """
        return self.variants[index.row()][0][-1]

    @property
    def query(self):
        return self._query

    @query.setter
    def query(self, query: Query):
        # PS: default group by method: ("chr","pos","ref","alt")
        self._query = query

    def load(self):
        """Load variant data into the model from query attributes

        Called by:
            - on_change_query() from the view.
            - sort() and setPage() by the model.
        """
        self.beginResetModel()
        # Set total of variants for pagination
        self.total = self.query.variants_count()

        # Get columns not concerned by the group by in order to mask them
        # These columns have an arbitrary value choosen among all retrieved values
        # ..seealso:: Masking is made in data()
        self.indexes_in_group_by = {
            index
            for index, col in enumerate(self._query.columns, 1)
            if col in self._query.group_by
        }

        # Append a list because child can be append after
        self.variants = [
            [tuple(variant)]
            for variant in self._query.items(self.limit, self.page * self.limit)
        ]

        LOGGER.debug("QueryModel:load:: variants queried\n%s", self.variants)
        self.endResetModel()

    def group_by_changed(self, group_by_columns):
        """Slot called when the currentIndex in the combobox changes
        either through user interaction or programmatically

        It triggers a reload of the model and a change of the group by
        command of the query.
        """
        self._query.group_by = group_by_columns
        self.load()

    def sort(self, column: int, order):
        """Overrided"""
        if column < self.columnCount():
            colname = self._query.columns[column]

            print("ORDER", order)
            self._query.order_by = colname
            self._query.order_desc = order == Qt.DescendingOrder
            self.load()

    def hasPage(self, page):
        return page >= 0 and page * self.limit < self.total

    def setPage(self, page):
        if self.hasPage(page):
            self.page = page
            self.load()

    def displayed(self):
        """Get ids of first, last displayed variants on the total number

        :return: Tuple with (first_id, last_id, self.total).
        :rtype: <tuple <int>,<int>,<int>>
        """
        first_id = self.limit * self.page

        if self.hasPage(self.page + 1):
            # Remainder : self.total - (self.limit * (self.page + 1)))
            last_id = self.limit * (self.page + 1)
        else:
            # Remainder : self.total - (self.limit * self.page)
            last_id = self.total

        return (first_id, last_id, self.total)

    def nextPage(self):
        """Display the next page of data if it exists"""
        if self.hasPage(self.page + 1):
            self.setPage(self.page + 1)

    def previousPage(self):
        """Display the previous page of data if it exists"""
        if self.hasPage(self.page - 1):
            self.setPage(self.page - 1)

    def firstPage(self):
        self.setPage(0)

    def lastPage(self):
        self.setPage(int(self.total / self.limit))

    def variant(self, index: QModelIndex):

        if index.parent() == QModelIndex():
            return self.variants[index.row()][0]

        if index.parent().parent() == QModelIndex():
            return self.variants[index.parent().row()][index.row()]

    def _draw_children_count_icon(self, count: int) -> QIcon:

        pix = QPixmap(48, 41)
        pix.fill(Qt.transparent)
        painter = QPainter()
        painter.begin(pix)
        painter.setBrush(QColor("#f1646c"))
        painter.setPen(Qt.NoPen)
        painter.drawRoundedRect(pix.rect().adjusted(1, 1, -1, -1), 10, 10)
        font = QFont()
        font.setBold(True)
        font.setPixelSize(25)
        painter.setFont(font)
        painter.setPen(Qt.white)
        painter.drawText(pix.rect(), Qt.AlignCenter, str(count))

        painter.end()

        return QIcon(pix)


class QueryDelegate(QStyledItemDelegate):
    """
    This class specify the aesthetic of the view

    styles and color of each variant displayed in the view are setup here


    """

    def paint(self, painter, option, index):
        """
        overriden

        Draw the view item for index using a painter

        """

        palette = qApp.palette("QTreeView")
        #  get column name of the index
        colname = index.model().headerData(index.column(), Qt.Horizontal)

        #  get value of the index
        value = index.data(Qt.DisplayRole)

        # get select sate
        select = option.state & QStyle.State_Selected

        #  draw selection if it is
        if not select:
            bg_brush = option.backgroundBrush
        else:
            bg_brush = palette.brush(QPalette.Highlight)

        painter.setBrush(bg_brush)
        painter.setPen(Qt.NoPen)
        painter.drawRect(option.rect)

        alignement = Qt.AlignLeft | Qt.AlignVCenter

        # # Add margin for first columns if index is first level
        # if index.column() == 0 and index.parent() == QModelIndex():

        #     expanded = bool(option.state & QStyle.State_Open)

        #     branch_option = copy.copy(option)
        #     branch_option.rect.setWidth(65)

        #     qApp.style().drawPrimitive(QStyle.PE_IndicatorBranch, branch_option, painter)

        #     icon = index.data(Qt.DecorationRole)
        #     if icon:
        #         target = QRect(0,0, option.decorationSize.width(), option.decorationSize.height())
        #         target.moveCenter(option.rect.center())
        #         painter.drawPixmap(option.rect.x()+5, target.top() ,icon.pixmap(option.decorationSize))

        # if index.column() == 0:
        #     option.rect.adjust(40,0,0,0)

        # Draw cell depending column name
        if colname == "impact":
            painter.setPen(
                QPen(style.IMPACT_COLOR.get(value, palette.color(QPalette.Text)))
            )
            painter.drawText(option.rect, alignement, str(index.data()))
            return

        if colname == "gene":
            painter.setPen(QPen(style.GENE_COLOR))
            painter.drawText(option.rect, alignement, str(index.data()))
            return

        if "genotype" in colname and value != "...":
            val = int(value)

            icon_path = GENOTYPE_ICONS.get(val, -1)
            icon = QPixmap(icon_path).scaled(16, 16)
            painter.setRenderHint(QPainter.Antialiasing)
            painter.drawPixmap(option.rect.left(), option.rect.center().y() - 8, icon)
            return

        painter.setPen(
            QPen(palette.color(QPalette.HighlightedText if select else QPalette.Text))
        )
        painter.drawText(option.rect, alignement, str(index.data()))

    def draw_biotype(self, value):
        pass

    def sizeHint(self, option, index):
        """Override: Return row height"""
        return QSize(0, 30)


class ViewQueryWidget(QueryPluginWidget):
    """Contains the view of query with several controller"""

    variant_clicked = Signal(dict)

    def __init__(self):
        super().__init__()
        self.model = QueryModel()
        self.delegate = QueryDelegate()
        self.setWindowTitle(self.tr("Variants"))
        self.topbar = QToolBar()
        self.bottombar = QToolBar()
        self.view = QTreeView()

        # self.view.setFrameStyle(QFrame.NoFrame)
        self.view.setModel(self.model)
        self.view.setItemDelegate(self.delegate)
        self.view.setAlternatingRowColors(True)
        self.view.setSortingEnabled(True)
        self.view.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.view.setSelectionMode(QAbstractItemView.ContiguousSelection)
        self.view.setRootIsDecorated(True)  # Manage from delegate
        # self.view.setIndentation(0)
        self.view.setIconSize(QSize(22, 22))
        self.view.setAnimated(True)
        self.view.setStyleSheet("QAbstractScrollArea {border-left: 20px solid red}")

        # self.view.setItemDelegate(self.delegate)

        main_layout = QVBoxLayout()
        main_layout.addWidget(self.topbar)
        main_layout.addWidget(self.view)
        main_layout.addWidget(self.bottombar)
        main_layout.setContentsMargins(0, 0, 0, 0)

        # Construct top bar
        # These actions should be disabled until a query is made (see query setter)
        self.export_csv_action = self.topbar.addAction(
            self.tr("Export variants"), self.export_csv
        )
        self.export_csv_action.setEnabled(False)

        # Add spacer to push next buttons to the right
        spacer = QWidget()
        spacer.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.topbar.addWidget(spacer)

        # Add combobox to choose the grouping method of variants
        self.topbar.addWidget(QLabel(self.tr("Group by method:")))
        self.group_by_combobox = QComboBox()
        combobox_text_data = {
            "variant (chr, pos, ref, alt)": ("chr", "pos", "ref", "alt"),
            "site (chr, pos)": ("chr", "pos"),
        }
        for text, data in combobox_text_data.items():
            self.group_by_combobox.addItem(text, data)
        self.topbar.addWidget(self.group_by_combobox)
        self.group_by_combobox.currentIndexChanged.connect(self.on_group_by_changed)

        # Construct bottom bar
        # These actions should be disabled until a query is made (see query setter)
        self.page_info = QLabel()
        self.page_box = QLineEdit()
        self.page_box.setReadOnly(False)
        self.page_box.setValidator(QIntValidator())
        # self.page_box.setFrame(QFrame.NoFrame)
        self.page_box.setFixedWidth(50)
        self.page_box.setAlignment(Qt.AlignHCenter)
        self.page_box.setStyleSheet("QWidget{background-color: transparent;}")
        self.page_box.setText("0")
        self.page_box.setFrame(QFrame.NoFrame)
        spacer = QWidget()
        spacer.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        # Setup actions
        self.show_sql_action = self.bottombar.addAction(
            FIcon(0xF865), self.tr("See SQL query"), self.show_sql
        )
        self.show_sql_action.setEnabled(False)
        self.bottombar.addWidget(self.page_info)
        self.bottombar.addWidget(spacer)
        self.bottombar.addAction(FIcon(0xF792), "<<", self.model.firstPage)
        self.bottombar.addAction(FIcon(0xF04D), "<", self.model.previousPage)
        self.bottombar.addWidget(self.page_box)
        self.bottombar.addAction(FIcon(0xF054), ">", self.model.nextPage)
        self.bottombar.addAction(FIcon(0xF793), ">>", self.model.lastPage)

        self.bottombar.setIconSize(QSize(16, 16))
        self.bottombar.setMaximumHeight(30)

        self.bottombar.setContentsMargins(0, 0, 0, 0)

        self.setLayout(main_layout)

        self.model.modelReset.connect(self.updateInfo)

        # Create menu
        self.context_menu = VariantPopupMenu()

        # emit variant when clicked
        self.view.clicked.connect(self._variant_clicked)
        self.page_box.returnPressed.connect(self._update_page)

    def on_init_query(self):
        """Method override from AbstractQueryWidget"""
        self.export_csv_action.setEnabled(True)
        self.show_sql_action.setEnabled(True)
        self.model.query = self.query

    def on_change_query(self):
        """Method override from AbstractQueryWidget"""
        #  reset current page
        self.model.page = 0
        self.model.load()
        self.view.header().setSectionResizeMode(0, QHeaderView.ResizeToContents)

    def updateInfo(self):
        """Update metrics for the current query

        .. note:: Update page_info and page_box.
        """

        # Set text
        self.page_info.setText(
            self.tr("{} variant(s)  {}-{} of {}").format(
                self.model.total, *self.model.displayed()
            )
        )
        page_box_text = str(self.model.page)
        self.page_box.setText(page_box_text)

        # Adjust page_èbox size to content
        fm = self.page_box.fontMetrics()
        # self.page_box.setFixedWidth(fm.boundingRect(page_box_text).width() + 5)

    def _variant_clicked(self, index):
        """Slot called when the view (QTreeView) is clicked

        .. note:: Emit variant through variant_clicked signal.
            This signal updates InfoVariantWidget.
        .. note:: Is also called manually by contextMenuEvent() in order to
            get the variant and refresh InfoVariantWidget when the
            ContextMenuEvent is triggered.
        :return: The variant.
        :rtype: <dict>
        """
        # Get the rowid of the element at the given index
        rowid = self.model.variant(index)[0]
        # Get data from database
        variant = sql.get_one_variant(self.model.query.conn, rowid)
        # Emit variant through variant_clicked signal
        self.variant_clicked.emit(variant)
        return variant

    def export_csv(self):
        """Export variants displayed in the current view to a CSV file"""
        filepath, filter = QFileDialog.getSaveFileName(
            self,
            self.tr("Export variants of the current view"),
            "view.csv",
            self.tr("CSV (Comma-separated values) (*.csv)"),
        )

        if not filepath:
            return

        with open(filepath, "w") as f_d:
            writer = csv.writer(f_d, delimiter=",")
            # Write headers (columns in the query) + variants from the model
            writer.writerow(self.model.query.columns)
            # Duplicate the current query, but remove automatically added columns
            # and remove group by/order by commands.
            # Columns are kept as they are selected in the GUI
            query = copy.copy(self.model.query)
            query.group_by = None
            query.order_by = None
            # Query the database
            writer.writerows(
                query.conn.execute(query.sql(do_not_add_default_things=True))
            )

    def on_group_by_changed(self, index):
        """Slot called when the currentIndex in the combobox changes
        either through user interaction or programmatically

        It triggers a reload of the model and a change of the group by
        command of the query.
        """
        self.model.group_by_changed(self.group_by_combobox.currentData())

    def show_sql(self):
        box = QMessageBox()
        try:
            text = self.model.query.sql()
        except AttributeError:
            text = self.tr("No query to show")

        box.setInformativeText(text)
        box.exec_()

    def contextMenuEvent(self, event: QContextMenuEvent):
        """Overrided method: Show custom context menu associated to the current variant"""
        # Get the variant (and refresh InfoVariantWidget)
        current_index = self.view.currentIndex()
        variant = self._variant_clicked(current_index)
        # Show the context menu with the given variant
        self.context_menu.popup(variant, event.globalPos())

    def _update_page(self):
        """Set page from page_box edit. When user set a page manually, this method is called"""
        self.model.setPage(int(self.page_box.text()))

        self.page_box.clearFocus()
