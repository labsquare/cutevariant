# Standard imports
import re

# Custom imports
from . import sql
from . import vql
from cutevariant.commons import logger

LOGGER = logger()

_GENOTYPE_FUNCTION_NAME = "genotype"
_PHENOTYPE_FUNCTION_NAME = "phenotype"

class Query:
    """
    This is a class for build sql query to select variant record according different attributes 

    Attributes:
        conn (sqlite3.Connection) 
        columns (list of str and tuple): fields name from variants and annotations table (Select clause)   
        filter (dict): Hierarchical dictionnary to filter variants (Where clause) 
        selection (str): Virtual table of variants (From clause) 
        order_by(str): Order variants by a specific column 
        group_by(tuple of str): Group variants by columns  

    Columns and filter can contains function as tuple. For example : 

    query.columns = ["chr","pos", ("genotype","boby","GT")] 

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

        self._samples_to_join = []

        ##-----------------------------------------------------------------------------------------------------------

    # def sample_from_expression(self, expression):
    #     """
    #     ..warning:: WILL BE REMOVE AFTER FIXING #33 

    #     """
    #     # extract <sample> from <gt("sample")>
    #     regexp = r"gt(.*).gt"
    #     match = re.search(regexp, expression)
    #     if match:
    #         return match.group(1)
    #     else:
            # return None

        ##-----------------------------------------------------------------------------------------------------------

    def _detect_samples(self):
        """ 
        Detect if columns or filter contains function. 
        Function are tuple . For example , this is a columns list with 2 normal field and 1 genotype function field.

            query.columns = ("chr","pos",("genotype","boby","gt"))

        This columns selection can be writted in VQL as follow : 

            SELECT chr, pos, genotype("boby").gt 

        """

        self._samples_to_join.clear()
        self._detect_samples_from_columns()
        self._detect_samples_from_filter()


        # Parse filter 



    def _detect_samples_from_columns(self):
        """
        detect if columns contains function and keep function args as sample name for sql join with sample tables
        """
        for col in self.columns:
            if type(col) == tuple and len(col) == 3: 
                fct, arg , field = col 

                if fct == _GENOTYPE_FUNCTION_NAME:
                    self._samples_to_join.append(arg)


    def _detect_samples_from_filter(self):
        """
        detect if filter contains function and keep function args as sample name for sql join with sample tables
        """
        


        # Recursive loop over filter to extract field name only 
        def iter(node):
            if type(node) == dict and len(node) == 3:
                    yield node["field"]

            if type(node) == dict:
                for i in node:
                    yield from iter(node[i])

            if type(node) == list:
                for i in node:
                    yield from iter(i)


        print("et ho", self.filter)

        for col in iter(self.filter):
            if type(col) == tuple and len(col) == 3:
                fct, arg , field = col 
                if fct == _GENOTYPE_FUNCTION_NAME:
                    self._samples_to_join.append(arg)
   


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
       # sample_ids = self.detect_samples()

        if len(self.columns) == 0:
            self.columns = ["chr", "pos", "ref", "alt"]


        #  Replace columns gt(sacha) by sv4.gt ( where 4 is the sample id for outer join)
        sql_columns = []
        sql_columns.append("variants.id")
        for col in self.columns:
        #     sample = self.sample_from_expression(col)
        #     if sample is not None:
        #         sql_columns.append(f"gt{sample}.gt")
        #     else:
            sql_columns.append(col)


        # if group by , add extra columns ( child count and child ids )
        # Required for viewquerywidget.py
        if self.group_by:
            sql_columns.extend(["COUNT(variants.id) as 'childs'"])

        query = f"SELECT {','.join(sql_columns)} "

        # Add Select clause

        if self.selection == "all":
            query += f"FROM variants LEFT JOIN annotations ON annotations.variant_id = variants.id"
        else:
            #  manage jointure with selection

            query += f"""
            FROM variants
            LEFT JOIN annotations ON annotations.variant_id = variants.id 
            INNER JOIN selection_has_variant sv ON sv.variant_id = variants.id
            INNER JOIN selections s ON s.id = sv.selection_id AND s.name = '{self.selection}'
            """

        # if len(sample_ids):
        #     for sample, i in sample_ids.items():
        #         query += f" LEFT JOIN sample_has_variant gt{sample} ON gt{sample}.variant_id = variants.rowid AND gt{sample}.sample_id = {i} "

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



            return field + operator + value

        else:
            logic = list(node.keys())[0]
            out = []
            for child in node[logic]:
                out.append(self.filter_to_sql(child))

            return "(" + f" {logic} ".join(out) + ")"

    #     ##-----------------------------------------------------------------------------------------------------------

    # def samples(self):
    #     """
    #     Return samples 

    #     ..warning:: WILL BE REMOVE AFTER FIXING #33 

    #     """
    #     return self.detect_samples().keys()

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
