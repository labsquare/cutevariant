from .readerfactory import ReaderFactory

class Importer:
	'''
	Import a supported filename into sqlite database 
	'''
	def __init__(self, db):
		self.database = db 

	
	def import_file(self, filename):
		# depend on file type.. Actually, only one 
		reader = ReaderFactory.create_reader(filename)

		for v in reader.get_variants():
			print(v)




		
