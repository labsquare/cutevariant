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


FILTERS = {
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
                                {"field": "gene", "operator": "=", "value": "chr12"},
                                {"field": "gene", "operator": "=", "value": "chr12"},
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


def test_model_load(qtmodeltester, conn):

    model = widgets.FilterModel(conn)

    model.load(FILTERS)
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
    assert model.rowCount(model.index(0, 0)) == len(FILTERS["AND"])

    #  Clear data
    model.clear()
    assert model.rowCount(model.index(0, 0)) == 0

    #  Get back data from file
    model.from_json(filename)
    assert model.rowCount(model.index(0, 0)) == len(FILTERS["AND"])


def test_save_view(qtbot, monkeypatch, conn):

    view = widgets.FiltersEditorWidget()
    view.model.conn = conn
    view.model.load(FILTERS)

    #  test if settings works ( saving filter_path )
    temp_dir = tempfile.mkdtemp(prefix="filter")
    file_path_1 = temp_dir + "/test1.filter.json"
    file_path_2 = temp_dir + "/test2.filter.json"

    view.filter_path = temp_dir
    assert view.filter_path == temp_dir

    #  ON_SET_DIRECTORY
    view.filter_path = "/"
    monkeypatch.setattr(QFileDialog, "exec_", lambda x: True)
    monkeypatch.setattr(QFileDialog, "selectedFiles", lambda x: [temp_dir])
    view.on_set_directory()
    assert view.filter_path == temp_dir

    # ON SAVE_AS file_path_1
    monkeypatch.setattr(QFileDialog, "exec_", lambda x: True)
    monkeypatch.setattr(QFileDialog, "selectedFiles", lambda x: [file_path_1])
    view.on_save_as()
    assert os.path.exists(file_path_1)
    assert view.combo.count() == 1
    assert view.combo.currentText() == "test1"
    assert view.model.filters == FILTERS

    # ON SAVE_AS file_path_2 ( is an empty file )
    view.model.clear()
    monkeypatch.setattr(QFileDialog, "exec_", lambda x: True)
    monkeypatch.setattr(QFileDialog, "selectedFiles", lambda x: [file_path_2])
    view.on_save_as()
    assert os.path.exists(file_path_2)
    assert view.combo.count() == 2  #  There is 2 file in the combo
    assert view.combo.currentText() == "test2"
    assert view.model.filters == {"AND": []}

    #  test change file from combo
    view.combo.setCurrentText("test1")
    assert view.model.filters == FILTERS

    # ON DELETE
    monkeypatch.setattr(QMessageBox, "exec_", lambda x: True)
    view.on_delete()
    assert not os.path.exists(file_path_1)
