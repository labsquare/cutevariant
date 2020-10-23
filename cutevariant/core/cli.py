# Standard imports
import argparse
import os
import sys

# Custom imports
import progressbar
from columnar import columnar
from cutevariant.core.importer import async_import_file
from cutevariant.core import sql, vql
from cutevariant.core.querybuilder import *
from cutevariant.commons import log_level


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
        default="critical",
        choices=["debug", "info", "critical", "error", "warning"],
    )

    sub_parser = parser.add_subparsers(dest="subparser")

    # Common parser: Database file requirement #################################
    parent_parser = argparse.ArgumentParser(add_help=False)
    parent_parser.add_argument(
        "--db", help="SQLite database. By default, $CUTEVARIANT_DB is used."
    )

    # Create DB parser #########################################################
    createdb_parser = sub_parser.add_parser(
        "createdb",
        help="Build a SQLite database from a vcf file",
        parents=[parent_parser],
    )
    createdb_parser.add_argument("-i", "--input", help="VCF file path", required=True)

    # Show parser ##############################################################
    show_parser = sub_parser.add_parser(
        "show", help="Display table content", parents=[parent_parser]
    )
    show_parser.add_argument(
        "table",
        choices=["fields", "selections", "samples"],
        help="Possible names of tables.",
    )

    # Remove parser ############################################################
    remove_parser = sub_parser.add_parser(
        "remove", help="remove selection", parents=[parent_parser]
    )
    remove_parser.add_argument("names", nargs="+", help="Name(s) of selection(s).")

    # VQL parser ###############################################################
    select_parser = sub_parser.add_parser(
        "exec",
        help="Execute a VQL statement.",
        parents=[parent_parser],
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""Examples:

    $ cutevariant-cli exec "SELECT favorite,chr,pos,ref,alt FROM variants"
    or
    $ cutevariant-cli exec -g ??????? "????"
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
    select_parser.add_argument(
        "-g",
        "--group",
        action="store_true",
        help="Group SELECT query by...(chr,pos,ref,alt).",
    )
    select_parser.add_argument(
        "-s", "--to-selection", help="Save SELECT query into a selection name."
    )

    # Set parser ###############################################################
    # set_parser = sub_parser.add_parser("set", help="Set variable", parents=[parent_parser])

    args = parser.parse_args()

    if len(sys.argv) == 1:
        parser.print_help(sys.stderr)
        sys.exit(1)

    # Set log level
    # _logger.setLevel(logging.DEBUG)
    log_level(args.verbose)

    # Create DB parser #########################################################
    if args.subparser == "createdb":
        if not args.db:
            # Database file is not set:
            # The output file will be based on the name of the VCF one
            args.db = args.input + ".db"

        if os.path.exists(args.db):
            # Remove existing file
            os.remove(args.db)

        conn = sql.get_sql_connexion(args.db)
        if conn:
            # TODO: bug ... max is not 100...
            for i, message in progressbar.progressbar(
                async_import_file(conn, args.input), redirect_stdout=True
            ):
                print(message)

        print("The database is successfully created!")
        exit()

    # Prepare SQL connection on DB file
    if "CUTEVARIANT_DB" in os.environ and args.subparser != "createdb":
        args.db = os.environ["CUTEVARIANT_DB"]
    elif not args.db:
        print("You must specify a database file via $CUTEVARIANT_DB or --db argument")
        exit()

    # Init SQL connection
    conn = sql.get_sql_connexion(args.db)

    # Show parser ##############################################################
    if args.subparser == "show":
        if args.table == "fields":
            print(
                columnar(
                    [i.values() for i in sql.get_fields(conn)],
                    headers=["id", "Name", "table", "type", "description"],
                    no_borders=True,
                )
            )

        if args.table == "samples":
            print(
                columnar(
                    [i.values() for i in sql.get_samples(conn)],
                    headers=["id", "Name"],
                    no_borders=True,
                )
            )

        if args.table == "selections":
            print(
                columnar(
                    [i.values() for i in sql.get_selections(conn)],
                    headers=["id", "Name", "Count"],
                    no_borders=True,
                )
            )

    # Remove parser ############################################################
    if args.subparser == "remove":
        for name in args.names:
            sql.delete_selection_by_name(conn, name)

    # VQL parser ###############################################################
    if args.subparser == "exec":
        query = "".join(args.vql)

        # Test the VQL query
        try:
            cmd = next(vql.parse_vql(query))
        except (vql.textx.TextXSyntaxError, vql.VQLSyntaxError) as e:
            # Available attributes: e.message, e.line, e.col
            print("%s: %s, col: %d" % (e.__class__.__name__, e.message, e.col))
            print("For query:", query)
            exit(0)

        # Select command
        # if cmd["cmd"] == "select_cmd":

        print("Work in progress...")


if __name__ == "__main__":
    main()
