from cutevariant.core.reader.fakereader import FakeReader
from tests import utils
import pytest
import tempfile

# Qt imports
from PySide6 import QtCore, QtWidgets


from cutevariant.gui.plugins.variant_view import widgets
from cutevariant.core import sql
from cutevariant.core.reader import VcfReader


@pytest.fixture
def conn():

    # Required a real file to make it work !
    tempdb = tempfile.mkstemp(suffix=".db")[1]
    conn = sql.get_sql_connection(tempdb)
    sql.import_reader(conn, FakeReader())
    return conn


def test_plugin(qtbot, conn):

    plugin = widgets.VariantViewWidget()
    plugin.mainwindow = utils.create_mainwindow()
    plugin.on_refresh()
    qtbot.addWidget(plugin)


def test_model_load(qtmodeltester, qtbot, conn):

    model = widgets.VariantModel()
    model.conn = conn

    model.fields = ["chr", "pos", "ref", "alt"]

    # Load asynchronously
    with qtbot.waitSignals([model.variant_loaded, model.count_loaded], timeout=10000) as blocker:
        model.load()

    # Test default variants !
    assert model.total == 3
    assert model.rowCount() == model.total
    assert model.columnCount() == len(model.fields)
    qtmodeltester.check(model)


def test_model_pagination(qtbot, conn):

    model = widgets.VariantModel()
    model.conn = conn
    model.limit = 2
    model.fields = ["chr", "pos", "ref", "alt"]

    # Load asynchronously
    with qtbot.waitSignals([model.variant_loaded, model.count_loaded], timeout=10000) as blocker:
        model.load()

    # Test default variants !
    assert model.total == 3
    assert model.rowCount() == 2
    assert model.page == 1
    assert model.pageCount() == 2

    #  Move to next page

    assert model.hasPage(2)
    model.nextPage()

    with qtbot.waitSignal(model.load_finished, timeout=None):
        model.load()

    assert model.total == 3
    assert model.rowCount() == 1
    assert model.page == 2

    assert not model.hasPage(3)

    # Move to previous page
    # model.previousPage()
    # with qtbot.waitSignal(model.load_finished, timeout=10000):
    #     model.load()
    # assert model.page == 1

    # #  Move to last page
    # model.lastPage()
    # with qtbot.waitSignal(model.load_finished, timeout=10000):
    #     model.load()

    # assert model.page == 2

    # # Move to first page
    # with qtbot.waitSignal(model.load_finished, timeout=10000):
    #     model.firstPage()
    # assert model.page == 1


def test_model_data(qtbot, conn):

    model = widgets.VariantModel()
    model.conn = conn
    model.fields = ["chr", "pos", "ref", "alt"]

    # Load asynchronously
    with qtbot.waitSignal(model.load_finished, timeout=10000) as blocker:
        model.load()

    #  Test read variant
    variant = model.variant(0)
    assert isinstance(variant, dict)

    # Check if fields present in variant
    for field in model.fields:
        assert field in variant

    # Test header data
    assert model.fields[0] == "chr"
    assert model.headerData(0) == "chr"

    #  Test data first cells ( chromosome 11 )
    index = model.index(0, 0)
    assert model.data(index) == "11"


def test_model_sort(qtbot, conn):
    model = widgets.VariantModel()
    model.conn = conn
    model.fields = ["chr", "pos", "ref", "alt"]

    # First load data
    with qtbot.waitSignal(model.load_finished, timeout=10000):
        model.load()

    # Then Sort position ( colonne 2 )
    with qtbot.waitSignal(model.load_finished, timeout=10000) as blocker:
        model.sort(2, QtCore.Qt.DescendingOrder)


def test_view(qtbot, conn):

    view = widgets.VariantView()
    view.conn = conn

    # with qtbot.waitSignals(
    #     [view.model.variant_loaded, view.model.count_loaded], timeout=10000
    # ) as blocker:
    #     view.load()
