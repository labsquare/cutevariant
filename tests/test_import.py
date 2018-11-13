import pytest
import sys
from cutevariant.core.importer import import_file
from PySide2.QtCore import *

@pytest.fixture
def import_vcf():
	print("create database")
	import_file("exemples/test2.vcf", "test.db")
	

def test_truc(import_vcf):
	print("allo")

def test_truc2():
	print("tre")