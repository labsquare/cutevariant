import copy 

from PySide2.QtWidgets import *
from PySide2.QtCore import *
from PySide2.QtGui import *
from cutevariant.gui.ficon import FIcon


from .plugin import QueryPluginWidget
from cutevariant.core import Query
from cutevariant.core import sql


IMPACT_COLOR = {
    "LOW": "#71E096",
    "MODERATE": "#F5A26F",
    "HIGH": "#ed6d79",
    "MODIFIER": "#55abe1",
}


class QueryModel(QAbstractItemModel):
    def __init__(self, parent=None):
        super().__init__()
        self.limit = 50
        self.page = 0
        self.total = 0
        self._query = None
        self.variants = []
        self.childs = {}

    def rowCount(self, parent=QModelIndex()):
        """override"""
        if parent == QModelIndex():
            return len(self.variants)

        if parent.parent() == QModelIndex():
            return len(self.childs[parent.row()])

        return 0

    def columnCount(self, parent=QModelIndex()):
        """override """
        if not self._query:
            return 0
        return len(self._query.columns)

    def index(self, row, column, parent):
        """override"""
        if not self.hasIndex(row, column, parent):
            return QModelIndex()

        if parent == QModelIndex():
            return self.createIndex(row, column, 999999)   # HUGLY Hack.. TODO : how to manage pointer ??

        else:
            return self.createIndex(row, column, parent.row())


    def parent(self, child):
        """ override """
        if not child.isValid():
            return QModelIndex()
    
        parent_rowid = child.internalId()

        if parent_rowid == 99999999:  # HUGLY ... see upper
            return QModelIndex()

        else:
            return self.index(parent_rowid,0,QModelIndex())


    def data(self, index, role=Qt.DisplayRole):
        """ override """

        if not index.isValid():
            return None

        if role == Qt.DisplayRole:

            if index.parent() == QModelIndex():  # First level 
                return str(self.variants[index.row()][index.column() + 1])


            if index.parent().parent() == QModelIndex():
                return str(self.childs[index.parent().row()][index.row()][index.column() + 1])
            


        return None

    def headerData(self, section, orientation, role=Qt.DisplayRole):
        """override"""
        if orientation == Qt.Horizontal:
            if role == Qt.DisplayRole:
                return self._query.columns[section]

        if orientation == Qt.Vertical:
            if role == Qt.DisplayRole:
                return self.variants[index.row()][0]

        return None

    def hasChildren(self, parent: QModelIndex) -> bool:
        """ override """
        # if invisible root node, always return True
        if parent == QModelIndex():
            return True 

        if parent.parent() == QModelIndex():
            return self._child_count(parent) > 1

    def canFetchMore(self, parent: QModelIndex) -> bool:
        """ override """
        return self.hasChildren(parent)


    def fetchMore(self,parent : QModelIndex): 
        """override """
        if parent == QModelIndex():
            return

        count     = self._child_count(parent)
        child_ids = self._child_ids(parent)
        child_query = copy.copy(self.query)
        # Create a copy query to load childs 
        child_query.filter = {'AND':[]}
        child_query.group_by = None
        child_query.filter["AND"].append({'field': 'rowid', 'operator': ' IN ', 'value':child_ids})

        self.beginInsertRows(parent,0, count-1);

        self.childs[parent.row()] = []
        self.childs[parent.row()] = list(child_query.rows())

        print(self.childs[parent.row()])

        self.endInsertRows()
           




    def _child_count(self, index: QModelIndex):
        """ return child count for the index variant """
        if not self._query.group_by:
            return 0
        return self.variants[index.row()][-2]

    def _child_ids(self, index: QModelIndex):
        """ return childs sql ids for the index variant """
        if not self._query.group_by:
            return 0
        return self.variants[index.row()][-1].split(",")

    @property
    def query(self):
        return self._query

    @query.setter
    def query(self, query: Query):
        self._query = query
        #self._query.group_by=("chr","pos","ref","alt")

        self.total = query.count()
        self.load()

    def load(self):
        self.beginResetModel()
        self.variants.clear()
        self.variants = list(self._query.rows(self.limit, self.page * self.limit))

        print(self.variants)
        self.endResetModel()

    def hasPage(self, page):
        return page >= 0 and page * self.limit < self.total

    def setPage(self, page):
        if self.hasPage(page):
            self.page = page
            self.load()

    def nextPage(self):
        if self.hasPage(self.page + 1):
            self.setPage(self.page + 1)

    def previousPage(self):
        if self.hasPage(self.page - 1):
            self.setPage(self.page - 1)

    def sort(self, column: int, order):
        """override"""
        pass
        if column < self.columnCount():
            colname = self._query.columns[column]

            print("ORDER", order)
            self._query.order_by = colname
            self._query.order_desc = (order == Qt.DescendingOrder)
            self.load()

    def get_rowid(self, index):
        return self.variants[index.row()][0]


class QueryDelegate(QStyledItemDelegate):
    def paint(self, painter, option, index):
        """overriden"""

        palette = qApp.palette("QTreeView")
        colname = index.model().headerData(index.column(), Qt.Horizontal)
        value = index.data(Qt.DisplayRole)
        select = option.state & QStyle.State_Selected

        #  Draw selection background
        if select:
            bg_brush = palette.brush(QPalette.Highlight)
        #  Draw alternative
        else:
            if index.row() % 2:
                bg_brush = palette.brush(QPalette.Midlight)
            else:
                bg_brush = palette.brush(QPalette.Light)

        painter.setBrush(bg_brush)
        painter.setPen(Qt.NoPen)
        painter.drawRect(option.rect)

        if colname == "impact":
            painter.setPen(QPen(IMPACT_COLOR.get(value, palette.color(QPalette.Text))))
            painter.drawText(option.rect, Qt.AlignLeft | Qt.AlignVCenter, index.data())
            return

        painter.setPen(
            QPen(palette.color(QPalette.HighlightedText if select else QPalette.Text))
        )
        painter.drawText(option.rect, Qt.AlignLeft | Qt.AlignVCenter, index.data())

    def draw_biotype(self, value):
        pass

    def sizeHint(self, option, index):
        """override"""
        return QSize(0, 30)


class ViewQueryWidget(QueryPluginWidget):

    variant_clicked = Signal(dict)

    def __init__(self):
        super().__init__()
        self.model = QueryModel()
        self.delegate = QueryDelegate()
        # self.delegate = VariantDelegate()
        self.setWindowTitle(self.tr("Variants"))
        self.topbar = QToolBar()
        self.bottombar = QToolBar()
        self.view = QTreeView()

        self.view.setFrameStyle(QFrame.NoFrame)
        self.view.setModel(self.model)
        self.view.setItemDelegate(self.delegate)
        self.view.setAlternatingRowColors(True)
        self.view.setSortingEnabled(True)
        # self.view.setItemDelegate(self.delegate)

        main_layout = QVBoxLayout()
        main_layout.addWidget(self.topbar)
        main_layout.addWidget(self.view)
        main_layout.addWidget(self.bottombar)
        main_layout.setContentsMargins(0, 0, 0, 0)

        # Construct top bar
        self.topbar.addAction(self.tr("save"))

        # Construct bottom bar
        self.page_info = QLabel()
        self.page_box = QLineEdit()
        self.page_box.setReadOnly(True)
        self.page_box.setFrame(QFrame.NoFrame)
        self.page_box.setMaximumWidth(50)
        self.page_box.setAlignment(Qt.AlignHCenter)
        self.page_box.setStyleSheet("QWidget{background-color: transparent;}")
        self.page_box.setText("0")
        spacer = QWidget()
        spacer.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        self.bottombar.addAction(FIcon(0xf865),"sql", self.show_sql)
        self.bottombar.addWidget(self.page_info)
        self.bottombar.addWidget(spacer)
        self.bottombar.addAction(FIcon(0xf141), "<", self.model.previousPage)
        self.bottombar.addWidget(self.page_box)
        self.bottombar.addAction(FIcon(0xf142),">", self.model.nextPage)
        self.bottombar.setIconSize(QSize(20,20))

        self.bottombar.setContentsMargins(0, 0, 0, 0)

        self.setLayout(main_layout)

        self.model.modelReset.connect(self.updateInfo)

        # emit variant when clicked
        self.view.clicked.connect(self._variant_clicked)

    @property
    def query(self):
        """ Method override from AbstractQueryWidget"""
        return self.model.query

    @query.setter
    def query(self, query: Query):
        """ Method override from AbstractQueryWidget"""
        self.model.query = query

    def updateInfo(self):

        self.page_info.setText(f"{self.model.total} variant(s)")
        self.page_box.setText(f"{self.model.page}")

    def _variant_clicked(self, index):
        #print("cicked on ", index)
        rowid = self.model.get_rowid(index)
        variant = sql.get_one_variant(self.model.query.conn, rowid)
        self.variant_clicked.emit(variant)

    def show_sql(self):
        box = QMessageBox()
        try:
            text = self.model.query.sql()
        except AttributeError:
            text = self.tr("No query to show")

        box.setInformativeText(text)
        box.exec_()
