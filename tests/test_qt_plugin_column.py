from PySide2.QtWidgets import * 
from PySide2.QtCore import * 

from cutevariant.core.importer import import_file
from cutevariant.gui.plugins.columns.widget import ColumnsModel, ColumnsWidget
import sqlite3


def test_model(qtbot,qtmodeltester):
    conn = sqlite3.connect(":memory:")
    import_file(conn, "examples/test.vcf")
    
    model = ColumnsModel(conn)
    model.load()

    assert model.rowCount(QModelIndex()) == 2

    # model.columns is a property : test setter and getter 
    # ensure itemChanged is not emited because it will raise an infinite loop with query_widget
    with qtbot.assertNotEmitted(model.itemChanged):
        checked_columns = ["chr","pos","ref","alt"]
        model.columns = checked_columns
        assert model.columns == checked_columns

    qtmodeltester.check(model)

def test_widget(qtbot):
    conn = sqlite3.connect(":memory:")
    import_file(conn, "examples/test.vcf")

    view = ColumnsWidget()
    view.conn = conn 

  





    




    