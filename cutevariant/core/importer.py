import peewee
from .readerfactory import ReaderFactory
from . import model
import os
from PySide2.QtCore import *


def import_file(filename, db_filename):
	
	database = peewee.SqliteDatabase(db_filename)
	model.db.initialize(database)

	try:
		os.remove(db_filename)
	except:
		pass

	# depend on file type.. Actually, only one 
	reader = ReaderFactory.create_reader(filename)

	# create dynamics variant fields 
	for field in reader.get_fields():
		column_name = field["category"]+"_"+field["name"]
		new_field = peewee.CharField(column_name=column_name,null=True)
		model.Variant._meta.add_field(column_name, new_field)



		# Create table 
	database.create_tables([
		model.Variant,
		model.Field])

	model.Field.insert_default()
	reader.device.seek(0)

	model.Field.insert_many(reader.get_fields()).execute()

	
	reader.device.seek(0)
	
	with database.atomic():

		chunk_size = 100
		chunk = []
		for i in reader.get_variants():

			chunk.append(i)

			if len(chunk)  == chunk_size:
				model.Variant.insert_many(chunk).execute()
				chunk.clear()

		model.Variant.insert_many(chunk).execute()


	print("done")





	
