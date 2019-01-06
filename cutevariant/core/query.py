import re


class Query:
    """ 
	This class is intended to build sql query according parameters 
	self.columns : columns from variant table 
	self.filter : filter filter as raw text 
	self.table : name of the variant set. Use "all" to select all variants 
	"""

    def __init__(
        self, conn, columns=["chr", "pos", "ref", "alt"], filter=None, table="variants"
    ):
        self.conn = conn
        self.columns = columns
        self.filter = filter
        self.table = table

        ##-----------------------------------------------------------------------------------------------------------

    def detect_samples(self):
        """ detect if query need sample join by looking genotype expression : genotype("boby").gt and return samples """

        # extract sample name from select and filter clause
        expression = r"genotype\([\"\'](.*)[\"\']\).gt"
        samples_detected = []
        combine_clause = self.columns

        for col in combine_clause:
            match = re.search(expression, col)
            if match:
                samples_detected.append(match.group(1))

                # Look in DB if sample exists and returns {sample:id} dictionnary
        in_clause = ",".join([f"'{sample}'" for sample in samples_detected])
        return dict(
            self.conn.execute(
                f"SELECT name, rowid FROM samples WHERE name IN ({in_clause})"
            ).fetchall()
        )

        ##-----------------------------------------------------------------------------------------------------------

    def sql(self, limit=0, offset=0):
        """ build query depending class parameter """

        if len(self.columns) == 0:
            self.columns = ["chr", "pos", "ref", "alt"]

        query = f"SELECT {','.join(self.columns)} "

        # Add Select clause

        if self.table == "variants":
            query += f"FROM variants"
        else:
            #  manage jointure with selection
            pass

            # Join samples
        sample_ids = self.detect_samples()
        if len(sample_ids):
            for i, sample in enumerate(self.samples):
                sample_id = sample_ids[sample]
                query += f" LEFT JOIN sample_has_variant sv{i} ON sv{i}.variant_id = variants.rowid AND sv{i}.sample_id = {sample_id} "

                # add filter clause
        if self.filter:
            query += " WHERE " + self.filter_to_sql(self.filter)

            #  add limit and offset
        if limit > 0:
            query += f" LIMIT {limit} OFFSET {offset}"

        return query

        ##-----------------------------------------------------------------------------------------------------------

    def rows(self, limit=0, offset=0):
        """ return query results as list by record """
        yield from self.conn.execute(self.sql(limit, offset))

        ##-----------------------------------------------------------------------------------------------------------

    def items(self, limit=0, offset=0):
        """ return query results as dict by record """
        for value in self.conn.execute(self.sql(limit, offset)):
            item = {}
            for index, col in enumerate(self.columns):
                item[col] = value[index]
            yield item

        ##-----------------------------------------------------------------------------------------------------------

    def filter_to_sql(self, node: dict) -> str:

        # function to detect if node is a Condition node (AND/OR) OR a field node {name,operator, value}
        is_field = lambda x: True if len(x) == 3 else False

        if is_field(node):
            if (
                type(node["value"]) == str
            ):  # Add quote for string .. Need to change in the future and use sqlite binding value
                value = "'" + str(node["value"]) + "'"
            else:
                value = str(node["value"])

            return str(node["field"]) + str(node["operator"]) + value

        else:
            logic = list(node.keys())[0]
            out = []
            for child in node[logic]:
                out.append(self.filter_to_sql(child))

            return "(" + f" {logic} ".join(out) + ")"

        ##-----------------------------------------------------------------------------------------------------------

    def samples(self):
        return self.detect_samples().keys()

        ##-----------------------------------------------------------------------------------------------------------

    def create_selection(self, name):
        pass

        ##-----------------------------------------------------------------------------------------------------------

    def count(self):
        """ return total row number """
        #  TODO : need to cache this method because it can take time to compute with large dataset
        return self.conn.execute(
            f"SELECT COUNT(*) as count FROM ({self.sql()})"
        ).fetchone()[0]

        ##-----------------------------------------------------------------------------------------------------------

    def __repr__(self):
        return f"""
		columns : {self.columns} 
		filter: {self.filter} 
		selection: {self.table}
		limit: 
		"""

        ##-----------------------------------------------------------------------------------------------------------

    def from_vql(self,raw : str):
    	# TODO @aluriak
    	pass 

        ##-----------------------------------------------------------------------------------------------------------

    def to_vql(self) -> str:
		# TODO @aluriak
    	pass 

        ##-----------------------------------------------------------------------------------------------------------

    def check(self):
    	''' Return True if query is valid ''' 
    	return True 



def intersect(query1, query2, by="site"):

    if by == "site":
        link = "q1.chr = q2.chr AND q1.pos = q2.pos"

    if by == "variant":
        link = "q1.chr = q2.chr AND q1.pos = q2.pos AND q1.ref = q2.ref AND q1.alt = q2.alt"

    query = f"""
	SELECT * FROM {query1} q1
	INNER JOIN {query2} q2 
	ON {link}
	"""

    return query


def union(query1, query2, by="site"):

    if by == "site":
        link = "q1.chr = q2.chr AND q1.pos = q2.pos"

    if by == "variant":
        link = "q1.chr = q2.chr AND q1.pos = q2.pos AND q1.ref = q2.ref AND q1.alt = q2.alt"

    query = f"""
	SELECT * FROM {query1} q1
	INNER JOIN {query2} q2 
	ON {link}
	"""

    return query
