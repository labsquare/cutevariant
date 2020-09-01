import sqlite3

FILTER_DATA = {"AND": []}

from .widgets import FilterModel

def test_model(qtbot, qtmodeltester):
    conn = sqlite3.connect("examples/test.db")

    model = FilterModel(conn)
    model.load(FILTER_DATA)
    qtmodeltester.check(model)

