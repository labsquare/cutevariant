from cutevariant.core.reader import VcfReader 
import json
import copy





			

with open("examples/test.snpeff.vcf") as file:

	reader = VcfReader(file,"snpeff")


	

	#print(list(reader.get_fields()))

	json.dumps(list(reader.get_fields()))
	print(json.dumps(list(reader.get_variants())))