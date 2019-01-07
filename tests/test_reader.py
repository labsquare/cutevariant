
from cutevariant.core.reader import CsvReader, VcfReader
import os 

def test_csv():
	filename = "exemples/test.csv"
	assert os.path.exists(filename), "file doesn't exists"

	with open(filename, "r") as file:
		reader = CsvReader(file)
		fields = [f["name"] for f in reader.get_fields()]
		
		assert "chr" in fields
		assert "pos" in fields
		assert "ref" in fields
		assert "alt" in fields


def test_vcf():
	filename = "exemples/test.vcf"
	assert os.path.exists(filename), "file doesn't exists"

	with open(filename, "r") as file:
		reader = VcfReader(file)
		fields = [f["name"] for f in reader.get_fields()]
		
		assert "chr" in fields
		assert "pos" in fields
		assert "ref" in fields
		assert "alt" in fields


def test_A():
	filename = "exemples/test.vcf"
	assert os.path.exists(filename), "file doesn't exists"

	with open(filename, "r") as file:
		reader = VcfReader(file)
		fields = [f["name"] for f in reader.get_fields()]
		
		assert "chr" in fields
		assert "pos" in fields
		assert "ref" in fields
		assert "alt" in fields

		#print(*reader.get_fields())








