from prompt_toolkit import PromptSession
from prompt_toolkit.history import InMemoryHistory
from prompt_toolkit.auto_suggest import AutoSuggestFromHistory

from cutevariant.core import command as cmd
from cutevariant.core import sql
from cutevariant.core.importer import import_file
from cutevariant.core.vql import VQLSyntaxError

from prompt_toolkit.lexers import PygmentsLexer
from pygments.lexers.sql import SqlLexer

import types

session = PromptSession(lexer=PygmentsLexer(SqlLexer))

conn = sql.get_sql_connexion(":memory:")

import_file(conn, "examples/test.snpeff.vcf")

while True:
    text = session.prompt('vql> ', auto_suggest=AutoSuggestFromHistory())

    if text == "exit":
        break
    
    try:
        fct = cmd.execute(conn, text)
        if isinstance(fct, types.GeneratorType):
            for variant in fct:
                print(variant)

        else:
            print(fct)

    except VQLSyntaxError as e :
        print("VQLSyntaxError: ", e.message)

    except:
        print("error syntax")

    finally:
        pass 

