"""Plugin to show all characteristics of a selected variant

VariantInfoWidget is showed on the GUI, it uses VariantPopupMenu to display a
contextual menu about the variant which is selected.
VariantPopupMenu is also used in viewquerywidget for the same purpose.
"""
from logging import DEBUG

# Qt imports
from PySide2.QtCore import QModelIndex, Qt, Slot, QSize
from PySide2.QtWidgets import *
from PySide2.QtGui import QFont, QColor

# Custom imports
from cutevariant.gui import FIcon, style
from cutevariant.core import sql, get_sql_connection
from cutevariant.gui.plugin import PluginWidget
from cutevariant import commons as cm

from cutevariant.gui.widgets import DictWidget


from cutevariant.gui.widgets.qjsonmodel import QJsonModel

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

        self._has_changed = False

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
        # self.comment_preview.setFrameStyle(QFrame.NoFrame)
        # self.comment_preview.viewport().setAutoFillBackground(False)

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

        self.toolbar = QToolBar()

        self.switch_button = QPushButton(self.tr("Edit comment..."))
        self.switch_button.setIcon(FIcon(0xF0354))
        # self.switch_button.setFlat(True)
        self.toolbar.addWidget(self.switch_button)
        # Create spacer
        spacer = QWidget()
        spacer.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.toolbar.addWidget(spacer)

        # Button layout
        save_action = self.toolbar.addAction(self.tr("Save"))
        self.save_button = self.toolbar.widgetForAction(save_action)
        self.save_button.setIcon(FIcon(0xF0E1E, "white"))
        self.save_button.setStyleSheet(
            "QToolButton:enabled{background-color: #038F6A; color:white}"
        )
        self.save_button.setAutoRaise(False)
        self.save_button.setToolButtonStyle(Qt.ToolButtonTextBesideIcon)

        self.toolbar.setIconSize(QSize(16, 16))

        # Main layout
        v_layout = QVBoxLayout()
        v_layout.addWidget(self.toolbar)
        v_layout.addLayout(title_layout)
        v_layout.addWidget(self.stack)
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

    def _on_changed(self):

        self._has_changed = True
        self.save_button.setEnabled(True)


class VariantEditWidget(PluginWidget):
    """Plugin to show all annotations of a selected variant"""

    ENABLE = True
    REFRESH_STATE_DATA = {"current_variant"}

    def __init__(self, parent=None):
        super().__init__(parent)

        self.setWindowIcon(FIcon(0xF0B73))
        # Current variant => set by on_refresh and on_open_project

        self.edit_panel = EditPanel()

        vlayout = QVBoxLayout(self)
        vlayout.setContentsMargins(0, 0, 0, 0)

        # Build comments tab
        self.edit_panel.saved.connect(self.on_save_variant)

        vlayout.addWidget(self.edit_panel)

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

    def clear(self):
        self.edit_panel.clear()

    def on_open_project(self, conn):
        self.conn = conn
        self.clear()
        self.on_refresh()

    def on_refresh(self):
        """Set the current variant by the variant displayed in the GUI"""
        self.current_variant = self.mainwindow.get_state_data("current_variant")

        if self.current_variant is None:
            return

        variant_id = self.current_variant["id"]
        data = dict(
            [
                (k, v)
                for k, v in sql.get_one_variant(self.conn, variant_id).items()
                if k not in ("variant_id", "sample_id", "annotations", "samples")
            ]
        )
        self.edit_panel.set_data(data)


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
