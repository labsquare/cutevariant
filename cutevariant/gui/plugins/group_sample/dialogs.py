# Standard imports
import sqlite3

import PySide6

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

class GroupSampleModel(QAbstractListModel):
    """Class to manage current samples found in DB and put them in new groups. 
    When nothing is checked in filters ; use load method
    When something is checked in a filter ; use Filter_bar.on refresh
    """
    def __init__(self, conn= None, parent=None):
        super().__init__(parent)
        self._data = []
        self.conn = conn
        self.list_samples = ChoiceWidget()
        self.filter_bar = Filter_Bar(conn)
        self.list_samples.setAutoFillBackground(True)

        self.list_samples._apply_btn.setVisible(False)
        # Creates the samples loading thread
        # self._load_samples_thread = SqlThread(self.conn)

        # # Connect samples loading thread's signals (started, finished, error, result ready)
        # self._load_samples_thread.started.connect(
        #     lambda: self.samples_are_loading.emit(True)
        # )
        # self._load_samples_thread.finished.connect(
        #     lambda: self.samples_are_loading.emit(False)
        # )
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

    def load(self, conn):
        self._data.clear()

        self._data = [i for i in sql.get_samples(conn)]
        for i in self._data:
            self.list_samples.add_item(QIcon(),i['name'])

        return self.list_samples

    def on_check_all_samples(self):
        at_least_one_not_selected = False
        for i in self.list_samples.get_all_items():
            dico=dict(i)
            if dico['checked'] == False:
                at_least_one_not_selected = True

        if at_least_one_not_selected:
            self.list_samples.check_all()
        else:
            self.list_samples.uncheck_all()


class Filter_Bar(QToolBar):
    """To filter samples in database, based on sample name/family/tags
    Possible to check all samples on current
    samples (use GroupSampleModel) and clear all filtrers"""
    signal_load=Signal()
    signal_check=Signal()

    def __init__(self, conn=None, parent=None):

        super().__init__(parent)
        self.conn=conn
        self.TAG_SEPARATOR = "&"

        self.filter_tag = []
        self.filter_family = []
        self.filter_name = []
        self.setIconSize(QSize(16, 16))
        self.icon = QIcon()
        """ dico_tagbrut_idsample are dico with id samples, tag brut (it's tag without split like in DB) and tag split
        it's tag brut with split in list. dico_tagbrut_tagsplit contains tag brut and tag split in list, it's only use for 
        sql get sample by"""
        self.dico_tagbrut_idsample = {}
        self.dico_tagbrut_tagsplit = {}

        self.valeur = None

        # self.icon.addFile("C:/Documents/Check.jpg")

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
            FIcon(0xF0C51), self.tr("Check/Uncheck all samples"), self._on_check_samples
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

    def get_dico_id_tag_brut(self, valeur:any):
        for i in sql.get_samples(self.conn):
            values = i['tags'].split(self.TAG_SEPARATOR)

            self.dico_tagbrut_idsample = {
                "id": i['id'],
                "tags": i['tags'],
                "tags_sep" : values
            }
            yield self.dico_tagbrut_idsample

    def on_refresh(self):
        """Generate all lists in filters"""
        self.samples_selector.clear()
        self.family_selector.clear()
        self.tag_selector.clear()
        self.filter_tag_brut=[]
        self.filter_tag.clear()
        self.filter_name.clear()
        self.filter_family.clear()

        # samples names
        self.filter_name = [i["name"] for i in sql.get_samples(self.conn)]
        self.filter_name.sort()
        for i in self.filter_name:
            self.samples_selector.add_item(FIcon(0xF0B55),i)

        # family in db
        self.filter_family = [i["family_id"] for i in sql.get_samples(self.conn)]
        self.filter_family = self.keep_sorted_unique_values(self.filter_family)
        for i in self.filter_family:
            self.family_selector.add_item(FIcon(0xF036E),i)

        # tags
        self.filter_tag_brut = [i["tags"] for i in sql.get_samples(self.conn)]

        for x in self.filter_tag_brut:
            if x == None or x == '' or x.isspace():
                #Samples in DB can have a NULL or empty tag String. Do not put those in the tag selector.
                pass
            else:
                self.valeur = x.split(self.TAG_SEPARATOR)
                if '' in self.valeur :
                    self.valeur .remove('')
                self.get_dico_id_tag_brut(self.valeur)
                self.dico_tagbrut_tagsplit[x] = self.valeur
                self.filter_tag = self.filter_tag+self.valeur

        for i in self.keep_sorted_unique_values(self.filter_tag):
            self.tag_selector.add_item(FIcon(0xF04FD),i)

    def keep_sorted_unique_values(self, check_list:list):
        """
        returns an ordered list keeping only unique values
        """
        check_list = list(set(check_list))
        check_list.sort()
        return check_list


class GroupSampleDialog(PluginDialog):
    """principal dialog. User choose sample (current sample find in GroupSampleModel). When user apply some filter they use
    on refresh model. He check current samples and switch in the left part with add button. Left part are too ChoiceWidget.
    You can remove sample group list. For Create group he need text on name group. Manage group it's only for remove
    some group in subdialog"""
    ENABLE = True

    def __init__(self, conn=None, parent=None ):

        super().__init__(parent)
        self.conn = conn
        self.setModal(False)

        """skeleton layout dialog principal"""
        self.vlayout = QVBoxLayout()
        self.hlayout_P = QHBoxLayout()  # L41
        self.vlayout_mid_P1 = QVBoxLayout()  # L42
        self.vlayout_mid_P2 = QVBoxLayout()
        self.vlayout_mid_P3 = QVBoxLayout()
        self.hlayout = QHBoxLayout()
        self.flayout_P3 = QFormLayout()
        self.group_list = ChoiceWidget()
        self.group_list._apply_btn.setVisible(False)
        self.group_list.set_placeholder(self.tr("Research sample name ..."))
        self.dialog2 = Group_Manage(conn)
        self.filter_bar = Filter_Bar(conn)
        self.model = GroupSampleModel(conn)

        """Hide part"""
        self.title = QLabel()
        self.title.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        self.title.setText(
            """<b>Create groups of samples</b> <br/>
            Select your samples with any filter and add them to the right to create your group
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
        self.vlayout_mid_P1.addWidget(self.filter_bar)
        self.vlayout_mid_P1.addWidget(self.model.load(conn))

        """Butonn in second part"""
        self.butt_add = QPushButton()
        # self.tr("Add sample")
        self.butt_add.clicked.connect(self.on_add_to_group)
        self.butt_add.setIcon(FIcon(0xF09C2))
        self.butt_remove = QPushButton()
        # self.tr("Remove sample")
        self.butt_remove.clicked.connect(self.on_remove_to_group)
        self.butt_remove.setIcon((FIcon(0xF09C0)))

        self.vlayout_mid_P2.addWidget(self.butt_add)
        self.vlayout_mid_P2.addWidget(self.butt_remove)

        """Last part for create the group"""
        self.name_group = QLineEdit()
        self.flayout_P3.addRow(self.tr("Name group :"), self.name_group)

        self.vlayout_mid_P3.addLayout(self.flayout_P3)
        self.vlayout_mid_P3.addWidget(self.group_list)

        """Add mid part on hlayout global"""
        self.hlayout_P.addLayout(self.vlayout_mid_P1)
        self.hlayout_P.addLayout(self.vlayout_mid_P2)
        self.hlayout_P.addLayout(self.vlayout_mid_P3)

        """Low part"""
        self.button_box = QDialogButtonBox(
            QDialogButtonBox.Apply | QDialogButtonBox.Cancel
        )
        # Permet d'ajouter des options pour qu'on puisse acceder aux boutons apply
        self.button_box.button(QDialogButtonBox.Apply).clicked.connect(
            self.create_group
        )
        self.button_box.rejected.connect(self.reject)
        self.butt_manage_group = QPushButton("Delete group")
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
        self.setWindowTitle("Group of samples")

        self.filter_bar.samples_selector.accepted.connect(self.on_refresh_model)
        self.filter_bar.tag_selector.accepted.connect(self.on_refresh_model)
        self.filter_bar.family_selector.accepted.connect(self.on_refresh_model)
        self.filter_bar.signal_load.connect(self.on_load_model_clear)
        self.filter_bar.signal_check.connect(self.model.on_check_all_samples)
        self.dialog2.signal_close.connect(self.filter_bar.on_refresh)

    def mouseDoubleClickEvent(self, event:PySide6.QtGui.QMouseEvent) :
        """
        For debugging purposes
        """
        for i in sql.get_samples(self.conn):
            dico=dict(i)
        for i in self.filter_bar.tag_selector.get_all_items():
            dico=dict(i)

    def on_load_model_clear(self):
        self.model._data.clear()
        self.model.list_samples.clear()
        self.model.load(self.conn)

    def filter_check_list_samples(self):
        result_list_samples=[]

        if self.filter_bar.samples_selector.checked() == True:
            my_generator_samples = self.filter_bar.samples_selector.selected_items()
            result_list_samples = list(my_generator_samples)

        else:
            result_list_samples = self.filter_bar.filter_name

        return result_list_samples

    def filter_check_list_families(self):
        result_list_families=[]

        if self.filter_bar.family_selector.checked() == True:
            my_generator_families = self.filter_bar.family_selector.selected_items()
            result_list_families = list(my_generator_families)

        else:
            result_list_families = self.filter_bar.filter_family

        return result_list_families

    def filter_check_list_tags(self):
        result_list_tags=[]

        if self.filter_bar.tag_selector.checked() == True:
            my_generator_tags = self.filter_bar.tag_selector.selected_items()
            result_list_tags = list(my_generator_tags)

        #Le else est utiliser pour récuperer toute la liste lorsque rien n'est séléctionner
        else:
            result_list_tags = self.filter_bar.filter_tag_brut

        return result_list_tags

    def get_all_tag(self):
        return self.filter_bar.tag_selector

    def on_refresh_model(self):
        """when you clicked on apply in any filtrer you activate sql request and generate nw list samples"""
        self.model._data.clear()
        self.model.list_samples.clear()

        self.model._data = [i["name"] for i in sql.get_samples_by(self.conn,
                                                                  self.filter_check_list_samples(),
                                                                  self.filter_check_list_families(),
                                                                  self.filter_check_list_tags(),
                                                                  self.filter_bar.dico_tagbrut_tagsplit
                                                                  )]
        for i in self.model._data:
            self.model.list_samples.add_item(QIcon(),i)

        return self.model.list_samples

    def on_add_to_group(self):
        """
        Connected to the main "Add" button, sends selected samples to the list on the right
        """
        already_present_items = []

        for i in self.group_list.get_all_items():
            items_to_add = dict(i)
            already_present_items.append(items_to_add['name'])

        if self.model.list_samples.checked() == True:
            if not already_present_items:
                for i in self.model.list_samples.selected_items():
                    items_to_add = dict(i)
                    i['checked']=False
                    self.group_list.add_item(QIcon(), items_to_add['name'])

            else:
                for i in self.model.list_samples.selected_items():
                    items_to_add=dict(i)
                    i['checked']=False

                    if already_present_items.count(items_to_add['name'])==0:
                        self.group_list.add_item(QIcon(), items_to_add['name'])

        return self.group_list

    def on_remove_to_group(self):
        list_unselected = ChoiceWidget()

        for i in self.group_list.get_all_items():
            item_to_keep = dict(i)

            if item_to_keep['checked']==False:
                list_unselected.add_item(QIcon(), item_to_keep['name'])

        self.group_list.clear()

        for i in list_unselected.get_all_items():
            item_to_keep = dict(i)
            self.group_list.add_item(QIcon(), item_to_keep['name'])

        return self.group_list

    def form_group(self, name_group:QLineEdit, dico_group:dict):
        if dico_group in (None, "", {}):
            return name_group.text()
        else:
            return '&' + name_group.text()

    def create_group(self):
        if self.check_form()==True:
            ##add a & to new tag name if tag list is not empty
            for i in self.group_list.get_all_items():
                dic=dict(i)
                nw_data = self.model.get_one_data(dic['name'])
                group_name = self.form_group(self.name_group, nw_data['tags'])
                old_tag = nw_data['tags']

                if old_tag == None:
                    nw_data.update({'tags':group_name})
                else :
                    nw_data.update({'tags': old_tag+group_name})

                sql.update_sample(self.conn,nw_data)
                self.filter_bar.on_refresh()
                self.dialog2.reload_tags()
            self.group_list.clear()

    def check_form(self):
        if not self.name_group.text()=='' and not self.name_group.text().isspace():
            return True

    def manage_group(self):
        self.dialog2.show()
        self.dialog2.accepted.connect(self.filter_bar.on_refresh)

class Group_Manage(QDialog):
    """The second dialog used to remove tags from the DB"""
    signal_close=Signal()

    def __init__(self, conn=None, parent=None):
        super().__init__(parent)
        self.TAG_SEPARATOR = "&"
        self.setModal(True)
        self.conn = conn
        self.filter_bar = Filter_Bar(conn)
        self.current_interface = QVBoxLayout()
        self.button_box = QDialogButtonBox(QDialogButtonBox.Apply|QDialogButtonBox.Cancel)

        self.title=QLabel()
        self.title.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        self.title.setText(
            """<b>Manage your groups in your current project </b> <br/>
            Remove selected groups
            """
        )
        self.list_tag = ChoiceWidget()
        self.list_tag._apply_btn.setVisible(False)


        self.current_interface.addWidget(self.title)
        self.current_interface.addWidget(self.list_tag)
        self.current_interface.addWidget(self.button_box)

        self.setLayout(self.current_interface)
        self.resize(300, 400)
        self.setWindowTitle("Group of tags")
        self.button_box.button(QDialogButtonBox.Apply).clicked.connect(self._del_group)
        self.button_box.rejected.connect(self.reject)
        self.filter_bar.on_refresh()
        self.reload_tags()

    def reload_tags(self):
        self.filter_bar.on_refresh()
        self.list_tag.clear()
        for i in self.filter_bar.keep_sorted_unique_values(self.filter_bar.filter_tag):
            self.list_tag.add_item(FIcon(0xF121F), i)

    def mouseDoubleClickEvent(self, event:PySide6.QtGui.QMouseEvent) :
        """
        For debugging purposes
        """
        print(self.filter_bar.filter_tag_brut)
        print(self.filter_bar.keep_sorted_unique_values(self.filter_bar.filter_tag))

    def _del_group(self):
        for selected_group in self.list_tag.selected_items():
            for sample_dic in self.filter_bar.get_dico_id_tag_brut(self.filter_bar.filter_tag):
                if selected_group["name"] in sample_dic["tags_sep"]:

                    # r = sample_dic["tags_sep"].index(selected_group['name'])
                    # del sample_dic['tags_sep'][r]
                    sample_dic["tags_sep"].remove(selected_group["name"])

                    sample_dic["tag"] = self.TAG_SEPARATOR.join(sample_dic["tags_sep"])
                    update_dic ={
                        "id" : sample_dic["id"],
                        "tags" : sample_dic["tag"]
                    }

                    sql.update_sample(self.conn, update_dic)
                    self.list_tag.clear()
                    self.signal_close.emit()
                    self.reload_tags()


if __name__ == "__main__":
    from PySide6.QtWidgets import QApplication
    import sys

    app = QApplication(sys.argv)
    # conn = sql.get_sql_connection("C:/Users/hameauel/Documents/Db cute/test1.db")
    conn = sql.get_sql_connection("C:/Users/HAMEAUEL/Documents/Db cute/Hemato_XTHS.db")
    conn.row_factory = sqlite3.Row

    dialog = GroupSampleDialog(conn)
    dialog.show()
    app.exec()



