import sys 
import json
import sqlite3
import os

from cutevariant.core.reader import VcfReader

import json 


reader  = VcfReader(open("examples/test.snpeff.splice.vcf"),"snpeff") 

json.dumps(list(reader.get_fields()))



print(json.dumps(list(reader.get_variants())))






