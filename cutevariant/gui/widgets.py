from PySide2.QtCore import *
from PySide2.QtWidgets import *
import sys


class BrowseFileEdit(QWidget):
    def __init__(self, parent=None):
        super(BrowseFileEdit, self).__init__(parent)
        self.edit = QLineEdit()
        self.button = QPushButton("Browse")
        self.main_layout = QHBoxLayout()

        self.main_layout.addWidget(self.edit)
        self.main_layout.addWidget(self.button)
        self.main_layout.setContentsMargins(0, 0, 0, 0)

        self.setLayout(self.main_layout)

        self.button.clicked.connect(self.browse)

    def browse(self):
        filename = QFileDialog.getOpenFileName(self)[0]
        if filename:
            self.edit.setText(filename)


# app = QApplication(sys.argv)


# w = BrowseFileEdit()

# w.show()

# app.exec()
