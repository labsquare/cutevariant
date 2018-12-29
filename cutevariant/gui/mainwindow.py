from PySide2.QtCore import *
from PySide2.QtWidgets import *
from .variantview import VariantView 


class MainWindow(QMainWindow):
    def __init__(self, parent=None):
        super(MainWindow, self).__init__()
        self.toolbar = self.addToolBar("test")
        self.view = VariantView()
        self.setCentralWidget(self.view)

