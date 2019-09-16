
from cutevariant.gui.plugins.columns.widgets import ColumnsModel
import sqlite3

def test_model(qtbot, qtmodeltester):
    conn = sqlite3.connect("examples/test.db")
    model = ColumnsModel(conn)
    model.load()
    #qtmodeltester.check(model)
    model.columns = ["chr","pos"]
    assert model.columns == ["chr","pos"]

    with qtbot.assertNotEmitted(model.itemChanged):
        model.columns = ["chr","pos","ref"]


