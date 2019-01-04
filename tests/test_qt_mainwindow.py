from PySide2.QtWidgets import * 
from PySide2.QtCore import * 




def test_hello(qtbot):
    widget = QLabel("Hello!")
    #qtbot.addWidget(widget)

    # click in the Greet button and make sure it updates the appropriate label
    #qtbot.mouseClick(widget.button_greet, QtCore.Qt.LeftButton)

    assert widget.text() == "Hello!"