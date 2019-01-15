from PySide2.QtWidgets import *
from PySide2.QtCore import *
from PySide2.QtGui import *


from .abstractquerywidget import AbstractQueryWidget
from cutevariant.core import Query
from cutevariant.core import sql



class VqlEditor(AbstractQueryWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Columns")
        self.text_edit = QPlainTextEdit()
        main_layout = QVBoxLayout()

        main_layout.addWidget(self.text_edit)
        self.setLayout(main_layout)

        self.text_edit.textChanged.connect(self.changed)



    def setQuery(self, query: Query):
        """ Method override from AbstractQueryWidget"""
        print("salut")
        self.query = query
        self.text_edit.setPlainText(self.query.to_vql())

    def getQuery(self):
        """ Method override from AbstractQueryWidget"""
        query = self.query.from_vql(self.text_edit.toPlainText())
        

        return self.query
