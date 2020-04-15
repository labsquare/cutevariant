from PySide2.QtWidgets import * 
from PySide2.QtCore import * 
from PySide2.QtGui import * 

import sys 
import json

from cutevariant.core.vql import execute_vql
from qjsonmodel import QJsonModel


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

		self.splitter = QSplitter(Qt.Horizontal)

		self.a = MyTextEdit()
		self.b = QTreeView()
		self.bmodel = QJsonModel()
		self.b.setModel(self.bmodel)

		self.splitter.addWidget(self.a)
		self.splitter.addWidget(self.b)

		vlayout = QVBoxLayout()
		vlayout.addWidget(self.splitter)
		self.setLayout(vlayout)

		self.a.returnPressed.connect(self.compile)

		self.resize(1600, 400)

	def compile(self):
		source = self.a.toPlainText() 
		datas = []
		for req in execute_vql(source):
			datas.append(req)
		

		datas = json.dumps(datas)
		datas = json.loads(datas)
		self.bmodel.load(datas)

		self.b.expandAll()



app = QApplication(sys.argv)

w = Editor()

w.show()
app.exec_()


a = execute_vql("CREATE a = b + c ")

i = next(a)

print(i)



