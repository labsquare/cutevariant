from PySide2.QtWidgets import *
from PySide2.QtCore import *
from PySide2.QtGui import *


from .abstractquerywidget import AbstractQueryWidget
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
        self.query = None
        self.variants = []

    def rowCount(self, parent=QModelIndex()):
        """override"""
        if parent == QModelIndex():
            return len(self.variants)
        return 0

    def columnCount(self, parent=QModelIndex()):
        """override """
        if self.query is None:
            return 0
        else:
            return len(self.query.columns)

    def index(self, row, column, parent):
        """override"""
        if not self.hasIndex(row, column, parent):
            return QModelIndex()

        return self.createIndex(row, column)

    def parent(self, child):
        """ override """
        if not child.isValid():
            return QModelIndex()

        return QModelIndex()

    def data(self, index, role=Qt.DisplayRole):
        """ override """

        if not index.isValid():
            return None

        if role == Qt.DisplayRole:
            # First row is variant id  don't show 
            return str(self.variants[index.row()][index.column()+1])

        return None

    def headerData(self, section, orientation, role=Qt.DisplayRole):
        """override"""
        if orientation == Qt.Horizontal:
            if role == Qt.DisplayRole:
                return self.query.columns[section]

        if orientation == Qt.Vertical:
            if role == Qt.DisplayRole:
                return self.variants[index.row()][0]

        return None

    def setQuery(self, query: Query):
        self.query = query
        self.total = query.count()
        self.load()

    def load(self):
        self.beginResetModel()
        self.variants.clear()
        self.variants = list(self.query.rows(self.limit, self.page * self.limit))
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
            colname = self.query.columns[column]

            print("ORDER", order)
            self.query.order_by = colname
            self.query.order_desc = True if order == Qt.DescendingOrder else False
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


class ViewQueryWidget(AbstractQueryWidget):

    variant_clicked = Signal(dict)

    def __init__(self):
        super().__init__()
        self.model = QueryModel()
        self.delegate = QueryDelegate()
        # self.delegate = VariantDelegate()
        self.setWindowTitle("Variants")
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
        self.topbar.addAction("save")

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
        self.bottombar.addAction("sql")
        self.bottombar.addWidget(self.page_info)
        self.bottombar.addWidget(spacer)
        self.bottombar.addAction("<", self.model.previousPage)
        self.bottombar.addWidget(self.page_box)
        self.bottombar.addAction(">", self.model.nextPage)

        self.bottombar.setContentsMargins(0, 0, 0, 0)

        self.setLayout(main_layout)

        self.model.modelReset.connect(self.updateInfo)

        #emit variant when clicked
        self.view.clicked.connect(self._variant_clicked)
    

    def setQuery(self, query: Query):
        """ Method override from AbstractQueryWidget"""
        self.model.setQuery(query)

    def getQuery(self):
        """ Method override from AbstractQueryWidget"""
        return self.model.query

    def updateInfo(self):

        self.page_info.setText(f"{self.model.total} variant(s)")
        self.page_box.setText(f"{self.model.page}")


    def _variant_clicked(self, index):
        print("cicked on ", index)
        rowid = self.model.get_rowid(index)
        variant = sql.get_one_variant(self.model.query.conn, rowid)
        self.variant_clicked.emit(variant)