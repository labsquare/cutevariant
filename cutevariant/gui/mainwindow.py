from PyQt5.QtCore import *
from PyQt5.QtWidgets import *


class MainWindow(QMainWindow):
	def __init__(self, parent= None):
		super(MainWindow,self).__init__()
		self.toolbar = self.addToolBar("test")

		



