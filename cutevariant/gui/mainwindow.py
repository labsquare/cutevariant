from PySide2.QtCore import *
from PySide2.QtWidgets import *


class MainWindow(QMainWindow):
	def __init__(self, parent= None):
		super(MainWindow,self).__init__()
		self.toolbar = self.addToolBar("test")

		



