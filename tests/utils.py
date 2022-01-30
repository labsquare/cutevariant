import sqlite3
from PySide2.QtWidgets import *


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


def create_conn(file_name=None, annotation_parser=None):
    if not file_name:
        file_name = "examples/test.snpeff.vcf"
        annotation_parser = "snpeff"
    conn = sql.get_sql_connection(":memory:")
    sql.import_reader(conn, VcfReader(file_name, annotation_parser))
    return conn


def create_qt_application():
    QApplication()
    qApp.setOrganizationName("labsquare")
    qApp.setApplicationName("cutevariantTest")
    return qApp
