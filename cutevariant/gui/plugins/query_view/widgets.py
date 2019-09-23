
import re


from cutevariant.gui import plugin, FIcon
from cutevariant.gui import formatter

from PySide2.QtWidgets import *
from PySide2.QtCore import *
from PySide2.QtGui import *



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
        #colname = index.model().headerData(index.column(), Qt.Horizontal)

        #  get value of the index
        #value = index.data(Qt.DisplayRole)

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

       
        painter.save()
        alignement = Qt.AlignLeft | Qt.AlignVCenter

        bg_color = index.data(Qt.BackgroundRole)
        fg_color = index.data(Qt.ForegroundRole)
        decoration = index.data(Qt.DecorationRole)

        font = index.data(Qt.FontRole)

        if bg_color:
            painter.setBrush(QBrush(bg_color))
            painter.setPen(Qt.NoPen)
            painter.drawRect(option.rect)

        if font:
            painter.setFont(QFont())
        
        if fg_color:
            painter.setPen(QPen(fg_color))

        if decoration:
            rect = QRect(0,0,25,25)
            rect.moveCenter(option.rect.center())
            painter.drawPixmap(rect,decoration.pixmap(25,25))
        else:
            painter.drawText(option.rect, alignement, str(index.data()))
        
        
        painter.restore()



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
        # if colname == "impact":
        #     painter.setPen(
        #         QPen(style.IMPACT_COLOR.get(value, palette.color(QPalette.Text)))
        #     )
        #     painter.drawText(option.rect, alignement, str(index.data()))
        #     return

        # if colname == "gene":
        #     painter.setPen(QPen(style.GENE_COLOR))
        #     painter.drawText(option.rect, alignement, str(index.data()))
        #     return

        # if re.match(r"genotype(.+).gt", colname):
        #     val = int(value)

        #     icon_code = GENOTYPE_ICONS.get(val, -1)
        #     icon = FIcon(icon_code, palette.color(QPalette.Text)).pixmap(20, 20)
        #     painter.setRenderHint(QPainter.Antialiasing)
        #     painter.drawPixmap(option.rect.left(), option.rect.center().y() - 8, icon)
        #     return

        # if "consequence" in colname:
        #     painter.save()
        #     painter.setClipRect(option.rect, Qt.IntersectClip)
        #     painter.setRenderHint(QPainter.Antialiasing)
        #     soTerms = value.split("&")
        #     rect = QRect()
        #     font = painter.font()
        #     font.setPixelSize(10)
        #     painter.setFont(font)
        #     metrics = QFontMetrics(painter.font())
        #     rect.setX(option.rect.x())
        #     rect.setY(option.rect.center().y() - 5)

        #     #  Set background color according so terms
        #     #  Can be improve ... Just a copy past from c++ code
        #     bg = "#6D7981"
        #     for so in soTerms:
        #         for i in style.SO_COLOR.keys():
        #             if i in so:
        #                 bg = style.SO_COLOR[i]

        #         painter.setPen(Qt.white)
        #         painter.setBrush(QBrush(QColor(bg)))
        #         rect.setWidth(metrics.width(so) + 8)
        #         rect.setHeight(metrics.height() + 4)
        #         painter.drawRoundedRect(rect, 3, 3)
        #         painter.drawText(rect, Qt.AlignCenter, so)

        #         rect.translate(rect.width() + 4, 0)

        #     painter.restore()
        #     return

        # painter.setPen(
        #     QPen(palette.color(QPalette.HighlightedText if select else QPalette.Text))
        # )
        # painter.drawText(option.rect, alignement, str(index.data()))



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
        if self.itemDelegate().__class__ is not QueryDelegate:
            #  Works only if delegate is a VariantDelegate
            return

        painter.save()
        painter.setPen(Qt.NoPen)
        painter.setBrush(self.itemDelegate().background_color_index(index))
        painter.drawRect(rect)

        if index.parent() != QModelIndex():
            #  draw child indicator
            painter.drawPixmap(rect.center(), FIcon(0xF12F).pixmap(10, 10))

        painter.restore()

        super().drawBranches(painter, rect, index)

class QueryViewWidget(plugin.PluginWidget):
    """Contains the view of query with several controller"""

    variant_clicked = Signal(dict)
    LOCATION = plugin.CENTRAL_LOCATION


    def __init__(self, parent = None):
        super().__init__(parent)


        self.delegate = QueryDelegate()
        self.setWindowTitle(self.tr("Variants"))
        self.topbar = QToolBar()
        self.bottombar = QToolBar()
        self.view = QueryTreeView()
        self.formatters = []

        # # self.view.setFrameStyle(QFrame.NoFrame)
        self.view.setItemDelegate(self.delegate)
        # # self.view.setAlternatingRowColors(True)
        self.view.setSortingEnabled(True)
        self.view.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.view.setSelectionMode(QAbstractItemView.ContiguousSelection)
        self.view.setRootIsDecorated(True)  # Manage from delegate
        ## self.view.setIndentation(0)
        self.view.setIconSize(QSize(22, 22))
        self.view.setAnimated(True)

        # # self.view.setItemDelegate(self.delegate)

        main_layout = QVBoxLayout()
        main_layout.addWidget(self.topbar)
        main_layout.addWidget(self.view)
        main_layout.addWidget(self.bottombar)
        main_layout.setContentsMargins(0, 0, 0, 0)

        self.topbar.setToolButtonStyle(Qt.ToolButtonTextBesideIcon)
        # Construct top bar
        # These actions should be disabled until a query is made (see query setter)
        self.export_csv_action = self.topbar.addAction(
            FIcon(0xF207), self.tr("Export variants"), self.export_csv
        )
        self.export_csv_action.setEnabled(False)

        self.grouped_action = self.topbar.addAction(FIcon(0xF191), "Group variant")
        self.grouped_action.setCheckable(True)
        self.grouped_action.setChecked(True)
        self.grouped_action.toggled.connect(self.on_group_changed)

        self.save_action = self.topbar.addAction(FIcon(0xF817), "Save selection")
        self.save_action.setToolTip("Save current selections")
        self.save_action.triggered.connect(self.on_save_clicked)


        # Add spacer to push next buttons to the right
        spacer = QWidget()
        spacer.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.topbar.addWidget(spacer)

        # # Add combobox to choose the grouping method of variants

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


        self.formatter_combo = QComboBox()

        for Object in formatter.find_formatters():
            self.formatters.append(Object()) 
            self.formatter_combo.addItem(str(Object.__module__))

        self.formatter_combo.activated.connect(self.on_formatter_changed)

        self.bottombar.addWidget(self.formatter_combo)

        self.show_sql_action.setEnabled(False)
        self.bottombar.addWidget(self.page_info)
        self.bottombar.addWidget(spacer)
      
        self.bottombar.setIconSize(QSize(16, 16))
        self.bottombar.setMaximumHeight(30)

        self.bottombar.setContentsMargins(0, 0, 0, 0)

        self.setLayout(main_layout)




    def setup_ui(self):
        self.bottombar.addAction(FIcon(0xF792), "<<", self.model.firstPage)
        self.bottombar.addAction(FIcon(0xF04D), "<", self.model.previousPage)
        self.bottombar.addWidget(self.page_box)
        self.bottombar.addAction(FIcon(0xF054), ">", self.model.nextPage)
        self.bottombar.addAction(FIcon(0xF793), ">>", self.model.lastPage)
        self.page_box.returnPressed.connect(self._update_page)
        self.model.modelReset.connect(self.updateInfo)
        self.view.selectionModel().currentRowChanged.connect(self._variant_clicked)


    def on_register(self, mainwindow):
        """ Override from PluginWidget """
        self.view.setModel(mainwindow.query_model)
        self.model = mainwindow.query_model
        self.setup_ui()
        formatter = self.formatters[self.formatter_combo.currentIndex()]
        self.model.formatter = formatter

    def on_setup_ui(self):
        """ Override from PluginWidget """
        print("setup ")

    def on_open_project(self, conn):
        """ Override from PluginWidget """
        pass



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

    def _variant_clicked(self, index, _):
        """Slot called when the view (QTreeView) is clicked

        .. note:: Emit variant through variant_clicked signal.
            This signal updates InfoVariantWidget.
        .. note:: Is also called manually by contextMenuEvent() in order to
            get the variant and refresh InfoVariantWidget when the
            ContextMenuEvent is triggered.
        :return: The variant.
        :rtype: <dict>
        """

        if not index.isValid():
            return 
        # Get the rowid of the element at the given index
        rowid = self.model.variant(index)[0]
        # Get data from database
        variant = sql.get_one_variant(self.model.conn, rowid)
        # Emit variant through variant_clicked signal
        
        if self.mainwindow:
            self.mainwindow.on_variant_changed(variant)

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

    def on_group_changed(self, changed: bool):
        """Slot called when the currentIndex in the combobox changes
        either through user interaction or programmatically

        It triggers a reload of the model and a change of the group by
        command of the query.
        """
        self.model.group_variant(changed)
        if changed:
            self.view.showColumn(0)
        else:
            self.view.hideColumn(0)

    def on_formatter_changed(self):

        formatter = self.formatters[self.formatter_combo.currentIndex()]
        self.model.formatter = formatter

    def show_sql(self):
        box = QMessageBox()
        try:
            text = self.model.builder.sql()
        except AttributeError:
            text = self.tr("No query to show")

        box.setText("The following query has been executed")
        box.setInformativeText(str(self.model.builder))
        box.setDetailedText(text)
        box.exec_()

    def contextMenuEvent(self, event: QContextMenuEvent):
        """Overrided method: Show custom context menu associated to the current variant"""
        menu = QMenu(self)

        # Get variant data 
        index = self.view.indexAt(self.view.viewport().mapFromGlobal(event.globalPos()))

        if not index:
            return

        variant_id = self.model.variant(index)[0]
        variant = sql.get_one_variant(self.model.conn, variant_id)


        if "favorite" in variant:
            if not variant["favorite"]:
                msg = "Mark variant"
                icon = FIcon(0xf4d2)
            else:
                msg = "Unmark variant"
                icon = FIcon(0xf4ce)
            menu.addAction(icon, msg, lambda : self.model.set_favorite(index,not variant["favorite"]))

        menu.addSeparator()
        # Create copy action 
        cell_value = self.model.variant(index)[index.column()]
        menu.addAction(FIcon(0xf18f),
        f"Copy {cell_value}", 
        lambda : qApp.clipboard().setText(str(self.model.variant(index)))
        )

        genomic_location = "{chr}:{pos}{ref}>{alt}".format(**variant)
        menu.addAction(FIcon(0xf18f),
        f"Copy {genomic_location}", 
        lambda : qApp.clipboard().setText(genomic_location)
        )


        menu.addSeparator()

        from functools import partial

        # Create open with action 
        open_with_action = QMenu(self.tr("Open with"))
        settings = QSettings()
        settings.beginGroup("plugins/query_view/links")
        urls = {}
        for key in settings.childKeys():
            url = QUrl(settings.value(key).format(**variant))
            open_with_action.addAction(FIcon(0xf339), key,  lambda url=url : QDesktopServices.openUrl(url))

        settings.endGroup()

        menu.addMenu(open_with_action)

        menu.exec_(event.globalPos())


    def _update_page(self):
        """Set page from page_box edit. When user set a page manually, this method is called"""
        self.model.setPage(int(self.page_box.text()))

        self.page_box.clearFocus()

    def on_save_clicked(self):
        name, success = QInputDialog.getText(self, "Text", "Enter name:")
        if success:
            self.model.builder.save(name)

            self.model.changed.emit()





if __name__ == "__main__":
    import sys
    from PySide2.QtWidgets import QApplication 

    def test():
        print("salut")

    app = QApplication(sys.argv)

    w = QueryViewWidget()
    w.show()
    

    app.exec_()