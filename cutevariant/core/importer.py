from sqlalchemy import create_engine
import os
import csv

from .readerfactory import ReaderFactory
from .model import *


def import_file(filename, engine):

    session = create_session(engine)

    Field.__table__.create(engine)
    View.__table__.create(engine)
    VariantSet.__table__.create(engine)

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


def import_bed(filename, engine):

    with open(filename, "r") as file:

        Region.__table__.create(engine)
        session = create_session(engine)
        for line in csv.reader(file, delimiter="\t"):
            region = Region(chr=line[0], start = line[1], end = line[2], name = line[3])
            session.add(region)
        session.commit()
