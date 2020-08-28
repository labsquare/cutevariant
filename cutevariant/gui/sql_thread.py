from PySide2.QtCore import QThread
import sqlite3

class SqlThread(QThread):

	"""Call a sql query connection from a Thread. 
	Get results when thread is finished.
	
	Usage:

	thread = SqlThread(conn)
	thread.execute("SELECT ..")
	thread.finished.connect(lambda : print(thread.results))

	"""
	
	def __init__(self, conn: sqlite3.Connection, parent = None):
		super().__init__(parent)
		# Get filename and create a new conn
		self.filename = conn.execute('PRAGMA database_list').fetchone()["file"]
		self.query = None
		self.results = None

	def exec_query(self, query):
		self.query = query
		self.run()

	def run(self):
		# We are in a new thread ...
		self.async_conn = sqlite3.Connection(self.filename)
		self.results = self.async_conn.execute(self.query).fetchall()
	