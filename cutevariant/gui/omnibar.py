from PySide2.QtCore import *
from PySide2.QtWidgets import *
from PySide2.QtGui import *

from cutevariant.core.query import Query
from cutevariant.gui.ficon import FIcon
import re

class OmniBar(QLineEdit):

	changed = Signal()

	def __init__(self):
		super().__init__()
		self.setMaximumWidth(400)
		self.setPlaceholderText(qApp.tr("chr3:100-100000"))
		self.action = self.addAction(FIcon(0xf349,"black"), QLineEdit.TrailingPosition)

		self.returnPressed.connect(self.changed)


	def to_coordinate(self):

		match = re.search(r'(chr\d\d?):(\d+)-(\d+)', self.text())
		
		if match:
			return (match[1], int(match[2]), int(match[3]))	
		else:
			return None	

	def setQuery(self, query: Query):
		self.query = query 


	def getQuery(self):

		coord = self.to_coordinate()
		if coord: 
			self.query.filter = {'AND': 
			[
			{'field': 'chr', 'operator': '=', 'value': coord[0]}, 
			{'field': 'pos', 'operator': '>', 'value': coord[1]}, 
			{'field': 'pos', 'operator': '<', 'value': coord[2]}
			]}

		return self.query



