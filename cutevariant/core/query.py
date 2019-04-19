# Standard imports
import re

# Custom imports
from . import sql
from . import vql
from cutevariant.commons import logger

LOGGER = logger()

class Query:
    """
    This is a class for build sql query to select variant record according different attributes 

    Attributes:
        conn (sqlite3.Connection) 
        columns (list of str): fields name from variants and annotations table (Select clause)   
        filter (dict): Hierarchical dictionnary to filter variants (Where clause) 
        selection (str): Virtual table of variants (From clause) 
        order_by(str): Order variants by a specific column 
        group_by(tuple of str): Group variants by columns  

    Example:
        conn = sqlite.connection(":memory")
        query = Query(conn)
        query.columns = ["chr","pos","ref","alt"]
        query.selection = "variants"
        query.filter = {"AND": [
                {"field": "ref", "operator": "=", "value": "A"},
                {
                    "OR": [
                        {"field": "chr", "operator": "=", "value": "chr5"},
                        {"field": "chr", "operator": "=", "value": "chr3"},
                    ]
                },}}

        conn.execute(conn.sql())


    """

    def __init__( self, conn, columns=["chr", "pos", "ref", "alt"], filter=None, selection="all"):
        self.conn = conn
        self.columns = columns
        self.filter = filter
        self.selection = selection
        self.order_by = None
        self.order_desc = True
        self.group_by = None

        ##-----------------------------------------------------------------------------------------------------------

    def sample_from_expression(self, expression):
        """
        ..warning:: WILL BE REMOVE AFTER FIXING #33 

        """
        # extract <sample> from <gt("sample")>
        regexp = r"gt(.*).gt"
        match = re.search(regexp, expression)
        if match:
            return match.group(1)
        else:
            return None

        ##-----------------------------------------------------------------------------------------------------------

    def detect_samples(self):
        """ 
        detect if query need sample join by looking genotype expression : genotype("boby").gt and return samples 
    
        ..warning:: WILL BE REMOVE AFTER FIXING #33 

        """

        # extract sample name from select and filter clause
        samples_detected = []
        combine_clause = self.columns

        for col in combine_clause:
            sample = self.sample_from_expression(col)
            if sample is not None:
                samples_detected.append(sample)

        if len(samples_detected) == 0:
            return {}
        # Look in DB if sample exists and returns {sample:id} dictionnary
        in_clause = ",".join([f"'{sample}'" for sample in samples_detected])

        return dict(
            self.conn.execute(
                f"SELECT name, rowid FROM samples WHERE name IN ({in_clause})"
            ).fetchall()
        )

        ##-----------------------------------------------------------------------------------------------------------

    def sql(self, limit=0, offset=0) -> str:
        """ 
        build a sql query according attributes 

        :param limit : SQL LIMIT for pagination 
        :param offset: SQL OFFSET for pagination
        :return: an SQL query 
        :rtype: str
        """

        #  Detect if join sample is required ...
        sample_ids = self.detect_samples()

        if len(self.columns) == 0:
            self.columns = ["chr", "pos", "ref", "alt"]


        #  Replace columns gt(sacha) by sv4.gt ( where 4 is the sample id for outer join)
        sql_columns = []
        sql_columns.append("variants.rowid")
        for col in self.columns:
            sample = self.sample_from_expression(col)
            if sample is not None:
                sql_columns.append(f"gt{sample}.gt")
            else:
                sql_columns.append(col)


        # if group by , add extra columns ( child count and child ids )
        if self.group_by:
            sql_columns.extend(["COUNT(rowid) as 'count'","group_concat(rowid) as 'childs'"])

        query = f"SELECT {','.join(sql_columns)} "

        # Add Select clause

        if self.selection == "all":
            query += f"FROM variants LEFT JOIN annotations ON annotations.variant_id = variants.rowid"
        else:
            #  manage jointure with selection

            query += f"""
            FROM variants
            INNER JOIN selection_has_variant sv ON sv.variant_id = variants.rowid
            INNER JOIN selections s ON s.rowid = sv.selection_id AND s.name = '{self.selection}'
            """

        if len(sample_ids):
            for sample, i in sample_ids.items():
                query += f" LEFT JOIN sample_has_variant gt{sample} ON gt{sample}.variant_id = variants.rowid AND gt{sample}.sample_id = {i} "

                # add filter clause
        if self.filter:
            query += " WHERE " + self.filter_to_sql(self.filter)
            #  add limit and offset

        if self.group_by:
            query += " GROUP BY chr,pos,ref,alt"

        if self.order_by is not None:
            direction = "DESC" if self.order_desc is True else "ASC"
            query += f" ORDER BY {self.order_by} {direction}"

        if limit > 0:
            query += f" LIMIT {limit} OFFSET {offset}"

        LOGGER.debug("Query:sql:: query: %s", query)
        return query

        ##-----------------------------------------------------------------------------------------------------------

    def rows(self, limit=0, offset=0):
        """ 
        Execute SQL query and return variants as a list 

        :param limit: SQL LIMIT for pagination 
        :param offset: SQL OFFSET for pagination
        :return: list of variants as a generator. Each variant is a list

        :Example:

        >> for row in query.rows():
            print(row) # [324, "chr2","24234","A","T", ...]


        ..seealso:: items()
        
        """
        yield from self.conn.execute(self.sql(limit, offset))

        ##-----------------------------------------------------------------------------------------------------------
    def items(self, limit=0, offset=0):
        """ 
        Execute SQL query and return variants as a dictionnary

        :param limit: SQL LIMIT for pagination 
        :param offset: SQL OFFSET for pagination
        :return: list of variants as a generator. Each variant is a dict

        :Example:

        >> for variant in query.items():
            print(variant) # {"rowid":23423, "chr":"chr2","pos":4234,"ref":"A","alt","T",...]

        ..seealso:: rows()
                 
        """
        for value in self.conn.execute(self.sql(limit, offset)):
            item = {}
            for index, col in enumerate(["rowid"] + self.columns):
                item[col] = value[index]
            yield item

        ##-----------------------------------------------------------------------------------------------------------

    def filter_to_sql(self, node: dict) -> str:
        """ 
        Recursive function to convert hierarchical dictionnary into a SQL Where clause 

        :param node: hierachical dictionnary 
        :return: a SQL WHERE clause

        ..seealso: filter 

        """

        if dict is None:
            return str()

        # function to detect if node is a Condition node (AND/OR) OR a field node {name,operator, value}
        is_field = lambda x: True if len(x) == 3 else False

        if is_field(node):
            # change value
            value = node["value"]
            operator = node["operator"]
            field = node["field"]

            # TODO ... c'est degeulasse .... 

            if type(value) == str:  # Add quote for string .. Need to change in the future and use sqlite binding value
                value = "'" + str(value) + "'"

            elif type(value) == list:
                value = "(" + ",".join(value) +")"
     
            else:
                value = str(value)

            #  change columns name for sample join
            sample = self.sample_from_expression(field)
            if sample:
                field = f"gt{sample}.gt"

            return field + operator + value

        else:
            logic = list(node.keys())[0]
            out = []
            for child in node[logic]:
                out.append(self.filter_to_sql(child))

            return "(" + f" {logic} ".join(out) + ")"

        ##-----------------------------------------------------------------------------------------------------------

    def samples(self):
        """
        Return samples 

        ..warning:: WILL BE REMOVE AFTER FIXING #33 

        """
        return self.detect_samples().keys()

        ##-----------------------------------------------------------------------------------------------------------

    def create_selection(self, name):
        """
        Store variant set from the current query into selection table.

        :param name: Name of the selection 

        :Example: 
        
        >> query1 = Query(conn)
        >> query1.from_vql("SELECT chr, pos FROM variants WHERE chr = 3 ")
        >> print(query1.count())  # 10 
        >> query1.create_selection("boby")
        >> query2 = Query(conn)
        >> query2.from_vql("SELECT chr, pos FROM boby")
        >> print(query2.count()) # 10 .. same as before

        """
        sql.create_selection_from_sql(self.conn, self.sql(), name=name, by="site")

        ##-----------------------------------------------------------------------------------------------------------

    def count(self)-> int:
        """ 
        return variant count from the current query 
        """
        #  TODO : need to cache this method because it can take time to compute with large dataset
        return self.conn.execute(
            f"SELECT COUNT(*) as count FROM ({self.sql()})"
        ).fetchone()[0]

        ##-----------------------------------------------------------------------------------------------------------

    def __repr__(self):
        return f"""
        columns : {self.columns}
        filter: {self.filter}
        selection: {self.selection}
        """

        ##-----------------------------------------------------------------------------------------------------------

    def from_vql(self, raw: str):
        """
        Build a Query from a VQL query 

        :param raw: VQL query 

        :Example: 

        query = Query(conn)
        query.from_vql("SELECT chr, pos FROM variants")
        query.sql()

        ..seealso: to_vql()
        ..todo: Should be a static methods

        """
        model = vql.model_from_string(raw)
        self.columns = list(model["select"])  # columns from variant table
        self.selection = model["from"]  # name of the variant set
        self.filter = model.get("where")  # filter as raw text; None if no filter
        # TODO: USING clause missing

        print("from vql", model)

        ##-----------------------------------------------------------------------------------------------------------

    def to_vql(self) -> str:
        """
        Build a VQL query from the current Query
        :return: A VQL query 
        """
        base = f"SELECT {','.join(self.columns)} FROM {self.selection}"
        where = ""
        if self.filter:
            where = f" WHERE {self.filter_to_sql(self.filter)}"
        return base + where

        ##-----------------------------------------------------------------------------------------------------------

    def check(self):
        """ Return True if query is valid """
        return True
