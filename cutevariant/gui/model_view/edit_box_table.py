import operator
import sqlite3
from PySide6.QtWidgets import *
from PySide6.QtCore import *
from PySide6.QtGui import *

from cutevariant.core import sql


class EditBoxTableModel(QAbstractTableModel):
    """
    To be used in edit widgets
    """
    def __init__(self, data, header):
        super().__init__()
        self._data = data
        self.header = header

    def rowCount(self, parent):
        """override"""
        return len(self._data)

    def columnCount(self, parent):
        """override"""
        return len(self._data[0])

    def data(self, index, role):
        """
        override
        center table value if it is an int
        """
        if not index.isValid():
            return None
        elif role == Qt.TextAlignmentRole:
            value = self._data[index.row()][index.column()]
            if isinstance(value, int) or isinstance(value, float):
                return Qt.AlignCenter
            else:
                return Qt.AlignVCenter
        elif role != Qt.DisplayRole:
            return None
        return self._data[index.row()][index.column()]

    def headerData(self, col, orientation, role):
        """override"""
        if orientation == Qt.Horizontal and role == Qt.DisplayRole:
            return self.header[col]
        return None

    def sort(self, col, order):
        """
        override
        sort table by given column number
        """
        self.emit(SIGNAL("layoutAboutToBeChange()"))
        self._data = sorted(self._data, key = operator.itemgetter(col))
        if order == Qt.DescendingOrder:
            self._data.reverse()
        self.emit(SIGNAL("layoutChanged()"))


class EditBoxTableView(QTableView):
    def __init__(self):
        super().__init__()
        self.setSortingEnabled(True)

        h_header = self.horizontalHeader()
        h_header.setSectionResizeMode(QHeaderView.ResizeToContents)
        h_header.setMaximumSectionSize(400)
        # if platform.system() == "Windows" and platform.release() == "10":
        #     h_header.setStyleSheet( "QHeaderView::section { border: 1px solid #D8D8D8; background-color: white; border-top: 0px; border-left: 0px;}")

        v_header = self.verticalHeader()
        v_header.setSectionResizeMode(QHeaderView.ResizeToContents)


def get_deja_vu_table(conn: sqlite3.Connection, variant_id: int, threshold = 0):
    """
    :return: the data as a list of tuples
    :return: header as a list of string
    """
    if "vaf" in sql.get_table_columns(conn, "sample_has_variant"):
        cmd = "SELECT samples.name, samples.classification, samples.tags, samples.comment, sample_has_variant.gt, sample_has_variant.vaf, sample_has_variant.classification, sample_has_variant.tags, sample_has_variant.comment"
        header = ["Sample", "Sample status", "Sample tags", "Sample comment", "GT", "VAF", "Validation status", "Validation tags", "Validation comment"]
        tags_index = [2, 7]
    else:
        cmd = "SELECT samples.name, samples.classification, samples.tags, samples.comment, sample_has_variant.gt, sample_has_variant.classification, sample_has_variant.tags, sample_has_variant.comment"
        header = ["Sample", "Sample status", "Sample tags", "Sample comment", "GT", "Validation status", "Validation tags", "Validation comment"]
        tags_index = [2, 6]

    cmd += " FROM sample_has_variant INNER JOIN samples on samples.id = sample_has_variant.sample_id WHERE sample_has_variant.classification > " + str(threshold) + " AND variant_id = " + str(variant_id)
    c = conn.cursor()
    c.row_factory = lambda cursor, row: list(row)
    res = c.execute(cmd).fetchall()

    for i in range(len(res)):
        for j in tags_index:
            if '&' in res[i][j]:
                res[i][j] = ", ".join(res[i][j].split('&'))
    return res, header