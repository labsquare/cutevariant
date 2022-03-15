import html
import sqlite3
from PySide6.QtWidgets import *
from PySide6.QtCore import *
from PySide6.QtGui import *

from cutevariant.core import sql
from cutevariant.commons import CLASSIFICATION, SAMPLE_VARIANT_CLASSIFICATION
from cutevariant.gui.widgets import ChoiceWidget, DictWidget, MarkdownEditor

from cutevariant.gui.ficon import FIcon

from cutevariant.gui.widgets.multi_combobox import MultiComboBox

class QHLine(QFrame):
    def __init__(self):
        super(QHLine, self).__init__()
        self.setFrameShape(QFrame.HLine)
        self.setFrameShadow(QFrame.Sunken)

class SampleVariantWidget(QWidget):
    def __init__(self, conn: sqlite3.Connection, parent=None):
        super().__init__()
        self.conn = conn
        self.TAG_LIST = ["#hemato", "#cardio", "#pharmaco"]
        self.TAG_SEPARATOR = "&"
        self.REVERSE_CLASSIF = {v:k for k, v in SAMPLE_VARIANT_CLASSIFICATION.items()}

        #Title
        self.title = QLabel()
        self.title.setTextFormat(Qt.RichText)
        self.title_variant = QLineEdit()
        self.title_sample = QLineEdit()
        self.title_variant.setReadOnly(True)
        self.title_sample.setReadOnly(True)
        title_layout = QHBoxLayout()
        title_layout.addWidget(self.title_sample)
        title_layout.addWidget(QLabel("for"))
        title_layout.addWidget(self.title_variant)

        # Validation
        self.classification = QComboBox()
        self.tab_widget = QTabWidget()
        self.tag_edit = MultiComboBox()
        self.tag_button = QToolButton()
        self.tag_button.setAutoRaise(True)
        self.tag_button.setIcon(FIcon(0xF0349))

        self.tag_layout = QHBoxLayout()
        self.tag_layout.setContentsMargins(0, 0, 0, 0)
        self.tag_layout.addWidget(self.tag_edit)

        self.tag_choice = ChoiceWidget()
        self.tag_choice_action = QWidgetAction(self)
        self.tag_choice_action.setDefaultWidget(self.tag_choice)

        self.menu = QMenu()
        self.menu.addAction(self.tag_choice_action)

        self.tag_button.setMenu(self.menu)
        self.tag_button.setPopupMode(QToolButton.InstantPopup)

        self.tag_edit.addItems(self.TAG_LIST)

        # validation
        # val_layout = QFormLayout()
        # val_layout.addWidget(self.lock_button)
        # val_layout.addWidget(QComboBox())

        self.edit_comment_btn = QPushButton("Edit comment")
        self.edit_comment_btn.setSizePolicy(QSizePolicy.Maximum, QSizePolicy.Minimum)
        self.comment = MarkdownEditor()
        self.comment.preview_btn.setText("Preview/Edit comment")

        self.info_lock = QLabel()

        validation_box = QGroupBox()
        validation_layout = QFormLayout(validation_box)

        validation_layout.addRow("Validation", self.classification)
        validation_layout.addRow("Tags", self.tag_layout)
        validation_layout.addRow("Comment", self.comment)
        validation_layout.addRow("", self.info_lock)

        ### <tabs block> ###
        # sample and variant information
        # self.general_info = DictWidget()
        self.var_info = DictWidget()
        self.sample_info = DictWidget()
        self.sample_has_var_info = DictWidget()

        # info_widget = QWidget()
        # info_layout = QVBoxLayout()
        
        # info_widget = QWidget()
        # info_layout = QFormLayout(info_widget)
        # self.info_var = QLabel()
        # info_layout.addRow("", self.info_var)
        # info_layout.addRow("", self.info_lock)

        # var_layout = QVBoxLayout()
        # self.var_title = QLabel("Variant")
        # self.var_title.setAlignment(Qt.AlignCenter)
        # var_layout.addWidget(self.var_title)
        # var_layout.addWidget(self.var_info)
        
        # sample_layout = QVBoxLayout()
        # self.sample_title = QLabel("Sample")
        # self.sample_title.setAlignment(Qt.AlignCenter)
        # sample_layout.addWidget(self.sample_title)
        # sample_layout.addWidget(self.sample_info)
        
        # info_layout.addLayout(var_layout)
        # info_layout.addLayout(sample_layout)
        # info_widget.setLayout(info_layout)

        self.tab_widget.addTab(validation_box, "Edit")
        # self.tab_widget.addTab(self.general_info, "Information")
        self.tab_widget.addTab(self.sample_has_var_info, "Genotyping")
        self.tab_widget.addTab(self.var_info, "Variant")
        self.tab_widget.addTab(self.sample_info, "Sample")
        ### </tabs block> ###

        vLayout = QVBoxLayout()
        # vLayout.addWidget(self.title)
        vLayout.addLayout(title_layout)
        vLayout.addWidget(QHLine())
        # vLayout.addWidget(validation_box)
        vLayout.addWidget(self.tab_widget)

        button_layout = QHBoxLayout()
        button_layout.addStretch()
        vLayout.addLayout(button_layout)

        self.setLayout(vLayout)

    def load(self, var: dict, sample: dict):
        self.sample_has_var_data = sql.get_sample_annotations(self.conn, var["id"], sample["id"])
        self.initial_db_validation = self.get_validation_from_data(self.sample_has_var_data)
        
        var_name = "{chr}-{pos}-{ref}-{alt}".format(**var)
        if len(var_name) > 30:
            var_name = var_name[0:20] + "..." + var_name [-10:]

        self.title.setText('<html><head/><body><p align="center">Validation status of variant <span style=" font-weight:700;">' 
                            + html.escape(var_name)
                            + '</span> in sample <span style=" font-weight:700;">'
                            + str(sample["name"])
                            + '</span></p></body></html>'
                        )
        self.setWindowTitle("edit box")
        self.title_variant.setText(var_name)
        self.title_sample.setText(sample["name"])

        # self.classification.addItems([v for v in SAMPLE_VARIANT_CLASSIFICATION.values()])
        # self.classification.setCurrentIndex(self.sample_has_var_data["classification"])
        for k, v in SAMPLE_VARIANT_CLASSIFICATION.items():
            self.classification.addItem(v, k)
        index = self.classification.findData(self.sample_has_var_data["classification"])
        self.classification.setCurrentIndex(index)

        if self.sample_has_var_data["tags"] is not None:
            for tag in self.sample_has_var_data["tags"].split(self.TAG_SEPARATOR):
                if tag in self.TAG_LIST:
                    self.tag_edit.model().item(self.TAG_LIST.index(tag)).setData(Qt.Checked, Qt.CheckStateRole)

        self.comment.setPlainText(self.sample_has_var_data["comment"])
        self.comment.preview_btn.setChecked(True)

        # self.var_title.setText(var_name)
        #tabs stuff
        self.sample_has_var_info.set_dict({k: v for k, v in self.sample_has_var_data.items() if k not in ("variant_id", "sample_id", "classification", "tags", "comment")})
        self.var_info.set_dict({k: v for k, v in var.items() if k not in ("id")})

        sample_info_dict = {k: v for k, v in sample.items() if k not in ("id")}
        for k, v in SAMPLE_VARIANT_CLASSIFICATION.items():
            sample_info_dict[v] = sql.get_sample_variant_classification_count(self.conn, sample["id"], k)
        self.sample_info.set_dict(sample_info_dict)
        self.sample_info.view.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)

        # req = get_sample_variant_classification_count(self.conn, sample["id"], 2)
        # self.info_var.setText("Total of validated variants for this sample: 0")
        valid_dict = {}

        # self.general_info.set_dict(valid_dict)
        # self.general_info.view.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)

        if sample["valid"] in (None, 0):
            self.info_lock.hide()
        else:
            self.info_lock.setText("Sample status: Locked (variant validation can't be edited)")
            #TODO: lock edition
        
        self.initial_state = self.get_gui_state()


    def save(self):
        """
        Two checks to perform: 
         - did the user change any value through the interface?
         - is the database state the same as when the dialog was first opened? 
        If yes and yes, update sample_has_variant
        """
        current_state = self.get_gui_state()
        if current_state == self.initial_state:
            return

        current_db_data = sql.get_sample_annotations(self.conn, self.sample_has_var_data["variant_id"], 
                                                    self.sample_has_var_data["sample_id"])
        current_db_validation = self.get_validation_from_data(current_db_data)
        if current_db_validation != self.initial_db_validation:
            ret = QMessageBox.warning(None, "Database has been modified by another user.", "Do you want to overwrite value?", QMessageBox.Yes | QMessageBox.No)
            if ret == QMessageBox.No:
                return
        
        update_data = {
            "variant_id": self.sample_has_var_data["variant_id"],
            "sample_id": self.sample_has_var_data["sample_id"],
            "classification": self.classification.currentIndex(),
            "tags": "&".join(self.tag_edit.currentData()),
            "comment": self.comment.toPlainText()
        }
        sql.update_sample_has_variant(self.conn, update_data)

    def get_validation_from_data(self, data):
        return {"classif_index": int("{classification}".format(**data)), 
                "tags": data["tags"], 
                "comment": data["comment"]
        }

    def get_gui_state(self):
        """
        Used to identify if any writable value was changed by an user when closing the widget
        """
        values = []
        values.append(self.classification.currentIndex())
        values.append(self.tag_edit.currentData())
        values.append(self.comment.toPlainText())
        return values

class SampleVariantDialog(QDialog):
    def __init__(self, conn, sample_id, var_id, parent=None):
        super().__init__()

        self.sample_id = sample_id
        self.var_id = var_id
        self.sample_data = sql.get_sample(conn, sample_id)
        self.variant_data = sql.get_variant(conn, var_id)

        self.w = SampleVariantWidget(conn)
        self.button_box = QDialogButtonBox(
            QDialogButtonBox.Save | QDialogButtonBox.Cancel
        )
        vLayout = QVBoxLayout(self)
        vLayout.addWidget(self.w)
        vLayout.addWidget(self.button_box)

        self.load()

        self.button_box.accepted.connect(self.save)
        self.button_box.rejected.connect(self.reject)

        # self.resize(800, 600)

    def load(self):
        self.w.load(self.variant_data, self.sample_data)
        self.setWindowTitle(self.w.windowTitle())

    def save(self):
        self.w.save()
        self.accept()


if __name__ == "__main__":
    import sys
    from cutevariant.core import sql

    app = QApplication(sys.argv)

    conn = sql.get_sql_connection("C:/Users/Ichtyornis/Projects/cutevariant/test2.db")

    w = SampleVariantDialog(conn, 1, 1)

    w.show()

    app.exec_()
