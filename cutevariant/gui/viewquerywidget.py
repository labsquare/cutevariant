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
    QueryModel is a Qt model class which contains variants datas from sql Query. 
    It loads paginated data from Query and create an interface for a Qt view.
    When a variant belong to many transcripts, duplicate variants are grouped by (chr,pos,ref,alt) 
    and stored as a Tree structure. Variant row can then be expanded to display each transcript annotation. 

    See Qt model/view programming for more information
    https://doc.qt.io/qt-5/model-view-programming.html

    Variants are stored internally as a list of variants. By default, there is only one transcript per row. 
    When user expand the row, it will append duplicates variants as children. 
    For example, this is a tree with 2 variants , each of them refer to many transcripts. 

    self.variants = [ 
        [(chr1,2434,A,T, transcriptA),(chr1,2434,A,T, transcriptB),(chr1,2434,A,T, transcriptC)],
        [(chr1,9999,C,T, transcriptA),(chr1,9999,C,T, transcriptB),(chr1,9999,C,T, transcriptC),(chr1,9999,C,T, transcriptD]
        ]
    ]

    ├── chr1,2434,A,T, transcriptA  # Cannonical transcripts
    │   ├── chr1,2434,A,T, transcriptB
    │   ├── chr1,2434,A,T, transcriptC
    ├── chr1,9999,C,T, transcriptA # Cannonical transcripts
    │   ├── chr1,9999,C,T, transcriptB
    │   ├── chr1,9999,C,T, transcriptC
    │   ├── chr1,9999,C,T, transcriptD

    Attributes:
        limit(int): Variant count to display. See SQL LIMIT
        page(int): current page to display. See SQL OFFSET
        total(int): Total variant count
        variants(list): Internal data to store variants

    Example:
        model = QueryModel()
        view = QTreeView()
        view.setModel(model)
        model.setQuery(query)

    """

    def __init__(self, parent=None):
        super().__init__()
        self.limit = 50
        self.page = 0
        self.total = 0
        self._query = None
        self.variants = []

    def level(self, index: QModelIndex) -> bool:
        """Return level of index. 

        Args:
            index (QModelIndex): The model index

        Returns: 
            int: 0 if index is the invisible root , 1 if index is a variant parent, 2 if index is a variant child  
        """

        if index == QModelIndex():
            return 0

        if index.parent() == QModelIndex():
            return 1

        if index.parent().parent() == QModelIndex():
            return 2

    def rowCount(self, parent=QModelIndex()):
        """Overrided : Return children count of index 
        """
        #  If parent is root
        if self.level(parent) == 0:
            return len(self.variants)

        if self.level(parent) == 1:
            return len(self.variants[parent.row()]) - 1  # Omit first

    def columnCount(self, parent=QModelIndex()):
        """Overrided: Return column count of parent . 

        Parent is not used here. 
        """

        # If no query is defined, return nothing
        if not self._query:
            return 0

        #  return query columns + child count columns
        #  children count - chr - pos .....
        return len(self._query.columns) + 1

    def index(self, row: int, column: int, parent=QModelIndex()) -> QModelIndex:
        """Overrided: Create a new model index from row, column and parent  
        
        Args:
            row (int): row number
            column (int): column number
            parent (QModelIndex): parent index

        """

        # avoid error
        if not self.hasIndex(row, column, parent):
            return QModelIndex()

        # Create index for variant as parent
        if self.level(parent) == 0:
            # createIndex take None as internalId. @see self.parent()
            return self.createIndex(row, column, None)

        # Create index for variant as child
        if self.level(parent) == 1:
            # createIndex take parent.row() as internalId . @see self.parent()
            return self.createIndex(row, column, parent.row())

    def parent(self, index: QModelIndex()) -> QModelIndex:
        """Overrided: Return the parent of index """

        #  avoid error
        if not index.isValid():
            return QModelIndex()

        #  If internalId is None, index is a variant parent
        if index.internalId() == None:
            return QModelIndex()

        # Otherwise, index is a variant child at position row=internalid in the parent
        else:
            return self.index(index.internalId(), 0, QModelIndex())

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

        #  ---- Display Role ----
        if role == Qt.DisplayRole:
            # Return data for the first level
            if self.level(index) == 1:
                # First column correspond to children count
                if index.column() == 0:
                    return str(self.children_count(index))
                # Other data come from internal self.variants list
                else:
                    return str(self.variant(index)[index.column()])
                    # return str(self.variants[index.row()][0][index.column()])

            # Return data for the second level
            if self.level(index) == 2:
                if index.column() == 0:
                    # No children for the first columns
                    return ""
                else:
                    #  Display children data
                    return str(self.variant(index)[index.column()])
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
        """Overrided: Return True if parent index has children """

        # if invisible root node, always return True
        if parent == QModelIndex():
            return True

        if self.level(parent) == 1:
            children_count = self.children_count(parent)
            return children_count >= 1

        return False

        # if parent.parent() == QModelIndex():
        #     return self._children_count(parent) > 1

    def canFetchMore(self, parent: QModelIndex) -> bool:
        """ Overrided : Return True if children fetching is required """
        return self.hasChildren(parent)

    def fetchMore(self, parent: QModelIndex):
        """Overrided: Fetch children variant 
        """

        # avoid error
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
        LOGGER.debug(
            "QueryModel:fetchMore:: Extra children cols sub query %s", sub_query
        )

        records = list(self._query.conn.cursor().execute(sub_query).fetchall())

        # remove last item because it's the same as parent
        records.pop()

        # Insert children
        self.beginInsertRows(parent, 0, len(records))

        # Clear pevious children
        self.variants[parent.row()][1:] = []

        for idx, record in enumerate(records):  # skip first records
            self.variants[parent.row()].append(tuple(record))

        self.endInsertRows()

    def children_count(self, index: QModelIndex) -> int:
        """Return children count from variant

        This one is the last value of sql record output and correspond to the COUNT(annotation)
        of the GROUP BY
        """
        return self.variants[index.row()][0][-1] - 1

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

        # Append a list because child can be append after
        self.variants = [
            [tuple(variant)]
            for variant in self._query.items(self.limit, self.page * self.limit)
        ]

        LOGGER.debug("QueryModel:load:: variants queried\n%s", self.variants)
        self.endResetModel()

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
        self.setPage(int(self.total / self.limit))

    def sort(self, column: int, order):
        """Overrided: Sort data by specified column 
        
        column (int): column id 
        order (Qt.SortOrder): Qt.AscendingOrder or Qt.DescendingOrder 

        """
        if column < self.columnCount():
            colname = self._query.columns[column - 1]

            self._query.order_by = colname
            self._query.order_desc = order == Qt.DescendingOrder
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

    def variant(self, index: QModelIndex):
        """ Return variant data according index 
        
        Examples:
            variant = model.variant(index)
            print(variant) # ["chr","242","A","T",.....]

        """

        if self.level(index) == 1:
            return self.variants[index.row()][0]

        if self.level(index) == 2:
            return self.variants[index.parent().row()][
                index.row() + 1
            ]  #  + 1 because the first element is the parent


class QueryDelegate(QStyledItemDelegate):
    """
    This class specify the aesthetic of the view

    styles and color of each variant displayed in the view are setup here


    """

    def background_color_index(self, index):
        """ return background color of index """

        base_brush = qApp.palette("QTreeView").brush(QPalette.Base)
        alternate_brush = qApp.palette("QTreeView").brush(QPalette.AlternateBase)

        if index.parent() == QModelIndex():
            if index.row() % 2:
                return base_brush
            else:
                return alternate_brush

        if index.parent().parent() == QModelIndex():
            return self.background_color_index(index.parent())

        return base_brush

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
            bg_brush = self.background_color_index(index)
        else:
            bg_brush = palette.brush(QPalette.Highlight)

        painter.save()
        painter.setBrush(bg_brush)
        painter.setPen(Qt.NoPen)
        painter.drawRect(option.rect)
        painter.restore()

        # painter.setPen(pen)

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

        if "genotype" in colname:
            val = int(value)

            icon_code = GENOTYPE_ICONS.get(val, -1)
            icon = FIcon(icon_code, Qt.white).pixmap(20, 20)
            painter.setRenderHint(QPainter.Antialiasing)
            painter.drawPixmap(option.rect.left(), option.rect.center().y() - 8, icon)
            return

        if "consequence" in colname:
            painter.save()
            painter.setClipRect(option.rect, Qt.IntersectClip)
            painter.setRenderHint(QPainter.Antialiasing)
            soTerms = value.split("&")
            rect = QRect()
            font = painter.font()
            font.setPixelSize(10)
            painter.setFont(font)
            metrics = QFontMetrics(painter.font())
            rect.setX(option.rect.x())
            rect.setY(option.rect.center().y() - 5)

            #  Set background color according so terms
            #  Can be improve ... Just a copy past from c++ code
            bg = "#6D7981"
            for so in soTerms:
                for i in style.SO_COLOR.keys():
                    if i in so:
                        bg = style.SO_COLOR[i]

                painter.setPen(Qt.white)
                painter.setBrush(QBrush(QColor(bg)))
                rect.setWidth(metrics.width(so) + 8)
                rect.setHeight(metrics.height() + 4)
                painter.drawRoundedRect(rect, 3, 3)
                painter.drawText(rect, Qt.AlignCenter, so)

                rect.translate(rect.width() + 4, 0)

            painter.restore()
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


class QueryTreeView(QTreeView):
    def __init__(self, parent=None):
        super().__init__()

    def drawBranches(self, painter, rect, index):
        """ overrided : Draw Branch decorator with background 
        
        Backround is not alternative for children but inherits from parent 

        """
        painter.save()
        painter.setPen(Qt.NoPen)
        painter.setBrush(self.itemDelegate().background_color_index(index))
        painter.drawRect(rect)

        if index.parent() != QModelIndex():
            #  draw child indicator
            painter.drawPixmap(rect.center(), FIcon(0xF12F).pixmap(10, 10))

        painter.restore()

        super().drawBranches(painter, rect, index)


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
        self.view = QueryTreeView()

        # self.view.setFrameStyle(QFrame.NoFrame)
        self.view.setModel(self.model)
        self.view.setItemDelegate(self.delegate)
        # self.view.setAlternatingRowColors(True)
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
