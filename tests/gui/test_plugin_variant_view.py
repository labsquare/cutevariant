from tests import utils
import pytest
import tempfile

# Qt imports
from PySide2 import QtCore, QtWidgets


from cutevariant.gui.plugins.variant_view import widgets
from cutevariant.core import sql, importer
from cutevariant.core.reader import VcfReader


@pytest.fixture
def conn():

    #  Required a real file to make it work !
    tempdb = tempfile.mkstemp(suffix=".db")[1]
    conn = sql.get_sql_connection(tempdb)
    importer.import_reader(conn, VcfReader(open("examples/test.snpeff.vcf"), "snpeff"))
    return conn


def test_model_load(qtmodeltester, qtbot, conn):

    model = widgets.VariantModel()
    model.conn = conn

    model.fields = ["chr", "pos", "ref", "alt"]

    # Load asynchronously
    with qtbot.waitSignals(
        [model.variant_loaded, model.count_loaded], timeout=5000
    ) as blocker:
        model.load()

    # Test default variants !
    assert model.total == 11
    assert model.rowCount() == model.total
    assert model.columnCount() == len(model.fields) + 1
    qtmodeltester.check(model)


def test_model_pagination(qtbot, conn):

    model = widgets.VariantModel()
    model.conn = conn
    model.limit = 6
    model.fields = ["chr", "pos", "ref", "alt"]

    # Load asynchronously
    with qtbot.waitSignals(
        [model.variant_loaded, model.count_loaded], timeout=5000
    ) as blocker:
        model.load()

    # Test default variants !
    assert model.total == 11
    assert model.rowCount() == 6
    assert model.page == 1
    assert model.pageCount() == 2

    #  Move to next page

    assert model.hasPage(2)
    model.nextPage()

    with qtbot.waitSignal(model.load_finished, timeout=5000):
        model.load()

    assert model.total == 11
    assert model.rowCount() == 5
    assert model.page == 2

    assert not model.hasPage(3)

    # Move to previous page
    # model.previousPage()
    # with qtbot.waitSignal(model.load_finished, timeout=5000):
    #     model.load()
    # assert model.page == 1

    # #  Move to last page
    # model.lastPage()
    # with qtbot.waitSignal(model.load_finished, timeout=5000):
    #     model.load()

    # assert model.page == 2

    # # Move to first page
    # with qtbot.waitSignal(model.load_finished, timeout=5000):
    #     model.firstPage()
    # assert model.page == 1


def test_model_data(qtbot, conn):

    model = widgets.VariantModel()
    model.conn = conn
    model.fields = ["chr", "pos", "ref", "alt"]

    # Load asynchronously
    with qtbot.waitSignal(model.load_finished, timeout=5000) as blocker:
        model.load()

    #  Test read variant
    variant = model.variant(0)
    assert isinstance(variant, dict)

    # Check if fields present in variant
    for field in model.fields:
        assert field in variant

    # Test header data
    assert model.fields[0] == "chr"
    assert model.headerData(1) == "chr"

    #  Test data first cells ( chromosome 5 )
    index = model.index(1, 0)
    assert model.data(index) == "5"


def test_model_sort(qtbot, conn):
    model = widgets.VariantModel()
    model.conn = conn
    model.fields = ["chr", "pos", "ref", "alt"]

    # First load data
    with qtbot.waitSignal(model.load_finished, timeout=5000):
        model.load()

    # Then Sort position ( colonne 2 )
    with qtbot.waitSignal(model.load_finished, timeout=5000) as blocker:
        model.sort(2, QtCore.Qt.DescendingOrder)


def test_view(qtbot, conn):

    view = widgets.VariantView()
    view.conn = conn

    # with qtbot.waitSignals(
    #     [view.model.variant_loaded, view.model.count_loaded], timeout=5000
    # ) as blocker:
    #     view.load()
