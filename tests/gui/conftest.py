from PySide6 import QtCore, QtWidgets


def pytest_configure(config):
    QtWidgets.QApplication()
    qApp.setOrganizationName("labsquare")
    qApp.setApplicationName("cutevariantTest")


def pytest_sessionstart(session):
    pass
