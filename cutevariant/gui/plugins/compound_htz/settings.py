## ================= Settings widgets ===================
# Qt imports
from PySide6.QtCore import *
from PySide6.QtGui import QStandardItem, QStandardItemModel
from PySide6.QtWidgets import *

# Custom imports
from cutevariant.gui.plugin import PluginSettingsWidget
from cutevariant.gui.settings import AbstractSettingsWidget
from cutevariant.gui import FIcon
import cutevariant.constants as cst

import typing

class QHLine(QFrame):
    def __init__(self):
        super(QHLine, self).__init__()
        self.setFrameShape(QFrame.HLine)
        self.setFrameShadow(QFrame.Sunken)


class GeneralSettings(AbstractSettingsWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("General")
        self.setWindowIcon(FIcon(0xF070F))
        label = QLabel(
            """
            Define how to select compound htz variants
            """
        )
        label.setTextFormat(Qt.RichText)

        definition_form = QFormLayout()
        self.gene_edit = QLineEdit()
        self.filter_edit = QLineEdit()
        self.gene_edit.setPlaceholderText("ann.gene")
        self.filter_edit.setPlaceholderText("tags !IN ('#ARTIFACT') AND classification >= 0")

        definition_form.addRow("Gene field:", self.gene_edit)
        definition_form.addRow("VQL filter:", self.filter_edit)

        tag_form = QFormLayout()
        self.tag_edit = QLineEdit()
        self.tag_edit.setPlaceholderText("#COMPOUND_HTZ")
        tag_form.addRow("Tag identifying compound htz:", self.tag_edit)


        vlayout = QVBoxLayout(self)
        vlayout.addWidget(label)
        vlayout.addLayout(definition_form)
        vlayout.addWidget(QHLine())
        vlayout.addLayout(tag_form)

    def save(self):

        config = self.section_widget.create_config()
        config["gene_field"] = self.gene_edit.text()
        config["vql_filter"] = self.filter_edit.text()
        config["tag"] = self.tag_edit.text()
        config.save()

    def load(self):
        config = self.section_widget.create_config()
        gene = config.get("gene_field", "ann.gene")
        vql_filter = config.get("vql_filter", None)
        tag = config.get("tag", "#COMPOUND_HTZ")
        self.gene_edit.setText(gene)
        self.filter_edit.setText(vql_filter)
        self.tag_edit.setText(tag)


class CompoundHtzSettingsWidget(PluginSettingsWidget):
    """Instantiated plugin in the settings panel of Cutevariant
    """

    ENABLE = True

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowIcon(FIcon(0xF1542))
        self.setWindowTitle("Compound htz")
        self.add_page(GeneralSettings())


if __name__ == "__main__":
    import sys

    app = QApplication(sys.argv)
    dlg = CompoundHtzSettingsWidget()
    dlg.show()
    exit(app.exec_())
