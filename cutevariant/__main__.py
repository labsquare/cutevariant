# Standard imports
import sys
from PySide2.QtWidgets import *
from PySide2.QtCore import *

# Custom imports
from cutevariant.gui import MainWindow

def main():
    """The main routine."""

    # Define the names of the organization and the application
    # The value is used by the QSettings class when it is constructed using
    # the empty constructor. This saves having to repeat this information
    # each time a QSettings object is created.
    # The default scope is QSettings::UserScope
    QCoreApplication.setOrganizationName("labsquare")
    QCoreApplication.setApplicationName("cutevariant")

    app = QApplication(sys.argv)
    w = MainWindow()
    w.show()
    app.exec_()


if __name__ == "__main__":

    main()
