from cutevariant.gui.queryrouter import QueryRouter
from cutevariant.core.importer import import_file
from cutevariant.gui.abstractquerywidget import AbstractQueryWidget
import sqlite3
import pytest

@pytest.fixture
def conn():
    db_path = "/tmp/test_cutevaiant.db"
    import_file("exemples/test.csv", db_path)
    conn = sqlite3.connect(db_path)
    return conn


class A(AbstractQueryWidget):
	def __init__(self):
		super().__init__()

	def setQuery(query):
		print("set A")

	def updateQuery(query):
		print("set B")

def test_routing(conn):
	router = QueryRouter(conn)





