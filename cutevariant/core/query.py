# Standard imports
import re
import sqlite3
from functools import lru_cache

# Custom imports
from . import sql
from . import vql
from cutevariant.commons import logger, DEFAULT_SELECTION_NAME

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
        group_by(list of str): Group variants by columns

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
        self,
        conn,
        columns=["chr", "pos", "ref", "alt"],
        filter=dict(),
        selection=DEFAULT_SELECTION_NAME,
        group_by=["chr", "pos", "ref", "alt"],
    ):
        self.conn = conn
        self.columns = columns
        self.filter = filter
        self.selection = selection
        self.order_by = None
        self.order_desc = True
        self.group_by = group_by

        self._samples_to_join = set()

        # Mapping cols => table
        # Get columns description from the given table
        tables = ("variants", "annotations")
        self.col_table_mapping = {
            table_name: set(sql.get_columns(self.conn, table_name))
            for table_name in tables
        }

    def extract_samples_from_columns_and_filter(self, filter_only=False):
        """Extract samples if columns or filter contains function.

        The aim is to dynamically add JOIN clauses on 'samples' table.
        `self._samples_to_join` is modified here.

        .. note:: About functions:
            `columns` and `filter` can contains function as tuple.
            A function is defined by:
                - function name
                - arguments (sample name, etc.)
                - sql field name

            This columns selection can be writted in VQL as follow:

                SELECT chr, pos, genotype("boby").gt

            "boby" will be added to `self._samples_to_join`

        .. note:: `_samples_to_join` is a dict with sample_names as keys
            and sample_ids as values.
        """
        # Set sample names to join by searching them in columns
        if not filter_only:
            columns_in_columns = self.get_samples_names_from_functions(
                self.columns, _GENOTYPE_FUNCTION_NAME
            )
        else:
            columns_in_columns = set()

        # Set sample names to join by searching them in filter
        # iter_filter(): Recursive loop over filter to extract field name only
        columns_in_filter = self.get_samples_names_from_functions(
            self.iter_filter(self.filter), _GENOTYPE_FUNCTION_NAME
        )

        # Get samples required by columns and filter
        required_samples_names = columns_in_columns | columns_in_filter

        self._samples_to_join = {
            sample["name"]: sample["id"]
            for sample in sql.get_samples(self.conn)
            if sample["name"] in required_samples_names
        }

        LOGGER.debug("DETECT %s in %s", self._samples_to_join.keys(), self.columns)

    def get_samples_names_from_functions(self, columns, function_name):
        """Get samples names from given functions if their function_name matches
        to the given one.

        :param columns: Iterable of columns in which functions are searched.
        :param function_name: Function name to be search in functions.
        :return: Set of arguments (samples names).
        :rtype: <set>
        """
        samples = set()
        # Get function tuples
        #  A function is a tuple with 3 elements.
        #  The second element is the sample name
        # TODO: is test on length usefull?
        functions = (col for col in columns if isinstance(col, tuple) and len(col) == 3)

        for function in functions:
            function_name, function_argument, field_name = function

            if function_name == function_name:
                # function_argument is a sample_name here
                samples.add(function_argument)
        return samples

    def detect_annotations_table_requirement(self, filter_only=False):
        """Return True if annotations table is required after searching in
        columns and / or filter.

        :key filter_only: If True, the search will be made only in 'self.filter'
        :type filter_only: <boolean>
        :rtype: <boolean>
        """
        # Get columns in filter
        cols_in_annotations = {
            col for col in self.iter_filter(self.filter)
        } & self.col_table_mapping["annotations"]
        if cols_in_annotations:
            LOGGER.debug(
                "detect_annotations_table_requirement: found col in filter: %s",
                cols_in_annotations,
            )
            return True

        if filter_only:
            # Stop here, no col has been found in filter => False
            return False

        # Get columns in columns
        cols_in_annotations = set(self.columns) & self.col_table_mapping["annotations"]
        if cols_in_annotations:
            LOGGER.debug(
                "detect_annotations_table_requirement: found col in columns: %s",
                cols_in_annotations,
            )
            return True
        return False

    def iter_filter(self, node):
        """Recursive loop over filter to extract field name only
        Recall: {'AND': [{'field': 'ref', 'operator': 'IN', 'value': "('A', 'T', 'G', 'C')"},
        {'field': 'alt', 'operator': 'IN', 'value': "('A', 'T', 'G', 'C')"}]}
        Aim: yield columns involved in filter
        """
        if isinstance(node, dict) and len(node) == 3:
            yield node["field"]

        if isinstance(node, dict):
            for i in node:
                yield from self.iter_filter(node[i])

        if isinstance(node, list):
            for i in node:
                yield from self.iter_filter(i)

    ##--------------------------------------------------------------------------

    def get_columns(self, do_not_add_default_things=False):
        """Get list of columns ready to be inserted in a query string
        .. seealso:: sql() or sql_count()
        :rtype: <list>
       """
        # Set default columns if columns is empty
        # Otherwise, columns are kept unmodified
        if not self.columns:
            self.columns = ["chr", "pos", "ref", "alt"]

        if do_not_add_default_things:
            # Keep columns as they are set in the query
            sql_columns = []
        else:
            # Some queries must have this field in addition to theirs
            sql_columns = ["variants.id"]

        # Replace genotype function by name
        # Transform ("genotype", "boby","gt") to "`gt_boby`.gt" to perform SQL JOIN
        for col in self.columns:
            if isinstance(col, tuple):
                function_name, arg, field_name = col
                if function_name == _GENOTYPE_FUNCTION_NAME:
                    # Secure column name
                    col = f"`gt_{arg}`.{field_name}"

            sql_columns.append(col)

        # If 'group by', add extra columns (child count and child ids)
        # Required for viewquerywidget.py
        if not do_not_add_default_things and self.group_by:
            sql_columns.extend(["COUNT(*) as 'children'"])

        return sql_columns

    def get_joints(self, do_not_add_default_things=False, filter_only=False):
        """Get string of joints ready to be appended to a query string
        .. seealso:: sql() or sql_count()
        :key filter_only: If True, the search will be made only in 'self.filter'
        :type filter_only: <boolean>
        :rtype: <str>
        """
        # On filter and columns
        # Joint on annotations is mandatory for display queries
        # We do not do joint if it is explicitly forbidden (in this case
        # a join is automatically decided if it is required by filter or columns)
        is_col_in_annotations = self.detect_annotations_table_requirement(
            filter_only=filter_only
        )
        query = (
            ""
            if do_not_add_default_things and not is_col_in_annotations
            else " LEFT JOIN annotations ON annotations.variant_id = variants.id"
        )

        if self.selection and self.selection != DEFAULT_SELECTION_NAME:
            # Add jointure with 'selections' table
            query += f"""
            INNER JOIN selection_has_variant sv ON sv.variant_id = variants.id
            INNER JOIN selections s ON s.id = sv.selection_id AND s.name = '{self.selection}'
            """

        #  Add Join on sample_has_variant
        #  This is done if genotype() function has been found in columns or filter,
        # or filter only if specified.
        # _samples_to_join is a dict with sample_names as keys and sample_ids as values
        self.extract_samples_from_columns_and_filter(filter_only=filter_only)
        for sample_name, sample_id in self._samples_to_join.items():
            query += f"""
            LEFT JOIN sample_has_variant `gt_{sample_name}`
             ON `gt_{sample_name}`.variant_id = variants.id
             AND `gt_{sample_name}`.sample_id = {sample_id}
            """
        return query

    def sql(self, limit=0, offset=0, do_not_add_default_things=False) -> str:
        """Build a sql query according to attributes for raw and display queries

        .. note:: Some queries require that this functions doesn't automatically
            add default columns or joins.
            In this case the argument 'do_not_add_default_things' must be set to True.

            - `variants.id` will not be appended to SELECT clause.
            - A LEFT JOIN on annotations will not be made if it is not required
            by a filter or by columns.
            Typical query concerned: see ChartQueryWidget:on_change_query()
            In other cases, 'annotations' table is mandatory for display queries
            which group variants on transcripts for example.

        .. note:: This function can be called as this, but its main purpose is
            to be used by self.items().

        .. seealso:: sql_count()

        :param limit: SQL LIMIT for pagination
        :param offset: SQL OFFSET for pagination
        :key do_not_add_default_things: See previous note (default: False)
        :return: A SQL query ready to be executed.
        :rtype: <str>
        """
        ## Build columns
        sql_columns = self.get_columns(do_not_add_default_things)
        query = f"SELECT {','.join(sql_columns)} "

        ## Add FROM clause
        # Explicitly query all variants + ...
        # do_not_add_default_things set to True to avoid groups of variants
        # when there is no checked column in annotations.
        query += "FROM variants" + self.get_joints(do_not_add_default_things=True)

        ## Add WHERE filter
        if self.filter:
            query += " WHERE " + self.filter_to_sql(self.filter)

        ## Add GROUP BY command
        if self.group_by:
            query += " GROUP BY " + ",".join(self.group_by)

        ## Add ORDER BY command
        if self.order_by is not None:
            direction = "DESC" if self.order_desc else "ASC"
            query += f" ORDER BY {self.order_by} {direction}"

        ## Add LIMIT and OFFSET clauses
        if limit > 0:
            query += f" LIMIT {limit} OFFSET {offset}"

        LOGGER.debug("Query:sql:: query: %s", query)
        return query

    def sql_count(self):
        """Build a query for count aggregation queries

        Aim: Build queries with chunks of joints/group by commands that
        are only required based on the columns and filters used.

        Useful chunks:
            - Joints:
                - annotations: Only if a column in filter is stored in that table.
                We don't care if such a column is used in SELECT clause.
                It's a time saving and a generator of cleaner queries.
                => decided by detect_annotations_table_requirement(filter_only=True)
                - selections: Only if a selection is selected, and if this is not
                the default one.
                - samples: Only if a sample function is used in filter clause.
                We don't care if such a column is used in SELECT clause.
                It's a time saving and a generator of cleaner queries.
            - Group by:
                - (chr, pos, ref, alt) is the primary key so there will be as many
                groups as variants in the database.
                => no group by is required in this case.
                - (chr, pos) is a group by that modifies the number of variants
                because it modifies the definition of the unicity of a variant.
                => group by is required to reduce the number of variants.

        .. seealso:: sql()
        """
        ## Build columns
        query = "SELECT variants.id "

        ## Add FROM clause
        # Search annotations need on filter only
        # Explicitly query all variants + ...
        # do_not_add_default_things is True to force the removing of annotations
        # as much as possible
        query += "FROM variants" + self.get_joints(
            do_not_add_default_things=True, filter_only=True
        )

        ## Add WHERE filter
        if self.filter:
            query += " WHERE " + self.filter_to_sql(self.filter)

        ## Add GROUP BY command
        if self.group_by != ["chr", "pos", "ref", "alt"]:
            # (chr, pos) is a group by that modifies the number of variants
            # because it modifies the definition of the unicity of a variant.
            # (chr, pos, ref, alt) is the primary key so there will be as many
            # groups as variants in the database.
            query += " GROUP BY " + ",".join(self.group_by)

        LOGGER.debug("Query:sql_count:: query: %s", query)
        return query

    ##--------------------------------------------------------------------------

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
        """Recursive function to convert the self.filter hierarchical dictionnary
        into a SQL WHERE clause.

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

            elif isinstance(value, list):
                value = "(" + ",".join(value) + ")"

            else:
                value = str(value)

            # Process field
            if isinstance(field, tuple) and len(field) == 3:
                #  Function ? ("genotype","sample","gt")
                fct, arg, f = field
                field = f"`gt_{arg}`.{f}"

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

    ##--------------------------------------------------------------------------

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
        # TODO: handle by key argument
        return sql.create_selection_from_sql(self.conn, self.sql(), name=name)

    ##--------------------------------------------------------------------------

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
        if (
            (not self.selection or self.selection == DEFAULT_SELECTION_NAME)
            and not self.filter
            and self.group_by == ["chr", "pos", "ref", "alt"]
        ):
            LOGGER.debug("SELECT MAX(...")
            return self.conn.execute(
                "SELECT MAX(variants.id) as count FROM variants"
            ).fetchone()[0]

        LOGGER.debug(sql_query)
        return self.conn.execute(
            f"SELECT COUNT(*) as count FROM ({sql_query})"
        ).fetchone()[0]

    def variants_count(self) -> int:
        """Return variant count from the current query

        .. note:: This function is used in:
            - viewquerywidget.py in `load()` to keep the total of variants for
            paging purposes of the interface.
        """
        LOGGER.debug("Query:variants_count:: query:")
        count = self._cached_variants_count_query(self.sql_count())
        LOGGER.debug(
            "Query:variants_count:: %s", self._cached_variants_count_query.cache_info()
        )
        return count

    ##--------------------------------------------------------------------------

    def __repr__(self):
        return f"""
        columns : {self.columns}
        filter: {self.filter}
        selection: {self.selection}
        """

    ##--------------------------------------------------------------------------
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
                    col = f'genotype("{arg}")'
            _c.append(col)

        base = f"SELECT {','.join(_c)} FROM {self.selection}"
        where = ""
        if self.filter:
            where = f" WHERE {self.filter_to_sql(self.filter)}"
        return base + where

    ##--------------------------------------------------------------------------

    def check(self):
        """Return True if query is valid"""
        raise NotImplementedError
