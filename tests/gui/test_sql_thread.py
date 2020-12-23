import pytest
import tempfile

from cutevariant.gui.sql_thread import SqlThread
from cutevariant.core import sql, importer
from cutevariant.core.reader import VcfReader
from cutevariant.core.command import count_cmd


@pytest.fixture
def conn():
    # Do not use ":memory:" ! SqlThread open the file
    tempdb = tempfile.mkstemp(suffix=".db")[1]
    conn = sql.get_sql_connection(tempdb)
    importer.import_reader(conn, VcfReader(open("examples/test.snpeff.vcf"), "snpeff"))
    return conn


def test_query(qtbot, conn):
    """Test asynchrone count query"""
    # Fill with a function that will be executed in a separated thread
    thread = SqlThread(conn, sql.get_variants_count)

    # with qtbot.waitSignal(thread.finished, timeout=1000) as blocker:
    thread.exec_()

    # # Same Query but via VQL wrapper
    # runnable = SqlRunnable(conn, function=count_cmd)

    # with qtbot.waitSignal(runnable.finished, timeout=10000) as blocker:
    #     QThreadPool.globalInstance().start(runnable)

    # expected = {"count": 11}
    # assert expected == runnable.results
