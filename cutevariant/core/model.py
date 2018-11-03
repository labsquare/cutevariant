from peewee import * 


db = SqliteDatabase('test.db')

class Variant(Model):
	chrom = CharField()
	pos   = IntegerField()
	ref   = CharField()
	alt   = CharField()

	class Meta:
		database = db 


class Field(Model):
	name = CharField()
	description = CharField()
	field_type  = CharField()

	class Meta:
		database = db 

