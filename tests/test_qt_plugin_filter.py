from PySide2.QtWidgets import * 
from PySide2.QtCore import * 

from cutevariant.core.importer import import_file
from cutevariant.gui.plugins.filter.widget import FilterModel, FilterWidget
import sqlite3


def test_filter_model(qtbot,qtmodeltester):
    conn = sqlite3.connect(":memory:")
    import_file(conn, "examples/test.vcf")
    
    model = FilterModel(conn)

    data = {
        "AND": [
            {"field": "chr", "operator": "=", "value": "chr"},
            {
                "OR": [
                    {"field": "i0", "operator": "=", "value": 5},
                    {"field": "i1", "operator": "=", "value": 3},
                    {"field": "i2", "operator": "=", "value": 3},
                ]
            },
        ]
    }
    model.filter = data 
    assert model.filter == data 
    #qtmodeltester.check(model)

def test_filter_widget(qtbot):
    conn = sqlite3.connect(":memory:")
    import_file(conn, "examples/test.vcf")

    view = FilterWidget()
    view.conn = conn

    # check if adding condition raise a changed signal 
    with qtbot.waitSignal(view.changed):
        view.on_add_logic()
        assert view.filters == {'AND': []}


    


    




    