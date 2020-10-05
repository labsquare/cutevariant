from PySide2.QtCore import QThreadPool

from cutevariant.gui.sql_runnable import SqlRunnable
from cutevariant.core import sql, importer
from cutevariant.core.reader import VcfReader
from cutevariant.core.command import count_cmd
import pytest
import tempfile


@pytest.fixture
def conn():
    # Do not use ":memory:" ! SqlThread open the file
    tempdb = tempfile.mkstemp(suffix=".db")[1]
    conn = sql.get_sql_connexion(tempdb)
    importer.import_reader(conn, VcfReader(open("examples/test.snpeff.vcf"), "snpeff"))
    return conn


def test_query(qtbot, conn):

    runnable = SqlRunnable(
        conn,
        lambda conn: list(conn.execute("SELECT COUNT(*) FROM variants").fetchone())[0],
    )

    with qtbot.waitSignal(runnable.signals.finished, timeout=10000) as blocker:
        QThreadPool.globalInstance().start(runnable)

    assert runnable.results == 11
