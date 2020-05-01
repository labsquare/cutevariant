
from cutevariant.core.querybuilder import * 
from cutevariant.core import sql, vql 
import sqlite3
import networkx as nx 
import os 
import functools
import csv




def select_cmd(
    conn: sqlite3.Connection, 
    fields = ["chr", "pos", "ref", "alt"],
    source = "variants",
    filters = dict(),
    order_by = None, 
    order_desc = True, 
    limit = 50,
    offset = 0,
    **kwargs):
        """Select query Command 
        
        Args:
            conn (sqlite3.Connection): Description
            fields (list, optional): Description
            filters (TYPE, optional): Description
            source (str, optional): Description
            order_by (None, optional): Description
            order_desc (bool, optional): Description
            limit (int, optional): Description
            offset (int, optional): Description
        
        Yields:
            TYPE: Description
        """
        default_tables = dict([(i["name"], i["category"]) for i in sql.get_fields(conn)])
        samples_ids = dict([(i["name"], i["id"]) for i in sql.get_samples(conn)])
        query = build_query(fields, source, filters, order_by, order_desc, limit, offset, default_tables, samples_ids = samples_ids) 
        for i in conn.execute(query):
            yield dict(i)



def count_cmd(conn: sqlite3.Connection, source = "variants", filters = {}, distinct=True, **kwargs):
    """Count command 
    
    Args:
        conn (sqlite3.Connection): Description
        source (str, optional): Description
        filters (dict, optional): Description
    
    Returns:
        TYPE: Description
    """
    default_tables = dict([(i["name"], i["category"]) for i in sql.get_fields(conn)])
    samples_ids = dict([(i["name"], i["id"]) for i in sql.get_samples(conn)])
    query = build_query([""], source, filters, None,None, None, None, default_tables, samples_ids =samples_ids) 
    from_pos = query.index("FROM")

    if distinct:
        query = "SELECT COUNT(DISTINCT variants.id) " + query[from_pos:] 
    else:
        query = "SELECT COUNT(variants.id) " + query[from_pos:] 

    return {"count": conn.execute(query).fetchone()[0]}

def drop_cmd(conn: sqlite3.Connection, feature, name ,**kwargs ): 

    accept_features = ["selections","sets"]

    if feature not in accept_features:
        raise vql.VQLSyntaxError(f"{feature} doesn't exists")

    if feature == "selections":
        conn.execute(f"DELETE FROM selections WHERE name = '{name}'")
        conn.commit()
        return {"success": True}

    if feature == "sets":
        print("delete")
        res = conn.execute(f"DELETE FROM sets WHERE name = '{name}'")
        conn.commit()
        return {"success": True}



def create_cmd(conn: sqlite3.Connection, target, source = "variants", filters = dict(), count = 0,**kwargs ):

    default_tables = dict([(i["name"], i["category"]) for i in sql.get_fields(conn)])
    samples_ids = dict([(i["name"], i["id"]) for i in sql.get_samples(conn)])

    if target is None:
        return {} 

    cursor = conn.cursor()

    sql_query = build_query(["id"],source,filters, default_tables = default_tables,  samples_ids =samples_ids) 
    count = sql.count_query(conn, sql_query)


    selection_id = sql.insert_selection(cursor, sql_query, name=target, count=count)


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


    conn.commit()

    if cursor.rowcount:
        return {"id": cursor.lastrowid}
    return {}


def set_cmd(conn: sqlite3.Connection, target, first, second, operator, **kwargs):

    if target is None or first is None or second is None or operator is None:
        return {}

    cursor = conn.cursor()

    query_first = build_query(["id"], first, limit = None) 
    query_second = build_query(["id"], second, limit = None) 


    if operator == "+":
        sql_query = sql.union_variants(query_first, query_second)

    if operator == "-":
        sql_query = sql.subtract_variants(query_first, query_second)

    if operator == "&":
        sql_query = sql.intersect_variants(query_first, query_second)


    selection_id = sql.insert_selection(cursor, sql_query, name=target, count= 0 )

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

    conn.commit()
    if cursor.rowcount:
        return {"id": cursor.lastrowid}
    return {}



def bed_cmd(conn: sqlite3.Connection, path, target, source, **kwargs):

    if not os.path.exists(path):
        raise vql.VQLSyntaxError(f"{path} doesn't exists")

    def read_bed():
        with open(path) as file:
            reader = csv.reader(file, delimiter="\t")
            for line in reader: 
                if len(line) >= 3:
                    yield {"chr":line[0], "start":int(line[1]), "end": int(line[2]), "name": ""}


    selection_id = sql.create_selection_from_bed(conn, source, target, read_bed())
    return {"id": selection_id}


def show_cmd(conn:sqlite3.Connection, feature: str, **kwargs):

    accept_features = ["selections","fields","samples","sets"]

    if feature not in accept_features:
        raise vql.VQLSyntaxError(f"option {feature} doesn't exists")

    if feature == "fields":
        for field in sql.get_fields(conn):
            yield field

    if feature == "samples":
        for sample in sql.get_samples(conn):
            yield sample 

    if feature == "selections":
        for selection in sql.get_selections(conn):
            yield selection

    if feature == "sets":
        for item in sql.get_sets(conn):
            yield item 


def import_cmd(conn: sqlite3.Connection, feature=str, name=str, path=str, **kwargs):

    accept_features = ["sets"]
    if feature not in accept_features:
        raise vql.VQLSyntaxError(f"option {feature} doesn't exists")

    if os.path.exists(path):
        sql.insert_set_from_file(conn, name, path)
    else:
        raise vql.VQLSyntaxError(f"{path} doesn't exists")

    return {"success": True}



    

def create_command_from_obj(conn, vql_obj: dict): 

    if vql_obj["cmd"] == "select_cmd":
        return functools.partial(select_cmd,conn, **vql_obj)

    if vql_obj["cmd"] == "create_cmd":
        return functools.partial(create_cmd,conn, **vql_obj) 

    if vql_obj["cmd"] == "set_cmd":
        return functools.partial(set_cmd,conn, **vql_obj)

    if vql_obj["cmd"] == "bed_cmd": 
        return functools.partial(bed_cmd,conn, **vql_obj)

    if vql_obj["cmd"] == "show_cmd": 
        return functools.partial(show_cmd,conn, **vql_obj)

    if vql_obj["cmd"] == "import_cmd":
        return functools.partial(import_cmd,conn, **vql_obj)
    
    if vql_obj["cmd"] == "drop_cmd":
        return functools.partial(drop_cmd,conn, **vql_obj)

    if vql_obj["cmd"] == "count_cmd":
        return functools.partial(count_cmd,conn, **vql_obj)

    return None
 

def execute(conn, vql_source: str):
    vql_obj = vql.parse_one_vql(vql_source)
    cmd = create_command_from_obj(conn, vql_obj)
    return cmd()

def execute_all(conn, vql_source: str):
    for vql in vql.parse_vql(vql_source):
        cmd = create_command_from_obj(conn, vql)
        yield cmd()



# class CommandGraph(object):
#     def __init__(self, conn):
#         super().__init__()
#         self.conn = conn
#         self.graph = nx.DiGraph() 
#         self.graph.add_node("variants")

#     def add_command(self, command: Command):

#         if type(command) == CreateCommand:
#             self.graph.add_node(command.target)
#             self.graph.add_edge(command.source, command.target)

#         if type(command) == SelectCommand:
#             self.graph.add_node("Select")
#             self.graph.add_edge(command.source, "Select")

#         if type(command) == SetCommand:
#             self.graph.add_node(command.target)
#             self.graph.add_edge(command.first, command.target)
#             self.graph.add_edge(command.second, command.target)

#     def set_source(self, source):
#         self.graph.clear()
#         for vql_obj in vql.execute_vql(source):
#             cmd = create_command_from_vql_objet(self.conn, vql_obj)
#             self.add_command(cmd)

