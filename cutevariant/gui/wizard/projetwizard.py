from PySide2.QtWidgets import *
from PySide2.QtCore import *

import os
import sqlite3
from cutevariant.core.importer import async_import_file


class ProjetPage(QWizardPage):
    def __init__(self):
        super().__init__()

        self.setTitle("Project creation")
        self.setSubTitle("This wizard will guide you to create a cutevariant project.")

        self.projet_name_edit = QLineEdit()
        self.projet_path_edit = QLineEdit()
        self.projet_path_edit.setText(os.getcwd())
        self.browse_button = QPushButton("Browse")
        self.reference = QComboBox()

        self.reference.addItem("hg19")
        self.registerField("project_name", self.projet_name_edit, "text")
        self.registerField("project_path", self.projet_path_edit, "text")
        self.registerField("reference", self.reference, "currentText")

        v_layout = QFormLayout()

        browse_layout = QHBoxLayout()
        browse_layout.addWidget(self.projet_path_edit)
        browse_layout.addWidget(self.browse_button)
        browse_layout.setContentsMargins(0, 0, 0, 0)

        v_layout.addRow("Reference genom", self.reference)
        v_layout.addRow("Project Name", self.projet_name_edit)
        v_layout.addRow("Create in", browse_layout)

        self.setLayout(v_layout)

        self.browse_button.clicked.connect(self._browse)
        self.projet_path_edit.textChanged.connect(self.completeChanged)
        self.projet_name_edit.textChanged.connect(self.completeChanged)

    def _browse(self):
        path = QFileDialog.getExistingDirectory(self, "Select a path for the project")
        if path:
            self.projet_path_edit.setText(path)

    def isComplete(self):
        """Conditions to unlock next button"""
        return True if (
            QDir(self.projet_path_edit.text()).exists()
            and self.projet_path_edit.text()
            and self.projet_name_edit.text()
        ) else False


class FilePage(QWizardPage):
    def __init__(self):
        super().__init__()

        self.setTitle("Select a file")
        self.setSubTitle("Supported file are vcf and vcf.gz.")

        self.file_path_edit = QLineEdit()
        self.button = QPushButton("Browse")
        v_layout = QHBoxLayout()

        v_layout.addWidget(self.file_path_edit)
        v_layout.addWidget(self.button)
        self.setLayout(v_layout)

        self.button.clicked.connect(self._browse)
        self.file_path_edit.textChanged.connect(self.completeChanged)

        self.registerField("filename", self.file_path_edit, "text")

    def _browse(self):
        filename = QFileDialog.getOpenFileName(
            self, "Open a file", QDir.homePath(), "VCF file (*.vcf, *.vcf.gz)"
        )
        if filename:
            self.file_path_edit.setText(filename[0])

    def isComplete(self):
        """Conditions to unlock next button"""
        return True if (
            self.file_path_edit.text() and QFile(self.file_path_edit.text()).exists()
        ) else False


class ImportThread(QThread):

    progress_changed = Signal(int, str)
    finished_status = Signal(bool)

    def __init__(self):
        super().__init__()
        self._stop = False
        self.filename = None
        self.db_filename = None

    def run(self):
        """Overrided QThread method

        .. warning:: This method is the only one to be executed in the thread.
            SQLite objects created in a thread can only be used in that same
            thread; so no use of self.conn is allowed elsewhere.
        """
        self._stop = False

        if self.db_filename is None:
            self.db_filename = self.filename + ".db"

        if os.path.exists(self.db_filename):
            os.remove(self.db_filename)
        self.conn = sqlite3.connect(self.db_filename)

        for value, message in async_import_file(self.conn, self.filename):
            if self._stop == True:
                self.conn.close()
                break
            # Send progression
            self.progress_changed.emit(value, message)
        # Send status (True when there is no error)
        self.finished_status.emit(not self._stop)

    def stop(self):
        self._stop = True


class ImportPage(QWizardPage):
    def __init__(self):
        super().__init__()

        self.setTitle("Import file")
        self.setSubTitle("Please click on Import/Stop to start or stop the process.")
        self.text_buttons = ["Import", "Stop"]

        self.thread_finished = False
        self.thread = ImportThread()
        self.progress = QProgressBar()
        self.import_button = QPushButton(self.text_buttons[0])

        v_layout = QHBoxLayout()
        v_layout.addWidget(self.progress)
        v_layout.addWidget(self.import_button)

        m_layout = QVBoxLayout()

        self.log_edit = QPlainTextEdit()
        self.tab_widget = QTabWidget()
        self.tab_widget.addTab(self.log_edit, "log")

        m_layout.addLayout(v_layout)
        m_layout.addWidget(self.tab_widget)
        self.setLayout(m_layout)

        self.log_edit.appendPlainText(self.field("filename"))

        self.thread.started.connect(lambda: self.log_edit.appendPlainText("Started"))
        self.thread.finished.connect(lambda: self.log_edit.appendPlainText("Done"))
        self.import_button.clicked.connect(self.run)

        self.thread.progress_changed.connect(self.progress_changed)
        self.thread.finished.connect(self.import_thread_finished)
        self.thread.finished_status.connect(self.import_thread_finished_status)

    def progress_changed(self, value, message):
        self.progress.setValue(value)
        self.log_edit.appendPlainText(message)

    def import_thread_finished(self):
        """Force the activation of the finish button after a successful import"""
        self.completeChanged.emit()

    def import_thread_finished_status(self, status):
        """Set the finished status of import thread

        .. note:: Called at the end of run()
        """
        self.thread_finished = status

        if status:
            self.import_button.setDisabled(True)

    def run(self):
        if self.thread.isRunning():
            print("stop thread")
            self.import_button.setDisabled(True)
            self.thread.stop()
            self.progress.setValue(0)
            self.import_button.setDisabled(False)
            self.import_button.setText(self.text_buttons[0])

        else:
            self.thread.filename = self.field("filename")
            self.thread.db_filename = (
                self.field("project_path")
                + QDir.separator()
                + self.field("project_name")
                + ".db"
            )

            self.log_edit.appendPlainText("Import " + self.thread.filename)
            self.import_button.setText(self.text_buttons[1])
            self.thread.start()

    def isComplete(self):
        """Conditions to unlock next button"""
        return self.thread_finished


class ProjetWizard(QWizard):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Cutevariant - Project creation wizard")

        self.addPage(ProjetPage())
        self.addPage(FilePage())
        self.addPage(ImportPage())
