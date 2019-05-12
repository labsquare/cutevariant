# Standard imports
import re
import sqlite3
from functools import lru_cache

# Custom imports
from . import sql
from . import vql
from cutevariant.commons import logger

LOGGER = logger()

_GENOTYPE_FUNCTION_NAME = "genotype"
_PHENOTYPE_FUNCTION_NAME = "phenotype"


class Query:
    """Class used to build sql query to select variants records

    Available attributes:
        conn (sqlite3.Connection)
        columns (list of str and tuple): Fields names from variants and annotations table (Select clause)
        filter (dict): Hierarchical dictionnary to filter variants (Where clause)
        selection (str): Virtual table of variants (From clause)
        order_by(str): Order variants by a specific column
        group_by(tuple of str): Group variants by columns

    About functions:
        `columns` and `filter` can contains function as tuple.
        A function is defined by:
            - function name
            - arguments (sample name, etc.)
            - sql field name

        For example :

            query.columns = ["chr","pos", ("genotype","boby","GT")]

        is equivalent to:

            SELECT chr, pos, genotype("boby").gt

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

    def __init__(
        self, conn, columns=["chr", "pos", "ref", "alt"], filter=dict(), selection="all"
    ):
        self.conn = conn
        self.columns = columns
        self.filter = filter
        self.selection = selection
        self.order_by = None
        self.order_desc = True
        self.group_by = None

        self._samples_to_join = set()

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
        """Detect if columns or filter contains function.

        Functions are tuples. For example, this is a columns list with 2 normal
        field and 1 genotype function field:

            query.columns = ("chr","pos", ("genotype", "boby", "gt"))

        This columns selection can be writted in VQL as follow :

            SELECT chr, pos, genotype("boby").gt
        """
        self._samples_to_join.clear()
        self._detect_samples_from_columns()
        self._detect_samples_from_filter()
        #  TODO: Parse filter

    def _detect_samples_from_columns(self):
        """Detect if columns contains function and keep function args as sample name for sql join with sample tables.

        Functions are defined as tuples. For exemple `genotype("boby").gt` will
        be written as `("genotype", "boby", "gt")`.
        """
        # Get function tuples
        #  A function is a tuple with 3 elements. The second element is the sample name
        # TODO: is test on length usefull?
        functions = (
            col for col in self.columns if isinstance(col, tuple) and len(col) == 3
        )
        # TODO: set on intention here
        for function in functions:
            function_name, sample_name, field_name = function

            if function_name == _GENOTYPE_FUNCTION_NAME:
                self._samples_to_join.add(sample_name)

    def _detect_samples_from_filter(self):
        """Detect if filter contains function and keep function args as sample name for sql join with sample tables

        Functions are defined as tuples. For exemple `genotype("boby").gt` will
        be written as `("genotype", "boby", "gt")`.
        """
        # Recursive loop over filter to extract field name only
        def iter(node):
            if isinstance(node, dict) and len(node) == 3:
                yield node["field"]

            if isinstance(node, dict):
                for i in node:
                    yield from iter(node[i])

            if isinstance(node, list):
                for i in node:
                    yield from iter(i)

        # Get function tuples
        #  A function is a tuple with 3 elements. The second element is the sample name
        # TODO: is test on length usefull?
        functions = (
            col for col in iter(self.filter) if isinstance(col, tuple) and len(col) == 3
        )
        # TODO: set on intention here
        for function in functions:
            function_name, sample_name, field_name = function

            if function_name == _GENOTYPE_FUNCTION_NAME:
                self._samples_to_join.add(sample_name)

        ##-----------------------------------------------------------------------------------------------------------

    def sql(self, limit=0, offset=0) -> str:
        """Build a sql query according to attributes

        :param limit : SQL LIMIT for pagination
        :param offset: SQL OFFSET for pagination
        :return: an SQL query
        :rtype: str
        """

        # Detect if join sample is required ...
        # sample_ids = self.detect_samples()


        ## Build columns
        # Set default columns if columns is empty
        # Otherwise, columns are kept unmodified
        if not self.columns:
            self.columns = ["variants.id", "chr", "pos", "ref", "alt"]

        # Replace genotype function by name
        # Transform ("genotype", "boby","gt") to "`gt_boby`.gt" to perform SQL JOIN
        sql_columns = []
        for col in self.columns:
            if isinstance(col, tuple):
                function_name, arg, field_name = col
                if function_name == _GENOTYPE_FUNCTION_NAME:
                    col = f"`gt_{arg}`.{field_name}"

            sql_columns.append(col)

        # If 'group by', add extra columns (child count and child ids)
        # Required for viewquerywidget.py
        if self.group_by:
            sql_columns.extend(["COUNT(variants.id) as 'children'"])
            # TODO: test with count (*)

        query = f"SELECT {','.join(sql_columns)} "

        ## Add SELECT clause
        if not self.selection:
            # Explicitly query all variants
            query += "FROM variants"

        elif self.selection == "all":
            query += "FROM variants LEFT JOIN annotations ON annotations.variant_id = variants.id"
        else:
            # Add jointure with 'selections' table
            query += f"""
            FROM variants
            LEFT JOIN annotations ON annotations.variant_id = variants.id
            INNER JOIN selection_has_variant sv ON sv.variant_id = variants.id
            INNER JOIN selections s ON s.id = sv.selection_id AND s.name = '{self.selection}'
            """

        #  Add Join on sample_has_variant
        #  This is done if genotype() function has been found in columns or fields. @see _detect_samples
        self._detect_samples()
        #        print("DETECT", self.columns, self._samples_to_join)
        if self._samples_to_join:
            for sample in sql.get_samples(self.conn):
                if sample["name"] in self._samples_to_join:
                    sample_id = sample["id"]
                    sample_name = sample["name"]
                    query += f" LEFT JOIN sample_has_variant gt_{sample_name} ON gt_{sample_name}.variant_id = variants.id AND gt_{sample_name}.sample_id = {sample_id}"

        ## Add WHERE filter
        if self.filter:
            query += " WHERE " + self.filter_to_sql(self.filter)

        ## Add GROUP BY command
        if self.group_by:
            query += " GROUP BY chr,pos,ref,alt"

        ## Add ORDER BY command
        if self.order_by is not None:
            direction = "DESC" if self.order_desc else "ASC"
            query += f" ORDER BY {self.order_by} {direction}"

        ## Add LIMIT and OFFSET clauses
        if limit > 0:
            query += f" LIMIT {limit} OFFSET {offset}"

        LOGGER.debug("Query:sql:: query: %s", query)
        return query

        ##-----------------------------------------------------------------------------------------------------------

    def items(self, limit=0, offset=0):
        """Execute SQL query and return variants as a list

        .. note:: Used:
            - as dict of variants in chartquerywidget.py
            - as tuples of variants in viewquerywidget.py

        :param limit: SQL LIMIT for pagination
        :param offset: SQL OFFSET for pagination
        :return: Generator of variants as sqlite3.Row objects.
            A Row instance serves as a highly optimized row_factory for
            Connection objects. It tries to mimic a tuple in most of its features.

            It supports mapping access by column name and index, iteration,
            representation, equality testing and len().
        :rtype: <generator <sqlite3.Row>>

        :Example:

            for row in query.items():
        ...     print(tuple(row))
        (324, "chr2", "24234", "A", "T", ...)
        ...     print(dict(row))
        {"rowid":23423, "chr":"chr2", "pos":4234, "ref":"A", "alt": "T", ...}

        """
        self.conn.row_factory = sqlite3.Row
        yield from self.conn.execute(self.sql(limit, offset))

    def filter_to_sql(self, node: dict) -> str:
        """Recursive function to convert hierarchical dictionnary into a SQL Where clause

        :param node: hierachical dictionnary
        :return: a SQL WHERE clause

        ..seealso: filter


        :Example of filter:
        filter: {'AND': [
            {'field': 'ref', 'operator': 'IN', 'value': "('A', 'T', 'G', 'C')"},
            {'field': 'alt', 'operator': 'IN', 'value': "('A', 'T', 'G', 'C')"}
        ]}
        """

        if not node:
            return ""

        # Function to detect IF node is a Condition node (AND/OR)
        # OR a field node with (name, operator, value) as keys
        is_field = lambda x: True if len(x) == 3 else False

        if is_field(node):
            # print("IS FIELD", node)

            # Process value
            value = node["value"]
            operator = node["operator"]
            field = node["field"]

            # TODO ... c'est degeulasse ....

            if operator in ("IN", "NOT IN"):
                # DO NOT enclose value in quotes
                # node: {'field': 'ref', 'operator': 'IN', 'value': "('A', 'T', 'G', 'C')"}
                # wanted: ref IN ('A', 'T', 'G', 'C')
                pass

            elif isinstance(value, str):
                # Add quote for string ..
                # TODO: Need to change in the future and use sqlite binding value
                value = "'" + value + "'"

            elif isinstance(value, list):
                value = "(" + ",".join(value) + ")"

            else:
                value = str(value)

            if (isinstance(field, tuple) and len(field) == 3):
                #  Function ? ("genotype","sample","gt")
                fct, arg, f = field
                field = f"gt_{arg}.{f}"

            # There must be spaces between these strings because of strings operators (IN, etc.)
            return "%s %s %s" % (field, operator, value)

        else:
            # Not a field: 1 key only: the logical operator
            logic_op = list(node.keys())[0]
            # Recursive call for each field in the list associated to the
            # logical operator.
            # node:
            # {'AND': [
            #   {'field': 'ref', 'operator': 'IN', 'value': "('A', 'T', 'G', 'C')"},
            #   {'field': 'alt', 'operator': 'IN', 'value': "('A', 'T', 'G', 'C')"}
            # ]}
            # Wanted: ref IN ('A', 'T', 'G', 'C') AND alt IN ('A', 'T', 'G', 'C')
            out = [self.filter_to_sql(child) for child in node[logic_op]]
            # print("OUT", out, "LOGIC", logic_op)
            # OUT ["refIN'('A', 'T', 'G', 'C')'", "altIN'('A', 'T', 'G', 'C')'"]

            return "(" + f" {logic_op} ".join(out) + ")"

    #     ##-----------------------------------------------------------------------------------------------------------

    # def samples(self):
    #     """
    #     Return samples

    #     ..warning:: WILL BE REMOVE AFTER FIXING #33

    #     """
    #     return self.detect_samples().keys()

    ##-----------------------------------------------------------------------------------------------------------

    def create_selection(self, name):
        """Store variant set from the current query into `selections` table

        :param name: Name of the selection

        :Example:

            query1 = Query(conn)
            query1.from_vql("SELECT chr, pos FROM variants WHERE chr = 3 ")
            print(query1.variants_count())
        10
            query1.create_selection("boby")
            query2 = Query(conn)
            query2.from_vql("SELECT chr, pos FROM boby")
            print(query2.variants_count())
        10 # same as before

        :return: The id of the new selection in the database. None in case of error.
        :rtype: <int> or None
        """
        return sql.create_selection_from_sql(
            self.conn, self.sql(), name=name, by="site"
        )

        ##-----------------------------------------------------------------------------------------------------------

    @lru_cache(maxsize=128)
    def _cached_variants_count_query(self, sql_query):
        """Wrapped function with a memoizing callable that saves up to the
        maxsize most recent calls.

        .. note:: The LRU feature performs best when maxsize is a power-of-two.

        .. note:: The COUNT() aggregation function is expensive on partially
            indexed tables (because dynamically built) for large dataset
            and it seems difficult to predict which fields will be requested
            by the user.
        """
        # Trick to accelerate UI refresh on basic queries
        if not self.selection or self.selection == "all" and not self.filter:
            return self.conn.execute(
                "SELECT MAX(variants.id) as count FROM variants"
            ).fetchone()[0]

        return self.conn.execute(
            f"SELECT COUNT(*) as count FROM ({sql_query})"
        ).fetchone()[0]

    def variants_count(self) -> int:
        """Return variant count from the current query

        .. note:: This function is used in:
            - viewquerywidget.py in `load()` to keep the total of variants for
            paging purposes of the interface.
        """
        LOGGER.debug("Query:variants_count:: %s", self.sql())
        count = self._cached_variants_count_query(self.sql())
        LOGGER.debug(
            "Query:variants_count:: %s",
            self._cached_variants_count_query.cache_info(),
        )
        return count

        ##-----------------------------------------------------------------------------------------------------------

    def __repr__(self):
        return f"""
        columns : {self.columns}
        filter: {self.filter}
        selection: {self.selection}
        """

        ##-----------------------------------------------------------------------------------------------------------

    def from_vql(self, raw: str):
        """Build the current Query from a VQL query

        :param raw: VQL query

        :Example:

                query = Query(conn)
                query.from_vql("SELECT chr, pos FROM variants")
                query.sql()

        .. seealso:: to_vql()
        .. todo:: Should be a static method
        """
        model = vql.model_from_string(raw)
        self.columns = list(model["select"])  # columns from variant table
        self.selection = model["from"]  # name of the variant set
        self.filter = model.get("where", dict())  # filter as raw text; dict if no filter
        # TODO: USING clause missing

        print("from vql", model)
        print("from vql", self.filter)

    def to_vql(self) -> str:
        """Build a VQL query from the current Query

        .. seealso:: from_vql()
        .. todo:: Should be a static method

        :return: A VQL query
        :rtype: <str>
        """

        # TODO : move all VQL to VQLEDItor
        #  DEGEU.. pour tester juste
        _c = []
        for col in self.columns:
            if isinstance(col, tuple):
                fct, arg, field = col
                if fct == _GENOTYPE_FUNCTION_NAME:
                    col = f"genotype(\"{arg}\").{field}"
            _c.append(col)

        base = f"SELECT {','.join(_c)} FROM {self.selection}"
        where = ""
        if self.filter:
            where = f" WHERE {self.filter_to_sql(self.filter)}"
        return base + where

        ##-----------------------------------------------------------------------------------------------------------

    def check(self):
        """Return True if query is valid"""
        raise NotImplementedError
