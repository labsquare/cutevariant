from cutevariant.core.engine import AbstractDB

import duckdb


class DuckDB(AbstractDB):
    def __init__(self, filename: str) -> None:
        super().__init__()
        self._filename = filename
        self.conn = duckdb.connect(self._filename)

    def create(self):
        self.conn.execute(
            """CREATE TABLE fields
            (id INTEGER PRIMARY KEY, name VARCHAR, category VARCHAR, type VARCHAR, description VARCHAR, UNIQUE(name, category))
            """
        )
