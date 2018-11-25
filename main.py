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


    # check Variant count from Variant Table
    print(Variant.select().count())

    # Create a sql View 
    SubView = Variant.create_view("sub", Variant.ref == 'A')

    # show the view 
    print(SubView.select().count())

    # TODO 
    # child = Variant.subtract(SubView)   , intersect etc ... 


  