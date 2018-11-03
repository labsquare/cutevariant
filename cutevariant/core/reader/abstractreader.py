from abc import ABC, abstractclassmethod

class AbstractReader(ABC):
	def __init__(self, filename):
		super(AbstractReader,self).__init__()
		self.filename = filename


	@abstractclassmethod
	def get_variants(self):
		raise NotImplemented()

	@abstractclassmethod
	def get_fields(self):
		raise NotImplemented()





		