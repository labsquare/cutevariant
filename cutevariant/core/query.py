
from sqlalchemy import text
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
		self.session = create_session(self.engine)


	def query(self):
		''' build query depending class parameter ''' 

		if self.selection_name == "all":
			query = self.session.query(Variant)

		else:
			query = self.session.query(Variant).join(Selection, Variant.selections).filter(Selection.name == self.selection_name)

		if self.condition:
			query = query.filter(text(self.condition))

		if self.fields:
			query = query.options(load_only(*self.fields))

		return query


	def to_list(self):
		for variant in self.query():
			yield tuple([variant[field] for field in self.fields])

	def create_selection(self, name, description = None):
		''' create selection with the current query ''' 
		selection = Selection(name=name, description= description, count = 0)
		for variant in self.query():
			selection.variants.append(variant)
			selection.count+=1
	
		self.session.add(selection)
		self.session.commit() 

		return selection


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

