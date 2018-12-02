from PySide2.QtWidgets import *
from PySide2.QtCore import *
import sys
import os

import sqlalchemy

from cutevariant.core.importer import import_file
from cutevariant.core.model import create_session, Variant, select_variant
from cutevariant.gui.variantview import * 


if __name__ == "__main__":
    print("test")

    path = "/tmp/cutevariant.db"
    if os.path.exists(path):
        os.remove(path)

    engine = sqlalchemy.create_engine(f"sqlite:///{path}", echo=False)


    import_file("exemples/test.csv", engine)

    app = QApplication(sys.argv)
    w = VariantView()
    w.load(engine)

    w.show()

    app.exec_()