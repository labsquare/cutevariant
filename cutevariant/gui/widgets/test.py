from PySide2.QtWidgets import *
from PySide2.QtCore import *
from PySide2.QtGui import *

from PySide2.QtQuick import QQuickView


import sys

# Essaie material si tu veux ...
sys.argv += ["--style", "Fusion"]

app = QApplication(sys.argv)

w = QQuickView("test.qml")

w.show()


app.exec_()
