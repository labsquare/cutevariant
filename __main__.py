from PySide2.QtWidgets import *
from PySide2.QtCore import *
import sys
import os
import sqlalchemy
from sqlalchemy import text
from cutevariant.core.importer import import_file, open_db
from cutevariant.gui.variantview import *

if __name__ == "__main__":

    path = "/tmp/cutevariant.db"
    if os.path.exists(path):
        os.remove(path)

    import_file("exemples/test.csv", path)

    open_db(path)

    print(Variant)







