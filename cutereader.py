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



reader  = VcfReader(open("/home/sacha/Downloads/test.hg19_multianno_MPA_20190529.vcf")) 
# reader = FakeReader()
conn = sqlite3.connect("/tmp/test.db")

import_reader(conn,reader)

# print(json.dumps(list(reader.get_fields())))

# for i in reader.get_variants():
#     print(json.dumps(i))
#     break




