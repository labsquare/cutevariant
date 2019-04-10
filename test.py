from cutevariant.core.reader import VcfReader, FakeReader
from cutevariant.core.importer import async_import_reader
import json
import copy
import sqlite3
import os

from cutevariant.core.readerfactory import detect_vcf_annotation


try:
	os.remove("/tmp/test.db")
except: 
	pass


print(detect_vcf_annotation("examples/test.vep.vcf"))

# reader  = FakeReader()
# print(json.dumps(list(reader.get_fields())))

# conn = sqlite3.connect("/tmp/test.db")

# for progression, message in async_import(conn, reader):
# 	print(progression, message)


# ann = "snpeff"		

# with open(f"examples/test.{ann}.vcf") as file:

# 	reader = VcfReader(file,ann)

# 	conn = sqlite3.connect("/tmp/test.db")
# 	for progression, message in async_import_reader(conn, reader):
# 		print(progression, message)


	#print(json.dumps(list(reader.get_fields())))

	# json.dumps(list(reader.get_fields()))
	# print(json.dumps(list(reader.get_variants())))

