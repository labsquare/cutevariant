from PySide2.QtWidgets import *
from PySide2.QtCore import *
from PySide2.QtGui import *
from enum import Enum

from .plugin import QueryPluginWidget
from cutevariant.core import Query
from cutevariant.gui.ficon import FIcon
from cutevariant.gui.fields import *


class FilterQueryWidget(QueryPluginWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle(self.tr("Filter"))
        self.view = QTreeView()
        self.model = FilterModel(None)
        self.delegate = FilterDelegate()
        self.toolbar = QToolBar()
        self.toolbar.setIconSize(QSize(20, 20))
        self.view.setModel(self.model)
        self.view.setItemDelegate(self.delegate)

        layout = QVBoxLayout()
        layout.addWidget(self.view)
        layout.addWidget(self.toolbar)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        self.setLayout(layout)
        self.model.filterChanged.connect(self.on_filter_changed)

        # setup Menu

        self.add_menu = QMenu()
        self.add_button = QToolButton()
        self.add_button.setIcon(FIcon(0xF703))
        self.add_button.setPopupMode(QToolButton.InstantPopup)
        self.add_menu.addAction(FIcon(0xF8E0), "Add Logic", self.add_logic)
        self.add_menu.addAction(FIcon(0xF70A), "Add Condition", self.add_condition)
        self.add_button.setMenu(self.add_menu)

        self.toolbar.addWidget(self.add_button)
        self.toolbar.addAction(FIcon(0xF143), "up")
        self.toolbar.addAction(FIcon(0xF140), "down")

        spacer = QWidget()
        spacer.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.toolbar.addWidget(spacer)

        self.toolbar.addAction(FIcon(0xF5E8), "delete", self.on_delete_item)

        self.view.selectionModel().currentChanged.connect(self.on_selection_changed)

    def on_init_query(self):
        """ Overrided """
        self.model.conn = self.query.conn

        # self.model.query = self.query

    def on_change_query(self):
        """ override methods """
        # self.model.load()
        print(self.query.filter)
        self.model.load(self.query.filter)

    def on_filter_changed(self):

        self.query.filter = self.model.fromItem()
        self.query_changed.emit()

    def add_logic(self):
        index = self.view.currentIndex()
        self.model.add_logic_item(parent=index)

    def add_condition(self):
        index = self.view.currentIndex()
        self.model.add_condition_item(parent=index)

    def on_delete_item(self):

        ret = QMessageBox.question(
            self,
            "remove row",
            "Are you to remove this item ? ",
            QMessageBox.Yes | QMessageBox.No,
        )

        if ret == QMessageBox.Yes:
            self.model.remove_item(self.view.currentIndex())

    def on_selection_changed(self):
        """ Enable/Disable add button depending item type """

        print("selection changed")
        index = self.view.currentIndex()
        if self.model.item(index).type() == FilterItem.CONDITION_TYPE:
            self.add_button.setDisabled(True)
        else:
            self.add_button.setDisabled(False)
