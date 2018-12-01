from sqlalchemy import Column,Integer,String,Float,Boolean
from sqlalchemy.ext.declarative import declarative_base
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

    @classmethod
    def create_column_from_field(cls,field: Field):
        column_type = eval(field.value_type) # Integer,String,Float,Boolean
        Variant.create_column(field.name, Column(column_type))

    
class View(Base):
    __tablename__="views"
    id = Column(Integer,primary_key=True)
    name = Column(String)
    description = Column(String)



if __name__ == "__main__":

    pass


    #import_file("../../exemples/test2.vcf", "/tmp/test4.db")







