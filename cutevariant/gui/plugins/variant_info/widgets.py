"""Plugin to show all characteristics of a selected variant

VariantInfoWidget is showed on the GUI, it uses VariantPopupMenu to display a
contextual menu about the variant which is selected.
VariantPopupMenu is also used in viewquerywidget for the same purpose.
"""
from logging import DEBUG

# Qt imports
from PySide2.QtCore import Qt, Slot, QSize
from PySide2.QtWidgets import *
from PySide2.QtGui import QFont

# Custom imports
from cutevariant.gui import FIcon, style
from cutevariant.core import sql, get_sql_connection
from cutevariant.gui.plugin import PluginWidget
from cutevariant import commons as cm

from cutevariant.gui.widgets import DictWidget

LOGGER = cm.logger()


class EditPanel(QFrame):
    """Edit Panel

    A panel box to edit a variant

    get_data: returned updated variant with favorite, comment and classification
    set_data: Fill the formular a variant

    """

    # A signal emit when save button is pressed
    saved = Signal()

    _form_changed = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)

        # Create fav button
        self.fav_button = QToolButton()
        self.fav_button.setCheckable(True)
        self.fav_button.setAutoRaise(True)
        self.fav_button.clicked.connect(self._form_changed)
        icon = QIcon()
        icon.addPixmap(FIcon(0xF00C3).pixmap(32, 32), QIcon.Normal, QIcon.Off)
        icon.addPixmap(FIcon(0xF00C0).pixmap(32, 32), QIcon.Normal, QIcon.On)
        self.fav_button.setIcon(icon)

        # Create classification combobox
        self.class_edit = QComboBox()
        self.class_edit.setFrame(False)
        self.class_edit.currentIndexChanged.connect(self._form_changed)

        for key in style.CLASSIFICATION:
            self.class_edit.addItem(
                FIcon(
                    style.CLASSIFICATION[key]["icon"],
                    style.CLASSIFICATION[key]["color"],
                ),
                style.CLASSIFICATION[key]["name"],
            )

        # Create comment form . This is a stack widget with a PlainText editor
        # and a Markdown preview as QTextBrowser

        self.comment_edit = QPlainTextEdit()
        self.comment_edit.setPlaceholderText("Write a comment in markdown ...")
        self.comment_edit.textChanged.connect(self._form_changed)

        self.comment_preview = QTextBrowser()
        self.comment_preview.setPlaceholderText("Press edit to add a comment ...")
        self.comment_preview.setAlignment(Qt.AlignTop | Qt.AlignLeft)
        self.comment_preview.setOpenExternalLinks(True)
        self.comment_preview.setFrameStyle(QFrame.NoFrame)

        # Create stacked
        self.stack = QStackedWidget()
        self.stack.addWidget(self.comment_edit)
        self.stack.addWidget(self.comment_preview)
        self.stack.setCurrentIndex(1)

        # Build layout
        self.setFrameShape(QFrame.StyledPanel)

        # header  layout
        title_layout = QHBoxLayout()
        title_layout.addWidget(self.class_edit)
        title_layout.addWidget(self.fav_button)

        # Button layout
        self.switch_button = QPushButton(self.tr("Edit comment..."))
        self.switch_button.setFlat(True)
        self.save_button = QPushButton(self.tr("Save"))
        self.save_button.setFlat(True)
        bar_layout = QHBoxLayout()
        bar_layout.addWidget(self.switch_button)
        bar_layout.addStretch()
        bar_layout.addWidget(self.save_button)

        # Main layout
        v_layout = QVBoxLayout()
        v_layout.addLayout(title_layout)
        v_layout.addWidget(self.stack)
        v_layout.addLayout(bar_layout)
        self.setLayout(v_layout)

        # Create connection
        self.switch_button.clicked.connect(self.switch_mode)
        self.save_button.clicked.connect(self._on_save)
        self._form_changed.connect(lambda: self.save_button.setEnabled(True))

    def switch_mode(self):
        """Switch comment mode between editable and previewer"""
        if self.stack.currentWidget() == self.comment_edit:
            self.stack.setCurrentIndex(1)
            self.comment_preview.setMarkdown(str(self.comment_edit.toPlainText()))
            self.switch_button.setText(self.tr("Edit comment..."))
        else:
            self.stack.setCurrentIndex(0)
            self.switch_button.setText(self.tr("Preview comment..."))

    def _on_save(self):
        """ private slot reacting when save_button is pressed """

        if self.stack.currentWidget() == self.comment_edit:
            self.switch_mode()
        self.saved.emit()
        self.save_button.setEnabled(False)

    def set_text(self, text: str):
        """Set comment

        Args:
            text (str): Description

        """
        if text is None:
            self.clear()
            return

        self.comment_edit.setPlainText(str(text))
        try:
            self.comment_preview.setMarkdown(str(text))
        except AttributeError:
            # Fallback Qt 5.14-
            self.comment_preview.setPlainText(str(text))

    def clear(self):
        """Clear comment"""
        self.comment_edit.clear()
        self.comment_preview.clear()

    def set_data(self, variant: dict):
        """Set Form with variant data

        Args:
            variant (dict):

        Exemples:
            w.set_data({"favorite": 1, "comment":'salut', "classification":4})
        """

        self.clear()
        if "classification" in variant:
            self.class_edit.setCurrentIndex(variant["classification"])

        if "comment" in variant:
            self.set_text(variant["comment"])

        if "favorite" in variant:
            self.fav_button.setChecked(
                Qt.Checked if variant["favorite"] else Qt.Unchecked
            )

        self.save_button.setEnabled(False)

    def get_data(self) -> dict:
        """Get variant data from Form input

        Returns:
            dict: variant updated data
        """
        return {
            "classification": self.class_edit.currentIndex(),
            "comment": self.comment_edit.toPlainText(),
            "favorite": int(self.fav_button.isChecked()),
        }


class VariantInfoWidget(PluginWidget):
    """Plugin to show all annotations of a selected variant"""

    ENABLE = True

    def __init__(self, parent=None):
        super().__init__(parent)

        self.setWindowIcon(FIcon(0xF0B73))
        # Current variant => set by on_refresh and on_open_project
        self.current_variant = None

        self.view = QTabWidget()
        self.toolbar = QToolBar()
        # self.toolbar.setIconSize(QSize(16, 16))

        # Build comments tab
        self.edit_panel = EditPanel()
        self.edit_panel.saved.connect(self.on_save_variant)
        self.view.addTab(self.edit_panel, self.tr("User"))

        # Build variant tab
        self.variant_view = DictWidget()
        self.variant_view.set_header_visible(True)

        self.view.addTab(self.variant_view, self.tr("Variant"))

        # Build transcript tab
        self.transcript_combo = QComboBox()
        self.transcript_view = DictWidget()
        self.transcript_view.set_header_visible(True)
        tx_layout = QVBoxLayout()
        tx_layout.addWidget(self.transcript_combo)
        tx_layout.addWidget(self.transcript_view)
        tx_widget = QWidget()
        tx_widget.setLayout(tx_layout)
        self.view.addTab(tx_widget, self.tr("Transcripts"))
        self.transcript_combo.currentIndexChanged.connect(self.on_transcript_changed)

        # Build Samples tab
        self.sample_combo = QComboBox()
        self.sample_view = DictWidget()
        self.sample_view.set_header_visible(True)

        tx_layout = QVBoxLayout()
        tx_layout.addWidget(self.sample_combo)
        tx_layout.addWidget(self.sample_view)
        tx_widget = QWidget()
        tx_widget.setLayout(tx_layout)
        self.view.addTab(tx_widget, self.tr("Samples"))
        self.sample_combo.currentIndexChanged.connect(self.on_sample_changed)

        # Build genotype tab
        self.genotype_view = QListWidget()
        # self.genotype_view.setIconSize(QSize(20, 20))
        self.view.addTab(self.genotype_view, self.tr("Genotypes"))

        v_layout = QVBoxLayout()
        v_layout.setContentsMargins(0, 0, 0, 0)
        v_layout.addWidget(self.view)
        self.setLayout(v_layout)

        # # Create menu
        # TODO: restore this
        # self.context_menu = VariantPopupMenu()
        # # Ability to trigger the menu
        # self.view.setContextMenuPolicy(Qt.CustomContextMenu)
        # self.view.customContextMenuRequested.connect(self.show_menu)
        # self.add_tab("variants")

        # Cache all database fields and their descriptions for tooltips
        # Field names as keys, descriptions as values
        self.fields_descriptions = None

        # Cache genotype icons
        # Values in gt field as keys (str), FIcon as values
        self.genotype_icons = {
            key: FIcon(val) for key, val in cm.GENOTYPE_ICONS.items()
        }

    def clear(self):
        """ Clear all view """
        self.variant_view.clear()
        self.transcript_view.clear()
        self.sample_view.clear()
        self.genotype_view.clear()
        self.edit_panel.clear()

    def on_save_variant(self):

        # if view is visible
        if "variant_view" in self.mainwindow.plugins:
            variant_view = self.mainwindow.plugins["variant_view"]

            update_data = self.edit_panel.get_data()

            index = variant_view.main_right_pane.view.currentIndex()
            variant_view.main_right_pane.model.update_variant(index.row(), update_data)

            # variant_view.main_right_pane.model.update_variant(index.row(), update_data)

        else:
            # TODO BUT UNNECESSARY because we always have a variant_viex ...
            # Save directly in database ?
            pass

    def on_open_project(self, conn):
        self.conn = conn
        self.clear()
        self.on_refresh()
        # Cache DB fields descriptions
        self.fields_descriptions = {
            field["name"]: field["description"] for field in sql.get_fields(self.conn)
        }

    def on_refresh(self):
        """Set the current variant by the variant displayed in the GUI"""
        self.current_variant = self.mainwindow.state.current_variant
        self.populate()

    def populate(self):
        """Show the current variant attributes on the TreeWidget

        .. note:: RichText in Markdown is supported starting PySide 5.14
        """
        if not self.current_variant or "id" not in self.current_variant:
            return

        variant_id = self.current_variant["id"]

        # Populate variant
        data = dict(
            [
                (k, v)
                for k, v in sql.get_one_variant(self.conn, variant_id).items()
                if k not in ("variant_id", "sample_id", "annotations", "samples")
            ]
        )
        self.variant_view.set_dict(data)

        self.edit_panel.set_data(data)

        title = "{chr}:{pos} {ref}>{alt}".format(**data)
        # self.parent().setWindowTitle(title)

        # Populate annotations
        self.transcript_combo.blockSignals(True)
        self.transcript_combo.clear()

        for annotation in sql.get_annotations(self.conn, variant_id):
            if "transcript" in annotation:
                self.transcript_combo.addItem(annotation["transcript"], annotation)
        self.on_transcript_changed()
        self.transcript_combo.blockSignals(False)

        # Populate samples
        self.sample_combo.blockSignals(True)
        self.sample_combo.clear()
        for sample in sql.get_samples(self.conn):
            self.sample_combo.addItem(sample["name"], sample["id"])
        self.on_sample_changed()
        self.sample_combo.blockSignals(False)

        # Populate genotypes for samples
        self.genotype_view.clear()
        query = f"""SELECT samples.name, sv.gt FROM samples 
                 LEFT JOIN sample_has_variant sv ON samples.id = sv.sample_id 
                 AND sv.variant_id = {variant_id}"""

        for sample_name, genotype in self.conn.execute(query):
            item = QListWidgetItem()
            icon = self.genotype_icons.get(genotype, self.genotype_icons[-1])

            item.setText(sample_name)
            item.setIcon(icon)
            item.setToolTip(cm.GENOTYPE_DESC.get(genotype, -1))

            self.genotype_view.addItem(item)

    @Slot()
    def on_transcript_changed(self):
        """This method is triggered when transcript change from combobox

        Fill fields & values for selected transcript.
        """
        annotations = self.transcript_combo.currentData()
        self.transcript_view.set_dict(annotations)

    @Slot()
    def on_sample_changed(self):
        """This method is triggered when sample change from combobox

        Fill fields & values for selected sample.
        """
        sample_id = self.sample_combo.currentData()
        variant_id = self.current_variant["id"]

        self.sample_view.set_dict(
            sql.get_sample_annotations(self.conn, variant_id, sample_id)
        )

    # @Slot()
    # def on_save_clicked(self):
    #     """Save button
    #     """
    #     classification = self.classification_box.currentIndex()
    #     favorite = self.favorite_checkbox.isChecked()
    #     comment = self.comment_input.toPlainText()

    #     updated = {
    #         "classification": classification,
    #         "favorite": favorite,
    #         "comment": comment,
    #     }

    #     if "variant_view" in self.mainwindow.plugins:
    #         main_view = self.mainwindow.plugins["variant_view"]
    #         print(main_view)

    # sql.update_variant(self.conn, updated)

    # def show_menu(self, pos: QPoint):
    #     """Show context menu associated to the current variant"""
    #     if not self.current_variant:
    #         return
    #     self.context_menu.popup(self.current_variant, self.view.mapToGlobal(pos))


if __name__ == "__main__":
    import sys

    app = QApplication(sys.argv)

    conn = get_sql_connection("/home/schutz/Dev/cutevariant/examples/test.db")

    w = VariantInfoWidget()
    w.conn = conn

    variant = sql.get_one_variant(conn, 1)

    w.current_variant = variant

    w.show()

    app.exec_()
