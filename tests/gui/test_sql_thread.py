"""Summary
"""
import pytest
import tempfile
import time
from cutevariant.gui.sql_thread import SqlThread
from cutevariant.core import sql
from cutevariant.core.reader import VcfReader
from cutevariant.core.command import count_cmd


@pytest.fixture
def conn():
    """Summary

    Returns:
        TYPE: Description
    """
    # Do not use ":memory:" ! SqlThread open the file
    tempdb = tempfile.mkstemp(suffix=".db")[1]
    conn = sql.get_sql_connection(tempdb)
    sql.import_reader(conn, VcfReader("examples/test.snpeff.vcf", "snpeff"))
    return conn


def test_query(qtbot, conn):
    """Test asynchrone count query"""
    # Fill with a function that will be executed in a separated thread

    thread = SqlThread(conn, sql.get_variants_count)
    with qtbot.waitSignal(thread.result_ready, timeout=1000) as blocker:
        thread.start()

    assert thread.results == 11

    thread = SqlThread(conn)
    with qtbot.waitSignal(thread.finished, timeout=1000) as blocker:
        thread.start_function(sql.get_variants_count)

    assert thread.results == 11

    thread = SqlThread(conn)
    with qtbot.waitSignal(thread.result_ready, timeout=1000) as blocker:
        thread.start_function(sql.get_variants_count)

    assert thread.results == 11


def test_interupt(qtbot, conn):
    """Test sqlite interruption on a long query"""

    def slow_query(conn):
        """A Sqlite long query that take a long time to execute"""
        conn.execute(
            """
            WITH RECURSIVE r(i) AS (
            VALUES(0)
            UNION ALL
            SELECT i FROM r
            LIMIT 50000000
        )
        SELECT i FROM r WHERE i = 1;
        """
        )

    thread = SqlThread(conn, slow_query)
    with qtbot.waitSignal(thread.error, timeout=2000):
        thread.start()
        time.sleep(1)
        thread.interrupt()

    assert "interrupted" in thread.last_error
