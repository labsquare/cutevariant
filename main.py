from cutevariant.core.importer import ImportTask

import peewee
import sys 
from cutevariant.gui import *
from cutevariant.gui.Test import VariantModel
from cutevariant.core import model


from PySide2.QtWidgets import *
from PySide2.QtCore import *



task = ImportTask("exemples/test2.vcf","test.db")

task.run()