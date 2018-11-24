from PySide2.QtWidgets import * 
from PySide2.QtCore import * 
import sys
import peewee
from cutevariant.core.model import * 
from cutevariant.core.reader import *

from cutevariant.core.readerfactory import ReaderFactory
from cutevariant.core.importer import import_file

from cutevariant.gui.variantview import * 





if __name__ == "__main__":

    # try:
    #     os.remove("/tmp/test2.db")
    # except:
    #     pass 

    database = SqliteDatabase("/tmp/test2.db")
    db.initialize(database)

    import_file("exemples/test2.vcf", "/tmp/test2.db")




    app= QApplication()
    d = VariantDelegate()
    v = VariantModel()
    v.load()

    w = QTreeView()
    w.setItemDelegate(d)

    w.setModel(v)
    w.show()
    app.exec_()


