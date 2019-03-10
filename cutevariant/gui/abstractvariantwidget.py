from PySide2.QtWidgets import *
from PySide2.QtCore import *
from PySide2.QtGui import *



class AbstractVariantWidget(QWidget):
	def __init__(self):
		super().__init__() 


	def set_variant(self, variant):
		raise NotImplemented()




class InfoVariantWidget(AbstractVariantWidget):

	def __init__(self):
		super().__init__()

		self.label = QLabel("salut")
		v_layout = QVBoxLayout()
		v_layout.addWidget(self.label)
		self.setLayout(v_layout)

	def set_variant(self, variant):
		self.label.setText("{chr} {pos}".format(**variant))
