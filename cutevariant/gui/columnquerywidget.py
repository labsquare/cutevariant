from PySide2.QtWidgets import *
from PySide2.QtCore import *
from PySide2.QtGui import *


from .abstractquerywidget import AbstractQueryWidget 
from cutevariant.core import Query
from cutevariant.core.model import Field


class ColumnQueryModel(QStandardItemModel):
	def __init__(self):
		super().__init__()
		self.setColumnCount(2)
		self.query = None 

	def setQuery(self, query: Query):
		self.query = query
		self.load() 

	def updateQuery(self, query: Query) -> Query:
		selected_columns = []
		for i in range(self.rowCount()):
			if self.item(i).checkState() == Qt.Checked:
				selected_columns.append(self.item(i).text())

		query.columns = selected_columns
		return query



	def load(self):
		self.clear()
		for record in Field(self.query.conn).items():
			item = QStandardItem(record["name"])
			item.setCheckable(True)
			self.appendRow(item)










class ColumnQueryWidget(AbstractQueryWidget):
	def __init__(self):
		super().__init__()

		self.view = QTreeView()
		self.model = ColumnQueryModel()
		self.view.setModel(self.model)
		self.view.setIndentation(0)
		self.view.header().setVisible(False)
		layout = QVBoxLayout()

		layout.addWidget(self.view)
		self.setLayout(layout)


		self.model.itemChanged.connect(self.changed)



	def setQuery(self,query: Query):
		self.model.setQuery(query) 
		self.model.updateQuery(query)

	def updateQuery(self,query: Query):
		return self.model.updateQuery(query) 


