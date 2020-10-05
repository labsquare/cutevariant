import pytest
import tempfile

from PySide2.QtCore import QThreadPool

from cutevariant.gui.sql_runnable import SqlRunnable
from cutevariant.core import sql, importer
from cutevariant.core.reader import VcfReader
from cutevariant.core.command import count_cmd


@pytest.fixture
def conn():
    # Do not use ":memory:" ! SqlThread open the file
    tempdb = tempfile.mkstemp(suffix=".db")[1]
    conn = sql.get_sql_connexion(tempdb)
    importer.import_reader(conn, VcfReader(open("examples/test.snpeff.vcf"), "snpeff"))
    return conn


def test_query(qtbot, conn):
    """Test asynchrone count query"""
    # Fill with a function that will be executed in a separated thread
    runnable = SqlRunnable(
        conn,
        sql.get_variants_count,
    )

    with qtbot.waitSignal(runnable.signals.finished, timeout=10000) as blocker:
        QThreadPool.globalInstance().start(runnable)

    expected = 11
    assert expected == runnable.results

    # Same Query but via VQL wrapper
    runnable = SqlRunnable(
        conn,
        count_cmd,
    )

    with qtbot.waitSignal(runnable.signals.finished, timeout=10000) as blocker:
        QThreadPool.globalInstance().start(runnable)

    expected = {"count": 11}
    assert expected == runnable.results
