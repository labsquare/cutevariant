from cutevariant.core.reader import VcfReader, FakeReader
from cutevariant.core import sql, Query, importer
import sys 
import json
import sqlite3
import os

from PySide2.QtWidgets import * 
from PySide2.QtCore import * 
from PySide2.QtGui import * 




try:
    os.remove("/tmp/test.db")
except:
    pass

conn = sqlite3.connect("/tmp/test.db")

reader = VcfReader(open("examples/test.snpeff.vcf") , "snpeff")

print(reader.get_samples())

importer.import_reader(conn, reader)


