from PySide2.QtWidgets import *
from PySide2.QtCore import *
from PySide2.QtGui import *
from cutevariant.core.query import Query



class QueryRouter(QObject):
	def __init__(self):
		super().__init__(conn)
		self.widgets = []
		self.builder = Query(conn)

	def addWidget(widget: QWidget):
		self.widgets.append(widget)

		# widget must have : setQueryBuilder, updateQueryBuilder , changed Signals 




