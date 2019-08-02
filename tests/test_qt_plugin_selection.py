from PySide2.QtWidgets import * 
from PySide2.QtCore import * 

from cutevariant.core.importer import import_file
from cutevariant.gui.plugins.selection.widget import selectionModel, SelectionWidget
import sqlite3


def test_selection_model(qtbot,qtmodeltester):
    conn = sqlite3.connect(":memory:")
    import_file(conn, "examples/test.vcf")


def test_selection_widget(qtbot):
    conn = sqlite3.connect(":memory:")
    import_file(conn, "examples/test.vcf")

    view = SelectionWidget()
    view.conn = conn

    # get first records 
    assert view.model.rowCount() == 1 
    item = view.model.record(view.model.index(0,0))
    assert item["name"] == "variants"

    

    
    
    

    #qtmodeltester.check(model)

    




    