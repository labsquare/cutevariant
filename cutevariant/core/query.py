
class QueryBuilder:
	''' 
	This class is intended to build sql query according parameters 
	self.fields : columns from variant table 
	self.conditions : where condition as raw text 
	self.selection_name : name of the variant set. Use "all" to select all variants 
	''' 
	def __init__(self, conn):
		self.conn = conn
		self.fields = []
		self.condition = str()
		self.selection_name = "all"

	def query(self):
		''' build query depending class parameter ''' 
		if self.fields:
			cursor = self.conn.execute(f"SELECT {','.join(self.fields)} FROM variants")
		else:
			cursor = self.conn.execute(f"SELECT * FROM variants")

		for row in cursor:
			yield row




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

