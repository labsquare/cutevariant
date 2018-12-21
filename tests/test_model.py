import pytest
import sqlite3
from cutevariant.core.model import * 
from cutevariant.core.importer import import_file


def table_exists(name, conn):
	c = conn.cursor()
	c.execute("SELECT name FROM sqlite_master WHERE name = 'f{name}'")
	print(c.fetchone())


def test_creation():
	conn = sqlite3.connect("/tmp/test_cutevariant.db")

	table_exists("variants", conn)

 
