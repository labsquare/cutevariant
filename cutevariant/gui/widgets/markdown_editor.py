# Standard imports
from pkg_resources import parse_version

# Qt imports
from PySide6 import __version__ as pyside_version
from PySide6.QtCore import Qt, QSize
from PySide6.QtGui import QKeySequence, QIcon, QActionGroup
from PySide6.QtWidgets import (
    QTextEdit,
    QDialog,
    QApplication,
    QWidget,
    QStackedWidget,
    QVBoxLayout,
    QHBoxLayout,
    QSizePolicy,
    QPushButton,
    QToolBar,
    QPlainTextEdit,
    QSplitter,
    QDialogButtonBox,
)

# Custom imports
from cutevariant.gui.ficon import FIcon
from cutevariant import constants as cst

from cutevariant import LOGGER


class MarkdownEditor(QWidget):
    """Markdown editor used to add comments on variants

    On PySide6 5.14+, comments can be edited in Markdown and previewed.

    """

    def __init__(self, parent=None, default_text=""):
        """Init Markdown editor

        :param default_text: Populate source edit with current comment in db.
        :type default_text: <str>
        """
        super().__init__(parent)

        self.setWindowTitle("Cutevariant - " + self.tr("Comment editor"))
        self.setWindowIcon(QIcon(cst.DIR_ICONS + "app.png"))

        self.stack_widget = QStackedWidget()

        main_vlayout = QVBoxLayout()
        # main_vlayout.setContentsMargins(0, 0, 0, 0)
        self.setLayout(main_vlayout)

        # Setup edit view
        self.source_edit = QPlainTextEdit()  # Markdown content
        self.rich_edit = QTextEdit()
        self.source_edit.setPlainText(default_text)
        self.stack_widget.addWidget(self.source_edit)

        self.rich_edit.setAcceptRichText(True)
        self.rich_edit.setAutoFormatting(QTextEdit.AutoAll)
        self.rich_edit.setReadOnly(True)
        self.stack_widget.addWidget(self.rich_edit)

        # Setup toolbar
        self.toolbar = QToolBar()
        self.editor_actions = QActionGroup(self)
        self.toolbar.setIconSize(QSize(16, 16))
        self.act_undo = self.toolbar.addAction(self.tr("undo"), self.source_edit.undo)
        self.act_undo.setIcon(FIcon(0xF054C))
        self.act_undo.setShortcut(QKeySequence.Undo)
        self.editor_actions.addAction(self.act_undo)

        self.act_redo = self.toolbar.addAction(self.tr("redo"), self.source_edit.redo)
        self.act_redo.setIcon(FIcon(0xF044E))
        self.act_redo.setShortcut(QKeySequence.Redo)
        self.editor_actions.addAction(self.act_redo)

        self.act_bold = self.toolbar.addAction(self.tr("bold"), lambda: self.infix("**"))
        self.act_bold.setIcon(FIcon(0xF0264))
        self.act_bold.setShortcut(QKeySequence("CTRL+B"))
        self.editor_actions.addAction(self.act_bold)

        self.act_italic = self.toolbar.addAction(self.tr("italic"), lambda: self.infix("*"))
        self.act_italic.setIcon(FIcon(0xF0277))
        self.act_italic.setShortcut(QKeySequence("CTRL+I"))
        self.editor_actions.addAction(self.act_italic)

        self.act_heading = self.toolbar.addAction(self.tr("insert title"), lambda: self.heading())
        self.act_heading.setShortcut(QKeySequence("CTRL+H"))
        self.act_heading.setIcon(FIcon(0xF0274))
        self.editor_actions.addAction(self.act_heading)

        self.act_unorder_list = self.toolbar.addAction(
            self.tr("insert list item"), self.unorder_list
        )
        self.act_unorder_list.setIcon(FIcon(0xF0279))
        self.editor_actions.addAction(self.act_unorder_list)

        self.act_quote = self.toolbar.addAction(self.tr("quote"), self.quote)
        self.act_quote.setIcon(FIcon(0xF027E))
        self.editor_actions.addAction(self.act_quote)

        self.act_link = self.toolbar.addAction(self.tr("insert link"), self.link)
        self.act_link.setIcon(FIcon(0xF0339))
        self.editor_actions.addAction(self.act_link)

        self.preview_btn = QPushButton("Preview")
        self.preview_btn.setCheckable(True)
        self.preview_btn.toggled.connect(self.toggle_edit_mode)
        spacer = QWidget()
        spacer.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.toolbar.addWidget(spacer)
        self.toolbar.addWidget(self.preview_btn)

        main_vlayout.addWidget(self.toolbar)
        main_vlayout.addWidget(self.stack_widget)
        main_vlayout.setContentsMargins(0, 0, 0, 0)

    def toggle_edit_mode(self, mode: bool = True):
        self.stack_widget.setCurrentIndex(int(mode))
        self.editor_actions.setDisabled(mode)
        if mode:
            self.update_rich_text()

    def update_rich_text(self):
        """Update preview with Markdown content

        .. warning:: Depends PySide Qt5.14
        """
        self.rich_edit.setMarkdown(self.source_edit.toPlainText())

    def infix(self, prefix: str, suffix=None):
        """Add tags before and after the selected text"""
        if suffix is None:
            suffix = prefix

        cursor = self.source_edit.textCursor()

        if not cursor.hasSelection():
            cursor.insertText(f"{prefix}Text{suffix}")
            return

        start = cursor.selectionStart()
        end = cursor.selectionEnd()

        # must be made in 1 step to avoid flooding the history (do/undo)
        text = self.source_edit.toPlainText()
        cursor.insertText(prefix + text[start:end] + suffix)

    def heading(self):
        """Add header tag before selected text"""
        cursor = self.source_edit.textCursor()

        if not cursor.hasSelection():
            cursor.insertText("# Title")
            return

        start = cursor.selectionStart()
        cursor.setPosition(start)
        cursor.insertText("# ")

    def unorder_list(self):
        """Add list tag before selected text"""
        cursor = self.source_edit.textCursor()

        if not cursor.hasSelection():
            cursor.insertText("- List item")
            return

        start = cursor.selectionStart()
        cursor.setPosition(start)
        cursor.insertText("- ")

    def quote(self):
        """Quote the selected text"""
        cursor = self.source_edit.textCursor()

        if not cursor.hasSelection():
            cursor.insertText("> text")
            return

        start = cursor.selectionStart()
        end = cursor.selectionEnd()

        # must be made in 1 step to avoid flooding the history (do/undo)
        text = self.source_edit.toPlainText()
        cursor.insertText("\n> %s\n" % text[start:end])

    def link(self):
        """Format selected text into URL link"""
        cursor = self.source_edit.textCursor()

        if not cursor.hasSelection():
            cursor.insertText("[text](url)")
            return

        start = cursor.selectionStart()
        end = cursor.selectionEnd()

        # must be made in 1 step to avoid flooding the history (do/undo)
        text = self.source_edit.toPlainText()
        cursor.insertText("[text](%s)" % text[start:end])

    def toPlainText(self):
        """Get source text from the current comment

        Used to save the comment in the database by variant_view plugin.
        """
        return self.source_edit.toPlainText()

    def setPlainText(self, text):
        self.source_edit.setPlainText(text)
        self.update_rich_text()


class MarkdownDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__()

        self.widget = MarkdownEditor()

        self.ok_button = QPushButton(self.tr("Ok"))
        self.cancel_button = QPushButton(self.tr("Cancel"))

        btn_layout = QHBoxLayout()
        btn_layout.addWidget(self.ok_button)
        btn_layout.addWidget(self.cancel_button)

        vLayout = QVBoxLayout(self)
        vLayout.addWidget(self.widget)
        vLayout.addLayout(btn_layout)

        self.ok_button.clicked.connect(self.accept)
        self.cancel_button.clicked.connect(self.reject)


if __name__ == "__main__":
    import sys
    from cutevariant.gui.ficon import setFontPath
    import cutevariant.constants as cst

    app = QApplication(sys.argv)

    setFontPath(cst.FONT_FILE)

    edit = MarkdownDialog()

    edit.show()

    app.exec_()
