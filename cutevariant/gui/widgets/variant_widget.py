from PySide6.QtWidgets import *
from PySide6.QtCore import *
from PySide6.QtGui import *

from cutevariant.gui.widgets import DictWidget, MarkdownEditor
from cutevariant.gui.widgets import TagEdit
from cutevariant.gui.style import CLASSIFICATION, SAMPLE_VARIANT_CLASSIFICATION
from cutevariant.config import Config
from cutevariant.gui import FIcon
from cutevariant.gui.model_view.edit_box_table import EditBoxTableModel, EditBoxTableView, get_deja_vu_table

from cutevariant.core import sql
import sqlite3

from PySide6.QtWidgets import (
    QApplication,
    QWidget,
    QTableView,
    QMainWindow,
    QVBoxLayout,
    QLineEdit,
)
from PySide6.QtCore import Qt, QSortFilterProxyModel, QAbstractTableModel


class QHLine(QFrame):
    def __init__(self):
        super(QHLine, self).__init__()
        self.setFrameShape(QFrame.HLine)
        self.setFrameShadow(QFrame.Sunken)


class TableModel(QAbstractTableModel):
    def __init__(self, data=None):
        super().__init__()
        self._data = [[1, 2], [1, 2]]

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

        self.TAG_SEPARATOR = "&"
        self.REVERSE_CLASSIF = {v["name"]: k for k, v in CLASSIFICATION.items()}
        self._conn = conn

        # self.name_edit = QLabel()
        # self.name_edit.setAlignment(Qt.AlignCenter)
        # self.name_edit.setSizePolicy(QSizePolicy.Minimum, QSizePolicy.Maximum)
        # info_layout.addWidget(self.name_edit)

        # Title
        self.title = QLabel()
        self.title.setTextFormat(Qt.RichText)
        self.title_variant = QLineEdit()
        self.title_variant.setReadOnly(True)
        title_layout = QHBoxLayout()
        title_layout.addWidget(QLabel("Variant "))
        title_layout.addWidget(self.title_variant)
        # FIcon(0xF014C),

        ### <validation block> ###
        validation_widget = QWidget()
        validation_layout = QFormLayout(validation_widget)

        self.favorite = QCheckBox()
        self.favorite.setSizePolicy(QSizePolicy.Maximum, QSizePolicy.Maximum)
        self.favorite.setText(self.tr("Mark variant as favorite"))

        self.classification = QComboBox()

        # self.tag_model = QStringListModel(["arefaire", "refactoring des tags", "attention"])
        # self.tag_completer = QCompleter()
        # self.tag_completer.setModel(self.tag_model)
        self.tag_edit = TagEdit()
        self.tag_edit.setPlaceholderText(self.tr("Tag separated by comma ..."))
        # self.tag_edit.setCompleter(self.tag_completer)

        self.tag_layout = QHBoxLayout()
        self.tag_layout.setContentsMargins(0, 0, 0, 0)
        self.tag_layout.addWidget(self.tag_edit)

        self.tag_choice = TagEdit()

        self.edit_comment_btn = QPushButton("Edit comment")
        self.edit_comment_btn.setSizePolicy(QSizePolicy.Maximum, QSizePolicy.Minimum)

        self.comment = MarkdownEditor()
        self.comment.preview_btn.setText("Preview/Edit comment")

        validation_layout.addRow("Favorite", self.favorite)
        validation_layout.addRow("Classification", self.classification)
        validation_layout.addRow("Tags", self.tag_layout)
        validation_layout.addRow("Comment", self.comment)

        self.variant_view = DictWidget()
        self.ann_view = DictWidget()
        self.sample_view = EditBoxTableView()
        self.history_view = DictWidget()

        self.tab_widget = QTabWidget()

        self.ann_combo = QComboBox()
        self.ann_combo.currentIndexChanged.connect(self.load_annotation)
        self.ann_widget = QWidget()

        ann_layout = QVBoxLayout(self.ann_widget)
        ann_layout.addWidget(self.ann_combo)
        ann_layout.addWidget(self.ann_view)

        self.tab_widget.addTab(validation_widget, "Edit")
        self.tab_widget.addTab(self.variant_view, "Variant")
        self.tab_widget.addTab(self.ann_widget, "Annotations")
        self.tab_widget.addTab(self.ann_widget, "Annotations")
        self.tab_widget.addTab(self.sample_view, "Validated samples")
        self.tab_widget.addTab(self.history_view, "History")
        # self.tab_widget.addTab(self.comment, "Comments")
        ### </othertabs block> ###

        # self.sample_tab_model = TableModel()
        # self.proxy_model = QSortFilterProxyModel()
        # self.proxy_model.setFilterKeyColumn(-1)  # Search all columns.
        # self.proxy_model.setSourceModel(self.sample_tab_model)
        # self.proxy_model.sort(0, Qt.AscendingOrder)

        ### <sample tab block> ###
        self.table = QTableView()
        self.table.setShowGrid(False)
        self.table.setShowGrid(False)
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.setSortingEnabled(True)
        self.table.setIconSize(QSize(16, 16))
        self.table.horizontalHeader().setHighlightSections(False)
        # self.table.setModel(self.proxy_model)

        # self.searchbar = QLineEdit()

        # You can choose the type of search by connecting to a different slot here.
        # see https://doc.qt.io/qt-5/qsortfilterproxymodel.html#public-slots
        # self.searchbar.textChanged.connect(self.proxy_model.setFilterFixedString)

        # sample_layout = QVBoxLayout()
        # sample_layout.addWidget(self.searchbar)
        # sample_layout.addWidget(self.table)
        # container = QWidget()
        # container.setLayout(sample_layout)
        ### </sample tab block> ###

        main_layout = QVBoxLayout(self)

        main_layout.addLayout(title_layout)
        main_layout.addWidget(QHLine())

        # central_layout = QHBoxLayout()
        # splitter = QSplitter(Qt.Horizontal)
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
            ret = QMessageBox.warning(
                None,
                "Database has been modified by another user.",
                "Do you want to overwrite value?",
                QMessageBox.Yes | QMessageBox.No,
            )
            if ret == QMessageBox.No:
                return

        # avoid losing tags who exist in DB but not in config.yml
        update_data = {"id": self.data["id"]}
        if self.favorite.isChecked():
            update_data["favorite"] = 1
        else:
            update_data["favorite"] = 0
        update_data["classification"] = self.classification.currentData()
        update_data["tags"] = self.TAG_SEPARATOR.join(self.tag_edit.text().split(","))
        update_data["comment"] = self.comment.toPlainText()
        sql.update_variant(self._conn, update_data)

    def load(self, variant_id: int):

        # Get variant data
        self.data = sql.get_variant(
            self._conn, variant_id, with_annotations=True, with_samples=True
        )
        self.initial_db_validation = self.get_validation_from_data(self.data)

        # Set title
        self.setWindowTitle("Variant edition")

        self.ann_combo.clear()

        # Set name
        #name = "{chr}-{pos}-{ref}-{alt}".format(**self.data)

        # Config
        config = Config("variables") or {}

        # Get variant_name_pattern
        variant_name_pattern="{chr}:{pos} - {ref}>{alt}"
        if "variant_name_pattern" in config:
            variant_name_pattern=config["variant_name_pattern"]
        else:
            config["variant_name_pattern"]=variant_name_pattern
            config.save()

        # Get variant_name_pattern_length
        variant_name_pattern_length=40
        if "variant_name_pattern_length" in config:
            variant_name_pattern_length = int(config["variant_name_pattern_length"])
        else:
            config["variant_name_pattern_length"]=variant_name_pattern_length
            config.save()

        #formatted_variant = "{chr}:{pos}-{ref}-{alt}".format(**full_variant)
        # Get fields
        #variant_id = self.data["id"]
        variant = sql.get_variant(self._conn, variant_id, with_annotations=True)
        if len(variant["annotations"]):
            for ann in variant["annotations"][0]:
                variant["annotations___"+str(ann)]=variant["annotations"][0][ann]
        variant_name_pattern=variant_name_pattern.replace("ann.","annotations___")
        variant_name = variant_name_pattern.format(**variant)
        self.title_variant.setText(variant_name)
       

        if "annotations" in self.data:
            for i, val in enumerate(self.data["annotations"]):
                if "transcript" in val:
                    self.ann_combo.addItem(val["transcript"])
                else:
                    self.ann_combo.addItem(f"Annotation {i}")

        # if "samples" in self.data:
        #     sdata = {i["name"]: i["gt"] for i in self.data["samples"] if i["gt"] > 0}
        #     self.sample_view.set_dict(sdata)
        #     self.sample_tab_model.update(
        #         [[i["name"], i["gt"]] for i in self.data["samples"] if i["gt"] > 0]
        #     )
        # replaced by validation status instead of genotype
        if "samples" in self.data:
            sdata = {
                i["name"]: SAMPLE_VARIANT_CLASSIFICATION[i["classification"]]["name"]
                for i in self.data["samples"]
                if i["classification"] > 0
            }
            # self.sample_view.set_dict(sdata)
            # self.sample_tab_model.update(
            #     [
            #         [i["name"], SAMPLE_VARIANT_CLASSIFICATION[i["classification"]]]
            #         for i in self.data["samples"]
            #         if i["classification"] > 0
            #     ]
            # )
        deja_vu, header = get_deja_vu_table(self._conn, variant_id)
        self.deja_vu_model = EditBoxTableModel(deja_vu, header)
        self.sample_view.setModel(self.deja_vu_model)

        if self.data["favorite"] == 1:
            self.favorite.setCheckState(Qt.CheckState(2))

        for k, v in CLASSIFICATION.items():
            self.classification.addItem(v["name"], k)
        index = int(self.classification.findData(self.data["classification"]))
        self.classification.setCurrentIndex(index)

        if self.data["tags"] is not None:
            self.tag_edit.setText(",".join(self.data["tags"].split(self.TAG_SEPARATOR)))

        self.comment.setPlainText(self.data["comment"])
        self.comment.preview_btn.setChecked(True)
        self.variant_view.set_dict(self.data)
        self.history_view.set_dict(self.get_history_variants(variant_id=variant_id))

        self.initial_state = self.get_gui_state()

    def get_validation_from_data(self, data):
        return {
            "favorite": data["favorite"],
            "classif_index": int("{classification}".format(**data)),
            "tags": data["tags"],
            "comment": data["comment"],
        }

    def get_gui_state(self):
        """
        Used to identify if any writable value was changed by an user when closing the widget
        """
        values = []
        values.append(self.favorite.isChecked())
        values.append(self.classification.currentIndex())
        values.append(self.tag_edit.text())
        values.append(self.comment.toPlainText())
        return values

    def load_annotation(self):

        if not self.data:
            return

        current = self.ann_combo.currentIndex()

        if "annotations" in self.data:

            adata = self.data["annotations"][current]
            self.ann_view.set_dict({i: k for i, k in adata.items() if k != ""})

    def get_history_variants(self, variant_id = None):
        """ Get the history of samples """
        results = {}
        if not variant_id:
            return results
        for record in self._conn.execute(
            f"""SELECT   ('[' || `timestamp` || ']') as time,
                        ('[' || `history`.`id` || ']') as id,
                            ( '[' || `user` || ']' || ' - ' || '"' || `field` || '" from "' || `before` || '" to "' || `after` || '"') as 'change'
                    FROM `history`
                    INNER JOIN `variants` ON `history`.`table_rowid`=`variants`.`rowid`
                    WHERE `table`='variants' AND `variants`.`id` = {variant_id}"""
            ):
            results[record["time"] + " " + record["id"]] = record["change"]

        return results


class VariantDialog(QDialog):
    def __init__(self, conn, variant_id, parent=None):
        super().__init__(parent)

        self.variant_id = variant_id
        self.w = VariantWidget(conn)
        self.button_box = QDialogButtonBox(QDialogButtonBox.Save | QDialogButtonBox.Cancel)
        vLayout = QVBoxLayout(self)
        vLayout.addWidget(self.w)
        vLayout.addWidget(self.button_box)

        self.button_box.accepted.connect(self.save)
        self.button_box.rejected.connect(self.reject)

        # self.resize(800, 600)

        self.load()
        self.setWindowTitle(self.w.windowTitle())

    def load(self):
        self.w.load(self.variant_id)

    def save(self):
        self.w.save(self.variant_id)
        self.accept()


if __name__ == "__main__":
    import sys

    app = QApplication(sys.argv)
    # conn = sql.get_sql_connection("/home/sacha/exome/exome.db")
    conn = sql.get_sql_connection("C:/Users/Ichtyornis/Projects/cutevariant/may2022.db")
    w = VariantDialog(conn, 1)

    w.show()

    app.exec()
