from cutevariant.core.importer import ImportTask

import peewee
import sys 
from cutevariant.gui import *
from cutevariant.gui.Test import VariantModel


from PyQt5.QtWidgets import *
from PyQt5.QtCore import *


task = ImportTask("/home/sacha/test2.vcf", "test.db")

