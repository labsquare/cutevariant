from sqlalchemy import Column,Integer,String
from sqlalchemy import create_engine, MetaData
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import os 

Base = declarative_base()


class Field(Base):
	__tablename__ = "fields"
	id = Column(Integer,primary_key=True)
	name = Column(String)
	category = Column(String)
	description = Column(String)
	value_type = Column(String)

class Variant(Base):
	__tablename__="variants"
	id = Column(Integer,primary_key=True)

	def __getitem__(self, index):
		return getattr(self, index)

	def __setitem__(self,index, value):
		setattr(self, index, value)

	@classmethod	
	def create_column(cls,name,column):
		setattr(cls, name, column)
	
class View(Base):
	__tablename__="views"
	id = Column(Integer,primary_key=True)
	name = Column(String)
	description = Column(String)



try:
	os.remove("/tmp/test.db")
except:
	pass

engine = create_engine("sqlite:////tmp/test.db", echo=True)
Session = sessionmaker(bind=engine)
session = Session()

Variant.create_column("chr", Column(String))


Base.metadata.create_all(engine)

for i in range(50):
	variant = Variant()
	variant["chr"] = f"chr{i}"
	session.add(variant)

session.commit()


for i in session.query(Variant).filter((Variant.id < 5) | (Variant.chr == "chr5")):
	print(i)

# field = Field(name="sacha",description="test", category="test", value_type="test")

# session.add(field)
# session.commit()

# print(session)
