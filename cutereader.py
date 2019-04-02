from cutevariant.core.reader import VcfReader
import sys 
import json

filename = sys.argv[1]
options = sys.argv[2]

with open(filename,"r") as file:

	reader = VcfReader(file)

	if options == "fields":
		print(json.dumps(list(reader.get_fields())))

	else: 
		print(json.dumps(list(reader.get_variants())))
