from .abstractreader import AbstractReader

class VcfReader(AbstractReader):
	def __init__(self,filename):
		super(VcfReader,self).__init__(filename)
		print("create vcf reader")

	def get_variants(self):
		return ("chr","pos","alt","ref")

	def get_fields(self):
		return None
