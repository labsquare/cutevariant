import peewee
from .readerfactory import ReaderFactory
from . import model
import os

class Importer:
	'''
	Import a supported filename into sqlite database 
	'''
	def __init__(self, db_filename):
		self.db_filename = db_filename



	def import_file(self, filename):

		# Init database
		self.database = peewee.SqliteDatabase(self.db_filename)
		model.db.initialize(self.database)

		try:
			os.remove(self.db_filename)
		except:
			pass
	


		# depend on file type.. Actually, only one 
		reader = ReaderFactory.create_reader(filename)

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
		model.Field.insert_many(reader.get_fields()).execute()

	
		with self.database.atomic():
			chunk_size = 100
			chunk = []
			for i in reader.get_variants():
				chunk.append(i)

				if len(chunk)  == chunk_size:
					model.Variant.insert_many(chunk).execute()
					chunk.clear()


			model.Variant.insert_many(chunk).execute()




				




		
