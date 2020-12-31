from PySide2.QtWidgets import QLineEdit, QPushButton, QFileDialog, QAction, QStyle
from PySide2.QtGui import QFont
import os


class FileEdit(QLineEdit):
    def __init__(self, parent=None):
        super().__init__(parent)

        self.path_type = "file"  #  or directory

        self._open_action = QAction(
            qApp.style().standardIcon(QStyle.SP_DialogOpenButton), "open"
        )

        self._error_action = QAction(
            qApp.style().standardIcon(QStyle.SP_MessageBoxCritical), "error"
        )

        self.addAction(self._open_action, QLineEdit.TrailingPosition)
        self.addAction(self._error_action, QLineEdit.LeadingPosition)
        self._error_action.setVisible(False)
        self._open_action.triggered.connect(self._browse_file)
        self.textChanged.connect(self._text_changed)

    def set_path_type(self, path_type: str):

        self.path_type = path_type

    def _browse_file(self):

        if self.path_type == "file":
            path, _ = QFileDialog.getOpenFileName(self, "set a filename")

        if self.path_type == "dir":
            path = QFileDialog.getExistingDirectory(self, "get a directory")

        if path:
            self.setText(path)

    def _text_changed(self):
        if self.text() == "":
            self._error_action.setVisible(False)
        else:
            self._error_action.setVisible(not self.exists())

    def exists(self):
        return os.path.exists(self.text())


if __name__ == "__main__":
    from PySide2.QtWidgets import QApplication
    import sys

    app = QApplication(sys.argv)

    w = FileEdit()
    w.show()

    app.exec_()
