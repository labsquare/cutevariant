from peewee import * 
import os

db = Proxy()  # Create a proxy for our db.


class Field(Model):
	name = CharField()
	category = CharField()
	description = CharField()
	value_type  = CharField()


	class Meta:
		database = db 

		default_field =	{
		"chr": {"name": "chr", "category":"variant","description":"chromosom","value_type":"Char"},
		"pos": {"name": "pos", "category":"variant","description":"position","value_type":"Integer"},
		"ref": {"name": "ref", "category":"variant","description":"reference base","value_type":"Char"},
		"alt": {"name": "alt", "category":"variant","description":"alternative base","value_type":"Char"}
		}
		


	def to_meta_field(self):
		if self.value_type == "Integer":
			return IntegerField(column_name=self.name, null=True, help_text=self.description)

		if self.value_type == "Char":
			return CharField(column_name=self.name, null=True, help_text=self.description)

		if self.value_type == "Float":
			return FloatField(column_name=self.name, null=True, help_text=self.description)

		if self.value_type == "Boolean":
			return BooleanField(column_name=self.name, null=True, help_text=self.description)

		return CharField(column_name=self.name, null=True, help_text=self.description)

	def default_field(name):
		return Field._meta.default_field.get(name)
		



class Variant(Model):
	class Meta:
		database = db 

	def __getitem__(self, key):
		return getattr(self, key, None)

	def create_meta_field(field: Field):
		Variant._meta.add_field(field.name, field.to_meta_field())









if __name__ == "__main__":

	try:
		os.remove("/tmp/test.db")
	except:
		pass 

	database = SqliteDatabase("/tmp/test.db")
	db.initialize(database)
	Field.create_table()

	Field.default_field("chr").save()
	Field.default_field("pos").save()
	Field.default_field("ref").save()
	Field.default_field("alt").save()

	for field in Field.select():
		Variant.create_meta_field(field)



	Variant.create_table()






