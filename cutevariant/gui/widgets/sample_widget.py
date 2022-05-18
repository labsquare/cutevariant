import operator
import re
import sqlite3
from PySide6.QtWidgets import *
from PySide6.QtCore import *
from PySide6.QtGui import *

from cutevariant.gui.widgets import MarkdownEditor
from cutevariant.core import sql
from cutevariant.config import Config
from cutevariant.core.querybuilder import fields_to_sql

from cutevariant.gui.ficon import FIcon

from cutevariant.gui.widgets import ChoiceWidget, DictWidget
from cutevariant.gui.widgets.multi_combobox import MultiComboBox

from cutevariant import LOGGER

class EditTableModel(QAbstractTableModel):
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

class EditTableView(QTableView):
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


class HpoWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__()

        self.view = QListView()
        self.add_button = QToolButton()
        self.add_button.setAutoRaise(True)
        self.add_button.setText("+")
        self.rem_button = QToolButton()
        self.rem_button.setAutoRaise(True)
        self.rem_button.setText("-")

        self.view.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

        btn_layout = QHBoxLayout()
        btn_layout.addWidget(self.add_button)
        btn_layout.addWidget(self.rem_button)
        btn_layout.setSizeConstraint(QLayout.SetMinimumSize)
        spacer = QWidget()
        spacer.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        btn_layout.addWidget(spacer)

        vLayout = QVBoxLayout(self)
        vLayout.addWidget(self.view, 5)
        vLayout.addLayout(btn_layout)
        vLayout.setContentsMargins(0, 0, 0, 0)


class SampleWidget(QWidget):
    def __init__(self, conn: sqlite3.Connection, parent=None):
        super().__init__()
        self.conn = conn
        if Config("validation")["sample_tags"] != None:
            self.TAG_LIST = [tag["name"] for tag in Config("validation")["sample_tags"]]
        else:
            self.TAG_LIST = []
        self.TAG_SEPARATOR = "&"
        self.SAMPLE_CLASSIFICATION = {
            -1: {"name": "Rejected"},
            0: {"name": "Unlocked"},
            1: {"name": "Locked"},
        }
        self.REVERSE_CLASSIF = {v["name"]: k for k, v in self.SAMPLE_CLASSIFICATION.items()}

        # Identity
        self.name_edit = QLineEdit()
        self.name_edit.setReadOnly(True)
        self.fam_edit = QLineEdit()
        self.tab_widget = QTabWidget()
        self.classification = QComboBox()
        self.tag_edit = MultiComboBox()
        self.tag_button = QToolButton()
        self.tag_button.setAutoRaise(True)
        self.tag_button.setIcon(FIcon(0xF0349))

        self.tag_layout = QHBoxLayout()
        self.tag_layout.setContentsMargins(0, 0, 0, 0)
        self.tag_layout.addWidget(self.tag_edit)

        identity_widget = QWidget()
        identity_layout = QFormLayout(identity_widget)

        identity_layout.addRow("Name", self.name_edit)
        identity_layout.addRow("Family", self.fam_edit)

        identity_layout.addRow("Tags", self.tag_layout)
        identity_layout.addRow("Statut", self.classification)

        self.tag_choice = ChoiceWidget()
        self.tag_choice_action = QWidgetAction(self)
        self.tag_choice_action.setDefaultWidget(self.tag_choice)

        self.menu = QMenu()
        self.menu.addAction(self.tag_choice_action)

        self.tag_button.setMenu(self.menu)
        self.tag_button.setPopupMode(QToolButton.InstantPopup)

        self.tag_edit.addItems(self.TAG_LIST)

        # validation
        val_layout = QFormLayout()

        # val_layout.addWidget(self.lock_button)
        # val_layout.addWidget(QComboBox())

        # phenotype
        self.sex_combo = QComboBox()
        self.sex_combo.addItems(["Unknown", "Male", "Female"])
        self.phenotype_combo = QComboBox()  # case /control
        self.phenotype_combo.addItems(["Missing", "Unaffected", "Affected"])

        # comment
        # self.tag_edit = QLineEdit()
        # self.tag_edit.setPlaceholderText("Tags separated by comma ")
        self.comment = MarkdownEditor()
        self.comment.preview_btn.setText("Preview/Edit comment")

        identity_layout.addRow("Comment", self.comment)

        self.hpo_widget = HpoWidget()

        pheno_widget = QWidget()
        pheno_layout = QFormLayout(pheno_widget)
        pheno_layout.addRow("Sexe", self.sex_combo)
        pheno_layout.addRow("Affected", self.phenotype_combo)
        # pheno_layout.addRow("HPO", self.hpo_widget) #hidden for now
        self.tab_widget.addTab(identity_widget, "Edit")
        self.tab_widget.addTab(pheno_widget, "Phenotype")

        self.variant_view = EditTableView()
        self.tab_widget.addTab(self.variant_view, "Validated variants")

        self.history_view = DictWidget()
        self.tab_widget.addTab(self.history_view, "History")
        # self.tab_widget.currentChanged.connect(self.on_tab_change)

        header_layout = QHBoxLayout()
        header_layout.addLayout(val_layout)

        vLayout = QVBoxLayout()
        vLayout.addLayout(header_layout)
        vLayout.addWidget(self.tab_widget)

        button_layout = QHBoxLayout()
        button_layout.addStretch()
        vLayout.addLayout(button_layout)

        self.setLayout(vLayout)

    # def on_tab_change(self):
    #     self.adjustSize()

    def load(self, sample_id: int):

        self.sample_id = sample_id
        data = sql.get_sample(self.conn, sample_id)
        self.initial_db_validation = self.get_validation_from_data(data)
        print("loaded data:", data)
        self.name_edit.setText(data.get("name", "?"))
        self.fam_edit.setText(data.get("family_id", "?"))
        self.sex_combo.setCurrentIndex(data.get("sex", 0))
        self.phenotype_combo.setCurrentIndex(data.get("phenotype", 0))

        # self.classification.addItems([v["name"] for v in self.SAMPLE_CLASSIFICATION.values()])
        for k, v in self.SAMPLE_CLASSIFICATION.items():
            self.classification.addItem(v["name"], k)
        index = self.classification.findData(data["valid"])
        self.classification.setCurrentIndex(index)

        if data["tags"] is not None:
            for tag in data["tags"].split(self.TAG_SEPARATOR):
                if tag in self.TAG_LIST:
                    self.tag_edit.model().item(self.TAG_LIST.index(tag)).setData(Qt.Checked, Qt.CheckStateRole)

        self.comment.setPlainText(data.get("comment", ""))
        self.comment.preview_btn.setChecked(True)
        self.history_view.set_dict(self.get_history_samples())

        self.setWindowTitle("Sample edition: " + data.get("name", "Unknown"))
        self.initial_state = self.get_gui_state()

        # Get validated variants
        validated_variants, header = get_validated_variants_table(self.conn, self.sample_id)
        self.variant_model = EditTableModel(validated_variants, header)
        self.variant_view.setModel(self.variant_model)


    def save(self, sample_id: int):
        """
        Two checks to perform:
         - did the user change any value through the interface?
         - is the database state the same as when the dialog was first opened?
        If yes and yes, update sample_has_variant
        """
        current_state = self.get_gui_state()
        if current_state == self.initial_state:
            return

        current_db_data = sql.get_sample(self.conn, self.sample_id)
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
        missing_tags = []
        for tag in self.initial_db_validation["tags"].split(self.TAG_SEPARATOR):
            if tag not in self.TAG_LIST:
                missing_tags.append(tag)

        data = {
            "id": sample_id,
            "name": self.name_edit.text(),
            "family_id": self.fam_edit.text(),
            "sex": self.sex_combo.currentIndex(),
            "phenotype": self.phenotype_combo.currentIndex(),
            "valid": self.REVERSE_CLASSIF[self.classification.currentText()],
            "tags": self.TAG_SEPARATOR.join(self.tag_edit.currentData() + missing_tags),
            "comment": self.comment.toPlainText(),
        }

        sql.update_sample(self.conn, data)

    def get_validation_from_data(self, data):
        return {
            "fam": data["family_id"],
            "tags": data["tags"],
            "comment": data["comment"],
            "valid": int("{valid}".format(**data)),
            "sex": data["sex"],
            "phenotype": data["phenotype"],
        }

    def get_gui_state(self):
        """
        Used to identify if any writable value was changed by an user when closing the widget
        """
        values = []
        values.append(self.fam_edit.text())
        values.append(self.classification.currentIndex())
        values.append(self.tag_edit.currentData())
        values.append(self.comment.toPlainText())
        values.append(self.sex_combo.currentIndex())
        values.append(self.phenotype_combo.currentIndex())
        return values

    def get_history_samples(self):
        """Get the history of samples"""
        results = {}
        for record in self.conn.execute(
            f"""SELECT  ('[' || `timestamp` || ']') as time,
                        ('[' || `history`.`id` || ']') as id,
                        ( '[' || `user` || ']' || ' - ' || '[' || `samples`.`name` || ']' || ' - ' || '"' || `field` || '" from "' || `before` || '" to "' || `after` || '"') as 'change'
                FROM `history`
                INNER JOIN `samples` ON `history`.`table_rowid`=`samples`.`rowid`
                WHERE `table`='samples'"""
        ):
            results[record["time"] + " " + record["id"]] = record["change"]

        return results


def get_validated_variants_table(conn: sqlite3.Connection, sample_id: int):
    """
    Creates a table for all variants with classification > 1 for the current sample, with the columns:
    variant_name (from config)
    GT
    VAF (if it exists)
    sample_has_variant tag
    sample_has_variant comment
    variant comment

    :return: the data as a list of tuples$
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

class SampleDialog(QDialog):
    def __init__(self, conn, sample_id, parent=None):
        super().__init__()

        self.sample_id = sample_id
        self.w = SampleWidget(conn)
        self.button_box = QDialogButtonBox(QDialogButtonBox.Save | QDialogButtonBox.Cancel)
        vLayout = QVBoxLayout(self)
        vLayout.addWidget(self.w)
        vLayout.addWidget(self.button_box)

        self.load()

        self.button_box.accepted.connect(self.save)
        self.button_box.rejected.connect(self.reject)

        # self.resize(800, 600)

    def load(self):
        self.w.load(self.sample_id)
        self.setWindowTitle(self.w.windowTitle())

    def save(self):
        self.w.save(self.sample_id)
        self.accept()


if __name__ == "__main__":
    import sys
    from cutevariant.core import sql

    app = QApplication(sys.argv)

    # conn = sql.get_sql_connection("/home/sacha/exome/exome.db")
    conn = sql.get_sql_connection("C:/Users/Ichtyornis/Projects/cutevariant/edit_sample_update.db")

    w = SampleDialog(conn, 1)

    w.show()

    app.exec_()
