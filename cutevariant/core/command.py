
from cutevariant.core.querybuilder import * 
from cutevariant.core import sql
import sqlite3


class Command(object):
    def __init__(self, conn : sqlite3.Connection):
        self.conn = conn

    def do(self, **args):
        raise NotImplemented() 

    def undo(self):
        pass 


class SelectCommand(Command):
    def __init__(self, conn : sqlite3.Connection):
        super().__init__(conn) 
        self.columns=["chr", "pos", "ref", "alt"]
        self.filters=dict()
        self.source="variants"
        self.order_by=None
        self.order_desc=True
        self.grouped = False 
        self.limit = 50
        self.offset = 0
        self.as_dict = True
        self.default_tables = self._get_default_tables()


    def _get_default_tables(self):
        return dict([(i["name"], i["category"]) for i in sql.get_fields(self.conn)])

    def _build_query(self):

        sql_query = ""
        # Create columns 
        sql_columns = ["`variants`.`id`"] + [fields_to_sql(col, self.default_tables) for col in self.columns if "id" not in col]
        sql_query = f"SELECT {','.join(sql_columns)} "

        # Add child count if grouped 
        if self.grouped:
            sql_query += ", COUNT(*) as `children`"

        #  Add source table
        sql_query += f"FROM variants"

        # Extract columns from filters 
        columns_in_filters = [i["field"] for i in filters_to_flat(self.filters)]
        
        # Loop over columns and check is annotations is required 
        need_join_annotations = False
        for col in self.columns + columns_in_filters:
            if "annotations." in col:
                need_join_annotations = True
                break

        print(self.columns)

        if need_join_annotations:
            sql_query += (
                " LEFT JOIN annotations ON annotations.variant_id = variants.id"
            )

        #  Add Join Selection
        # TODO: set variants as global variables
        if self.source != "variants":
            sql_query += (
                " INNER JOIN selection_has_variant sv ON sv.variant_id = variants.id "
                f"INNER JOIN selections s ON s.id = sv.selection_id AND s.name = '{self.source}'"
            )

        #  Add Join Samples
        ## detect if columns contains function like (genotype,TUMOR,gt)
        # all_columns = columns_in_filters + self.columns
        # samples_in_query = set([fct[1] for fct in self._get_functions(all_columns)])
        # ## Create Sample Join
        # for sample_name in samples_in_query:
        #     sample_id = self.cache_samples_ids[sample_name]
        #     sql_query += (
        #         f" LEFT JOIN sample_has_variant `gt_{sample_name}`"
        #         f" ON `gt_{sample_name}`.variant_id = variants.id"
        #         f" AND `gt_{sample_name}`.sample_id = {sample_id}"
        #     )

        #  Add Where Clause
        if self.filters:
            where_clause = filter_to_sql(self.filters)
            # TODO : filter_to_sql should returns empty instead of ()
            if where_clause and where_clause != "()":
                sql_query += " WHERE " + where_clause

        #  Add Group By
        if self.grouped:
            sql_query += " GROUP BY " + ",".join(["chr","pos","ref","alt"])

        #  Add Order By
        if self.order_by:
            # TODO : sqlite escape field with quote
            orientation = "DESC" if self.order_desc else "ASC"
            order_by = self.column_to_sql(self.order_by)
            sql_query += f" ORDER BY {order_by} {orientation}"

        if self.limit:
            sql_query += f" LIMIT {self.limit} OFFSET {self.offset}"

        return sql_query


    def do(self, **args):
        self.conn.row_factory = sqlite3.Row
        sql = self._build_query()
        for v in self.conn.execute(sql):
            yield dict(v)

            

class CreateCommand(Command):
    def __init__(self, conn: sqlite3.Connection):
        super().__init__(conn)

    def do(self):
        pass 

    def undo(self):
        pass 




class SetCommand(Command):
    def __init__(self, conn: sqlite3.Connection):
        super().__init__(conn)

    def do(self):
        pass 

    def undo(self):
        pass 
    