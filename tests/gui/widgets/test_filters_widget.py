from cutevariant.gui.widgets import FiltersWidget, FiltersModel

from PySide6.QtCore import Qt
from PySide6.QtGui import QKeySequence

from cutevariant.gui.widgets import (
    FiltersModel,
    FiltersWidget,
    FilterItem,
    FilterWidget,
)
from tests import utils


def test_item():
    conn = utils.create_conn()
    model = FiltersModel(conn)

    expected_filters = {"$and": [{"pos": 42}, {"ref": "A"}]}

    item = FiltersModel.to_item(expected_filters)
    assert item.type == FilterItem.LOGIC_TYPE
    assert len(item.children) == 2

    item1 = item.children[0]

    assert item1.type == FilterItem.CONDITION_TYPE
    assert item1.get_field() == list(expected_filters["$and"][0].keys())[0]
    assert item1.get_value() == list(expected_filters["$and"][0].values())[0]
    assert item1.get_operator() == "$eq"


def test_filter_widget(qtbot):

    conn = utils.create_conn()
    widget = FilterWidget(conn)

    qtbot.addWidget(widget)
    widget.set_filter({"pos": 42})
    assert widget.get_filter() == {"pos": {"$eq": 42}}


def test_model(qtmodeltester):
    conn = utils.create_conn()
    model = FiltersModel(conn)

    expected_filters = {"$and": [{"pos": 42}, {"ref": "A"}]}
    model.set_filters(expected_filters)
    assert model.get_filters() == expected_filters

    # Check AND
    assert model.rowCount() == 1
    # Check "children"
    root = model.index(0, 0)
    assert model.rowCount(root) == 2

    # Add items
    model.add_condition_item(("ref", "$eq", "A"), root)
    assert model.rowCount(root) == 3

    # Rem items
    model.remove_item(model.index(0, 0, root))
    assert model.rowCount(root) == 2

    model.clear()
    assert model.rowCount() == 1
    assert model.rowCount(model.index(0, 0)) == 0

    qtmodeltester.check(model)


def test_filters_widget(qtbot):
    conn = utils.create_conn()
    widget = FiltersWidget(conn)

    expected_filters = {"$and": [{"pos": 42}, {"ref": "A"}]}
    root = widget.model().index(0, 0)
    assert widget.model().rowCount() == 1
    assert widget.model().rowCount(root) == 0

    widget.set_filters(expected_filters)
    root = widget.model().index(0, 0)
    assert widget.model().rowCount(root) == 2

    qtbot.addWidget(widget)
