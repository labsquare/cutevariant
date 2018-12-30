
class QueryBuilder:
	''' 
	This class is intended to build sql query according parameters 
	self.columns : columns from variant table 
	self.where : where where as raw text 
	self.table : name of the variant set. Use "all" to select all variants 
	''' 
	def __init__(self, conn):
		self.conn = conn
		self.columns = []
		self.where = str()
		self.table = "variants"
		self.samples = []

	def query(self):
		''' build query depending class parameter ''' 
		query = ""
		if self.columns:
			query = f"SELECT {','.join(self.columns)}"
		else:
			query = f"SELECT * "


		if self.table == "variants":
			query += f"FROM variants"
		else:
			# manage jointure with selection 
			pass 


		# Join samples 
		if len(self.samples):

			sample_ids = dict(self.conn.execute(f"SELECT name, rowid FROM samples").fetchall())

			for i,sample in enumerate(self.samples):
				sample_id = sample_ids[sample]
				query +=f" LEFT JOIN sample_has_variant sv{i} ON sv{i}.variant_id = variants.rowid AND sv{i}.sample_id = {sample_id} "


		if self.where:
			query += " WHERE " + self.where

		return query 

	def rows(self):
		yield from self.conn.execute(self.query())


	def create_selection(self, name):
		pass 


	def __repr__(self):
		return f"""
		columns : {self.columns} 
		where: {self.where} 
		selection: {self.table}
		limit: 
		"""



def intersect(query1, query2, by = "site"):

	if by == "site":
		link = "q1.chr = q2.chr AND q1.pos = q2.pos"

	if by == "variant":
		link = "q1.chr = q2.chr AND q1.pos = q2.pos AND q1.ref = q2.ref AND q1.alt = q2.alt"

	query = f'''
	SELECT * FROM {query1} q1
	INNER JOIN {query2} q2 
	ON {link}
	'''

	return query 


def union(query1, query2, by = "site"):

	if by == "site":
		link = "q1.chr = q2.chr AND q1.pos = q2.pos"

	if by == "variant":
		link = "q1.chr = q2.chr AND q1.pos = q2.pos AND q1.ref = q2.ref AND q1.alt = q2.alt"

	query = f'''
	SELECT * FROM {query1} q1
	INNER JOIN {query2} q2 
	ON {link}
	'''

	return query 
