from cutevariant.core.importer import Importer

import peewee
import sys 
from cutevariant.gui import * 


from PyQt5.QtWidgets import *
from PyQt5.QtCore import *

app = QApplication(sys.argv)


w = MainWindow()

w.show()

app.exec()





#test = Importer("test.db")
#test.import_file("/home/sacha/test2.vcf")

# model = VariantModel()


# view = QListView()

# view.setModel(model)

# model.load("test.db")

# view.show()