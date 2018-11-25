from peewee import *
import os


db = Proxy()  # Create a proxy for our db.


class Field(Model):
    name = CharField()
    category = CharField()
    description = CharField()
    value_type = CharField()

    class Meta:
        database = db

        default_field = {
            "chr": {
                "name": "chr",
                "category": "variant",
                "description": "chromosom",
                "value_type": "Char",
            },
            "pos": {
                "name": "pos",
                "category": "variant",
                "description": "position",
                "value_type": "Integer",
            },
            "ref": {
                "name": "ref",
                "category": "variant",
                "description": "reference base",
                "value_type": "Char",
            },
            "alt": {
                "name": "alt",
                "category": "variant",
                "description": "alternative base",
                "value_type": "Char",
            },
        }

    def to_meta_field(self):
        if self.value_type == "Integer":
            return IntegerField(
                column_name=self.name, null=True, help_text=self.description
            )

        if self.value_type == "Char":
            return CharField(
                column_name=self.name, null=True, help_text=self.description
            )

        if self.value_type == "Float":
            return FloatField(
                column_name=self.name, null=True, help_text=self.description
            )

        if self.value_type == "Boolean":
            return BooleanField(
                column_name=self.name, null=True, help_text=self.description
            )

        return CharField(column_name=self.name, null=True, help_text=self.description)

    def default_field(name):
        return Field._meta.default_field.get(name)


class Variant(Model):
    class Meta:
        database = db

    def __getitem__(self, key):
        return getattr(self, key, None)

    @staticmethod
    def create_meta_fields():
        for field in Field.select():
            Variant.create_meta_field(field)

    @staticmethod
    def create_meta_field(field: Field):
        Variant._meta.add_field(field.name, field.to_meta_field())

    @classmethod
    def create_view(cls, name, where_clause):
        sql = Variant.select().where(where_clause).sql()

        # refactor
        raw = sql[0]
        params = sql[1]

        for param in params:
            param = f"'{param}'"
            raw = raw.replace("?", param, 1)

        Variant._meta.database.obj.execute_sql(f"CREATE VIEW {name} AS {raw}")
        # Create a class dynamically
        class VariantView(cls):
            class Meta:
                db_table = name

        return VariantView


class View(Model):
    name = CharField()
    sql = CharField()
    description = CharField()
    count = IntegerField()

    class Meta:
        database = db


if __name__ == "__main__":

    pass


    #import_file("../../exemples/test2.vcf", "/tmp/test4.db")







