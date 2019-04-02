from cutevariant.core.reader import VcfReader, FakeReader
from cutevariant.core import sql 
import sys 
import json
import sqlite3
import os


filename = "examples/test.vcf"

try:
	os.remove("/tmp/test.db")
except:
	pass



with open(filename,"r") as file:

	reader = FakeReader(file)
	conn = sqlite3.connect("/tmp/test.db")

	sql.create_table_fields(conn)
	sql.insert_many_fields(conn, reader.get_fields())

	sql.create_table_samples(conn)
	sql.insert_many_samples(conn, reader.get_samples())

	sql.create_table_variants(conn, reader.get_fields())

	sql.insert_many_variants(conn, reader.get_variants())






	# if options == "fields":
	# 	print(json.dumps(list(reader.get_fields())))

	# else: 
	# 	print(json.dumps(list(reader.get_variants())))
