
from sqlalchemy import *
from sqlalchemy.orm import load_only


class QueryBuilder:
	''' 
	This class is intended to build sqlAlchemy query according parameters 
	self.fields : columns from variant table 
	self.conditions : where condition as raw text 
	self.selection_name : name of the variant set. Use "all" to select all variants 
	''' 

	def __init__(self, engine):
		self.engine = engine
		self.fields = []
		self.condition = str()
		self.selection_name = "all"
		self.metadata = MetaData(bind=engine)
		self.variant_table = Table('variants', self.metadata, autoload=True)



	def query(self):
		''' build query depending class parameter ''' 

		return self.engine.execute(self.variant_table.select())


  #   for i in engine.execute(user.select()):
  #       print(i)





	def __repr__(self):
		return f"""
		fields : {self.fields} 
		condition: {self.condition} 
		selection: {self.selection_name}
		limit: 
		"""




		# self.engine.execute(f"INSERT INTO `selection_has_variants` (variant_id, selection_id) {")





    # # for i in s
    # #     print(i.pos)

