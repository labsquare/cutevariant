"""Widget to display variants from a query in the GUI.

ViewQueryWidget class is added to a QTabWidget and is seen by the user;
it uses QueryModel class as a model that handles records from the database.
QueryDelegate class handles the aesthetic of the view.
"""

# Standard imports
import copy
import csv
import sys
import sqlite3
import re

# Qt imports
from PySide2.QtWidgets import (
    QStyledItemDelegate,
    QTreeView,
    QWidget,
    QAction,
    QToolBar,
    QVBoxLayout,
    QAbstractItemView,
    QApplication,
    QSizePolicy,
    QLabel,
    QLineEdit,
    QFrame,
    QStyle,
    QInputDialog
)
from PySide2.QtCore import (
    QAbstractTableModel,
    QRect,
    Signal,
    Slot,
    QModelIndex,
    QSize,
    Qt
)
from PySide2.QtGui import (
    QPainter,
    QContextMenuEvent,
    QIntValidator,
    QPalette,
    QPen,
    QBrush,
)

# Custom imports
from cutevariant.gui.ficon import FIcon
from cutevariant.core import sql
from cutevariant.gui import style
from cutevariant.gui.formatter import Formatter
from cutevariant.commons import logger
from cutevariant.commons import GENOTYPE_ICONS
from cutevariant.core.command import SelectCommand, CountCommand, create_commands

LOGGER = logger()


class QueryModel(QAbstractTableModel):
    """
    QueryModel is a Qt model class which contains variants datas from sql.VariantBuilder . 
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
        self.cmd = None
        # Keep after all initialization 
        self.conn = conn

    @property
    def conn(self):
        """ Return sqlite connection """
        if self.cmd:
            return self.cmd.conn
        return None

    @conn.setter
    def conn(self, conn):
        """ Set sqlite connection """
        self.cmd = SelectCommand(conn)
        self.emit_changed = True

    @property
    def fields(self):
        """ Return query columns list displayed """
        return self.cmd.columns
        
    @fields.setter
    def fields(self, columns: list):
        """ Set query columns list to display """
        self.cmd.columns = columns
        self.emit_changed = True

    @property
    def filters(self):
        """ Return query filter """
        return self.cmd.filters
        self.emit_changed = True

    @filters.setter
    def filters(self, filters):
        """ Set query filter """
        self.cmd.filters = filters
        self.emit_changed = True

    @property
    def source(self):
        """ Return query selection """
        return self.cmd.source

    @source.setter
    def source(self, source):
        """ Set query source """
        self.cmd.source = source
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
            if role == Qt.DisplayRole:
                return str(self.variant(index.row())[column_name])

            # ------ Other Role -----

            if self.formatter:
                if role in self.formatter.supported_role():
                    value = self.data(index, Qt.DisplayRole)
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

        #Display columns headers
        if orientation == Qt.Horizontal:
            if role == Qt.DisplayRole:
                return self.headers[section]
        return None


    def load(self, emit_changed = True, reset_page=False):
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

        self.cmd.limit = self.limit 
        self.cmd.offset = self.page * self.limit

        self.variants = list(self.cmd.do())

        print(self.cmd.sql())

        if self.variants:
            self.headers = list(self.variants[0].keys())


        self.endResetModel()

        if emit_changed:
            self.changed.emit()
            #Probably need to compute total 
            count_cmd = CountCommand(self.conn)
            count_cmd.source = self.cmd.source 
            count_cmd.filters = self.cmd.filters 
            self.total = count_cmd.do()["count"]

    def load_from_vql(self, vql):

        cmd = next(create_commands(self.conn, vql))
        if isinstance(cmd, SelectCommand):
            self.cmd = cmd
            self.load()



    def hasPage(self, page: int) -> bool:
        """ Return True if <page> exists otherwise return False """
        return page >= 0 and page * self.limit < self.total

    def setPage(self, page: int):
        """ set the page of the model """
        if self.hasPage(page):
            self.page = page
            print("set page ")
            self.load(emit_changed = False)

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
            colname = self.headers[column]

            self.cmd.order_by = colname
            self.cmd.order_desc = order == Qt.DescendingOrder
            self.load(emit_changed = False)

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

    def variant(self, row : int) -> dict:
    #     """ Return variant data according index 

        return self.variants[row]


        
    #     Examples:
    #         variant = model.variant(index)
    #         print(variant) # ["chr","242","A","T",.....]

    #     """
    #     if self.level(index) == 1:
    #         return self.variants[index.row()][0]

    #     if self.level(index) == 2:
    #         return self.variants[index.parent().row()][
    #             index.row() + 1
    #         ]  #  + 1 because the first element is the parent

  




# class QueryDelegate(QStyledItemDelegate):
#     """
#     This class specify the aesthetic of the view

#     styles and color of each variant displayed in the view are setup here


#     """

#     def background_color_index(self, index):
#         """ return background color of index """

#         base_brush = qApp.palette("QTreeView").brush(QPalette.Base)
#         alternate_brush = qApp.palette("QTreeView").brush(QPalette.AlternateBase)

#         if index.parent() == QModelIndex():
#             if index.row() % 2:
#                 return base_brush
#             else:
#                 return alternate_brush

#         if index.parent().parent() == QModelIndex():
#             return self.background_color_index(index.parent())

#         return base_brush

#     def paint(self, painter, option, index):
#         """
#         overriden

#         Draw the view item for index using a painter

#         """

#         palette = qApp.palette("QTreeView")
#         #  get column name of the index
#         colname = index.model().headerData(index.column(), Qt.Horizontal)

#         #  get value of the index
#         value = index.data(Qt.DisplayRole)

#         # get select sate
#         select = option.state & QStyle.State_Selected

#         #  draw selection if it is
#         if not select:
#             bg_brush = self.background_color_index(index)
#         else:
#             bg_brush = palette.brush(QPalette.Highlight)

#         painter.save()
#         painter.setBrush(bg_brush)
#         painter.setPen(Qt.NoPen)
#         painter.drawRect(option.rect)
#         painter.restore()

#         # painter.setPen(pen)

#         alignement = Qt.AlignLeft | Qt.AlignVCenter

#         # # Add margin for first columns if index is first level
#         # if index.column() == 0 and index.parent() == QModelIndex():

#         #     expanded = bool(option.state & QStyle.State_Open)

#         #     branch_option = copy.copy(option)
#         #     branch_option.rect.setWidth(65)

#         #     qApp.style().drawPrimitive(QStyle.PE_IndicatorBranch, branch_option, painter)

#         #     icon = index.data(Qt.DecorationRole)
#         #     if icon:
#         #         target = QRect(0,0, option.decorationSize.width(), option.decorationSize.height())
#         #         target.moveCenter(option.rect.center())
#         #         painter.drawPixmap(option.rect.x()+5, target.top() ,icon.pixmap(option.decorationSize))

#         # if index.column() == 0:
#         #     option.rect.adjust(40,0,0,0)

#         # Draw cell depending column name
#         if colname == "impact":
#             painter.setPen(
#                 QPen(style.IMPACT_COLOR.get(value, palette.color(QPalette.Text)))
#             )
#             painter.drawText(option.rect, alignement, str(index.data()))
#             return

#         if colname == "gene":
#             painter.setPen(QPen(style.GENE_COLOR))
#             painter.drawText(option.rect, alignement, str(index.data()))
#             return

#         if re.match(r"genotype(.+).gt", colname):
#             val = int(value)

#             icon_code = GENOTYPE_ICONS.get(val, -1)
#             icon = FIcon(icon_code, palette.color(QPalette.Text)).pixmap(20, 20)
#             painter.setRenderHint(QPainter.Antialiasing)
#             painter.drawPixmap(option.rect.left(), option.rect.center().y() - 8, icon)
#             return

#         if "consequence" in colname:
#             painter.save()
#             painter.setClipRect(option.rect, Qt.IntersectClip)
#             painter.setRenderHint(QPainter.Antialiasing)
#             soTerms = value.split("&")
#             rect = QRect()
#             font = painter.font()
#             font.setPixelSize(10)
#             painter.setFont(font)
#             metrics = QFontMetrics(painter.font())
#             rect.setX(option.rect.x())
#             rect.setY(option.rect.center().y() - 5)

#             #  Set background color according so terms
#             #  Can be improve ... Just a copy past from c++ code
#             bg = "#6D7981"
#             for so in soTerms:
#                 for i in style.SO_COLOR.keys():
#                     if i in so:
#                         bg = style.SO_COLOR[i]

#                 painter.setPen(Qt.white)
#                 painter.setBrush(QBrush(QColor(bg)))
#                 rect.setWidth(metrics.width(so) + 8)
#                 rect.setHeight(metrics.height() + 4)
#                 painter.drawRoundedRect(rect, 3, 3)
#                 painter.drawText(rect, Qt.AlignCenter, so)

#                 rect.translate(rect.width() + 4, 0)

#             painter.restore()
#             return

#         painter.setPen(
#             QPen(palette.color(QPalette.HighlightedText if select else QPalette.Text))
#         )
#         painter.drawText(option.rect, alignement, str(index.data()))

#     def draw_biotype(self, value):
#         pass

#     def sizeHint(self, option, index):
#         """Override: Return row height"""
#         return QSize(0, 30)

