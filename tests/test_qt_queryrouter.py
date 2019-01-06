
import sqlite3
import pytest
import json
from time import sleep
from PySide2.QtWidgets import *
from PySide2.QtCore import *

from cutevariant.core.importer import import_file
from cutevariant.core import Query

from cutevariant.gui.abstractquerywidget import AbstractQueryWidget
from cutevariant.gui.viewquerywidget import ViewQueryWidget
from cutevariant.gui.columnquerywidget import ColumnQueryWidget
from cutevariant.gui.filterquerywidget import FilterQueryWidget
from cutevariant.gui.queryrouter import QueryRouter


@pytest.fixture
def conn():
    db_path = "/tmp/test_cutevaiant.db"
    conn = sqlite3.connect(db_path)
    return conn


def test_filterQueryWidget(qtbot,qtmodeltester,conn):

	widget = FilterQueryWidget()
	qtbot.addWidget(widget)
	query = Query(conn)
	json_filter = json.loads('''{"AND" : [{"field":"pos", "operator":">", "value":"322424"} ]}''')
	query.filter = json_filter 

	# Set query and construct the treeview
	widget.setQuery(query)

	# test model 
	qtmodeltester.check(widget.model)

	# getQuery.filter must be same as before ( testing parser )
	assert widget.getQuery().filter == json_filter


def test_columnQueryWidget(qtbot,qtmodeltester,conn):

	widget = ColumnQueryWidget()
	qtbot.addWidget(widget)
	query = Query(conn)

	test_columns = ["chr","pos","ref","alt"]
	query.columns = test_columns
	widget.setQuery(query)
	#test du model
	qtmodeltester.check(widget.model)

	# Test if model is good
	model_rows = [widget.model.item(i).text() for i in range(widget.model.rowCount())]
	#models rows must return query.columns
	assert model_rows == test_columns
		


