from PySide2.QtWidgets import *
from PySide2.QtCore import *
import sys
import os
from cutevariant.gui import MainWindow
from cutevariant.gui.wizard.projetwizard import ProjetWizard


import sqlite3


if __name__ == "__main__":

    app = QApplication(sys.argv)

    w = MainWindow()

    w.show()

    # w = MainWindow()

    # w.show()

    app.exec_()
