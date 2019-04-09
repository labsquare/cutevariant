from cutevariant.core.reader import VcfReader 
import json
import copy




ann = "vep"		

with open(f"examples/test.{ann}.vcf") as file:

	reader = VcfReader(file,ann)



	#print(json.dumps(list(reader.get_fields())))

	json.dumps(list(reader.get_fields()))
	print(json.dumps(list(reader.get_variants())))