from PySide2.QtWidgets import *
from PySide2.QtCore import *
from PySide2.QtGui import *


from .abstractquerywidget import AbstractQueryWidget
from cutevariant.core import Query


class QueryModel(QStandardItemModel):
    def __init__(self, parent=None):
        super().__init__()
        self.limit = 50
        self.page = 0
        self.total = 0
        self.query = None

    def setQuery(self, query: Query):
        self.query = query
        self.total = query.count()
        self.load()

    def load(self):
        self.clear()
        self.setColumnCount(len(self.query.columns))
        self.setHorizontalHeaderLabels(self.query.columns)

        for row in self.query.rows(self.limit, self.page * self.limit):
            items = []
            for item in row:
                items.append(QStandardItem(str(item)))
            self.appendRow(items)

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


class QueryDelegate(QStyledItemDelegate):
    def paint(self, painter, option, index):
        """overriden"""
        super().paint(painter, option, index)

    def sizeHint(self, option, index):
        """override"""
        return QSize(0, 30)


class ViewQueryWidget(AbstractQueryWidget):

    save_clicked = Signal()

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

    def setQuery(self, query: Query):
        """ Method override from AbstractQueryWidget"""
        self.model.setQuery(query)

    def getQuery(self):
        """ Method override from AbstractQueryWidget"""
        return self.model.query

    def updateInfo(self):

        self.page_info.setText(f"{self.model.total} variant(s)")
        self.page_box.setText(f"{self.model.page}")
