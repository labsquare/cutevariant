import sys 
import json
import sqlite3
import os

from cutevariant.core.reader import VcfReader,FakeReader
from cutevariant.core.importer import import_reader
from cutevariant.core.sql import QueryBuilder

import json 

try:
    os.remove("/tmp/test.db")
except:
    pass 


from cutevariant.core.vql import execute_vql

#reader  = VcfReader(open("/home/sacha/Downloads/test.hg19_multianno_MPA_20190529.vcf")) 
reader = FakeReader()
conn = sqlite3.connect("/tmp/test.db")

import_reader(conn,reader)


q = QueryBuilder(conn)
q.set_from_vql("SELECT chr,pos, annotation.ref FROM variants WHERE pos > 3 ")

print(q.sql())


# for i in reader.get_variants():
#     print(json.dumps(i))





