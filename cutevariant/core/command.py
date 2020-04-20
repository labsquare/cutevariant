
from cutevariant.core.querybuilder import * 
from cutevariant.core import sql, vql 
import sqlite3
import networkx as nx 

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
        self.default_tables = dict([(i["name"], i["category"]) for i in sql.get_fields(self.conn)])


    def do(self):
        q = build_query(self.columns, self.source, self.filters, self.order_by, self.order_desc, self.grouped, self.limit, self.offset, self.default_tables) 

        self.conn.row_factory = sqlite3.Row

        for i in self.conn.execute(q):
            yield dict(i)

    

class CreateCommand(Command):
    def __init__(self, conn: sqlite3.Connection):
        super().__init__(conn)
        self.filters=dict()
        self.source="variants"
        self.target = None
        self.count = 0 
        self.default_tables = dict([(i["name"], i["category"]) for i in sql.get_fields(self.conn)])



    def do(self):
        if self.target is None:
            return 

        cursor = self.conn.cursor()

        sql_query = build_query(["id"], self.source, self.filters, default_tables = self.default_tables) 
        count = sql.count_query(self.conn, sql_query)


        selection_id = sql.insert_selection(cursor, sql_query, name=self.target, count=count)


        q = f"""
        INSERT INTO selection_has_variant
        SELECT DISTINCT id, {selection_id} FROM ({sql_query})
        """

        # DROP indexes
        # For joints between selections and variants tables
        try:
            cursor.execute("""DROP INDEX idx_selection_has_variant""")
        except sqlite3.OperationalError:
            pass

        cursor.execute(q)

        # # REBUILD INDEXES
        # # For joints between selections and variants tables
        sql.create_selection_has_variant_indexes(cursor)

        self.conn.commit()
        if cursor.rowcount:
            return {"id": cursor.lastrowid}
        return {}




    def undo(self):
        pass 




class SetCommand(Command):
    def __init__(self, conn: sqlite3.Connection):
        super().__init__(conn)
        self.target = None
        self.first = None
        self.second = None 
        self.operator = None

    def do(self):
        
        if self.target is None or self.first is None or self.second is None or self.operator is None:
            return {}

        cursor = self.conn.cursor()

        query_first = build_query(["id"], self.first) 
        query_second = build_query(["id"], self.second) 


        if self.operator == "+":
            sql_query = sql.union_variants(query_first, query_second)

        if self.operator == "-":
            sql_query = sql.subtract_variants(query_first, query_second)

        if self.operator == "&":
            sql_query = sql.intersect_variants(query_first, query_second)


        selection_id = sql.insert_selection(cursor, sql_query, name=self.target, count= 0 )

        q = f"""
        INSERT INTO selection_has_variant
        SELECT DISTINCT id, {selection_id} FROM ({sql_query})
        """

        # DROP indexes
        # For joints between selections and variants tables
        try:
            cursor.execute("""DROP INDEX idx_selection_has_variant""")
        except sqlite3.OperationalError:
            pass

        cursor.execute(q)

        # # REBUILD INDEXES
        # # For joints between selections and variants tables
        sql.create_selection_has_variant_indexes(cursor)

        self.conn.commit()
        if cursor.rowcount:
            return {"id": cursor.lastrowid}
        return {}

    def undo(self):
        pass 


def VqlCommand(Command):
    def __init__(self, conn: sqlite3.Connection, vql : str):
        super().__init__(conn)

        self.vql = vql 
        self.cmds = []

    def do(self):
        for cmd in self.cmds:
            cmd.do()

    def undo(self):
        for cmd in self.cmds:
            cmd.undo()

    def _create_cmds(self):
        pass


def cmd_from_vql(conn, vql_cmd): 
    if vql_cmd["cmd"] == "select_cmd":
        cmd = SelectCommand(conn)
        cmd.columns = vql_cmd["columns"]
        cmd.source = vql_cmd["source"]
        cmd.filters = vql_cmd["filters"]
        return cmd 

    if vql_cmd["cmd"] == "create_cmd":
        cmd = CreateCommand(conn)
        cmd.source = vql_cmd["source"]
        cmd.filters = vql_cmd["filters"]
        cmd.target = vql_cmd["target"] 
        return cmd 

    if vql_cmd["cmd"] == "set_cmd":
        cmd = SetCommand(conn)
        cmd.target = vql_cmd["target"]
        cmd.first = vql_cmd["first"]
        cmd.second = vql_cmd["second"]
        cmd.operator = vql_cmd["operator"]
        return cmd

    return None


class CommandGraph(object):
    def __init__(self, conn):
        super().__init__()
        self.conn = conn
        self.graph = nx.DiGraph() 
        self.graph.add_node("variants")

    def add_command(self, command: Command):

        if type(command) == CreateCommand:
            self.graph.add_node(command.target)
            self.graph.add_edge(command.source, command.target)

        if type(command) == SelectCommand:
            self.graph.add_node("Select")
            self.graph.add_edge(command.source, "Select")

        if type(command) == SetCommand:
            self.graph.add_node(command.target)
            self.graph.add_edge(command.first, command.target)
            self.graph.add_edge(command.second, command.target)

    def set_source(self, source):
        self.graph.clear()
        for vql_cmd in vql.execute_vql(source):
            cmd = cmd_from_vql(self.conn, vql_cmd)
            self.add_command(cmd)

