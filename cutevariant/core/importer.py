from .readerfactory import ReaderFactory
from .model import *
import os


def import_file(filename, db_filename):
    
    try:
        os.remove(db_filename)
    except:
        pass

    engine,session = create_connection(db_filename)

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

