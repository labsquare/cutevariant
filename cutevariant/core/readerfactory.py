from .reader.vcfreader import VcfReader

class ReaderFactory(object):
	'''
	Create reader depending file type 
	'''
	def __init__(self):
		pass 

	@staticmethod
	def create_reader(filename):
		
		# create a reader depending file type .. actually, only one 
		return VcfReader(filename)
		pass 

