from PySide2.QtWidgets import * 
from PySide2.QtCore import * 

from cutevariant.core.importer import import_file
from cutevariant.gui.plugins.selection.widget import selectionModel, SelectionWidget
import sqlite3


def test_model(qtbot,qtmodeltester):
    conn = sqlite3.connect(":memory:")
    import_file(conn, "examples/test.vcf")
    
    

    #qtmodeltester.check(model)

    




    