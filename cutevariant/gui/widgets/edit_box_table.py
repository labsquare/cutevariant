"""
Table widget, model, and functions to create the associated data
Used in the edit boxes of sample_widget and variant_widget
"""

import operator
import re
import sqlite3

from PySide6.QtWidgets import *
from PySide6.QtCore import *
from PySide6.QtGui import *

from cutevariant.config import Config
from cutevariant.core import querybuilder
from cutevariant.core import sql

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


def classif_number_to_label(classif_config):
    """Create a dic to convert from classification number to label, based on Config values

    Args:
        classif_config (list): classification of interest in config. Ex: Config("classifications")["variants"]

    Returns:
        dict: {<classif number1> : <classif label1>, ...}

    Examples:
    >>> get_classif_dict([{'color': '#ff5500', 'description': '', 'name': 'Likely Pathogenic', 'number': 4}, {'color': '#b7b7b8', 'description': '', 'name': 'VSI', 'number': 3}])
    {"4": "Likely Pathogenic", "3": "VSI"}
    """
    dic = {}
    for c in classif_config:
        dic[c["number"]] = c["name"]
    if 0 not in dic.keys(): #default classif for new variants, has to be defined if not in config
        dic[0] = "Unassigned (0)"
    return dic

def get_variants_classif_stats(conn: sqlite3.Connection, sample_id: int):
    """For a given sample
            for each variant classification in DB
                display total number of variants

    Args:
        conn (sqlite3.Connection): 
        sample_id (int): 

    Returns:
        list: data table as a list of tuples
        list: header as a list of string
    """
    header = ["Variant classification", "Total"]
    data = sql.get_classification_stats(conn, sample_id, "variants.classification")

    classif_dict = classif_number_to_label(Config("classifications")["variants"])
    for v in data:
        v[0] = classif_dict[v[0]]
    return data, header

def get_variants_valid_stats(conn: sqlite3.Connection, sample_id: int):
    """For a given sample
            for each variant validation status in DB (genotype.classification, previously sample_has_variant.classification)
                display total number of variants

    Args:
        conn (sqlite3.Connection): 
        sample_id (int): 

    Returns:
        list: data table as a list of tuples
        list: header as a list of string
    """
    header = ["Validation status", "Total"]
    data = sql.get_classification_stats(conn, sample_id, "sample_has_variant.classification")

    classif_dict = classif_number_to_label(Config("classifications")["genotypes"])
    for v in data:
        v[0] = classif_dict[v[0]]
    return data, header


def get_deja_vu(conn: sqlite3.Connection, variant_id: int, threshold = 0):
    """For a given variant, return the list of all samples with validation status above threshold
    + some infos associated to that validation

    Args:
        conn (sqlite3.Connection):
        variant_id (int):
        threshold (int, optional):

    Returns:
        list: data table as a list of tuples
        list: header as a list of string
    """
    res, header, classif_index = sql.get_deja_vu_table(conn,variant_id, threshold)

    #fetch classif names instead of number
    genotypes_classif = classif_number_to_label(Config("classifications")["genotypes"])
    for r in res:
        r[classif_index] = genotypes_classif[r[classif_index]]
    samples_classif = classif_number_to_label(Config("classifications")["samples"])
    for r in res:
        r[1] = samples_classif[r[1]]
    return res, header


def get_variant_name_select():
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
    assert len(seps) == len(cols) - 1, "Unexpected error in get_variant_name_select()"
    imax = len(cols)
    name = pattern.split("{")[0]
    for i in range(imax):
        name += "ifnull(" + querybuilder.fields_to_sql([cols[i]])[0] + ", '')"
        if i < imax - 1:
            name += " || '" + seps[i] + "' || "
    name += pattern.split("}")[-1]
    return name