import sqlite3


def table_exists(conn: sqlite3.Connection, name):
    c = conn.cursor()
    c.execute(f"SELECT name FROM sqlite_master WHERE name = '{name}'")
    return c.fetchone() != None


def table_count(conn: sqlite3.Connection, name):
    c = conn.cursor()
    c.execute(f"SELECT COUNT(*) as 'count' FROM {name}")
    return c.fetchone()[0]


def table_drop(conn, name):
    c = conn.cursor()
    c.execute(f"DROP TABLE IF EXISTS {name}")


from cutevariant.core import sql
from cutevariant.core.reader import VcfReader
from cutevariant.core.importer import import_reader


def create_conn():
    conn = sql.get_sql_connexion(":memory:")
    import_reader(conn, VcfReader(open("examples/test.snpeff.vcf"), "snpeff"))
    return conn
