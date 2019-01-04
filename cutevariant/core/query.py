import re 

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
		self.where = {}
		self.table = "variants"
		self.limit = 10 
		self.offset = 0


	def detect_samples(self):
		''' detect if query need sample join by looking genotype expression : genotype("boby").gt and return samples '''

		# extract sample name from select and where clause 
		expression = r'genotype\([\"\'](.*)[\"\']\).gt'
		samples_detected = []
		combine_clause = self.columns 

		for col in combine_clause:
			match = re.search(expression, col)
			if match :
				samples_detected.append(match.group(1))

		# Look in DB if sample exists and returns {sample:id} dictionnary
		in_clause = ",".join([ f"'{sample}'" for sample in samples_detected])
		return dict(self.conn.execute(f"SELECT name, rowid FROM samples WHERE name IN ({in_clause})").fetchall())






	def query(self):
		''' build query depending class parameter ''' 

		if len(self.columns) == 0:
			self.columns = ["chr","pos","ref","alt"]

		query = f"SELECT {','.join(self.columns)} "


		# Add Select clause 
		
		if self.table == "variants":
			query += f"FROM variants"
		else:
			# manage jointure with selection 
			pass 


		# Join samples 
		sample_ids = self.detect_samples()
		if len(sample_ids):
			for i,sample in enumerate(self.samples):
				sample_id = sample_ids[sample]
				query +=f" LEFT JOIN sample_has_variant sv{i} ON sv{i}.variant_id = variants.rowid AND sv{i}.sample_id = {sample_id} "

		# add where clause 
		# if self.where:
		# 	query += " WHERE " + self.where

		# add limit and offset 
		if self.limit is not None:
			query += f" LIMIT {self.limit} OFFSET {self.offset}"

		return query 

	def rows(self):
		''' return query results as list by record ''' 
		yield from self.conn.execute(self.query())

	def items(self):
		''' return query results as dict by record ''' 
		for value in self.conn.execute(self.query()):
			item = {}
			for index, col in enumerate(self.columns):
				item[col] = value[index]
			yield item


	def parse_where_dict(self, node):

		def is_field(node):
			return True if len(node) == 3 else False

		if is_field(node) :
			return str(node["field"]) + str(node["operator"]) + str(node["value"])

		else:
			logic = list(node.keys())[0]
			out = []
			for child in node[logic]:
				out.append(self.parse_where_dict(child))

			return "("+f' {logic} '.join(out)+")"


	def samples(self):
		return self.detect_samples().keys()


	def create_selection(self, name):
		pass 


	def __repr__(self):
		return f"""
		columns : {self.columns} 
		where: {self.where} 
		selection: {self.table}
		limit: 
		"""


	def create_where_clause(self):
		pass


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
