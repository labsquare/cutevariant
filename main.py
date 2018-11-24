from PySide2.QtWidgets import * 
from PySide2.QtCore import * 
import sys
import peewee
from cutevariant.core.model import * 
from cutevariant.core.reader import *

from cutevariant.core.readerfactory import ReaderFactory
from cutevariant.core.importer import import_file


import_file("exemples/test2.vcf", "/tmp/test2.db")




