
import argparse
import os 
import progressbar
import pprint
import sys
import logging 

from prompt_toolkit import prompt 
from columnar import columnar

from cutevariant.core.importer import import_file, async_import_file
from cutevariant.core import sql
from cutevariant.core import vql


if __name__ == "__main__":
    logger = logging.getLogger()
    logger.setLevel(logging.CRITICAL)
    parser = argparse.ArgumentParser()
    sub_parser = parser.add_subparsers(dest='subparser')
    
    #createdb parser 
    createdb_parser = sub_parser.add_parser("createdb", help="Build a database")
    createdb_parser.add_argument("-i", "--input", help="VCF file path",metavar='in-file', required=True)
    createdb_parser.add_argument("-o", "--output", help="cutevariant sqlite database path",metavar='out-file' )

    #show parser 
    show_parser = sub_parser.add_parser("show", help="Display contents")
    show_parser.add_argument("table", choices=["fields","selections","samples"])
    show_parser.add_argument("--db", help="sqlite database", metavar="in-file")

    #exec parser 
    select_parser = sub_parser.add_parser("exec", help="Execute VQL statement")
    select_parser.add_argument("vql", help="A vql statement")
    select_parser.add_argument("--db", help="sqlite database", metavar="in-file")
    select_parser.add_argument("--limit", help="output line number", type=int, default=100)

    # #Set parser
    # set_parser = sub_parser.add_parser("set", help="Set variable")
    # set_parser.add_argument("--db", help="Set $CUTEVARIANT_DB env variable ",type=str)




    args = parser.parse_args()

    if len(sys.argv)==1:
        parser.print_help(sys.stderr)
        sys.exit(1)
 
    if "CUTEVARIANT_DB" in os.environ and args.subparser != "createdb":
        args.db = os.environ['CUTEVARIANT_DB']
        conn = sql.get_sql_connexion(args.db)


    # ====== CREATEDB ============================
    if args.subparser == "createdb":
        if args.output == None:

            args.output = args.input + ".db"

            if os.path.exists(args.output):
                os.remove(args.output)

        conn = sql.get_sql_connexion(args.output)

        if conn:
            #TODO: bug ... max is not 100...
            for i, message in progressbar.progressbar(async_import_file(conn, args.input), redirect_stdout=True):
                print(message)

    # ====== SHOW ============================
    if args.subparser == "show":
        if args.table == "fields":
            print("#name","category","description", sep="\t")
            for field in sql.get_fields(conn):
                print("{1:<10}\t{2:<10}\t{4}".format(*field.values()))

        if args.table == "samples":
            print("#name", sep="\t")
            for sample in sql.get_samples(conn):
                print("{1:<10}".format(*sample.values()))
        
        if args.table == "selections":
            print("#name", sep="\t")
            for selections in sql.get_selections(conn):
                print("{1:<10}".format(*selections.values()))

    # ====== EXEC VQL ============================
    if args.subparser == "exec":
        query = "".join(args.vql)

        print(query)

        cmd = next(vql.execute_vql(query))
        if cmd["cmd"] == "select_cmd":
            selector = sql.SelectVariant(conn)
            
            selector.columns = cmd.get("columns")
            selector.filters = cmd.get("filter")
            
            # remove ids 
            items = [list(i)[1:] for i in selector.items(limit = args.limit)]
            
            print(columnar(items, headers =selector.columns, no_borders=True))
            
          
