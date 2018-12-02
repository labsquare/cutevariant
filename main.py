from PySide2.QtWidgets import *
from PySide2.QtCore import *
import sys
import peewee
from cutevariant.core.model import *
from cutevariant.core.reader import *

from cutevariant.core.readerfactory import ReaderFactory
from cutevariant.core.importer import import_file

from sqlalchemy_views import CreateView, DropView



if __name__ == "__main__":

    # try:
    #     os.remove("/tmp/test2.db")
    # except:
    #     pass

    import_file("exemples/test2.csv", "/tmp/test2.db")


    engine,session = create_connection("/tmp/test2.db")

    a = VariantView()
    a.name = "test"
    a.sql = "SELECT * FROM variants WHERE chr == 'chr7'"

    b = VariantView()
    b.name = "test2"
    b.sql = "SELECT * FROM variants WHERE chr == 'chr5'"


    session.add(a)
    session.add(b)

    c = a + b 
    c.name = "test3"
    session.add(c)

    session.commit()


    #print(session.query(Variant).filter(Variant.ref == "A"))








    # # check Variant count from Variant Table
    # print(Variant.select().count())

    # # Create a sql View 
    # A = Variant.create_view("A", Variant.ref == 'A')

    # # show the view 
    # print(A.select().count())

    # B = A.create_view("B", Variant.alt == 'C')


    # print(B.select().sql())


    # # TODO 
    # # child = Variant.subtract(SubView)   , intersect etc ... 


    # app = QApplication(sys.argv)
    # w = VariantView()
    # w.load()

    # w.show()

    # app.exec_()