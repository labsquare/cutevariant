import sqlite3


def table_exists(name, conn: sqlite3.Connection):
    c = conn.cursor()
    c.execute(f"SELECT name FROM sqlite_master WHERE name = '{name}'")
    return c.fetchone() != None


def table_count(name, conn: sqlite3.Connection):
	c = conn.cursor()
	c.execute(f"SELECT COUNT(*) as 'count' FROM {name}")
	return c.fetchone()[0]