import peewee
from .readerfactory import ReaderFactory
from . import model
import os
from PyQt5.QtCore import *

class ImportTask(QRunnable):
	'''
	Import a supported filename into sqlite database 
	'''
	def __init__(self, filename, db_filename):
		super(ImportTask,self).__init__()
		self.filename = filename
		self.db_filename = db_filename

	def async_run(self):
		QThreadPool.globalInstance().run(self)


	def run(self):
		# Init database
		self.database = peewee.SqliteDatabase(self.db_filename)
		model.db.initialize(self.database)

		try:
			os.remove(self.db_filename)
		except:
			pass
	


		# depend on file type.. Actually, only one 
		reader = ReaderFactory.create_reader(self.filename)

		# create dynamics variant fields 
		for field in reader.get_fields():
			column_name = field["category"]+"_"+field["name"]
			new_field = peewee.CharField(db_column=column_name,null=True)
			model.Variant._meta.add_field(column_name, new_field)



			# Create table 
		self.database.create_tables([
			model.Variant,
			model.Field])

		model.Field.insert_default()
		reader.device.seek(0)

		model.Field.insert_many(reader.get_fields()).execute()

		
		reader.device.seek(0)
		
		with self.database.atomic():

			chunk_size = 100
			chunk = []
			for i in reader.get_variants():

				chunk.append(i)

				if len(chunk)  == chunk_size:
					model.Variant.insert_many(chunk).execute()
					chunk.clear()

			print(chunk)
			model.Variant.insert_many(chunk).execute()


		print("done")





		
