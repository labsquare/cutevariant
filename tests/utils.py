import sqlite3
from PySide6.QtWidgets import *


class FakeMainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self._state = {
            "fields": ["chr", "pos", "ref", "alt"],
            "filters": {},
            "source": "variants",
            "current_variant": {"id": 1},
            "executed_query_data": {"count": 100, "elapsed_time": 3.0},
            "samples": ["TUMOR"],
            "order_by": [],
            "order_asc": True,
        }

        self.step_counter = {}

    def on_register(self):
        pass

    def refresh_plugins(self, sender):
        pass

    def on_open_project(self):
        pass

    def set_state_data(self, key, value):
        self._state[key] = value

    def get_state_data(self, key):
        return self._state[key]


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


def create_mainwindow():
    return FakeMainWindow()


def create_conn(file_name=None, annotation_parser=None):
    if not file_name:
        file_name = "examples/test.snpeff.vcf"
        annotation_parser = "snpeff"
    conn = sql.get_sql_connection(":memory:")
    sql.import_reader(conn, VcfReader(file_name, annotation_parser))
    return conn
