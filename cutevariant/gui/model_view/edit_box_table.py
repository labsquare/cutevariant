import operator
import re
import sqlite3
from PySide6.QtWidgets import *
from PySide6.QtCore import *
from PySide6.QtGui import *

from cutevariant.core import sql
from cutevariant.config import Config
from cutevariant.core.querybuilder import fields_to_sql

from cutevariant import LOGGER


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
            if isinstance(value, int):
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


def get_variants_classif_stats(conn: sqlite3.Connection, sample_id: int):
    """
    :return: the data as a list of tuples
    :return: header as a list of string
    """
    cmd = "SELECT variants.classification, COUNT(id) from variants INNER JOIN sample_has_variant ON variants.id = sample_has_variant.variant_id WHERE sample_id = " + str(sample_id) + " GROUP BY variants.classification"
    header = ["Variant classification", "Total"]
    c = conn.cursor()
    c.row_factory = lambda cursor, row: list(row)
    res = c.execute(cmd).fetchall()
    return res, header

def get_variants_valid_stats(conn: sqlite3.Connection, sample_id: int):
    """
    :return: the data as a list of tuples
    :return: header as a list of string
    """
    cmd = "SELECT sample_has_variant.classification, COUNT(id) from variants INNER JOIN sample_has_variant ON variants.id = sample_has_variant.variant_id WHERE sample_id = " + str(sample_id) + " GROUP BY sample_has_variant.classification"
    header = ["Variant validation", "Total"]
    c = conn.cursor()
    c.row_factory = lambda cursor, row: list(row)
    res = c.execute(cmd).fetchall()
    return res, header

def get_validated_variants_table(conn: sqlite3.Connection, sample_id: int):
    """
    Creates a table for all variants with classification > 1 for the current sample, with the columns:
    variant_name (from config)
    GT
    VAF (if it exists)
    sample_has_variant tag
    sample_has_variant comment
    variant comment

    :return: the data as a list of tuples
    :return: header as a list of string
    """
    if "vaf" in sql.get_table_columns(conn, "sample_has_variant"):
        select_fields = ", sample_has_variant.gt, sample_has_variant.vaf, sample_has_variant.tags, sample_has_variant.comment, variants.comment"
        header = ["Variant name", "GT", "VAF", "Validation Tags", "Validation Comment", "Variant Comment"]
        tags_index = [3]
    else:
        select_fields = ", sample_has_variant.gt, sample_has_variant.tags, sample_has_variant.comment, variants.comment"
        header = ["Variant name", "GT", "Validation Tags", "Validation Comment", "Variant Comment"]
        tags_index = [2]

    cmd = "SELECT " + get_variant_name_select(conn) + select_fields + " FROM variants INNER JOIN sample_has_variant on variants.id = sample_has_variant.variant_id WHERE sample_has_variant.classification >1 AND sample_has_variant.sample_id = " + str(sample_id)
    print(cmd)
    c = conn.cursor()
    c.row_factory = lambda cursor, row: list(row)
    res = c.execute(cmd).fetchall()
    #beautify tags column
    for i in range(len(res)):
        for j in tags_index:
            if '&' in res[i][j]:
                res[i][j] = ", ".join(res[i][j].split('&'))
    return res, header


def get_variant_name_select(conn: sqlite3.Connection):
    """
    :param conn: sqlite3.connect
    :param config: config file to fetch variant name pattern
    :return: a string containing the fields for a SELECT fetching variant name properly

    example:
    input: Config("variables")["variant_name_pattern"] = {'tnomen':'cnomen'}
    return: "`variants.tnomen`|| ":" || `variants.cnomen``"
    """
    pattern = Config("variables")["variant_name_pattern"]
    if pattern == None:
        pattern = "{chr}:{pos}-{ref}>{alt}"
    if "{" not in pattern:
        LOGGER.warning(
            "Variants are named without using any data column. All variants are going to be named the same. You should edit Settings > Variables > variant_name_pattern"
        )
    cols = re.findall("\{(.*?)\}", pattern)
    seps = re.findall("\}(.*?)\{", pattern)
    assert len(seps) == len(cols) - 1, "Unexpected error in get_variant_name_select(args)"
    imax = len(cols)
    name = pattern.split("{")[0]
    for i in range(imax):
        name += "ifnull(" + fields_to_sql([cols[i]])[0] + ", '')"
        if i < imax - 1:
            name += " || '" + seps[i] + "' || "
    name += pattern.split("}")[-1]
    return name