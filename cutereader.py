import sys 
import json
import sqlite3
import os

from cutevariant.core.reader import VcfReader

from cutevariant.core import vql, importer

from textx import metamodel_from_str, get_children_of_type, metamodel_from_file

# print("salut")
# mm = metamodel_from_file("cutevariant/core/vql.tx")

# model = mm.model_from_str("SELECT sacha FROM variant")

filename = "/media/schutz/DATA/exome/freebayes/EXCRFER_Fam1.freebayes.indel.filtred.vcf"

try:
	os.remove("/tmp/mytest.db")
except:
	pass

conn = sqlite3.connect("/tmp/mytest.db")

importer.import_file(conn, filename)






# try:
#     os.remove("/tmp/test.db")
# except:
#     pass

# conn = sqlite3.connect("/tmp/test.db")

# reader = VcfReader(open("examples/test.snpeff.vcf") , "snpeff")

# print(reader.get_samples())

# importer.import_reader(conn, reader)


