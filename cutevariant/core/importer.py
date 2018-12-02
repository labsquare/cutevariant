from sqlalchemy import create_engine
import os
import csv

from .readerfactory import ReaderFactory
from .model import *


def import_file(filename,engine):


    session = create_session(engine)

    Field.__table__.create(engine)
    VariantView.__table__.create(engine)

    reader = ReaderFactory.create_reader(filename)

    for data in reader.get_fields():
        session.add(Field(**data))
        Variant.create_column_from_field(Field(**data))


    session.commit()

    
    Variant.__table__.create(engine)

 
    for i, data in enumerate(reader.get_variants()):
        variant = Variant(**data)
        session.add(variant)
    session.commit()



def import_bed(filename, db_filename):
    engine,session = create_connection(db_filename)

    with open(filename,"r") as file:
        for line in csv.reader(file, sep="\t"):
            print(line)


