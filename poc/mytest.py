
from cutevariant.core.importer import import_file, import_reader
from cutevariant.core.readerfactory import  create_reader
from cutevariant.core.reader import FakeReader, VcfReader
from cutevariant.core import sql, vql
from cutevariant.core import command as cmd 

from cutevariant.core.querybuilder import filters_to_vql, filters_to_sql
import sqlite3 
import re




import sys 

from PySide2.QtWidgets import * 
from PySide2.QtCore import * 
from PySide2.QtGui import * 


filters = {'AND': [{'field': 'chr', 'operator': '>', 'value': '100'}]}


print(filters_to_vql(filters))





# import_reader(conn, reader)


# sql.insert_set_from_file(conn, "sacha",  "examples/gene.txt")
# for variant in cmd.execute(conn, "SELECT chr, pos, gene FROM variants WHERE gene IN SET['sacha'] "):
# 	print(variant)

#cmd.execute(conn, "SELECT chr, pos FROM variants")




# app = QApplication(sys.argv)

# w = MainWindow()

# w.show()
# w = QTreeView()
# q = QueryModel(conn)
# print(conn)


# w.setSortingEnabled(True)

# print(q.columnCount())

# q.load_from_vql("SELECT chr, pos, gene, sample('TUMOR').gt FROM variants")
# w.setModel(q)
# w.show()

#app.exec_()