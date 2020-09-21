from PySide2.QtWidgets import * 
from PySide2.QtCore import * 
from PySide2.QtGui import * 
import sys 
import sqlite3

from cutevariant.core import command
from cutevariant.core.importer import import_file

import pydot
from networkx.drawing.nx_pydot import write_dot

class MyTextEdit(QTextEdit):

	returnPressed = Signal()

	def __init__(self):
		super().__init__()


	def keyPressEvent(self, event):
		if event.key() == Qt.Key_Return:
			self.returnPressed.emit()

		
		super().keyPressEvent(event)

class Editor(QWidget):
	def __init__(self):
		super().__init__() 

		self.conn = sqlite3.Connection(":memory:")
		import_file(self.conn, "examples/test.snpeff.vcf")


		self.cmd_graph = command.CommandGraph(self.conn)

		self.splitter = QSplitter(Qt.Horizontal) 
		self.label = QLabel("image") 
		self.label.setMinimumWidth(300)

		self.textedit = MyTextEdit()
		self.splitter.addWidget(self.textedit)
		self.splitter.addWidget(self.label)

		vlayout = QVBoxLayout()
		vlayout.addWidget(self.splitter)
		self.setLayout(vlayout)

		self.textedit.returnPressed.connect(self.compute_graph)

	def compute_graph(self):
		
		self.cmd_graph.set_source(self.textedit.toPlainText())


		write_dot(self.cmd_graph.graph, "grid.dot")
		(graph,) = pydot.graph_from_dot_file('grid.dot')
		graph.write_png('somefile.png')
		self.label.setPixmap(QPixmap("somefile.png"))



app = QApplication(sys.argv)



w = Editor()
w.show()

app.exec_()






