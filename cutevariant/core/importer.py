from .readerfactory import ReaderFactory
from .model import Field,Variant,View
import os
from sqlalchemy import create_engine, MetaData
from sqlalchemy.orm import sessionmaker


def import_file(filename, db_filename):
    
    try:
        os.remove(db_filename)
    except:
        pass

    engine = create_engine(f"sqlite:///{db_filename}", echo=False)
    Session = sessionmaker(bind=engine)
    session = Session()

    Field.__table__.create(engine)

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

