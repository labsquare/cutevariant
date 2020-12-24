
from PySide2 import QtCore, QtWidgets


def pytest_configure(config):
	QtWidgets.QApplication()

def pytest_sessionstart(session):
	pass
