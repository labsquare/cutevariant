from tests import utils
import pytest
import tempfile

# Qt imports
from PySide6 import QtCore, QtWidgets, QtGui
from tests import utils

from cutevariant.gui.plugins.genotypes import widgets as w
from cutevariant.core import sql
from cutevariant.core.reader import FakeReader


@pytest.fixture
def conn():

    # Required a real file to make it work !
    tempdb = tempfile.mkstemp(suffix=".db")[1]
    conn = sql.get_sql_connection(tempdb)
    sql.import_reader(conn, FakeReader())
    return conn


def test_model(conn, qtbot, qtmodeltester):

    model = w.GenotypeModel()
    model.conn = conn

    model.set_variant_id(1)
    model.set_samples(["sacha"])
    model.set_fields(["gt", "dp"])

    # Load
    with qtbot.waitSignals([model.load_finished], timeout=5000) as blocker:
        model.load()

    assert model.rowCount() == 1

    assert model.get_genotype(0)["gt"] == 1
    assert model.get_genotype(0)["name"] == "sacha"
    assert "dp" in model.get_genotype(0)

    # test edit
    model.edit([0], {"classification": 6})
    assert model.get_genotype(0)["classification"] == 6

    model.clear()
    assert model.rowCount() == 0
