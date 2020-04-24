
from cutevariant.core.querybuilder import * 
from cutevariant.core import sql, vql 
import sqlite3
import networkx as nx 
import os 
import csv

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
        self.fields=["chr", "pos", "ref", "alt"]
        self.filters=dict()
        self.source="variants"
        self.order_by=None
        self.order_desc=True
        self.grouped = False 
        self.limit = 50
        self.offset = 0
        self.as_dict = True

    def sql(self):
        default_tables = dict([(i["name"], i["category"]) for i in sql.get_fields(self.conn)])
        samples_ids = dict([(i["name"], i["id"]) for i in sql.get_samples(self.conn)])

        return build_query(self.fields, self.source, self.filters, self.order_by, self.order_desc, self.grouped, self.limit, self.offset, default_tables, samples_ids =samples_ids) 

    def do(self):
        for i in self.conn.execute(self.sql()):
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

        query_first = build_query(["id"], self.first, limit = None) 
        query_second = build_query(["id"], self.second, limit = None) 


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

class BedCommand(Command):
    def __init__(self, conn: sqlite3.Connection):
        super().__init__(conn)    
        self.bedfile = None
        self.source = None
        self.target = None

    def read_bed(self):
        with open(self.bedfile) as file:
            reader = csv.reader(file, delimiter="\t")
            for line in reader: 
                if len(line) >= 3:
                    yield {"chr":line[0], "start":int(line[1]), "end": int(line[2]), "name": ""}


    def do(self):
        selection_id = sql.create_selection_from_bed(self.conn, self.source, self.target, self.read_bed())
        return {"id": selection_id}

    def undo(self):
        pass
        




        
def create_command_from_vql_objet(conn, vql_obj: dict): 
    if vql_obj["cmd"] == "select_cmd":
        cmd = SelectCommand(conn)
        cmd.fields = vql_obj["fields"]
        cmd.source = vql_obj["source"]
        cmd.filters = vql_obj["filters"]
        return cmd 

    if vql_obj["cmd"] == "create_cmd":
        cmd = CreateCommand(conn)
        cmd.source = vql_obj["source"]
        cmd.filters = vql_obj["filters"]
        cmd.target = vql_obj["target"] 
        return cmd 

    if vql_obj["cmd"] == "set_cmd":
        cmd = SetCommand(conn)
        cmd.target = vql_obj["target"]
        cmd.first = vql_obj["first"]
        cmd.second = vql_obj["second"]
        cmd.operator = vql_obj["operator"]
        return cmd

    if vql_obj["cmd"] == "bed_cmd": 
        cmd = BedCommand(conn)
        cmd.target = vql_obj["target"]
        cmd.source = vql_obj["source"]
        cmd.bedfile = vql_obj["path"]
        return cmd
    return None

def create_commands(conn, vql_source: str):
    for vql_obj in vql.parse_vql(vql_source):
        cmd = create_command_from_vql_objet(conn, vql_obj)
        yield cmd 
        

def execute_vql(conn, vql_source: str):

    vql_obj = next(vql.parse_vql(vql_source))
    cmd = create_command_from_vql_objet(conn, vql_obj)
    return cmd.do()


def execute_full_vql(conn, vql_source: str):
    for vql_obj in vql.parse_vql(vql_source):
        cmd = create_command_from_vql_objet(conn, vql_obj)
        if type(cmd) == SelectCommand:
            yield cmd.do()
        else:
            yield cmd.do()

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
        for vql_obj in vql.execute_vql(source):
            cmd = create_command_from_vql_objet(self.conn, vql_obj)
            self.add_command(cmd)

