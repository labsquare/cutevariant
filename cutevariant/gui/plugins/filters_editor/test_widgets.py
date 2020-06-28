import sqlite3

FILTER_DATA = {"AND": [{"field": "chr", "operator": ">", "value": 4}]}


def test_model(qtbot, qtmodeltester):
    conn = sqlite3.connect("examples/test.db")
    # qtmodeltester.check(model)
