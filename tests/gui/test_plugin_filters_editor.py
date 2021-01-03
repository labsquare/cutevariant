from tests import utils
import pytest
import tempfile

# Qt imports
from PySide2 import QtCore, QtWidgets, QtGui

from tests import utils


from cutevariant.gui.plugins.filters_editor import widgets
from cutevariant.core import sql


@pytest.fixture
def conn():
    return utils.create_conn()


def test_model_load(qtmodeltester, conn):

    model = widgets.FilterModel(conn)

    data = {
        "AND": [
            {"field": "gene", "operator": "=", "value": "chr12"},
            {"field": "gene", "operator": "=", "value": "chr12"},
            {
                "AND": [
                    {"field": "gene", "operator": "=", "value": "chr12"},
                    {"field": "gene", "operator": "=", "value": "chr12"},
                    {
                        "AND": [
                            {"field": "gene", "operator": "=", "value": "chr12"},
                            {"field": "gene", "operator": "=", "value": "chr12"},
                            {
                                "AND": [
                                    {
                                        "field": "gene",
                                        "operator": "=",
                                        "value": "chr12",
                                    },
                                    {
                                        "field": "gene",
                                        "operator": "=",
                                        "value": "chr12",
                                    },
                                ]
                            },
                        ]
                    },
                ]
            },
            {"field": "gene", "operator": "=", "value": "chr12"},
            {"field": "gene", "operator": "=", "value": "chr12"},
        ]
    }

    model.load(data)
    qtmodeltester.check(model)

    root_index = model.index(0, 0)
    assert model.item(root_index).type == widgets.FilterItem.LOGIC_TYPE

    first_child = model.index(0, 0, root_index)
    item = model.item(first_child)

    assert item.type == widgets.FilterItem.CONDITION_TYPE
    assert item.data == ["gene", "=", "chr12"]

    #  test save model
    _, filename = tempfile.mkstemp()
    model.to_json(filename)

    #  load model
    assert model.rowCount(model.index(0, 0)) == len(data["AND"])

    #  Clear data
    model.clear()
    assert model.rowCount(model.index(0, 0)) == 0

    #  Get back data from file
    model.from_json(filename)
    assert model.rowCount(model.index(0, 0)) == len(data["AND"])
