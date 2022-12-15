from .abstractdbengine import AbstractDB

import sqlite3


class SqliteDB(AbstractDB):
    def __init__(self, filename: str) -> None:
        super().__init__()
        self._conn = sqlite3.Connection(filename)
        self._filename = filename

    def insert_field(
        self, name="no_name", table="variants", field_type="text", description=""
    ) -> None:
        """Insert one fields

        This is a shortcut and it calls insert_fields with one element

        Args:
            conn (sqlite.Connection): sqlite Connection
            name (str, optional): fields name. Defaults to "no_name".
            category (str, optional): fields table. Defaults to "variants".
            field_type (str, optional): type of field in python (str,int,float,bool). Defaults to "text".
            description (str, optional): field description"""

        insert_fields(
            self._conn,
            [
                {
                    "name": name,
                    "category": category,
                    "type": field_type,
                    "description": description,
                }
            ],
        )
