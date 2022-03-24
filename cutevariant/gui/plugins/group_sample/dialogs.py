# Standard imports
import sqlite3

import PySide6
from cutevariant.gui import mainwindow
from collections import OrderedDict
from cutevariant.core import get_sql_connection, get_metadatas, command


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
from PySide6.QtCore import Qt, QAbstractTableModel, QModelIndex, QThreadPool

# Custom imports
from cutevariant.gui.ficon import FIcon
from cutevariant.gui.plugin import PluginDialog
from cutevariant.gui.sql_thread import SqlThread
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
from cutevariant.core import sql, command
from cutevariant.core.reader import BedReader
from cutevariant.gui import plugin, FIcon, style
from cutevariant.commons import DEFAULT_SELECTION_NAME, SAMPLE_VARIANT_CLASSIFICATION
from cutevariant.gui.widgets import (
    ChoiceWidget,
    create_widget_action,
    SampleDialog,
    PresetAction,
)

from cutevariant.gui.widgets.choice_widget import ChoiceWidget
from cutevariant import LOGGER
from cutevariant.gui.sql_thread import SqlThread

from cutevariant.gui.style import GENOTYPE, CLASSIFICATION

from cutevariant.gui import FormatterDelegate
from cutevariant.gui.formatters.cutestyle import CutestyleFormatter


from PySide6.QtWidgets import *
import sys
from functools import partial
from PySide6.QtGui import QIcon

class GroupSampleModel(QAbstractListModel):
    """ CLass for manage current samples find in DB and put in new group. When they are none filter checked it' load methode and when they are
    filtrer it's Filter_bar.on refrresh. """
    def __init__(self, conn= None, parent=None):
        super().__init__(parent)
        self._data=[]
        self.conn=conn
        self.list_samples=ChoiceWidget()
        self.Filter_Bar=Filter_Bar(conn)
        self.list_samples.setAutoFillBackground(True)


        self.list_samples._apply_btn.setVisible(False)
        # Creates the samples loading thread
        self._load_samples_thread = SqlThread(self.conn)

        # Connect samples loading thread's signals (started, finished, error, result ready)
        self._load_samples_thread.started.connect(
            lambda: self.samples_are_loading.emit(True)
        )
        self._load_samples_thread.finished.connect(
            lambda: self.samples_are_loading.emit(False)
        )
        self.list_samples.set_placeholder(self.tr("Research sample name ..."))

    def data(self, index: QModelIndex, role: Qt.ItemDataRole):

        if not index.isValid():
            return None

        if role == Qt.DisplayRole:
            text = self._data[index.row()]["name"]
            return text

        if role == Qt.DecorationRole:
            return QIcon(self._data[index.row()]["icon"])

        if role == Qt.CheckStateRole:
            return Qt.Checked if self._data[index.row()]["checked"] else Qt.Unchecked

        if role == Qt.ToolTipRole:
            return self._data[index.row()]["description"]

    def setData(self, index: QModelIndex, value, role: Qt.ItemDataRole):
        """override"""

        if role == Qt.CheckStateRole:
            self._data[index.row()]["checked"] = True if value == Qt.Checked else False
            self.dataChanged.emit(index, index, [Qt.CheckStateRole])
            return True

        return False

    def get_one_data(self, name:str):
        self._data = [i for i in sql.get_samples(self.conn)]
        for i in self._data:
            if i['name']==name:
                return i
        # return self._data[]

    def load(self, conn):
        self._data.clear()

        self._data = [i for i in sql.get_samples(conn)]
        for i in self._data:
            self.list_samples.add_item(QIcon(),i['name'])

        return self.list_samples

    def on_check_all_samples(self):
        val_false=0
        for i in self.list_samples.get_all_items():
            dico=dict(i)
            if dico['checked'] == False:
                val_false+=1

        if  val_false >=1 :
            self.list_samples.check_all()

        else:
            self.list_samples.uncheck_all()


class Filter_Bar(QToolBar):
    """They are filter samples whit all samples in db, filter if family, filter tag, check all samples on current
    samples (use GroupSampleModel) and clear all filtrers"""
    signal_load=Signal()
    signal_check=Signal()

    def __init__(self, conn=None, parent=None):

        super().__init__(parent)
        self.conn=conn
        self.filter_tag=[]
        self.filter_family=[]
        self.filter_name=[]
        self.setIconSize(QSize(16, 16))
        self.icon=QIcon()
        """ dico_tagbrut_idsample are dico with id samples, tag brut (it's tag without split like in DB) and tag split
        it's tag brut with split in list. dico_tagbrut_tagsplit contains tag brut and tag split in list, it's only use for 
        sql get sample by"""
        self.dico_tagbrut_idsample={}
        self.dico_tagbrut_tagsplit={}

        self.valeur=None

        self.icon.addFile("C:/Documents/Check.jpg")

        self.samples_selector = ChoiceWidget()

        self.family_selector = ChoiceWidget()

        self.tag_selector = ChoiceWidget()

        self.setWindowIcon(FIcon(0xF0A8C))

        # samples action
        samples_action = create_widget_action(self, self.samples_selector)
        samples_action.setIcon(FIcon(0xF0013))
        samples_action.setText("Samples ")
        samples_action.setToolTip("Filter by samples")

        # family action
        fam_action = create_widget_action(self, self.family_selector)
        fam_action.setIcon(FIcon(0xF0B58))
        fam_action.setText("Family")
        fam_action.setToolTip("Filter by family")

        # tags action
        tag_action = create_widget_action(self, self.tag_selector)
        tag_action.setIcon(FIcon(0xF04FC))
        tag_action.setText("Tags ")
        tag_action.setToolTip("Filter by tags")

        # Menu action
        spacer = QWidget()
        spacer.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

        self.addWidget(spacer)
        self.addAction(
            FIcon(0xF01FE), self.tr("Check all samples"), self._on_check_samples
        )

        self.addAction(
            FIcon(0xF01FE), self.tr("Clear all filters"), self._on_clear_filters
        )
        self.on_refresh()

    def _on_check_samples(self):
        self.signal_check.emit()

    def _on_clear_filters(self):
        self.samples_selector.uncheck_all()
        self.family_selector.uncheck_all()
        self.tag_selector.uncheck_all()
        self.signal_load.emit()

    def get_dico_id_tagbrut(self, valeur:any):
        for i in sql.get_samples(self.conn):
            sep="&"
            values = i['tags'].split(sep)

            self.dico_tagbrut_idsample = {
                "id": i['id'],
                "tags": i['tags'],
                "tags_sep" : values
            }
            yield self.dico_tagbrut_idsample

    def on_refresh(self):
        """Generate all list on filter. Check item repeat it's for reemove repeat items"""
        sep = "&"
        self.samples_selector.clear()
        self.family_selector.clear()
        self.tag_selector.clear()
        self.filter_tag_brut=[]
        self.filter_tag.clear()
        self.filter_name.clear()
        self.filter_family.clear()

        # samples names
        self.filter_name = [i["name"] for i in sql.get_samples(self.conn)]
        self.filter_name.sort(reverse=False)
        for i in self.filter_name:
            self.samples_selector.add_item(QIcon(),i)

        # family in db
        self.filter_family = [i["family_id"] for i in sql.get_samples(self.conn)]
        self.filter_family.sort(reverse=False)
        self.filter_family=self.check_item_repeat(self.filter_family)
        for i in self.filter_family:
            self.family_selector.add_item(QIcon(),i)

        # tags
        self.filter_tag_brut = [i["tags"] for i in sql.get_samples(self.conn)]

        for x in self.filter_tag_brut:
            if x == None or x=='' or x==' ':
                pass
            else:
                self.valeur = x.split(sep)
                self.get_dico_id_tagbrut(self.valeur)
                self.dico_tagbrut_tagsplit[x]=self.valeur
                self.filter_tag=self.filter_tag+self.valeur
                self.filter_tag.sort(reverse=False)

        for i in self.check_item_repeat(self.filter_tag):
            self.tag_selector.add_item(QIcon(),i)

    def check_item_repeat(self, check_liste:list):
        for i in check_liste:
            if check_liste.count(i)>1:
                print(check_liste.count(i), i, "le nombre de i")
                check_liste.remove(i)
            elif i==' ' or i==None or i=='':
                check_liste.remove(i)
        check_liste=check_liste
        return check_liste



class GroupSampleDialog(PluginDialog):
    """principal dialog. User choice sample (current sample find in GroupSampleModel). When user apply some filter they use
    on refresh model. He check current samples and switch in the left part with add button. Left part are too ChoiceWidget.
    You can reemove sample group list. For Create group he need text on name group. Manage group it's only for reemove
    some group in subdialog"""
    ENABLE = True

    def __init__(self, conn=None, parent=None ):

        super().__init__(parent)
        self.conn = conn
        self.setModal(False)

        """skeleton layout dialo principal"""
        self.vlayout = QVBoxLayout()
        self.hlayout_P = QHBoxLayout()  # L41
        self.vlayout_Midd_P1 = QVBoxLayout()  # L42
        self.vlayout_Midd_P2 = QVBoxLayout()
        self.vlayout_Midd_P3 = QVBoxLayout()
        self.hlayout = QHBoxLayout()
        self.flayout_P3 = QFormLayout()
        self.Group_list=ChoiceWidget()
        self.Group_list._apply_btn.setVisible(False)
        self.Group_list.set_placeholder(self.tr("Research sample name ..."))
        self.dialog2 = Group_Manage(conn)
        self.Filter_Bar = Filter_Bar(conn)
        self.model=GroupSampleModel(conn)

        """Hide part"""
        self.title = QLabel()
        self.title.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        self.title.setText(
            """<b>Create groups of samples</b> <br/>
            Check your samples with any filter and add to te right for create your group
            """
        )

        """Not end it's for create error message when the name group are empty or exist on your db"""
        self.error_label = QLabel()
        self.error_label.setVisible(False)
        self.error_label.setStyleSheet(
            "QWidget{{background-color:'{}'; color:'{}'}}".format(
                style.WARNING_BACKGROUND_COLOR, style.WARNING_TEXT_COLOR
            )
        )

        """The mid part it's composed to 3 vlayout in hlayout with 2 list, button add, reemove and name group"""

        """First part in the mid part"""
        self.vlayout_Midd_P1.addWidget(self.Filter_Bar)
        self.vlayout_Midd_P1.addWidget(self.model.load(conn))


        """Butonn in second part"""
        self.butt_add = QPushButton("add")
        self.butt_add.clicked.connect(self.on_add_toGroup)
        self.butt_remove = QPushButton("remove")
        self.butt_remove.clicked.connect(self.on_remove_toGroup)

        self.vlayout_Midd_P2.addWidget(self.butt_add)
        self.vlayout_Midd_P2.addWidget(self.butt_remove)


        """Last part for create the group"""
        self.name_group = QLineEdit()
        self.flayout_P3.addRow(self.tr("Name group :"), self.name_group)

        self.vlayout_Midd_P3.addLayout(self.flayout_P3)
        self.vlayout_Midd_P3.addWidget(self.Group_list)

        """Add mid part on hlayout global"""
        self.hlayout_P.addLayout(self.vlayout_Midd_P1)
        self.hlayout_P.addLayout(self.vlayout_Midd_P2)
        self.hlayout_P.addLayout(self.vlayout_Midd_P3)

        """Low part"""
        self.button_box = QDialogButtonBox(
            QDialogButtonBox.Apply | QDialogButtonBox.Cancel
        )
        # Permet d'ajouter des options pour qu'on puisse acceder aux boutons apply
        self.button_box.button(QDialogButtonBox.Apply).clicked.connect(
            self.create_group
        )
        self.button_box.rejected.connect(self.reject)
        self.butt_manage_group=QPushButton("Manage group")
        self.butt_manage_group.clicked.connect(self.manage_group)

        self.hlayout.addWidget(self.butt_manage_group)
        self.hlayout.addWidget(self.button_box)

        """add widget on skeleton"""
        self.vlayout.addWidget(self.title)
        self.vlayout.addLayout(self.hlayout_P)
        self.vlayout.addLayout(self.hlayout)
        self.vlayout.addWidget(self.error_label)

        self.setLayout(self.vlayout)
        self.resize(700, 400)
        self.setWindowTitle("Group of tags")

        self.Filter_Bar.samples_selector.accepted.connect(self.on_refresh_model)
        self.Filter_Bar.tag_selector.accepted.connect(self.on_refresh_model)
        self.Filter_Bar.family_selector.accepted.connect(self.on_refresh_model)
        self.Filter_Bar.signal_load.connect(self.on_load_model_clear)
        self.Filter_Bar.signal_check.connect(self.model.on_check_all_samples)

    def mouseDoubleClickEvent(self, event:PySide6.QtGui.QMouseEvent) :
        for i in sql.get_samples(self.conn):
            dico=dict(i)
            print(dico)
        for i in self.Filter_Bar.tag_selector.get_all_items():
            dico=dict(i)
            print(dico)

    def on_load_model_clear(self):
        self.model._data.clear()
        self.model.list_samples.clear()
        self.model.load(self.conn)

    def Filtrer_check_list_samples(self):
        result_liste_samples=[]

        if self.Filter_Bar.samples_selector.checked() == True:
            my_generator_samples = self.Filter_Bar.samples_selector.selected_items()
            result_liste_samples = list(my_generator_samples)

        else:
            result_liste_samples = self.Filter_Bar.filter_name

        return result_liste_samples

    def Filtrer_check_list_families(self):
        result_list_families=[]

        if self.Filter_Bar.family_selector.checked() == True:
            my_generator_families = self.Filter_Bar.family_selector.selected_items()
            result_list_families = list(my_generator_families)

        else:
            result_list_families = self.Filter_Bar.filter_family

        return result_list_families

    def Filtrer_check_list_tag(self):
        result_liste_tags=[]

        if self.Filter_Bar.tag_selector.checked() == True:
            my_generator_tags = self.Filter_Bar.tag_selector.selected_items()
            result_liste_tags = list(my_generator_tags)

        #Le else est utiliser pour récuperer toute la liste lorsque rien n'est séléctionner
        else:
            result_liste_tags = self.Filter_Bar.filter_tag_brut

        return result_liste_tags

    def get_all_tag(self):
        return self.Filter_Bar.tag_selector

    def on_refresh_model(self):
        """when you clicked on apply in any filtrer you activate sql request and generate nw list samples"""
        self.model._data.clear()
        self.model.list_samples.clear()

        self.model._data = [i["name"] for i in sql.get_samples_by(self.conn,
                                                                  self.Filtrer_check_list_samples(),
                                                                  self.Filtrer_check_list_families(),
                                                                  self.Filtrer_check_list_tag(),
                                                                  self.Filter_Bar.dico_tagbrut_tagsplit
                                                                  )]
        for i in self.model._data:
            self.model.list_samples.add_item(QIcon(),i)

        return self.model.list_samples

    def on_add_toGroup(self):
        check_name=[]

        for i in self.Group_list.get_all_items():
            dico = dict(i)
            check_name.append(dico['name'])

        if self.model.list_samples.checked() == True:
            if not check_name:
                for i in self.model.list_samples.selected_items():
                    dico = dict(i)
                    i['checked']=False
                    self.Group_list.add_item(QIcon(), dico['name'])

            else:
                for i in self.model.list_samples.selected_items():
                    dico=dict(i)
                    i['checked']=False

                    if check_name.count(dico['name'])==0:
                        self.Group_list.add_item(QIcon(), dico['name'])

        return self.Group_list

    def on_remove_toGroup(self):
        list_unselected=ChoiceWidget()

        for i in self.Group_list.get_all_items():
            dico = dict(i)

            if dico['checked']==False:
                list_unselected.add_item(QIcon(), dico['name'])

        self.Group_list.clear()

        for i in list_unselected.get_all_items():
            dico = dict(i)
            self.Group_list.add_item(QIcon(), dico['name'])

        return self.Group_list

    def form_group(self, name_group:QLineEdit, dico_group:dict):
        if dico_group == None:
            return 'group#' + name_group.text()
        else:
            return '&group#' + name_group.text()

    def create_group(self):
        if self.check_form()==True:
            ##faire une forme qui permet de décier d'ajouter un &
            for i in self.Group_list.get_all_items():
                dico=dict(i)
                nw_data=self.model.get_one_data(dico['name'])
                print(nw_data)
                group_name=self.form_group(self.name_group, nw_data['tags'])
                print(group_name)
                old_tag=(nw_data)['tags']
                if old_tag ==None:
                    nw_data.update({'tags':group_name})
                else :
                    nw_data.update({'tags': old_tag+group_name})
                sql.update_sample(self.conn,nw_data)
                self.Filter_Bar.on_refresh()
                print("creation")

    def check_form(self):
        if not self.name_group.text()=='' or self.name_group.text()==' ':
            return True
    # ajouter un check qui permet de voir si le nom n'a pas était ajouter déja
    def manage_group(self):
        self.dialog2.show()
        self.dialog2.connect(self.Filter_Bar.on_refresh)

class Group_Manage(QDialog):
    """The second dialog for reemove some tag """
    signal_close=Signal()
    def __init__(self, conn=None, parent=None):
        super().__init__(parent)
        self.setModal(True)
        self.conn=conn
        self.Filter_bar=Filter_Bar(conn)
        self.current_interface=QVBoxLayout()
        self.button_box = QDialogButtonBox(QDialogButtonBox.Apply|QDialogButtonBox.Cancel)

        self.title=QLabel()
        self.title.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        self.title.setText(
            """<b>Manage your group in your DataBase </b> <br/>
            Reemove some group
            """
        )
        self.list_tag=ChoiceWidget()
        self.list_tag._apply_btn.setVisible(False)

        self.load_tags_reemove(self.list_tag)

        self.current_interface.addWidget(self.title)
        self.current_interface.addWidget(self.list_tag)
        self.current_interface.addWidget(self.button_box)

        self.setLayout(self.current_interface)
        self.resize(300, 400)
        self.setWindowTitle("Group of tags")
        self.button_box.button(QDialogButtonBox.Apply).clicked.connect(self.del_group)
        self.button_box.rejected.connect(self.reject)

    def load_tags_reemove(self, select_tag: ChoiceWidget):
        for i in self.Filter_bar.filter_tag:
            select_tag.add_item(QIcon(), i)

    def del_group(self):
        r=[]
        for i in self.list_tag.selected_items():
            for a in self.Filter_bar.get_dico_id_tagbrut(self.Filter_bar.valeur):
                if i['name'] in a['tags_sep']:
                    r=a['tags_sep'].index(i['name'])
                    del a['tags_sep'][r]
                    a['tag']="&".join(a['tags_sep'])
                    dico_update={
                        "id" : a["id"],
                        "tags" : a['tag']
                    }

                    sql.update_sample(self.conn, dico_update)
                    self.list_tag.clear()
                    self.load_tags_reemove(self.list_tag)


if __name__ == "__main__":
    from PySide6.QtWidgets import QApplication
    import sys

    app = QApplication(sys.argv)
    conn = sql.get_sql_connection("C:/Users/hameauel/Documents/Db cute/test1.db")
    conn.row_factory = sqlite3.Row

    dialog = GroupSampleDialog(conn)
    dialog.show()
    app.exec()



