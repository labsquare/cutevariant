import sys 
import json
import sqlite3
import os

from cutevariant.core.reader import VcfReader,FakeReader
from cutevariant.core.importer import import_reader

import json 

try:
    os.remove("/tmp/test.db")
except:
    pass 



#reader  = VcfReader(open("/home/schutz/kevin.vcf")) 
reader = FakeReader()
conn = sqlite3.connect("/tmp/test.db")

import_reader(conn,reader)

# json.dumps(list(reader.get_fields()))

# print(list(reader.get_variants()))




