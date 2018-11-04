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
			yield {
			"chrom":record.CHROM,
			"pos": record.POS,
			"ref":record.REF,
			"alt":record.ALT[0]
			}

	def get_fields(self):

		fields = []

		vcf_reader = vcf.Reader(open(self.filename, 'r'))
		for key,info in vcf_reader.infos.items():
			yield {
			"name":"info_"+key,
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


