from peewee import * 


db = Proxy()  # Create a proxy for our db.


class Variant(Model):
	chrom = CharField()
	pos   = IntegerField()
	ref   = CharField()
	alt   = CharField()

	class Meta:
		database = db 


class Field(Model):

 

	name = CharField()
	category = CharField()
	description = CharField()
	field_type  = CharField()



	@staticmethod
	def insert_default():
		Field(name = "chr", category="variant", description="truc", field_type="TEXT").save()
		Field(name = "pos", category="variant", description="truc", field_type="INTEGER").save()
		Field(name = "ref", category="variant", description="truc", field_type="TEXT").save()
		Field(name = "alt", category="variant", description="truc", field_type="TEXT").save()



	class Meta:
		database = db 

