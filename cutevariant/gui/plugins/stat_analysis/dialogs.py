# Standard imports
import os

import sqlite3

import PySide6

import plotly.express as px

# Qt imports
from PySide6.QtWidgets import (
    QVBoxLayout,
    QFormLayout,
    QTableView,
    QComboBox,
    QGroupBox,
    QLabel,
    QSizePolicy,
    QSpacerItem,
    QDialogButtonBox,
)
from PySide6.QtCore import Qt, QModelIndex

# Custom imports
from cutevariant.gui.ficon import FIcon
from cutevariant.gui.plugin import PluginDialog
from cutevariant.core import sql

import typing
from functools import cmp_to_key, partial
import time
import copy
import re

# Qt imports
from PySide6.QtWidgets import *
from PySide6.QtCore import *
from PySide6.QtGui import *


# Custom imports
from cutevariant.core import sql
from cutevariant.gui import plugin, FIcon, style
from cutevariant.gui.widgets import (
    ChoiceWidget,
    create_widget_action
)

from cutevariant.gui.widgets.choice_widget import ChoiceWidget
from cutevariant import LOGGER

from cutevariant.gui import FormatterDelegate
from cutevariant.gui.formatters.cutestyle import CutestyleFormatter


from PySide6.QtWidgets import *
import sys
from functools import partial
from PySide6.QtGui import QIcon

import pandas as pd
import numpy as np
from pandas import *
import seaborn as sns
import matplotlib.pyplot as plt
import dash_bio

class StatAnalysisDialog(PluginDialog):
    ENABLE = True

    def __init__(self, conn=None, parent=None):
        super().__init__(parent)
        self.setModal(False)

        self.conn = conn
        self.dico_tagbrut_tagsplit = {}
        self.dict_matrix_all_mutation={}
        self.TAG_SEPARATOR = "&"
        self.gt=None
        self.hlayout= QHBoxLayout()
        self.df=None
        self.brut_matrix=[]
        self.matrix=[]
        self.all_gnomen=[]
        self.row_matrix_gnomen=[]
        self.name_matrix=[]
        self.variant_id = []
        self.sample_id = []
        self.data_frame=[]#a enlever
        self.test=QLineEdit()
        self.data_dict_df=None

        self.all_tag_split=ChoiceWidget()

        self.hlayout.addWidget(self.all_tag_split)
        self.hlayout.addWidget(self.test)

        self.setLayout(self.hlayout)
        self.setWindowTitle("stat")

        self._load_tagsplit()
        self.all_tag_split.accepted.connect(self.get_data_between_tag_sample_as_variant)

    def _load_tagsplit(self):
        all_value=[]
        self.tag_brut = [i["tags"] for i in sql.get_samples(self.conn)]
        print(self.tag_brut)
        for x in self.tag_brut:
            if x == None or x == '' or x.isspace():
                # Samples in DB can have a NULL or empty tag String. Do not put those in the tag selector.
                pass
            else:
                self.valeur = x.split(self.TAG_SEPARATOR)
                if '' in self.valeur:
                    self.valeur.remove('')
                print(self.valeur)
                self.dico_tagbrut_tagsplit[x] = self.valeur
                all_value = all_value+self.valeur


        for i in self.keep_sorted_unique_values(all_value):
            self.all_tag_split.add_item(FIcon(0xF04FD),i)

    def keep_sorted_unique_values(self, check_list:list):
        """
        returns an ordered list keeping only unique values
        """
        check_list = list(set(check_list))
        check_list.sort()
        return check_list

    def get_data_between_tag_sample_as_variant(self):
        group_name = self.group_select()
        _data = [i for i in sql.get_samples(conn)]
        for _data_dico in _data:
            for _item_group_name in group_name:
                if _data_dico['tags'] == _item_group_name['name']:
                    id=str(_data_dico["id"])
                    self.sample_id.append(_data_dico["id"])
                    self.name_matrix.append(_data_dico['name']+_data_dico['tags'])

        self.data_dict_df = [i for i in sql.get_tag_sample_has_variant(conn, self.sample_id)]

        self.load_gnomen_list()
        self.fill_matrix_True_or_False_mutate()
        df=self.create_data_frame()
        self.draw_heatmap(df)

    def init_matrix(self):
        for i in self.all_gnomen:
            self.brut_matrix.append([0 for i in self.sample_id])

    def fill_matrix_True_or_False_mutate(self):
        self.init_matrix()
        for index,i in enumerate(self.sample_id):
            for index2,j in enumerate(self.all_gnomen):
                for item_dico_join in self.data_dict_df:
                    if item_dico_join['gnomen'] == j and item_dico_join['sample_id'] == i:
                        if  item_dico_join['gt'] >= 1:
                            self.brut_matrix[index2][index] =1
                        # print(self.brut_matrix)

                if any(self.brut_matrix[index2]):
                    self.row_matrix_gnomen.append(j)
                    self.matrix.append(self.brut_matrix[index2])

    def fill_matrix_count_variants(self):
        self.init_matrix()
        for index,i in enumerate(self.sample_id):
            for index2,j in enumerate(self.all_gnomen):
                for item_dico_join in self.data_dict_df:
                    if item_dico_join['gnomen'] == j and item_dico_join['sample_id'] == i:
                        if  item_dico_join['gt'] >= 1:
                            self.brut_matrix[index2][index] +=1
                        # print(self.brut_matrix)

                if any(self.brut_matrix[index2]):
                    self.row_matrix_gnomen.append(j)
                    self.matrix.append(self.brut_matrix[index2])



    def _gt_join_sample_has_variant(self, i:str,j:str) :
        for item_dico_join in self.data_dict_df:
            if item_dico_join['gnomen'] == j and item_dico_join['sample_id'] == i :
                self.gt=item_dico_join['gt']
        return self.gt

    def _item_sample_has_variant_join(self, gnomen:str):
        for item_dico_join in self.data_dict_df:
            if item_dico_join['gnomen'] == j and item_dico_join['sample_id'] == i :
                return item_dico_join

    def load_gnomen_list(self):
        for item_dico_join in self.data_dict_df:
            self.all_gnomen.append(item_dico_join['gnomen'])
        self.all_gnomen=self.keep_sorted_unique_values(self.all_gnomen)

        return self.all_gnomen

    def keep_sorted_unique_values(self, check_list:list):
        """
        returns an ordered list keeping only unique values
        """
        check_list = list(set(check_list))
        check_list.sort()
        return check_list

    def group_select(self):
        if self.all_tag_split.checked() == True:
            my_generator_tag = self.all_tag_split.selected_items()
            result_list_tag = list(my_generator_tag)
            return result_list_tag

    def create_data_frame(self):
        self.df = pd.DataFrame(self.get_matrix(),
                          index=self.get_row_matrix(),
                          columns=self.get_name_matrix_and_load())

        return self.df

    def draw_heatmap(self,df:DataFrame):
        g = sns.clustermap(df, row_cluster=True, col_cluster=False,cmap="mako_r")

        g.savefig('C:/Users/HAMEAUEL/Documents/Db cute/row_cluster_true.png', dpi=100)

    def get_data_frame(self):
        return self.df

    def get_matrix(self):
        return self.matrix

    def get_variant_id(self):
        return self.variant_id

    def get_row_matrix(self):
        return self.row_matrix_gnomen

    def get_name_matrix_and_load(self):
        return self.name_matrix

    def get_sample_id(self):
        return self.sample_id

    def get_all_mutation(self):
        return self.dict_matrix_all_mutation

    def get_all_gnomen(self):
        """je vais prendre tout les samples id qui ont le groupe select by user"""
        # self.all_gnomen
        return self.all_gnomen

    def get_dict_join(self):
        return self.data_dict_df

if __name__ == "__main__":

    if os.path.exists("C:/Users/HAMEAUEL/Documents/Db cute/test_col4.svg"):
        os.remove("C:/Users/HAMEAUEL/Documents/Db cute/test_col4.svg")

    from PySide6.QtWidgets import QApplication
    import sys

    app = QApplication(sys.argv)
    conn = sql.get_sql_connection("C:/Users/HAMEAUEL/Documents/Db cute/Big_Ech.db")
    conn.row_factory = sqlite3.Row

    dialog = StatAnalysisDialog(conn)
    dialog.show()
    app.exec()






