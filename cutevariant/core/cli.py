# Standard imports
import argparse
import os
import sys
from functools import partial

# Custom imports
import progressbar
from columnar import columnar
from cutevariant.core import sql, vql, command
from cutevariant.core.readerfactory import create_reader
from cutevariant.core.querybuilder import *
from cutevariant import LOGGER


def display_sql_results(data, headers, *args, **kwargs):
    """Display SQL results in the console in tabulated format"""
    print(
        columnar(
            data,
            headers=headers,
            no_borders=True,
            **kwargs,
        )
    )


def display_query_status(query_result):
    """Display error status of a valid and executed VQL query

    Supported results of VQL commands: drop/import; create/set/bed

    Args:
        query_result(dict)
    """
    # Success for drop/import; id present for create/set/bed
    if query_result.get("success") or ("id" in query_result):
        print("Done")
    else:
        print("An error occured, there is no result, or there is nothing to do.")
    exit(1)


def create_db(args):
    if not args.db:
        # Database file is not set:
        # The output file will be based on the name of the VCF one
        args.db = args.input + ".db"

    # if os.path.exists(args.db):
    #     # Remove existing file
    #     os.remove(args.db)

    conn = sql.get_sql_connection(args.db)
    # if args.pedfile
    if conn:
        # TODO: bug ... max is not 100...

        with create_reader(args.input) as reader:
            sql.import_reader(conn, reader, import_id = args.import_id)

        print("Successfully created database!")


def show(args, conn):
    if args.table == "fields":
        display_sql_results(
            (i.values() for i in sql.get_fields(conn)),
            ["id", "name", "table", "type", "description"],
        )

    if args.table == "samples":
        display_sql_results((i.values() for i in sql.get_samples(conn)), ["id", "name"])

    if args.table == "selections":
        display_sql_results(
            (i.values() for i in sql.get_selections(conn)),
            ["id", "name", "variant_count"],
        )

    if args.table == "wordsets":
        display_sql_results((i.values() for i in sql.get_wordsets(conn)), ["id", "word_count"])


def remove(args, conn):
    for name in args.names:
        rows_removed = sql.delete_selection_by_name(conn, name)
        if rows_removed:
            print(f"Successfully removed {rows_removed} variants from selection {name}")
        else:
            print(f"Could not remove selection {name}")
    return 0


def select(args, conn):
    query = "".join(args.vql)
    vql_command = None

    # Test the VQL query
    try:
        cmd = vql.parse_one_vql(query)
    except (vql.textx.TextXSyntaxError, vql.VQLSyntaxError) as e:
        # Available attributes: e.message, e.line, e.col
        print("%s: %s, col: %d" % (e.__class__.__name__, e.message, e.col))
        print("For query:", query)
        return 1

    # Select command with redirection to selection
    if cmd["cmd"] == "select_cmd" and args.to_selection:
        vql_command = partial(
            command.create_cmd,
            conn,
            args.to_selection,
            source=cmd["source"],
            filters=cmd["filters"],
        )

    try:
        # Is it redundant with check_vql ?
        # No because we also execute SQL statement here
        if vql_command:
            ret = vql_command()
        else:
            ret = command.create_command_from_obj(conn, cmd)()
        if not isinstance(ret, dict):
            # For drop_cmd, import_cmd,
            ret = list(ret)
    except (sqlite3.DatabaseError, vql.VQLSyntaxError) as e:
        LOGGER.exception(e)
        return 1

    LOGGER.debug("SQL result: %s", ret)
    LOGGER.debug("VQL command: %s", cmd["cmd"])
    # Note: show_cmd is supported in a separated command option

    # Select command
    if cmd["cmd"] in ("select_cmd",) and not args.to_selection:
        display_sql_results((i.values() for i in ret), ["id"] + cmd["fields"])

    if (
        cmd["cmd"] in ("drop_cmd", "import_cmd", "create_cmd", "set_cmd", "bed_cmd")
        or args.to_selection
    ):
        # PS: to_selection is used to detect select_cmd with selection creation
        display_query_status(ret)

    return 0


def main():
    # noinspection PyTypeChecker
    parser = argparse.ArgumentParser(
        formatter_class=lambda prog: argparse.RawDescriptionHelpFormatter(prog),
        description="""
Cutevariant cli mode helps to run actions directly from command-line.\n
The env variable $CUTEVARIANT_DB can be used to define a database instead of
the arguments.""",
        epilog="""Examples:

    $ cutevariant-cli show --db my_database.db samples
    or
    $ export CUTEVARIANT_DB=my_database.db
    $ cutevariant-cli show samples""",
    )
    # Default log level: critical
    parser.add_argument(
        "-vv",
        "--verbose",
        nargs="?",
        default="error",
        choices=["debug", "info", "critical", "error", "warning"],
    )

    sub_parser = parser.add_subparsers(dest="subparser")

    # Common parser: Database file requirement #################################
    parent_parser = argparse.ArgumentParser(add_help=False)
    parent_parser.add_argument("--db", help="SQLite database. By default, $CUTEVARIANT_DB is used.")

    # Create DB parser #########################################################
    createdb_parser = sub_parser.add_parser(
        "createdb",
        help="Build a SQLite database from a vcf file",
        parents=[parent_parser],
        epilog="""Examples:

        $ cutevariant-cli createdb -i "examples/test.snpeff.vcf"
        """,
    )
    createdb_parser.add_argument("-i", "--input", help="VCF file path", required=True)
    createdb_parser.add_argument(
        "-p", "--pedfile", help="A ped file describing the family relations between the samples."
    )
    createdb_parser.add_argument(
        "-m", "--import_id", help="Import ID to create a tag for each samples (optional, default <DATE>)."
    )
    createdb_parser.set_defaults(func=create_db)

    # Show parser ##############################################################
    show_parser = sub_parser.add_parser(
        "show", help="Display table content", parents=[parent_parser]
    )
    show_parser.add_argument(
        "table",
        choices=["fields", "selections", "samples", "wordsets"],
        help="Possible names of tables.",
    )
    show_parser.set_defaults(func=show)

    # Remove parser ############################################################
    remove_parser = sub_parser.add_parser(
        "remove", help="remove selection", parents=[parent_parser]
    )
    remove_parser.add_argument("names", nargs="+", help="Name(s) of selection(s).")
    remove_parser.set_defaults(func=remove)

    # VQL parser ###############################################################
    select_parser = sub_parser.add_parser(
        "exec",
        help="Execute a VQL statement.",
        parents=[parent_parser],
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""Examples:

    $ cutevariant-cli exec "SELECT favorite,chr,pos,ref,alt FROM variants"
    or
    $ cutevariant-cli exec "SELECT chr,ref,alt FROM variants" -s myselection
    or
    $ cutevariant-cli exec "IMPORT WORDSETs 'examples/gene.txt' AS mygenes"
    or
    $ cutevariant-cli exec "DROP WORDSETS mygenes"
    or
    $ cutevariant-cli exec "CREATE myselection1 FROM variants WHERE gene = 'CHID1'"
    $ cutevariant-cli exec "CREATE myselection2 FROM variants WHERE gene = 'CICP23'"
    $ cutevariant-cli exec "CREATE myselection3 = myselection2 | myselection2"
    or
    $ cutevariant-cli exec "CREATE boby FROM variants INTERSECT 'examples/test.bed'"
    """,
    )
    select_parser.add_argument("vql", help="A VQL statement.")
    select_parser.add_argument(
        "-l",
        "--limit",
        help="Limit the number of lines in output.",
        type=int,
        default=100,
    )
    # select_parser.add_argument(
    #     "-g",
    #     "--group",
    #     action="store_true",
    #     help="Group SELECT query by...(chr,pos,ref,alt).",
    # )
    select_parser.add_argument(
        "-s", "--to-selection", help="Save SELECT query into a selection name."
    )
    select_parser.set_defaults(func=select)

    # Set parser ###############################################################
    # set_parser = sub_parser.add_parser("set", help="Set variable", parents=[parent_parser])

    # Workaround for sphinx-argparse module that require the object parser
    # before the call of parse_args()
    if "html" in sys.argv:
        return parser
    args = parser.parse_args()

    LOGGER.setLevel(args.verbose.upper())
    
    # Prepare SQL connection on DB file
    if "CUTEVARIANT_DB" in os.environ:
        args.db = os.environ["CUTEVARIANT_DB"]

    #elif not args.db and args.subparser != "createdb":
    elif "db" not in dir(args) and args.subparser != "createdb":
        print("You must specify a database file via $CUTEVARIANT_DB or --db argument")
        print("Use --help for more information")
        return 1

    # Init SQL connection
    # If there is still no db defined at this point, it should mean that we are using the 'createdb' subparser

    # Generic subcommand, with database specified
    if args.db and args.subparser != "createdb":
        conn = sql.get_sql_connection(args.db)
        return args.func(args, conn)
    if args.subparser == "createdb":
        return create_db(args)

    print(
        "You specified no database to open, asked for none to be created, there is nothing more I can do!"
    )
    return 1


if __name__ == "__main__":
    exit(main())
