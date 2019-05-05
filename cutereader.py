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



reader = VcfReader(open("examples/test.snpeff.vcf") , "snpeff")


list(reader.get_fields())
print(json.dumps(list(reader.get_variants())))

