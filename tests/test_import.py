import pytest
import sys
from cutevariant.core.importer import import_file
from cutevariant.core.model import * 
from PySide2.QtCore import *
import peewee
import os

def import_vcf():
	print("create database")
	import_file("exemples/test2.vcf", "test.db")

@pytest.fixture
def connection():
	assert os.path.exists("test.db")
	db.initialize(peewee.SqliteDatabase("test.db"))  



def test_database(connection):
	assert len(Variant.select()) == 448
	assert len(Field.select()) == 62

def test_fields(connection):

	assert Field.get_by_id(1).name == "chr" 
	assert Field.get_by_id(2).name == "pos" 
	assert Field.get_by_id(3).name == "ref" 
	assert Field.get_by_id(4).name == "alt" 


def test_truc2():
	print("tre")