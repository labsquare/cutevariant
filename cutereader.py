from cutevariant.core.reader import VcfReader, FakeReader
from cutevariant.core import sql, Query
import sys 
import json
import sqlite3
import os

from PySide2.QtWidgets import * 
from PySide2.QtCore import * 
from PySide2.QtGui import * 



conn = sqlite3.connect("examples/test.db")


query = Query(conn)
query.group_by = ("chr","pos")
query.selection = "truc"

print(query.sql())




	# sql.create_table_variants(conn, reader.get_fields_by_category("variant"))

	# for _,_ in sql.async_insert_many_variants(conn, reader.get_variants()):
	# 	print("insert")



	# if options == "fields":
	# 	print(json.dumps(list(reader.get_fields())))

	# else: 
	# 	print(json.dumps(list(reader.get_variants())))
