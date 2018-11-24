from .abstractreader import AbstractReader
from ..model import Variant, Field
import csv 

class CsvReader(AbstractReader):
	def __init__(self, device):
		super(CsvReader,self).__init__(device)

	

	def get_fields(self):
		yield Field.default_field("chr")
		yield Field.default_field("pos")
		yield Field.default_field("ref")
		yield Field.default_field("alt")


	def get_variants(self):
		csvreader = csv.reader(self.device,delimiter="\t")
		for row in csvreader:
			variant = {}
			variant["chr"] = row[0]
			variant["pos"] = row[1]
			variant["ref"] = row[2]
			variant["alt"] = row[3]

			yield variant
			




if __name__ == "__main__":
	print("yello")