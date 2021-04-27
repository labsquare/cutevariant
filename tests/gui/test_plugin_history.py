from tests import utils
import pytest
import tempfile

# Qt imports
from PySide2 import QtCore, QtWidgets, QtGui

from tests import utils


from cutevariant.gui.plugins.vql_history import widgets as w
from cutevariant.core import sql


@pytest.fixture
def conn():
    return utils.create_conn()


def test_model(conn, qtmodeltester):

    model = w.HistoryModel()

    COUNT = 10
    for i in range(COUNT):
        model.add_record("SELECT chr,pos FROM variants", i, 0.33)

    qtmodeltester.check(model)

    assert model.rowCount() == COUNT
    assert model.columnCount() == 5

    # serialiser
    data = model.to_json()

    model.clear()
    assert model.rowCount() == 0

    #  unserialiser
    model.from_json(data)
    assert model.rowCount() == COUNT

    assert model.get_last_query() == "SELECT chr,pos FROM variants"

    #  Remove first and last rows
    first_index = model.index(0, 0)
    last_index = model.index(COUNT - 1, 0)

    model.removeRows([first_index, last_index])

    for i in range(model.rowCount()):
        index = model.index(i, 0)
        count = model.get_record(index)[-1]
        #  Count cannot be 0 or 10
        assert count != 0 and count != COUNT - 1


def test_plugin(conn, qtbot):

    widget = w.VqlHistoryWidget()
    widget.show()


# def test_plugin(conn, qtbot):
#     plugin = widgets.FieldsEditorWidget()
#     plugin.on_open_project(conn)

#     assert plugin.widget_fields.views[0]["model"].rowCount() == len(
#         sql.get_field_by_category(conn, "variants")
#     )
#     assert plugin.widget_fields.views[1]["model"].rowCount() == len(
#         sql.get_field_by_category(conn, "annotations")
#     )
#     assert plugin.widget_fields.views[2]["model"].rowCount() == len(
#         sql.get_field_by_category(conn, "samples")
#     ) * len(list(sql.get_samples(conn)))

#     checked_fields = [
#         "chr",
#         "pos",
#         "ann.gene",
#         "ann.impact",
#         "samples.TUMOR.gt",
#         "samples.NORMAL.gt",
#     ]
#     plugin.widget_fields.checked_fields = checked_fields
#     assert len(plugin.widget_fields.views[0]["model"].checked_fields) == 2
#     assert len(plugin.widget_fields.views[1]["model"].checked_fields) == 2
#     assert len(plugin.widget_fields.views[2]["model"].checked_fields) == 2
