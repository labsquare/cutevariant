from .abstractreader import AbstractReader
from ..model import Variant, Field

import peewee
import vcf


class VcfReader(AbstractReader):
	def __init__(self,filename):
		super(VcfReader,self).__init__(filename)
		print("create vcf reader")

	def get_variants(self):
		vcf_reader = vcf.Reader(open(self.filename, 'r'))
		for record in vcf_reader:

			for index, alt in enumerate(record.ALT):
				variant = {
				"chrom":record.CHROM,
				"pos": record.POS,
				"ref":record.REF,
				"alt":alt
				}

				# Read annotations 
				# print(record.INFO)
				for field  in self.get_fields():
					category = field["category"]
					name     = field["name"]
					ftype    = field["field_type"]
					colname  = category+"_"+name
					value    = None
		
					# PARSE INFO
					if category == "info":	 
						# Test flags 
						if ftype == "Flag":
							variant[colname] = True if name in record.INFO else False 
						else:
							if name in record.INFO: 
								if isinstance(record.INFO[name], list):
									value = record.INFO[name][0]
								else:
									value = record.INFO[name]
							variant[colname] = value


					# PARSE GENOTYPE / SAMPLE 
					if category == "sample":
						for sample in record.samples:
							sname = name.split("_")[0]

							for key, value in sample.data._asdict().items():
								colname = "sample_"+sname +"_"+key
								variant[colname] = value

							


			yield variant




	def get_fields(self):
		fields = []

		vcf_reader = vcf.Reader(open(self.filename, 'r'))
		for key,info in vcf_reader.infos.items():
			yield {
			"name":key,
			"category": "info",
			"description":info.desc,
			"field_type": info.type
			}

		for sample in vcf_reader.samples:
			for key, val in vcf_reader.formats.items():
				yield {
				"name":sample+"_"+key,
				"category":"sample",
				"description":val.desc,
				"field_type": val.type
				}


