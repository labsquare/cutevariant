from cutevariant.core.reader import VcfReader, FakeReader
from cutevariant.core import sql 
import sys 
import json
import sqlite3
import os

from PySide2.QtWidgets import * 
from PySide2.QtCore import * 
from PySide2.QtGui import * 



try:
	os.remove("/tmp/demo.db")
except:
	pass 

conn = sqlite3.connect("/tmp/demo.db")


with open("examples/test.vep.vcf") as file:

	reader = VcfReader(file, "vep")


	#print(json.dumps(list(reader.get_fields_by_category("variants"))))


	sql.create_table_samples(conn)
	sql.insert_many_samples(conn,reader.get_samples())

	sql.create_table_fields(conn)
	sql.insert_many_fields(conn, reader.get_fields())

	for ann in reader.get_fields_by_category("annotations"):
		print(ann)

	sql.create_table_annotations(conn, reader.get_fields_by_category("annotations"))
	# sql.create_table_variants(conn, reader.get_fields_by_category("variant"))

	# for _,_ in sql.async_insert_many_variants(conn, reader.get_variants()):
	# 	print("insert")



	# if options == "fields":
	# 	print(json.dumps(list(reader.get_fields())))

	# else: 
	# 	print(json.dumps(list(reader.get_variants())))
