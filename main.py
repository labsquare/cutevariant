from cutevariant.core.importer import ImportTask

import peewee
import sys 
from cutevariant.gui import *
from cutevariant.gui.Test import VariantModel
from cutevariant.core import model


from PyQt5.QtWidgets import *
from PyQt5.QtCore import *


database = peewee.SqliteDatabase("test.db")
model.db.initialize(database)

for v in model.Variant.select():
	print(v.chrom)