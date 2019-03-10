import re
from . import sql
from . import vql


class Query:
    """
    This class is intended to build sql query according parameters
    self.columns : columns from variant table
    self.filter : filter filter as raw text
    self.selection : name of the variant set. Use "all" to select all variants
    """

    def __init__(
        self, conn, columns=["chr", "pos", "ref", "alt"], filter=None, selection="all"
    ):
        self.conn = conn
        self.columns = columns
        self.filter = filter
        self.selection = selection
        self.order_by = None
        self.order_desc = True

        ##-----------------------------------------------------------------------------------------------------------

    def sample_from_expression(self, expression):
        # extract <sample> from <gt("sample")>
        regexp = r"gt(.*).gt"
        match = re.search(regexp, expression)
        if match:
            return match.group(1)
        else:
            return None

        ##-----------------------------------------------------------------------------------------------------------

    def detect_samples(self):
        """ detect if query need sample join by looking genotype expression : genotype("boby").gt and return samples """
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

    def sql(self, limit=0, offset=0):
        """ build query depending class parameter """

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

        query = f"SELECT {','.join(sql_columns)} "

        # Add Select clause

        if self.selection == "all":
            query += f"FROM variants"
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

        if self.order_by is not None:
            direction = "DESC" if self.order_desc is True else "ASC"
            query += f" ORDER BY {self.order_by} {direction}"

        if limit > 0:
            query += f" LIMIT {limit} OFFSET {offset}"

        print(query)
        return query

        ##-----------------------------------------------------------------------------------------------------------

    def rows(self, limit=0, offset=0):
        """ return query results as list by record """
        print(self.sql(limit, offset))
        yield from self.conn.execute(self.sql(limit, offset))

        ##-----------------------------------------------------------------------------------------------------------

    def items(self, limit=0, offset=0):
        """ return query results as dict by record """
        for value in self.conn.execute(self.sql(limit, offset)):
            item = {}
            for index, col in enumerate(["rowid"] + self.columns):
                item[col] = value[index]
            yield item

        ##-----------------------------------------------------------------------------------------------------------

    def filter_to_sql(self, node: dict) -> str:

        if dict is None:
            return str()

        # function to detect if node is a Condition node (AND/OR) OR a field node {name,operator, value}
        is_field = lambda x: True if len(x) == 3 else False

        if is_field(node):
            # change value
            value = node["value"]
            operator = node["operator"]
            field = node["field"]

            if (
                type(value) == str
            ):  # Add quote for string .. Need to change in the future and use sqlite binding value
                value = "'" + str(value) + "'"
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
        return self.detect_samples().keys()

        ##-----------------------------------------------------------------------------------------------------------

    def create_selection(self, name):
        sql.create_selection_from_sql(self.conn, name, self.sql())

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
        selection: {self.selection}
        """

        ##-----------------------------------------------------------------------------------------------------------

    def from_vql(self, raw: str):
        model = vql.model_from_string(raw)
        self.columns = model["select"]
        self.selection = model["from"]
        self.filter = model.get("where")  # None if no filter
        # TODO: USING clause missing

        print("from vql", model)

        ##-----------------------------------------------------------------------------------------------------------

    def to_vql(self) -> str:
        base = f"SELECT {','.join(self.columns)} FROM {self.selection}"
        where = ""
        if self.filter:
            where = f" WHERE {self.filter_to_sql(self.filter)}"
        return base + where + ";"

        ##-----------------------------------------------------------------------------------------------------------

    def check(self):
        """ Return True if query is valid """
        return True
