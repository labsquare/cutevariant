from PySide2.QtWidgets import (
    QTextEdit,
    QWidget,
    QApplication,
    QVBoxLayout,
    QToolBar,
    QTabWidget,
    QPlainTextEdit,
    QSplitter,
    QAction,
    QTextBrowser,
)

from PySide2.QtCore import Qt

from PySide2.QtGui import QKeySequence, QIcon

from cutevariant.gui.ficon import FIcon


class MarkdownEditor(QWidget):
    def __init__(self, parent=None):
        super().__init__()
        self.toolbar = QToolBar()
        self.tabwidget = QTabWidget()
        self.rich_edit = QTextEdit()
        self.source_edit = QPlainTextEdit()
        vlayout = QVBoxLayout()

        # self.rich_edit.setStyleSheet("QWidget {background-color:'lightgray'}")

        self.splitter = QSplitter(Qt.Horizontal)
        self.splitter.addWidget(self.source_edit)
        self.splitter.addWidget(self.rich_edit)

        self.rich_edit.setAcceptRichText(True)
        self.rich_edit.setAutoFormatting(QTextEdit.AutoAll)

        #  Setup toolbar
        self.act_undo = self.toolbar.addAction("undo", self.source_edit.undo)
        self.act_undo.setIcon(FIcon(0xF054C))
        self.act_undo.setShortcut(QKeySequence.Undo)

        self.act_redo = self.toolbar.addAction("redo", self.source_edit.redo)
        self.act_redo.setIcon(FIcon(0xF044E))
        self.act_redo.setShortcut(QKeySequence.Redo)

        self.act_bold = self.toolbar.addAction("bold", lambda: self.infix("**"))
        self.act_bold.setIcon(FIcon(0xF0264))
        self.act_bold.setShortcut(QKeySequence("CTRL+B"))

        self.act_italic = self.toolbar.addAction("italic", lambda: self.infix("*"))
        self.act_italic.setIcon(FIcon(0xF0277))
        self.act_italic.setShortcut(QKeySequence("CTRL+I"))

        self.act_heading = self.toolbar.addAction("heading", lambda: self.heading())
        self.act_heading.setShortcut(QKeySequence("CTRL+H"))
        self.act_heading.setIcon(FIcon(0xF0274))

        self.act_unorder_list = self.toolbar.addAction("unorder_list", self.u_list)
        self.act_unorder_list.setIcon(FIcon(0xF0279))

        self.act_quote = self.toolbar.addAction("quote")
        self.act_quote.setIcon(FIcon(0xF027E))

        self.act_link = self.toolbar.addAction("link")
        self.act_link.setIcon(FIcon(0xF0339))

        vlayout.addWidget(self.toolbar)
        vlayout.addWidget(self.splitter)

        self.setLayout(vlayout)

        #  Depend PySide Qt5.14
        self.source_edit.textChanged.connect(self.update_rich_text)

    def update_rich_text(self):
        self.rich_edit.setMarkdown(self.source_edit.toPlainText())

    def infix(self, prefix: str, suffix=None):

        if suffix is None:
            suffix = prefix

        if not self.source_edit.textCursor().hasSelection():
            self.source_edit.textCursor().insertText(f"{text}Text{text}")
            return

        start = self.source_edit.textCursor().selectionStart()
        end = self.source_edit.textCursor().selectionEnd()

        cursor = self.source_edit.textCursor()
        cursor.setPosition(start)
        cursor.insertText(text)
        cursor.setPosition(end + len(text))
        cursor.insertText(text)

    def heading(self):

        if not self.source_edit.textCursor().hasSelection():
            self.source_edit.textCursor().insertText(f"# Heading")
            return

        start = self.source_edit.textCursor().selectionStart()
        cursor = self.source_edit.textCursor()
        cursor.setPosition(start)
        cursor.insertText("# ")

    def u_list(self):

        if not self.source_edit.textCursor().hasSelection():
            self.source_edit.textCursor().insertText(f"- List item")
            return

        start = self.source_edit.textCursor().selectionStart()
        cursor = self.source_edit.textCursor()

        cursor.setPosition(start)
        cursor.insertText("- ")

    def on_return_pressed(self):
        pass


if __name__ == "__main__":
    import sys
    from cutevariant.gui.ficon import setFontPath

    app = QApplication(sys.argv)

    setFontPath("../../assets/fonts/materialdesignicons-webfont.ttf")

    edit = MarkdownEditor()

    edit.show()

    app.exec_()
