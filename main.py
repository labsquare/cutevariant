from cutevariant.core.importer import Importer

import peewee


print(peewee.__version__)


test = Importer("test.db")
test.import_file("/home/sacha/test2.vcf")

