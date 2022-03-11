from PySide6.QtWidgets import *
from PySide6.QtCore import *
from PySide6.QtGui import *

from cutevariant.gui.widgets import ChoiceWidget, DictWidget, MarkdownEditor
from cutevariant.gui.widgets.multi_combobox import MultiComboBox
from cutevariant.gui.style import CLASSIFICATION
from cutevariant.core import sql
import sqlite3

from PySide6.QtWidgets import QApplication, QWidget, QTableView, QMainWindow, QVBoxLayout, QLineEdit
from PySide6.QtCore import Qt, QSortFilterProxyModel, QAbstractTableModel

class TableModel(QAbstractTableModel):
    def __init__(self, data=None):
        super().__init__()
        self._data = data

    def data(self, index, role):
        if role == Qt.DisplayRole:
            # See below for the nested-list data structure.
            # .row() indexes into the outer list,
            # .column() indexes into the sub-list
            return self._data[index.row()][index.column()]

    def rowCount(self, index):
        # The length of the outer list.
        return len(self._data)

    def columnCount(self, index):
        # The following takes the first sub-list, and returns
        # the length (only works if all rows are an equal length)
        return len(self._data[0])

    def update(self, data):
        self._data = data


class VariantWidget(QWidget):

    def __init__(self, conn: sqlite3.Connection, parent=None):
        super().__init__()
        self.TAG_LIST = ["#hemato", "#cardio", "#pharmaco"]
        self.TAG_SEPARATOR = "&"
        self.REVERSE_CLASSIF = {v["name"]:k for k, v in CLASSIFICATION.items()}
        self._conn = conn

        info_box = QGroupBox()
        info_layout = QHBoxLayout(info_box)
        self.name_edit = QLabel()
        self.name_edit.setAlignment(Qt.AlignCenter)
        self.name_edit.setSizePolicy(QSizePolicy.Minimum, QSizePolicy.Maximum)
        info_layout.addWidget(self.name_edit)

        ### <validation block> ###
        validation_box = QGroupBox()
        validation_layout = QFormLayout(validation_box)
        self.favorite = QCheckBox()
        self.favorite.setSizePolicy(QSizePolicy.Maximum, QSizePolicy.Maximum)
        self.classification = QComboBox()
        # self.line_layout = QHBoxLayout()
        # self.line_layout.addWidget(self.favorite)
        # self.line_form = QFormLayout()
        # self.line_form.addRow("Classification", self.classification)
        # self.line_form.setContentsMargins(10, 0, 0, 0)
        # self.line_layout.addLayout(self.line_form)

        self.tag_edit = MultiComboBox()
        self.tag_layout = QHBoxLayout()
        self.tag_layout.setContentsMargins(0, 0, 0, 0)
        self.tag_layout.addWidget(self.tag_edit)

        self.tag_choice = ChoiceWidget()
        self.tag_choice_action = QWidgetAction(self)
        self.tag_choice_action.setDefaultWidget(self.tag_choice)
        self.tag_edit.addItems(self.TAG_LIST)

        # self.comment = QLabel()
        # self.comment.setTextFormat(Qt.TextFormat(3))
        # self.comment.setWordWrap(True)
        #self.comment.acceptRichText()
        #self.comment.setReadOnly(True)
        self.edit_comment_btn = QPushButton("Edit comment")
        self.edit_comment_btn.setSizePolicy(QSizePolicy.Maximum, QSizePolicy.Minimum)
        self.comment = MarkdownEditor()
        self.comment.preview_btn.setText("Preview/Edit comment")

        # validation_layout.addRow("Favorite", self.favorite)
        # validation_layout.addRow("Classification", self.classification)
        validation_layout.addRow("Favorite", self.favorite)
        validation_layout.addRow("Classification", self.classification)
        validation_layout.addRow("Tags", self.tag_layout)
        validation_layout.addRow("Comment", self.comment)
        ### </validation block> ###

        ### <other tabs block> ###
        self.variant_view = DictWidget()
        self.ann_view = DictWidget()
        self.sample_view = DictWidget()

        self.tab_widget = QTabWidget()

        self.ann_combo = QComboBox()
        self.ann_combo.currentIndexChanged.connect(self.load_annotation)
        self.ann_widget = QWidget()
        ann_layout = QVBoxLayout(self.ann_widget)
        ann_layout.addWidget(self.ann_combo)
        ann_layout.addWidget(self.ann_view)

        self.tab_widget.addTab(self.variant_view, "Variants")
        self.tab_widget.addTab(self.ann_widget, "Annotations")
        self.tab_widget.addTab(self.sample_view, "Samples")
        #self.tab_widget.addTab(self.comment, "Comments")
        ### </othertabs block> ###

        ### <sample tab block> ###
        self.table = QTableView()
        self.table.setShowGrid(False)
        self.table.setShowGrid(False)
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.setSortingEnabled(True)
        self.table.setIconSize(QSize(16, 16))
        self.table.horizontalHeader().setHighlightSections(False)
        self.sample_tab_data = [[1,2],[1,2]]

        self.sample_tab_model = TableModel(self.sample_tab_data)
        self.proxy_model = QSortFilterProxyModel()
        self.proxy_model.setFilterKeyColumn(-1) # Search all columns.
        self.proxy_model.setSourceModel(self.sample_tab_model)

        self.proxy_model.sort(0, Qt.AscendingOrder)

        self.table.setModel(self.proxy_model)

        self.searchbar = QLineEdit()

        # You can choose the type of search by connecting to a different slot here.
        # see https://doc.qt.io/qt-5/qsortfilterproxymodel.html#public-slots
        self.searchbar.textChanged.connect(self.proxy_model.setFilterFixedString)

        sample_layout = QVBoxLayout()

        sample_layout.addWidget(self.searchbar)
        sample_layout.addWidget(self.table)
        container = QWidget()
        container.setLayout(sample_layout)
        self.tab_widget.addTab(container, "Samples2")
        ### </sample tab block> ###

        main_layout = QVBoxLayout(self)
        # central_layout = QHBoxLayout()
        # splitter = QSplitter(Qt.Horizontal)
        main_layout.addWidget(self.name_edit)
        main_layout.addWidget(validation_box)
        main_layout.addWidget(self.tab_widget)
        
        # main_layout.addWidget(splitter)

        self.data = None

    def save(self, variant_id: int):
        """
        Two checks to perform: 
         - did the user change any value through the interface?
         - is the database state the same as when the dialog was first opened? 
        If yes and yes, update variant.
        """
        current_state = self.get_gui_state()
        if current_state == self.initial_state:
            return

        current_db_data = sql.get_variant(
            self._conn, variant_id, with_annotations=True, with_samples=True
        )
        current_db_validation = self.get_validation_from_data(current_db_data)
        if current_db_validation != self.initial_db_validation:
            ret = QMessageBox.warning(None, "Database has been modified by another user.", "Do you want to overwrite value?", QMessageBox.Yes | QMessageBox.No)
            if ret == QMessageBox.No:
                return
        
        update_data = {"id": self.data["id"]}
        if self.favorite.isChecked:
            update_data["favorite"] = 1
        else:
            update_data["favorite"] = 0
        update_data["classification"] = self.classification.currentIndex()
        update_data["tags"] = "&".join(self.tag_edit.currentData())
        update_data["comment"] = self.comment.toPlainText()
        sql.update_variant(self._conn, update_data)


    def load(self, variant_id: int):

        self.data = sql.get_variant(
            self._conn, variant_id, with_annotations=True, with_samples=True
        )
        self.initial_db_validation = self.get_validation_from_data(self.data)

        name = "{chr}-{pos}-{ref}-{alt}".format(**self.data)

        self.ann_combo.clear()

        if "annotations" in self.data:
            for i, val in enumerate(self.data["annotations"]):
                if "transcript" in val:
                    self.ann_combo.addItem(val["transcript"])
                else:
                    self.ann_combo.addItem(f"Annotation {i}")

        if "samples" in self.data:
            sdata = {i["name"]: i["gt"] for i in self.data["samples"] if i["gt"] > 0}
            self.sample_view.set_dict(sdata)
            self.sample_tab_model.update([[i["name"], i["gt"]] for i in self.data["samples"] if i["gt"] > 0])

        self.name_edit.setText("Variant: " + name)
        
        if self.data["favorite"] == 1:
            self.favorite.setCheckState(Qt.CheckState(2))
        for k, v in CLASSIFICATION.items():
            self.classification.addItem(v["name"])
        self.classification.setCurrentIndex(int("{classification}".format(**self.data)))

        if self.data["tags"] is not None:
            for tag in self.data["tags"].split(self.TAG_SEPARATOR):
                if tag in self.TAG_LIST:
                    self.tag_edit.model().item(self.TAG_LIST.index(tag)).setData(Qt.Checked, Qt.CheckStateRole)
        self.comment.setPlainText(self.data["comment"])
        self.comment.preview_btn.setChecked(True)
        self.variant_view.set_dict(self.data)

        self.initial_state = self.get_gui_state()

    def get_validation_from_data(self, data):
        return {"favorite": data["favorite"], 
                "classif_index": int("{classification}".format(**data)), 
                "tags": data["tags"], 
                "comment": data["comment"]
            }

    def get_gui_state(self):
        """
        Used to identify if any writable value was changed by an user when closing the widget
        """
        values = []
        values.append(self.favorite.isChecked())
        values.append(self.classification.currentIndex())
        values.append(self.tag_edit.currentData())
        values.append(self.comment.toPlainText())
        return values

    def load_annotation(self):

        if not self.data:
            return

        current = self.ann_combo.currentIndex()

        if "annotations" in self.data:

            adata = self.data["annotations"][current]
            self.ann_view.set_dict({i: k for i, k in adata.items() if k != ""})


class VariantDialog(QDialog):
    def __init__(self, conn, variant_id, parent=None):
        super().__init__(parent)

        self.variant_id = variant_id
        self.w = VariantWidget(conn)
        self.button_box = QDialogButtonBox(
            QDialogButtonBox.Save | QDialogButtonBox.Cancel
        )
        vLayout = QVBoxLayout(self)
        vLayout.addWidget(self.w)
        vLayout.addWidget(self.button_box)

        self.load()

        self.button_box.accepted.connect(self.save)
        self.button_box.rejected.connect(self.reject)

        self.resize(800, 600)

    def load(self):
        self.w.load(self.variant_id)

    def save(self):
        self.w.save(self.variant_id)
        self.accept()


if __name__ == "__main__":
    import sys

    app = QApplication(sys.argv)
    conn = sql.get_sql_connection("C:/Users/Ichtyornis/Projects/cutevariant/test2.db")
    w = VariantDialog(conn, 1)

    w.show()

    app.exec()
