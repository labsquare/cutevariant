from sqlalchemy import create_engine
import os
import csv

from .readerfactory import ReaderFactory
from .model import *


def import_file(filename, engine):

    session = create_session(engine)

    # Create tables 
    Field.__table__.create(engine)
    Selection.__table__.create(engine)
    selection_has_variant_table.create(engine)

    # get reader 
    reader = ReaderFactory.create_reader(filename)

    # extract fields and create Variant table 
    for data in reader.get_fields():
        session.add(Field(**data))
        Variant.create_column_from_field(Field(**data))

    # Create table 
    Variant.__table__.create(engine)

    session.commit()

    # load variant 
    variant_count = 0
    for i, data in enumerate(reader.get_variants()):
        variant = Variant(**data)
        session.add(variant)
        variant_count += 1
    session.commit()

    # Create default selection 
    session.add(Selection(name="all", description="all variant", count = variant_count))
    session.add(Selection(name="favoris", description="favoris", count = 0))
    
    session.commit()