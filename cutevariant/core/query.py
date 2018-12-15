
from .model import Variant, create_session, Selection
from sqlalchemy import text
from sqlalchemy.orm import load_only


class QueryBuilder:
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
			query = self.session.query(Variant).join(Selection, Variant.selections).filter(Selection.name == "sacha")

		if self.condition:
			query = query.filter(text(self.condition))

		if self.fields:
			query = query.options(load_only(*self.fields))

		return query

	def __iter__(self):
		''' iter over variant ''' 
		return iter(self.query())

	def create_selection(self, name, description = None):
		''' create selection with the current query ''' 
		selection = Selection(name=name, description= description, count = 0)
		for variant in self:
			selection.variants.append(variant)
			selection.count+=1
	
		self.session.add(selection)
		self.session.commit() 

		return selection



		# self.engine.execute(f"INSERT INTO `selection_has_variants` (variant_id, selection_id) {")





    # # for i in s
    # #     print(i.pos)

