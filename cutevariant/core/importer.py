from sqlalchemy import *
from sqlalchemy.ext.automap import automap_base
import os
import csv
from .readerfactory import ReaderFactory


def import_file(filename, dbpath):

    try:
        os.remove(dbpath)
    except:
        pass

    engine = create_engine(f"sqlite:///{dbpath}", echo=True)
    metadata = MetaData(bind=engine)
    # # get reader 
    reader = ReaderFactory.create_reader(filename)

    # # extract fields for variants table 
    columns = [Column(field["name"], eval(field["value_type"])) for field in reader.get_fields()]

    print(columns)

    variant_table = Table("variants", metadata,Column('id', Integer, primary_key=True), *columns)
    fields_table  = Table("fields", metadata,Column('id', Integer, primary_key=True) )


    metadata.create_all()


    insert = variant_table.insert()

    cache = []
    for variant in reader.get_variants():
        cache.append(variant)

    engine.execute(insert, cache) 



def open_db(dbpath):
    engine = create_engine(f"sqlite:///{dbpath}", echo=True)
    Base = automap_base()
    Base.prepare(engine, reflect=True)
    Variants  = Base.classes.variants
    






    # # Create default selection 
    # session.add(Selection(name="all", description="all variant", count = variant_count))
    # session.add(Selection(name="favoris", description="favoris", count = 0))
    
    # session.commit()
