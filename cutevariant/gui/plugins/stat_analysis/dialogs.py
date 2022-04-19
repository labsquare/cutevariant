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
from scipy.stats import chi2_contingency
from scipy.stats import chisquare
from scipy.stats import wilcoxon
class StatAnalysisDialog(PluginDialog):
    ENABLE = True

    def __init__(self, conn=None, parent=None):
        super().__init__(parent)
        self.setModal(False)
        self.conn = conn
        self.dico_tagbrut_tagsplit = {}
        self.dico_p_value_gene_group={}
        self.TAG_SEPARATOR = "&"
        self.gt=None
        self.vlayout= QVBoxLayout()
        self.df=None
        self.df_group1=None
        self.df_group2=None
        self.brut_matrix=[]
        self.all_gnomen=[]
        self.matrix=[]
        self.matrix_group1=[]
        self.matrix_group2=[]
        self.df_ki_2=pd.DataFrame()
        self.df_wilcoxon=pd.DataFrame()
        self.row_matrix_gnomen=[]
        self.row_matrix_group1_gnomen=[]
        self.row_matrix_group2_gnomen=[]
        self.name_matrix=[]
        self.name_matrix_group1=[]
        self.name_matrix_group2=[]
        self.sample_id = []
        self.sample_id_group1 = []
        self.sample_id_group2 = []
        self.group_name_select=[]
        self.apply_stat=QPushButton("Apply")
        self.data_dict_df=None
        self.cut_off_pourcentage=None

        """First part choix both groups"""
        self.hlayout_first_part=QHBoxLayout()
        self.spacer=QSpacerItem(80,10)
        self.all_tag_split_left=QComboBox()
        self.all_tag_split_right=QComboBox()

        self.hlayout_first_part.addWidget(self.all_tag_split_left)
        self.hlayout_first_part.addSpacerItem(self.spacer)
        self.hlayout_first_part.addWidget(self.all_tag_split_right)

        """Filtrers part"""
        self.filtrers=QComboBox()
        self.filtrers.addItem("Basic Filtrer")
        self.filtrers.addItem("Bio Filtrer")
        self.filtrers.addItem("Import Filtrer")

        """Field part"""
        self.fields=QComboBox()
        self.fields.addItem("Import")


        """Calculus part"""
        self.calculus=QComboBox()
        self.calculus.addItem("gnomen mutant or not")
        self.calculus.addItem("Count variant by mutant")

        """Stat analysis part"""
        self.stat=QComboBox()
        self.stat.addItem("Khi2")
        self.stat.addItem("Wilcoxon")


        """Cutt-off part"""
        validator=QIntValidator(0,100)
        self.cutt_off=QLineEdit()
        self.cutt_off.setValidator(validator)
        self.cutt_off.textChanged.connect(self.check_cut_off)
        self.flayout=QFormLayout()
        self.flayout.addRow(self.tr("p-value <"), self.cutt_off)

        """Range select"""
        self.range_sample=QComboBox()
        self.range_sample.addItem("All")
        self.range_sample.addItem("Mutant")
        self.range_sample.addItem("WT")
        self.flayout.addRow(self.tr("Range analyse"), self.range_sample)

        """Question save heatmap"""
        self.stockage=QComboBox()
        self.stockage.addItem("No")
        self.stockage.addItem("Yes")
        self.flayout.addRow(self.tr("Do you want save the Heatmap and matrix ?"), self.stockage)

        """Pop or not dialog for whrite name heatmap save"""
        self.stockage.currentIndexChanged.connect(self.on_curentIndexChanged)

        """Heatmap main"""
        self.central_widget=QWidget(self)
        self.central_widget.setVisible(False)

        """Skeleton part"""
        self.vlayout.addLayout(self.hlayout_first_part)
        self.vlayout.addWidget(self.filtrers)
        self.vlayout.addWidget(self.fields)
        self.vlayout.addWidget(self.calculus)
        self.vlayout.addWidget(self.stat)
        self.vlayout.addWidget(self.stat)
        self.vlayout.addLayout(self.flayout)
        self.vlayout.addWidget(self.central_widget)
        self.vlayout.addWidget(self.apply_stat)

        self.setLayout(self.vlayout)
        self.setWindowTitle("Stat analysis")

        self._load_tagsplit()
        self.apply_stat.clicked.connect(self.get_data_between_tag_sample_as_variant)

    def on_curentIndexChanged(self):
        if self.stockage.currentIndex() == 1:
            self.stockage_name = QLineEdit()
            self.flayout.addRow(self.tr("File name"), self.stockage_name)

        elif self.stockage.currentIndex() == 0:
            if self.flayout.getItemPosition(3) == (1, PySide6.QtWidgets.QFormLayout.ItemRole.FieldRole) :
                self.flayout.removeRow(3)

            else :
                pass

    def _load_tagsplit(self):
        all_value=[]
        self.tag_brut = [i["tags"] for i in sql.get_samples(self.conn)]
        for x in self.tag_brut:
            if x == None or x == '' or x.isspace():
                # Samples in DB can have a NULL or empty tag String. Do not put those in the tag selector.
                pass
            else:
                self.valeur = x.split(self.TAG_SEPARATOR)
                if '' in self.valeur:
                    self.valeur.remove('')
                self.dico_tagbrut_tagsplit[x] = self.valeur
                all_value = all_value+self.valeur


        for i in self.keep_sorted_unique_values(all_value):
            self.all_tag_split_left.addItem(FIcon(0xF04FD),i)
            self.all_tag_split_right.addItem(FIcon(0xF04FD),i)

    def keep_sorted_unique_values(self, check_list:list):
        """
        returns an ordered list keeping only unique values
        """
        check_list = list(set(check_list))
        check_list.sort()
        return check_list

    def group_select(self):
        self.group_selected={"tag_group1":self.all_tag_split_left.currentText(),
                             "tag_group2":self.all_tag_split_right.currentText()
                             }
        return self.group_selected

    def get_data_between_tag_sample_as_variant(self):
        _data = [i for i in sql.get_samples(conn)]
        self.sample_id.clear()
        self.sample_id_group1.clear()
        self.sample_id_group2.clear()

        """Warning for a global matrix change group1&2 by just group"""
        for key, value in self.group_select().items():
            for _data_dico in _data:
                if value == _data_dico['tags']:
                    self.sample_id_group1.append(_data_dico["id"])
                    self.name_matrix_group1.append(_data_dico['name']+_data_dico['tags'])

                elif value == _data_dico['tags']:
                    self.sample_id_group2.append(_data_dico["id"])
                    self.name_matrix_group2.append(_data_dico['name']+_data_dico['tags'])

        """Create 2 matrix for comparaison"""
        self.data_dict_df_group1 = [i for i in sql.get_tag_sample_has_variant(conn, self.sample_id_group1, self.range_sample.currentText())]
        self.data_dict_df_group2 = [i for i in sql.get_tag_sample_has_variant(conn, self.sample_id_group2, self.range_sample.currentText())]

        """For Test stat with only one matrix"""
        # self.data_dict_df = [i for i in sql.get_tag_sample_has_variant(conn, self.sample_id, 'mutant')]

        self.load_gnomen_list(self.data_dict_df_group1)

        if self.calculus.currentText() == "gnomen mutant or not":
            self.fill_matrix_True_or_False_mutate(self.data_dict_df_group1, self.sample_id_group1, 1)
            self.fill_matrix_True_or_False_mutate(self.data_dict_df_group2, self.sample_id_group2, 2)

        elif self.calculus.currentText() == "Count variant by mutant":
            self.fill_matrix_count_variants(self.data_dict_df_group1, self.sample_id_group1, 1)
            self.fill_matrix_count_variants(self.data_dict_df_group2, self.sample_id_group1, 2)

        self.create_data_frame('1')
        self.create_data_frame('2')

        if self.stat.currentText() == "Khi2":
            self.draw_heatmap(self.ki_2_contigency())

        elif self.stat.currentText() == "Wilcoxon":
            self.test_wilcoxon()
            self.draw_heatmap(self.test_wilcoxon())

    def init_matrix(self, sample_id:list):
        for i in self.all_gnomen:
            self.brut_matrix.append([0 for i in sample_id])

    def fill_matrix_True_or_False_mutate(self, data:list, sample_id:list, number_matrix:int):
        print("dedans")
        self.brut_matrix.clear()
        self.init_matrix(sample_id)
        for index,i in enumerate(sample_id):
            for index2,j in enumerate(self.all_gnomen):
                for item_dico_join in data:
                    if item_dico_join['gnomen'] == j and item_dico_join['sample_id'] == i:
                        if  item_dico_join['gt'] >= 1:
                            self.brut_matrix[index2][index] =1

        """Parcour les lignes de la matrice brut et selon si c'est une matrice de comparaison du ki2 ou une globale ,
        soit on ajoute toute les lignes soit on ajoute seulement celle qui ont une valeur sup à 1 """
        for index2, j in enumerate(self.all_gnomen):
            if number_matrix == 0:
                if any(self.brut_matrix[index2]):
                    self.row_matrix_gnomen.append(j)
                    self.matrix.append(self.brut_matrix[index2])

            elif number_matrix == 1:
                self.row_matrix_group1_gnomen.append(j)
                self.matrix_group1.append(self.brut_matrix[index2])

            elif number_matrix == 2:
                self.row_matrix_group2_gnomen.append(j)
                self.matrix_group2.append(self.brut_matrix[index2])

            elif number_matrix != 1 and number_matrix != 2 and number_matrix != 0:
                print("Erreur du nombre de la matrix")

    def fill_matrix_count_variants(self,data:list, sample_id:list, number_matrix:int):

        self.brut_matrix.clear()
        self.init_matrix(sample_id)
        for index,i in enumerate(sample_id):
            for index2,j in enumerate(self.all_gnomen):
                for item_dico_join in data:
                    if item_dico_join['gnomen'] == j and item_dico_join['sample_id'] == i:
                        if  item_dico_join['gt'] >= 1:
                            self.brut_matrix[index2][index] +=1

        """Parcour les lignes de la matrice brut et selon si c'est une matrice de comparaison du ki2 ou une globale ,
        soit on ajoute toute les lignes soit on ajoute seulement celle qui ont une valeur sup à 1 """
        for index2, j in enumerate(self.all_gnomen):
            if number_matrix == 0:
                if any(self.brut_matrix[index2]):
                    self.row_matrix_gnomen.append(j)
                    self.matrix.append(self.brut_matrix[index2])

            elif number_matrix == 1:
                self.row_matrix_group1_gnomen.append(j)
                self.matrix_group1.append(self.brut_matrix[index2])

            elif number_matrix == 2:
                self.row_matrix_group2_gnomen.append(j)
                self.matrix_group2.append(self.brut_matrix[index2])

            elif number_matrix != 1 and number_matrix != 2 and number_matrix != 0:
                print("Erreur du nombre de la matrix")

        #
        # self.init_matrix()
        # """remplir matrice"""
        # for index,i in enumerate(self.sample_id):
        #     for index2,j in enumerate(self.all_gnomen):
        #         for item_dico_join in self.data_dict_df:
        #             if item_dico_join['gnomen'] == j and item_dico_join['sample_id'] == i:
        #                 if  item_dico_join['gt'] >= 1:
        #                     self.brut_matrix[index2][index] +=1
        #                 # print(self.brut_matrix)
        #
        # for index2,j in enumerate(self.all_gnomen):
        #     if any(self.brut_matrix[index2]):
        #         self.row_matrix_gnomen.append(j)
        #         self.matrix.append(self.brut_matrix[index2])

    def check_cut_off(self):
        if self.cutt_off.text() == '':
            self.cut_off_pourcentage=0
        else:
            self.cut_off_pourcentage=int(self.cutt_off.text())

        if self.cut_off_pourcentage > 100:
            """Error message"""
            print("cut_off invalide")
        elif self.cut_off_pourcentage >= 100 or self.cut_off_pourcentage == '':
            pass

        return self.cut_off_pourcentage
        # TODO : add error message for globale error

    # def ki_2_(self, cut_off_pourcentage:int):
    #     """ANTHO normaliser un dataframe pour que la somme de chaque colonne soit identique : df2 = df.mul(df.sum.mean() / df.sum(), axis = 1)"""
    #     cut_off_pourcentage=cut_off_pourcentage/100
    #     data_ki_2=[]
    #     gnomen_ki_2=[]
    #     """On peut utiliser le meme row de collone pour ouvrir les donées de la matrices"""
    #     """"""
    #     for index, gnomen in enumerate(self.get_row_matrix("1")):
    #         gene_resul=None
    #
    #         group1=self.df_group1.iloc[[index]]
    #         group1_array=array(self.df_group1.iloc[index])
    #
    #         group2=self.df_group2.iloc[[index]]
    #         group2_array=array(self.df_group2.iloc[index])
    #         if group1_array.tolist() == group2_array.tolist() :
    #             """tupple pour gerer l'erreur ou les rows sont identifique https://stackoverflow.com/questions/65225316/python-pingouin-valueerror-zero-method-wilcox-and-pratt-do-not-work-if"""
    #             gene_resul=(999,1)
    #
    #
    #         else:
    #             gene_resul=chisquare([group1_array], [group2_array])
    #         print(gene_resul)
    #         if gene_resul[1] <= cut_off_pourcentage:
    #             print(gnomen, "///", gene_resul)
    #             group_concat_line=pd.concat([group1,group2], axis=1)
    #             self.df_ki_2=pd.concat([self.df_ki_2,group_concat_line],axis=0)
    #             titre="gene//"+gnomen
    #             result="p-value de "+str(gene_resul[1])
    #             self.dico_p_value_gene_group[titre]=result
    #
    #     return self.df_ki_2
    # def fill_matrix_VAF_variants(self):
    #     ##On a pas fait le filtre sur les gt -1 ou 0 dans la requette SQL il faut donc gerer le gt-1 ou on a None en vaf ad et dp
    #     self.init_matrix()
    #     for index,i in enumerate(self.sample_id):
    #         for index2,j in enumerate(self.all_gnomen):
    #             for item_dico_join in self.data_dict_df:
    #                 var_id=str(item_dico_join['variant_id'])
    #                 if item_dico_join['gnomen'] == j and item_dico_join['sample_id'] == i:
    #                     if item_dico_join['vaf'] == None:
    #                         if item_dico_join['ad'] != None and item_dico_join['dp'] != None :
    #                             self.brut_matrix[index2][index] = self.get_calcul_VAF(item_dico_join['ad'],item_dico_join['dp'])
    #                     elif item_dico_join['vaf'] != None:
    #                         self.brut_matrix[index2][index] = item_dico_join['vaf']
    #                     # print(str(item_dico_join['variant_id']))
    #
    #             self.row_matrix_gnomen.append(var_id+"//"+j)
    #             self.matrix.append(self.brut_matrix[index2])

    def mouseDoubleClickEvent(self, event:PySide6.QtGui.QMouseEvent) :
        """
        For debugging purposes
        """
        print(type(self.check_cut_off()))

    def ki_2_contigency(self):
        """Pour normaliser un dataframe pour que la somme de chaque colonne soit identique : df2 = df.mul(df.sum.mean() / df.sum(), axis = 1)"""
        cut_off_pourcentage=self.check_cut_off()/100
        data_ki_2=[]
        gnomen_ki_2=[]
        """On peut utiliser le meme row de collone pour ouvrir les donées de la matrices"""
        for index, gnomen in enumerate(self.get_row_matrix("1")):
            gene_resul=None

            group1=self.df_group1.iloc[[index]]
            group1_array=array(self.df_group1.iloc[index])

            group2=self.df_group2.iloc[[index]]
            group2_array=array(self.df_group2.iloc[index])

            mutation_name = ['group1' for i in group1_array] + ['group2' for a in group2_array]
            mutation_data = [i for i in group1_array] + [a for a in group2_array]

            df = pd.DataFrame({'mutation_name': mutation_name, 'mutation_data': mutation_data})
            # df=pd.DataFrame([[result_group1[1],result_group2[1]],[result_group1[0],result_group2[0]]],['Mutate','WT'])
            contigency = pd.crosstab(df['mutation_name'], df['mutation_data'])

            if group1_array.tolist() == group2_array.tolist() :
                """tupple pour gerer l'erreur ou les rows sont identifique https://stackoverflow.com/questions/65225316/python-pingouin-valueerror-zero-method-wilcox-and-pratt-do-not-work-if"""
                gene_resul=(999,1)

            else:
                print(contigency)
                c, p, dof, expected=chi2_contingency(contigency)

            if p <= cut_off_pourcentage:
                group_concat_line=pd.concat([group1,group2], axis=1)
                self.df_ki_2=pd.concat([self.df_ki_2,group_concat_line],axis=0)
                titre="gene//"+gnomen
                result=p
                self.dico_p_value_gene_group[titre]=result
                print("yo")

        return self.df_ki_2

    def test_wilcoxon(self):
        """Pour normaliser un dataframe pour que la somme de chaque colonne soit identique : df2 = df.mul(df.sum.mean() / df.sum(), axis = 1)"""
        cut_off_pourcentage=self.check_cut_off()/100
        data_wilcoxon=[]
        gnomen_wilcoxon=[]
        """On peut utiliser le meme row de collone pour ouvrir les donées de la matrices"""
        """"""
        for index, gnomen in enumerate(self.get_row_matrix("1")):
            gene_resul=None

            group1=self.df_group1.iloc[[index]]
            group1_for_array=self.df_group1.iloc[index]
            group1_array=array(group1_for_array)

            group2=self.df_group2.iloc[[index]]
            group2_for_array=self.df_group2.iloc[index]
            group2_array=array(group2_for_array)
            # print(group1_array.tolist(),"ENFOIRE!!!!!!!!!!!!!!")
            if group1_array.tolist() == group2_array.tolist() :
                """tupple pour gerer l'erreur ou les rows sont identifique https://stackoverflow.com/questions/65225316/python-pingouin-valueerror-zero-method-wilcox-and-pratt-do-not-work-if"""
                gene_resul=(999,1)

            else:
                gene_resul=wilcoxon(group1_array, group2_array)
            print(gnomen, "///", gene_resul)
            if gene_resul[1] <= cut_off_pourcentage:
                group_concat_line=pd.concat([group1,group2], axis=1)
                self.df_wilcoxon=pd.concat([self.df_wilcoxon,group_concat_line],axis=0)
                titre="gene//"+gnomen
                result="p-value de "+str(gene_resul[1])
                self.dico_p_value_gene_group[titre]=result

        return self.df_wilcoxon

    def _gt_join_sample_has_variant(self, i:str,j:str) :
        for item_dico_join in self.data_dict_df:
            if item_dico_join['gnomen'] == j and item_dico_join['sample_id'] == i :
                self.gt=item_dico_join['gt']
        return self.gt

    def _item_sample_has_variant_join(self, gnomen:str):
        for item_dico_join in self.data_dict_df:
            if item_dico_join['gnomen'] == j and item_dico_join['sample_id'] == i :
                return item_dico_join

    def load_gnomen_list(self,data:list):
        for item_dico_join in data:
            self.all_gnomen.append(item_dico_join['gnomen'])
        self.all_gnomen=self.keep_sorted_unique_values(self.all_gnomen)

        return self.all_gnomen

    def create_data_frame(self, matrix_number:str):
        if matrix_number == '0':
            self.df = pd.DataFrame(self.get_matrixs(matrix_number),
                              index=self.get_row_matrix(matrix_number),
                              columns=self.get_name_matrix(matrix_number))
            self.df.to_csv("C:/Users/HAMEAUEL/Documents/Db cute/matrix"+matrix_number+".txt", sep="\t", encoding="utf-8", index=True)
            return self.df

        if matrix_number == '1':
            self.df_group1 = pd.DataFrame(self.get_matrixs(matrix_number),
                              index=self.get_row_matrix(matrix_number),
                              columns=self.get_name_matrix(matrix_number))
            self.df_group1.to_csv("C:/Users/HAMEAUEL/Documents/Db cute/matrix"+matrix_number+".txt", sep="\t", encoding="utf-8", index=True)
            return self.df_group1

        if matrix_number == '2':
            self.df_group2 = pd.DataFrame(self.get_matrixs(matrix_number),
                              index=self.get_row_matrix(matrix_number),
                              columns=self.get_name_matrix(matrix_number))
            self.df_group2.to_csv("C:/Users/HAMEAUEL/Documents/Db cute/matrix"+matrix_number+".txt", sep="\t", encoding="utf-8", index=True)
            return self.df_group2

    def draw_heatmap(self, df:DataFrame):
        print(self.ki_2_contigency())
        df = df.drop_duplicates()
        current_heatmap = sns.clustermap(df, row_cluster=False, col_cluster=True,cmap="mako_r")
        current_heatmap.savefig("current_heatmap.svg", dpi=100)
        current_picture=QImage()

        if self.stockage.currentText() == "Yes" :
            if os.path.exists(self.stockage_name.text()+".svg"):
                os.remove(self.stockage_name.text()+".svg")
                print("Warning this name exist so the old are delete")
                # TODO : error message
            current_heatmap.savefig(self.stockage_name.text()+".svg", dpi=100)

        self.heatmap=QLabel(self.central_widget)
        self.heatmap.setPixmap(QPixmap("current_heatmap.svg"))


    def error_message(self):
        print("uu")



    def get_data_frames(self, data_frame_number:str):
        if data_frame_number == '0':
            return self.df

        if data_frame_number == '1':
            return self.df_group1

        if data_frame_number == '2':
            return self.df_group2

    def get_row_matrix(self, row_matrix_number:str):
        if row_matrix_number == '0':
            return self.row_matrix_gnomen

        if row_matrix_number == '1':
            return self.row_matrix_group1_gnomen

        if row_matrix_number == '2':
            return self.row_matrix_group2_gnomen

    def get_matrixs(self, matrix_number:str):
        if matrix_number == '0':
            return self.matrix

        if matrix_number == '1':
            return self.matrix_group1

        if matrix_number == '2':
            return self.matrix_group2

        if matrix_number == 'all':
            return self.matrix, self.matrix_group1, self.matrix_group2

    def get_sample_id(self):
        return self.sample_id

    def get_name_matrix(self, name_matrix_group:str):
        if name_matrix_group == '0':
            return self.name_matrix

        if name_matrix_group == '1':
            return self.name_matrix_group1

        if name_matrix_group == '2':
            return self.name_matrix_group2

    def get_all_gnomen(self):
        """je vais prendre tout les samples id qui ont le groupe select by user"""
        # self.all_gnomen
        return self.all_gnomen

    def get_dict_join(self):
        return self.data_dict_df

    def get_df_ki_2 (self):
        return self.df_ki_2

    def get_df_wilcoxon (self):
        return self.df_wilcoxon

    def get_dico_p_value(self):
        return self.dico_p_value_gene_group

    def get_calcul_VAF(self, ad:any,dp:int):
        if isinstance(ad,tuple):
            ad=ad[1]

        return ad/dp



if __name__ == "__main__":

    from PySide6.QtWidgets import QApplication
    import sys

    app = QApplication(sys.argv)
    conn = sql.get_sql_connection("C:/Users/HAMEAUEL/Documents/Db cute/Nw_tag.db")
    conn.row_factory = sqlite3.Row

    dialog = StatAnalysisDialog(conn)
    dialog.show()
    app.exec()









