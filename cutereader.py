from cutevariant.core.reader import VcfReader, FakeReader
from cutevariant.core import sql 
import sys 
import json
import sqlite3
import os

from PySide2.QtWidgets import * 
from PySide2.QtCore import * 
from PySide2.QtGui import * 


from cutevariant.gui.ficon import FIcon, FIconEngine


app = QApplication(sys.argv)
FIcon.setFontPath("cutevariant/assets/fonts/materialdesignicons-webfont.ttf")




button1 = QPushButton("sacha")
button2 = QPushButton("sacha")
button3 = QPushButton("sacha")

button1.setIcon(FIcon(0xf759))
button2.setIcon(FIcon(0xf759))
button3.setIcon(FIcon(0xf759))

button2.setDisabled(True)


layout = QVBoxLayout()
layout.addWidget(button1)
layout.addWidget(button2)
layout.addWidget(button3)

w = QWidget()
w.setLayout(layout)

w.show()



app.exec_()




	# if options == "fields":
	# 	print(json.dumps(list(reader.get_fields())))

	# else: 
	# 	print(json.dumps(list(reader.get_variants())))
