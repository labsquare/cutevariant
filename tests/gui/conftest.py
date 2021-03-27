
from PySide2 import QtCore, QtWidgets


def pytest_configure(config):
    QtWidgets.QApplication()
    qApp.setOrganizationName("labsquare")
    qApp.setApplicationName("cutevariant")


def pytest_sessionstart(session):
    pass
