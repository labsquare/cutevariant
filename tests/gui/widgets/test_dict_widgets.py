from cutevariant.gui.widgets import DictModel, DictWidget

from PySide6.QtCore import Qt
from PySide6.QtGui import QKeySequence


def test_dict_widget(qtbot, qtmodeltester):

    w = DictWidget()
    qtbot.addWidget(w)
    w.set_dict({"name": "boby", "age": 12, "valid": True})

    assert w.model.data(w.model.index(0, 0)) == "name"
    assert w.model.data(w.model.index(0, 1)) == "boby"

    #  test filters
    assert w.proxy_model.rowCount() == 3
    w.search_bar.setText("age")
    assert w.proxy_model.rowCount() == 1
