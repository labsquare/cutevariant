from PySide6.QtWidgets import *
from PySide6.QtCore import *
from PySide6.QtGui import *
import os
from cutevariant.gui.widgets.import_widget import VcfImportWidget, ImportThread
from cutevariant.gui.widgets import DictWidget

from cutevariant.core import sql

from cutevariant import LOGGER


class ProjectPage(QWizardPage):
    def __init__(self, parent=None):
        super().__init__()

        self.setTitle(self.tr("Create project"))
        self.setSubTitle(self.tr("Name your database where to import data"))

        self.name_edit = QLineEdit()
        self.name_edit.textChanged.connect(self.completeChanged)
        self.path_edit = QLineEdit()
        self.path_edit.textChanged.connect(self.completeChanged)

        self.browse_btn = QPushButton(self.tr("Browse..."))
        self.browse_btn.clicked.connect(self._browse)

        # button box
        path_layout = QHBoxLayout()
        path_layout.addWidget(self.path_edit)
        path_layout.addWidget(self.browse_btn)

        form_layout = QFormLayout()
        form_layout.addRow(self.tr("Name:"), self.name_edit)
        form_layout.addRow(self.tr("Create in:"), path_layout)

        self.setLayout(form_layout)

    def _browse(self):
        path = QFileDialog.getExistingDirectory(self, self.tr("Select a folder"), QDir.homePath())
        if path:
            self.path_edit.setText(path)

    def db_filename(self):
        return QDir(self.path_edit.text()).filePath(self.name_edit.text()) + ".db"

    def validatePage(self):
        name = self.name_edit.text()
        db_filename = self.db_filename()

        if os.path.exists(db_filename):
            reply = QMessageBox.warning(
                self,
                self.tr("Overwrite ?"),
                self.tr(
                    f"a <b>{name}.db</b> project already exists in this directory. <br>"
                    "Would you like to overwrite it ? All data will be lost."
                ),
                QMessageBox.Yes | QMessageBox.No,
            )

            if reply == QMessageBox.Yes:
                os.remove(db_filename)
                return True
            else:
                return False

        return True

    def initializePage(self):
        """Overridden: Prepare the page just before it is shown"""
        # Adjust the focus of project name field
        self.name_edit.setFocus()
        self.path_edit.setText(QDir.homePath())

    def isComplete(self):
        """Conditions to unlock next button"""

        return (
            True
            if (
                QDir(self.path_edit.text()).exists()
                and self.path_edit.text()
                and self.name_edit.text()
            )
            else False
        )


class FilePage(QWizardPage):
    def __init__(self, parent=None):
        super().__init__()

        self.widget = VcfImportWidget()
        vlayout = QVBoxLayout(self)
        vlayout.setContentsMargins(0, 0, 0, 0)
        vlayout.addWidget(self.widget)

    def filename(self):
        return self.widget.filename()

    def pedfile(self):
        return self.widget.pedfile()


class ImportPage(QWizardPage):

    completeChanged = Signal()

    def __init__(self, parent=None):
        super().__init__()

        self.setTitle(self.tr("Import file"))
        self.setSubTitle(self.tr("Please click on Import/Stop to start or stop the process."))

        # Async stuff
        self.thread_finished = False  # True if import process is correctly finished
        self.thread: ImportThread = ImportThread()
        self.progress = QProgressBar()
        self.stop_button = QPushButton(self.tr("Stop"))
        self.stop_button.clicked.connect(self.stop_thread)

        v_layout = QHBoxLayout()
        v_layout.addWidget(self.progress)
        v_layout.addWidget(self.stop_button)

        m_layout = QVBoxLayout()

        self.log_edit = QPlainTextEdit()
        self.tab_widget = QTabWidget()
        self.tab_widget.addTab(self.log_edit, "log")

        m_layout.addLayout(v_layout)
        m_layout.addWidget(self.tab_widget)
        self.setLayout(m_layout)

        self.timer = QElapsedTimer()

        # self.db_filename = None

        # # Ignored field from previous page; see initializePage()
        # self.ignored_fields = set()

        # self.annotation_parser = None

        self.thread.started.connect(self.timer.start)

        self.thread.progress_changed.connect(self.show_progress)
        self.thread.finished_status.connect(self.import_thread_finished)

        # # Note: self.run is automatically launched when ImportPage is displayed
        # # See initializePage()

        # self.thread.progress_changed.connect(self.progress_changed)
        # self.thread.finished_status.connect(self.import_thread_finished_status)

    def initializePage(self):

        self.thread_finished = False
        self.thread.db_filename = self.wizard().page(0).db_filename()
        self.thread.filename = self.wizard().page(1).filename()
        self.thread.pedfile = self.wizard().page(1).pedfile()
        self.thread.import_id = self.wizard().page(1).widget.get_import_id()
        self.thread.ignored_fields = self.wizard().page(1).widget.get_ignored_fields()
        self.thread.indexed_fields = self.wizard().page(1).widget.get_indexed_fields()
        self.thread.start()

    def import_thread_finished(self, status):
        """Force the activation of the finish button after a successful import"""
        # try:

        self.thread_finished = self.thread.isFinished()

        if status:
            self.completeChanged.emit()

    def show_log(self, message: str):

        timestamp = int(self.timer.elapsed() * 0.001)

        time_str = f"{timestamp//3600:02d}:{timestamp//60:02d}:{timestamp%60:02d}"

        self.log_edit.appendPlainText(f"[{time_str}] {message}")

    def show_progress(self, percent: float, message: str):
        self.progress.setValue(percent)
        self.show_log(message)

    def isComplete(self):
        """Conditions to unlock finish button"""
        LOGGER.debug("Complete ")
        return self.thread_finished

    def stop_thread(self):
        """Stop the thread and refresh the UI"""
        LOGGER.debug("ImportPage:run: stop thread")
        self.stop_button.setDisabled(True)
        self.thread.stop()
        self.progress.setValue(0)
        self.stop_button.setDisabled(False)


class FinishPage(QWizardPage):
    def __init__(self, parent=None):
        super().__init__(parent)

        self.widget = DictWidget()
        vLayout = QVBoxLayout(self)
        vLayout.addWidget(self.widget)

    def initializePage(self):
        self.db_filename = self.wizard().page(0).db_filename()
        conn = sql.get_sql_connection(self.db_filename)
        self.widget.set_dict(sql.get_summary(conn))


class ProjectWizard(QWizard):
    def __init__(self, parent=None):
        super().__init__()

        self.addPage(ProjectPage())
        self.addPage(FilePage())
        self.addPage(ImportPage())
        # self.addPage(FinishPage())
        self.setWizardStyle(QWizard.ClassicStyle)

        self.resize(800, 600)

    def db_filename(self):
        return self.page(0).db_filename()


if __name__ == "__main__":
    import sys

    app = QApplication(sys.argv)

    prj = ProjectWizard()
    prj.show()

    app.exec_()
