from tests import utils
import pytest
import tempfile
import os

# Qt imports

from PySide2.QtWidgets import *
from PySide2.QtCore import *
from PySide2.QtGui import *

from tests import utils


from cutevariant.gui.plugins.filters_editor import widgets
from cutevariant.core import sql


@pytest.fixture
def conn():
    return utils.create_conn()


FILTERS = {"$and": [{"gene": "chr12"}]}


def test_model_load(qtmodeltester, conn):

    model = widgets.FilterModel(conn)

    model.load(FILTERS)
    qtmodeltester.check(model)

    root_index = model.index(0, 0)
    assert model.item(root_index).type == widgets.FilterItem.LOGIC_TYPE

    first_child = model.index(0, 0, root_index)
    item = model.item(first_child)

    assert item.type == widgets.FilterItem.CONDITION_TYPE
    assert item.data == ["gene", "$eq", "chr12"]


def test_presets_model(qtmodeltester):
    filename = tempfile.mktemp()
    model = widgets.FiltersPresetModel(config_path=filename)

    model.add_preset(
        "preset A",
        {
            "$and": [
                {"ref": {"$eq": "A"}},
                {"ann.gene": {"$in": {"$wordset": "my_wordset"}}},
            ]
        },
    )
    model.add_preset(
        "preset B", {"$and": [{"ref": {"$eq": "A"}}, {"ann.gene": {"$eq": {"CFTR"}}}]}
    )
    model.add_preset(
        "preset C", {"$and": [{"ref": {"$eq": "A"}}, {"ann.impact": {"$eq": "HIGH"}}]}
    )

    assert model.rowCount() == 3

    model.rem_presets([1])
    assert model.rowCount() == 2

    model.save()

    model.clear()

    assert model.rowCount() == 0

    model.load()

    assert model.rowCount() == 2

    qtmodeltester.check(model)

    os.remove(filename)
