import sys
from cutevariant.core.importer import ImportTask
from PyQt5.QtCore import *

def test_import():
	task = ImportTask("exemples/test2.vcf", "test.db")
	task.run()


def test_truc():
	print("allo")