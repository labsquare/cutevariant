
import re

from cutevariant.core import command as cmd
from cutevariant.core import vql 
import  cutevariant.commons as cm

from cutevariant.gui import plugin, FIcon
from cutevariant.gui import formatter

from PySide2.QtWidgets import *
from PySide2.QtCore import *
from PySide2.QtGui import *

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
        self.order_by = None
        self.order_desc = True 
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


        offset = self.page * self.limit

        self.variants.clear()

        self.variants = list(cmd.select_cmd(self.conn,
            fields = self.fields,
            source = self.source,
            filters = self.filters,
            limit= self.limit,
            offset = offset,
            order_desc = self.order_desc,
            order_by= self.order_by, 
            group_by = self.group_by
            ))

        if self.variants:
            self.headers = list(self.variants[0].keys())


        self.endResetModel()

        if emit_changed:
            self.changed.emit()
            #Probably need to compute total 
            self.total = cmd.count_cmd(self.conn, self.source, self.filters)["count"]

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
        print("set page ")
        if self.hasPage(page):
            self.page = page
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
        self.setPage(self.pageCount())

    def pageCount(self):
        """ Return total page count """ 
        return int(self.total / self.limit)        


    def sort(self, column: int, order):
        """Overrided: Sort data by specified column 
        
        column (int): column id 
        order (Qt.SortOrder): Qt.AscendingOrder or Qt.DescendingOrder 

        """
        if column < self.columnCount():
            colname = self.headers[column]

            self.order_by = colname
            self.order_desc = order == Qt.DescendingOrder
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

        # return base_brush

    # def paint(self, painter, option, index):
        

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

    view_clicked = Signal()

    def __init__(self, parent = None):
        super().__init__()

        self.view = QTableView()
        self.model = VariantModel()

        self.view.setModel(self.model)
        #self.view.setFrameStyle(QFrame.NoFrame)
        self.view.setAlternatingRowColors(True)
        self.view.horizontalHeader().setStretchLastSection(True)
        self.view.setSelectionMode(QAbstractItemView.SingleSelection)
        self.view.verticalHeader().hide()

        self.view.setSortingEnabled(True)
        self.view.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.view.setSelectionMode(QAbstractItemView.ContiguousSelection)
        ## self.view.setIndentation(0)
        self.view.setIconSize(QSize(22, 22))

        self.view.setModel(self.model)
        #self.view.setItemDelegate(self.delegate)

        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(0,0,0,0)

   
        main_layout.addWidget(self.view)
        self.setLayout(main_layout)

        # broadcast focus signal 



        self.view.viewport().installEventFilter(self)


    def eventFilter(self, obj: QObject, event : QEvent):

        if event.type() == QEvent.MouseButtonPress:
            self.view_clicked.emit()

        return super().eventFilter(obj, event)
        




class VariantViewWidget(plugin.PluginWidget):
    """Contains the view of query with several controller"""

    variant_clicked = Signal(dict)
    LOCATION = plugin.CENTRAL_LOCATION

    ENABLE = True


    def __init__(self, parent = None):
        super().__init__(parent)

        self.splitter = QSplitter(Qt.Vertical)
        self.top_bar = QToolBar()
        self.bottom_bar = QToolBar()

        self.main_view = VariantView()
        self.sub_view = VariantView()
        # self.sub_view.hide()


        self.splitter.addWidget(self.main_view)
        self.splitter.addWidget(self.sub_view)

        self.current_view = self.main_view


        self.page_box = QComboBox()
        self.page_box.setEditable(True)
        self.page_box.setValidator(QIntValidator())
        self.page_box.setFixedWidth(50)
        #self.page_box.setAlignment(Qt.AlignHCenter)
        #self.page_box.setStyleSheet("QWidget{background-color: transparent;}")
        #self.page_box.("0")
        self.page_box.setFrame(QFrame.NoFrame)
        
        spacer = QWidget()
        spacer.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        

        # topbar 

        group_box = QComboBox()
        group_box.addItems(["nogroup", "chr,pos,ref,alt","gene"] )
        self.top_bar.addWidget(group_box)


        self.bottom_bar.addWidget(spacer)     
        self.bottom_bar.setIconSize(QSize(16, 16))
        self.bottom_bar.setMaximumHeight(30)
        self.bottom_bar.setContentsMargins(0, 0, 0, 0)


        self.bottom_bar.addAction(FIcon(0xF792), "<<", self.on_page_clicked)
        self.bottom_bar.addAction(FIcon(0xF04D), "<",  self.on_page_clicked)
        self.bottom_bar.addWidget(self.page_box)
        self.bottom_bar.addAction(FIcon(0xF054), ">",  self.on_page_clicked)
        self.bottom_bar.addAction(FIcon(0xF793), ">>", self.on_page_clicked)
        #self.page_box.returnPressed.connect()


        self.main_view.view.clicked.connect(self.on_variant_clicked)

        self.main_view.view_clicked.connect(self.on_view_clicked)
        self.sub_view.view_clicked.connect(self.on_view_clicked)

        self.page_box.currentTextChanged.connect(self.on_page_changed)


        # setup layout 
        main_layout  = QVBoxLayout()

        main_layout.addWidget(self.top_bar)
        main_layout.addWidget(self.splitter)
        main_layout.addWidget(self.bottom_bar)

        self.setLayout(main_layout)
        
    def on_view_clicked(self):

        view = self.sender()
        
        if view != self.current_view:
            self.current_view = view 
            self.update_current_view()


    def update_current_view(self):
        """ Update style and bottom bar when current view changed """ 

        if self.current_view == self.main_view:
            other = self.sub_view
        else:
            other = self.main_view

        self.current_view.setStyleSheet("QTableView{ border: 1px solid palette(highlight)}")
        other.setStyleSheet("QTableView{ border: 1px solid palette(shadow)}")

        # Update page count 
        self.update_page_control()


    def update_page_control(self):
        """ Update page control like previous, next according page Count """         
        self.page_box.clear()
        self.page_box.addItems([str(i) for i in range(self.current_view.model.pageCount())])
        
        enabled = True if self.current_view.model.pageCount() > 1 else False

        for action in self.bottom_bar.actions():
            if action.text() in ("<<",">>","<",">"):
                action.setEnabled(enabled)


    def on_page_clicked(self):

        action_text = self.sender().text()

        if action_text == "<<":
            fct = self.current_view.model.firstPage 

        if action_text == ">>":
            fct = self.current_view.model.lastPage
            
        if action_text == "<":
            fct = self.current_view.model.previousPage 
            
        if action_text == ">":
            fct = self.current_view.model.nextPage

        fct()
        self.page_box.setCurrentText(str(self.current_view.model.page))

    def on_page_changed(self):

        page = int(self.page_box.currentText())
        self.current_view.model.setPage(page)
        self.current_view.setFocus(Qt.OtherFocusReason)

    def on_open_project(self,conn):
        self.conn = conn 
        self.main_view.model.conn = self.conn
        self.sub_view.model.conn = self.conn

        self.on_refresh()

    def on_refresh(self):


        self.main_view.model.fields = self.mainwindow.state.fields 
        self.main_view.model.fields = self.mainwindow.state.fields 
        self.main_view.model.source = self.mainwindow.state.source
        self.main_view.model.filters = self.mainwindow.state.filters

        # self.main_view.model.group_by = ["chr","pos","ref","alt"]

        self.main_view.model.load()
        self.update_current_view()


    def on_variant_clicked(self, index: QModelIndex):
        
        variant = self.main_view.model.variant(index.row())

        self.sub_view.model.fields = self.main_view.model.fields
        self.sub_view.model.source = self.main_view.model.source
        self.sub_view.model.filters =   {"AND": [ {"field": "id", "operator": "=", "value": variant["id"]}]}

        self.sub_view.model.load()

        print("done")





if __name__ == "__main__":
    import sys
    from PySide2.QtWidgets import QApplication 
    from cutevariant.core.importer import import_file, import_reader
    from cutevariant.core.reader import FakeReader, VcfReader
    from cutevariant.core import sql

    app = QApplication(sys.argv)


    conn = sql.get_sql_connexion(":memory:")
    reader = VcfReader(open("/home/sacha/Dev/cutevariant/examples/test.snpeff.vcf"), "snpeff")
    import_reader(conn, reader)

    w = VariantViewWidget()



    #w.on_open_project(conn)
    #w.main_view.model.group_by = ["chr","pos","ref","alt"]
    #w.on_refresh()

    w.show()

    app.exec_()


