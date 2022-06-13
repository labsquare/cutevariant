from .widgets import QueryDialog, QueryListModel, QueryWidget

from PySide6.QtCore import Qt


def test_query_dialog(qtbot):
    w = QueryWidget()
    item = {
        "name": "sacha",
        "description": "A query",
        "query": "SELECT chr FROM variants",
    }
    w.set_item(item)
    d = w.get_item()
    assert d == item


def test_query_model(qtmodeltester):
    model = QueryListModel()
    model.add_preset("sacha", "Une requête sauvegardée", "SELECT chr,pos,ref FROM variants")
    model.add_preset(
        "charles", "Sa requête aussi", "SELECT chr FROM variants WHERE ann.gene='CFTR'"
    )
    qtmodeltester.check(model)

    assert model.data(model.get_preset_index("sacha"), Qt.DisplayRole) == "sacha"

    assert model.rowCount() == 2

    model.remove_preset(model.get_preset_index("sacha"))

    assert model.rowCount() == 1
