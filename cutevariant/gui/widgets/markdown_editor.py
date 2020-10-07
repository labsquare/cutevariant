# Standard imports
from pkg_resources import parse_version

# Qt imports
from PySide2 import __version__ as pyside_version
from PySide2.QtCore import Qt
from PySide2.QtGui import QKeySequence, QIcon
from PySide2.QtWidgets import (
    QTextEdit,
    QDialog,
    QApplication,
    QVBoxLayout,
    QToolBar,
    QPlainTextEdit,
    QSplitter,
    QDialogButtonBox,
)

# Custom imports
from cutevariant.gui.ficon import FIcon
from cutevariant import commons as cm

LOGGER = cm.logger()


class MarkdownEditor(QDialog):
    """Markdown editor used to add comments on variants

    On PySide2 5.14+, comments can be edited in Markdown and previewed.

    """

    def __init__(self, parent=None, default_text=""):
        """Init Markdown editor

        :param default_text: Populate source edit with current comment in db.
        :type default_text: <str>
        """
        super().__init__(parent)

        self.setWindowTitle("Cutevariant - " + self.tr("Comment editor"))
        self.setWindowIcon(QIcon(cm.DIR_ICONS + "app.png"))

        main_vlayout = QVBoxLayout()
        # main_vlayout.setContentsMargins(0, 0, 0, 0)
        self.setLayout(main_vlayout)

        # Setup edit view
        self.rich_edit = QTextEdit()  # Rich text result
        self.source_edit = QPlainTextEdit()  # Markdown content
        self.source_edit.setPlainText(default_text)

        vlayout = QVBoxLayout()
        vlayout.setSpacing(1)
        vlayout.setContentsMargins(0, 0, 0, 0)
        main_vlayout.addLayout(vlayout)

        self.splitter = QSplitter(Qt.Horizontal)
        self.splitter.addWidget(self.source_edit)

        if parse_version(pyside_version) >= parse_version("5.14"):
            # RichText in Markdown is supported starting PySide 5.14
            self.splitter.addWidget(self.rich_edit)
            # self.rich_edit.setStyleSheet(
            #     "QWidget {background-color:'lightgray'}")
            self.rich_edit.setAcceptRichText(True)
            self.rich_edit.setAutoFormatting(QTextEdit.AutoAll)
            self.rich_edit.setReadOnly(True)

            # Update preview with Markdown content
            self.source_edit.textChanged.connect(self.update_rich_text)
            # Auto refresh rich text content now
            self.update_rich_text()

        # Setup toolbar
        self.toolbar = QToolBar()
        self.act_undo = self.toolbar.addAction(self.tr("undo"), self.source_edit.undo)
        self.act_undo.setIcon(FIcon(0xF054C))
        self.act_undo.setShortcut(QKeySequence.Undo)

        self.act_redo = self.toolbar.addAction(self.tr("redo"), self.source_edit.redo)
        self.act_redo.setIcon(FIcon(0xF044E))
        self.act_redo.setShortcut(QKeySequence.Redo)

        self.act_bold = self.toolbar.addAction(
            self.tr("bold"), lambda: self.infix("**")
        )
        self.act_bold.setIcon(FIcon(0xF0264))
        self.act_bold.setShortcut(QKeySequence("CTRL+B"))

        self.act_italic = self.toolbar.addAction(
            self.tr("italic"), lambda: self.infix("*")
        )
        self.act_italic.setIcon(FIcon(0xF0277))
        self.act_italic.setShortcut(QKeySequence("CTRL+I"))

        self.act_heading = self.toolbar.addAction(
            self.tr("insert title"), lambda: self.heading()
        )
        self.act_heading.setShortcut(QKeySequence("CTRL+H"))
        self.act_heading.setIcon(FIcon(0xF0274))

        self.act_unorder_list = self.toolbar.addAction(
            self.tr("insert list item"), self.unorder_list
        )
        self.act_unorder_list.setIcon(FIcon(0xF0279))

        self.act_quote = self.toolbar.addAction(self.tr("quote"), self.quote)
        self.act_quote.setIcon(FIcon(0xF027E))

        self.act_link = self.toolbar.addAction(self.tr("insert link"), self.link)
        self.act_link.setIcon(FIcon(0xF0339))

        vlayout.addWidget(self.toolbar)
        vlayout.addWidget(self.splitter)

        # Add buttons
        buttons = QDialogButtonBox(QDialogButtonBox.Save | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        main_vlayout.addWidget(buttons)

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


if __name__ == "__main__":
    import sys
    from cutevariant.gui.ficon import setFontPath
    import cutevariant.commons as cm

    app = QApplication(sys.argv)

    setFontPath(cm.FONT_FILE)

    edit = MarkdownEditor()

    edit.show()

    app.exec_()
