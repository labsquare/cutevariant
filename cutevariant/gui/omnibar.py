from PySide2.QtCore import *
from PySide2.QtWidgets import *
from PySide2.QtGui import *

from cutevariant.core.query import Query
from cutevariant.gui.ficon import FIcon
import re


class OmniBar(QLineEdit):

    changed = Signal()

    def __init__(self):
        super().__init__()
        self.setMaximumWidth(400)
        self.setPlaceholderText(qApp.tr("chr3:100-100000"))
        self.action = self.addAction(FIcon(0xF349, "black"), QLineEdit.TrailingPosition)

        self.returnPressed.connect(self.changed)
        self._query = None

    def to_coordinate(self):

        match = re.search(r"(chr\d\d?):(\d+)-(\d+)", self.text())

        if match:
            return (match[1], int(match[2]), int(match[3]))
        else:
            return None

    @property
    def query(self):

        coord = self.to_coordinate()
        if coord:
            self._query.filter = {
                "AND": [
                    {"field": "chr", "operator": "=", "value": coord[0]},
                    {"field": "pos", "operator": ">", "value": coord[1]},
                    {"field": "pos", "operator": "<", "value": coord[2]},
                ]
            }

        return self._query

    @query.setter
    def query(self, query: Query):
        self._query = query
