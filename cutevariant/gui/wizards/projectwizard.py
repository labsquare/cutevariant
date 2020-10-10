# Standard imports
import os
from PySide2.QtWidgets import *
from PySide2.QtCore import (
    QThread,
    Signal,
    QDir,
    QSettings,
    QFile,
    Slot,
)
from PySide2.QtGui import QIcon

# Custom imports
from cutevariant.core.importer import async_import_file
from cutevariant.core import get_sql_connexion
import cutevariant.commons as cm
from cutevariant.core.readerfactory import detect_vcf_annotation, create_reader
from cutevariant.core.reader import PedReader
from cutevariant.gui.model_view import PedView

LOGGER = cm.logger()


class ProjectPage(QWizardPage):
    """Page: Creation of a new project
    We ask the reference genome, the name and the path of the future project file.
    """

    def __init__(self):
        super().__init__()

        self.setTitle(self.tr("Project creation"))
        self.setSubTitle(
            self.tr("This wizard will guide you to create a cutevariant project.")
        )

        # Reload last directory used
        app_settings = QSettings()
        self.last_directory = app_settings.value("last_directory", QDir.homePath())

        self.project_name_edit = QLineEdit()
        self.project_path_edit = QLineEdit()
        self.project_path_edit.setText(self.last_directory)
        self.browse_button = QPushButton(self.tr("Browse"))
        self.reference = QComboBox()

        # Unused for now
        self.reference.hide()

        self.reference.addItem("hg19")
        self.registerField("project_name", self.project_name_edit, "text")
        self.registerField("project_path", self.project_path_edit, "text")
        self.registerField("reference", self.reference, "currentText")

        v_layout = QFormLayout()

        browse_layout = QHBoxLayout()
        browse_layout.addWidget(self.project_path_edit)
        browse_layout.addWidget(self.browse_button)
        browse_layout.setContentsMargins(0, 0, 0, 0)

        v_layout.addRow(self.tr("Reference genom"), self.reference)
        v_layout.addRow(self.tr("Project Name"), self.project_name_edit)
        v_layout.addRow(self.tr("Create in"), browse_layout)

        self.setLayout(v_layout)

        self.browse_button.clicked.connect(self._browse)
        self.project_path_edit.textChanged.connect(self.completeChanged)
        self.project_name_edit.textChanged.connect(self.completeChanged)

    @Slot()
    def _browse(self):
        """Open a dialog box to set the directory where the project will be saved"""
        path = QFileDialog.getExistingDirectory(
            self, self.tr("Select a path for the project"), self.last_directory
        )
        if path:
            self.project_path_edit.setText(path)

    def isComplete(self):
        """Conditions to unlock next button"""
        return (
            True
            if (
                QDir(self.project_path_edit.text()).exists()
                and self.project_path_edit.text()
                and self.project_name_edit.text()
            )
            else False
        )


class FilePage(QWizardPage):
    """Page: Open the file containing variant data
    We ask the path of the data file
    """

    def __init__(self):
        super().__init__()

        self.setTitle(self.tr("Select a file"))
        self.setSubTitle(self.tr("Supported file are vcf, vcf.gz, vep.txt."))

        self.file_path_edit = QLineEdit()

        self.anotation_detect_label = QLabel()
        self.button = QPushButton(self.tr("Browse"))
        h_layout = QHBoxLayout()

        h_layout.addWidget(self.file_path_edit)
        h_layout.addWidget(self.button)

        self.v_layout = QVBoxLayout()
        self.v_layout.addLayout(h_layout)
        self.v_layout.addWidget(self.anotation_detect_label)
        self.setLayout(self.v_layout)

        self.button.clicked.connect(self._browse)
        self.file_path_edit.textChanged.connect(self.completeChanged)

        self.registerField("filename", self.file_path_edit, "text")
        # annotation ? should be an option or not ?
        self.registerField("annotation", self.anotation_detect_label, "text")

    @Slot()
    def _browse(self):
        """Open a dialog box to set the data file

        The file is opened and we show an alert if annotations are detected.
        """
        # Reload last directory used
        app_settings = QSettings()
        last_directory = app_settings.value("last_directory", QDir.homePath())

        filepath, filetype = QFileDialog.getOpenFileName(
            self,
            self.tr("Open a file"),
            last_directory,
            self.tr("VCF file (*.vcf *.vcf.gz);; CSV file (*.csv *.tsv *.txt)"),
        )

        if filepath:
            # Display and save directory
            self.file_path_edit.setText(filepath)
            app_settings.setValue("last_directory", os.path.dirname(filepath))

            if "vcf" in filepath:
                # TODO: detect annotations on other tyes of files...
                annotation_type = detect_vcf_annotation(filepath)
                if annotation_type:
                    text = self.tr("<b>%s annotations detected!</b>") % annotation_type
                else:
                    text = self.tr("<b>No annotation data has been detected!</b>")

                self.anotation_detect_label.setText(text)

    def isComplete(self):
        """Conditions to unlock next button"""
        return (
            True
            if (
                self.file_path_edit.text()
                and QFile(self.file_path_edit.text()).exists()
            )
            else False
        )


class SamplePage(QWizardPage):
    """Gather additional information on sequenced individuals and their families

    PED file is facultative, a user can manually fill the data in the dynamic view.

    See Also:
        :meth:`gui.model_view.pedigree.PedView`
    """
    def __init__(self):
        super().__init__()

        self.setTitle(self.tr("Samples"))
        self.setSubTitle(self.tr("Add sample description or skip this step"))
        self.view = PedView()
        self.import_button = QPushButton(self.tr("Import PED file (facultative)"))
        v_layout = QVBoxLayout()
        v_layout.addWidget(self.view)
        v_layout.addWidget(self.import_button)
        self.setLayout(v_layout)

        self.vcf_samples = list()

        self.import_button.clicked.connect(self.on_import_clicked)

        self.registerField("pedfile", self.view, "pedfile")

    def initializePage(self):
        """Overrided: Prepare the page just before it is shown

        We open variant file (vcf, etc.) to get the current samples that will
        be eventualy associated to a PED file later.
        """
        self.view.clear()
        # Open project file
        filename = self.field("filename")
        with create_reader(filename) as reader:
            # Get samples of the project
            self.vcf_samples = reader.get_samples()

            samples = [
                # family_id, individual_id, father_id, mother_id, sex, genotype
                ["fam", name, "0", "0", "0", "0", "0"]
                for name in self.vcf_samples
            ]
            self.view.set_samples(samples)

    def validatePage(self):
        """ override """
        # read table and create a dict for setFields
        return True

    @Slot()
    def on_import_clicked(self):
        """Slot called when import PED file is clicked

        We open PED file (ped, tfam) to get the their samples that will
        be associated to the current samples of the project.
        """
        # Reload last directory used
        app_settings = QSettings()
        last_directory = app_settings.value("last_directory", QDir.homePath())

        filepath, filetype = QFileDialog.getOpenFileName(
            self,
            self.tr("Open ped file"),
            last_directory,
            self.tr("PED files (*.ped *.tfam)"),
        )

        if not filepath:
            return

        LOGGER.info("vcf samples: %s", self.vcf_samples)

        # Get samples of individual_ids that are already on the VCF file
        self.view.samples = [
            # samples argument is empty dict since its not
            sample for sample in PedReader(filepath, dict())
            if sample[1] in self.vcf_samples
        ]


class ImportThread(QThread):
    """Thread used to create a new project by importing a variant file

    .. note:: This thread creates the database.
    .. seealso:: ImportPage class.
    """

    # Qt signals
    progress_changed = Signal(int, str)
    finished_status = Signal(bool)

    def __init__(self):
        super().__init__()
        self._stop = False
        # File top open
        self.filename = ""
        # Project's filepath
        self.db_filename = ""
        self.pedfile = ""
        self.project_settings = dict()

    def set_importer_settings(
        self, filename, pedfile, db_filename, project_settings={}
    ):
        """Init settings of the importer

        :param filename: File to be opened.
        :param db_filename: Filepath of the new project.
        :key project_settings: The reference genome and the name of the project.
            Keys have to be at least "reference" and "project_name".
        :type filename: <str>
        :type db_filename: <str>
        :type project_settings: <dict>
        :type sample_data: <dict>

        """
        # File top open
        self.filename = filename
        # Project's filepath
        self.db_filename = db_filename
        # Project settings
        self.project_settings = project_settings
        # Ped file
        self.pedfile = pedfile

    def run(self):
        """Overrided QThread method

        .. warning:: This method is the only one to be executed in the thread.
            SQLite objects created in a thread can only be used in that same
            thread; so no use of self.conn is allowed elsewhere.
        """
        self._stop = False

        if os.path.exists(self.db_filename):
            os.remove(self.db_filename)
        self.conn = get_sql_connexion(self.db_filename)

        try:
            # Import the file
            for value, message in async_import_file(
                self.conn, self.filename, self.pedfile, self.project_settings
            ):
                if self._stop == True:
                    self.conn.close()
                    break
                # Send progression
                self.progress_changed.emit(value, message)

        except BaseException as e:
            self.progress_changed.emit(0, str(e))
            self._stop = True
            raise e
        finally:
            # Send status (Send True when there is no error)
            self.finished_status.emit(not self._stop)

    def stop(self):
        self._stop = True


class ImportPage(QWizardPage):
    """Page: Creation of the database"""

    def __init__(self):
        super().__init__()

        self.setTitle(self.tr("Import file"))
        self.setSubTitle(
            self.tr("Please click on Import/Stop to start or stop the process.")
        )
        self.text_buttons = [self.tr("Import"), self.tr("Stop")]

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

        # File to open
        self.log_edit.appendPlainText(self.field("filename"))

        self.thread.started.connect(
            lambda: self.log_edit.appendPlainText(self.tr("Started"))
        )

        # Note: self.run is automatically launched when ImportPage is displayed
        # See on_current_id_changed of ProjectWizard
        self.import_button.clicked.connect(self.run)
        self.thread.progress_changed.connect(self.progress_changed)
        self.thread.finished.connect(self.import_thread_finished)
        self.thread.finished_status.connect(self.import_thread_finished_status)

    def initializePage(self):
        """ override """
        print(self.field("pedfile"))

    @Slot()
    def progress_changed(self, value, message):
        """Update the progress bar
        Slot called when progress_changed is emitted by the thread
        """
        self.progress.setValue(value)
        if message:
            self.log_edit.appendPlainText(message)

    @Slot()
    def import_thread_finished(self):
        """Force the activation of the finish button after a successful import"""
        self.completeChanged.emit()

    @Slot()
    def import_thread_finished_status(self, status):
        """Set the finished status of import thread

        .. note:: Called at the end of run()
        """
        self.thread_finished = status
        if status:
            # Block further import
            self.import_button.setDisabled(True)
            self.log_edit.appendPlainText(self.tr("Done"))
        else:
            # Display import on the button
            self.import_button.setText(self.text_buttons[0])
            self.log_edit.appendPlainText(self.tr("Stopped!"))

    @Slot()
    def run(self):
        """Called when import button is clicked
        Launch the import in a separate thread
        """
        if self.thread.isRunning():
            LOGGER.debug("ImportPage:run: stop thread")
            self.import_button.setDisabled(True)
            self.thread.stop()
            self.progress.setValue(0)
            self.import_button.setDisabled(False)
            self.import_button.setText(self.text_buttons[0])

        else:
            self.thread.set_importer_settings(
                # File to open
                filename=self.field("filename"),
                pedfile=self.field("pedfile"),
                # Project's filepath
                db_filename=(
                    self.field("project_path")
                    + QDir.separator()
                    + self.field("project_name")
                    + ".db"
                ),
                # Project's settings
                project_settings={
                    # Reference genome
                    "reference": self.field("reference"),
                    # Project's name
                    "project_name": self.field("project_name"),
                },
            )

            self.log_edit.appendPlainText(self.tr("Import ") + self.thread.filename)
            # display stop on the button
            self.import_button.setText(self.text_buttons[1])
            self.thread.start()

    def isComplete(self):
        """Conditions to unlock finish button"""
        return self.thread_finished


class ProjectWizard(QWizard):
    """Main window of the project wizard

    3 pages are instantiated here:
        - ProjectPage: Creation of a new project
        - FilePage: Open the file containing variant data
        - ImportPage: Creation of the database
    """

    def __init__(self):
        super().__init__()
        self.setWindowTitle(self.tr("Cutevariant - Project creation wizard"))
        self.setWindowIcon(QIcon(cm.DIR_ICONS + "app.png"))
        self.setWizardStyle(QWizard.ClassicStyle)
        self.addPage(ProjectPage())
        self.addPage(FilePage())
        self.addPage(SamplePage())
        self.addPage(ImportPage())

        self.currentIdChanged.connect(self.on_current_id_changed)

    @Slot()
    def on_current_id_changed(self, id):
        """Launch import process if currentPage is ImportPage

        Args:
            id (int): Current page id
        """
        current_page = self.currentPage()
        if isinstance(current_page, ImportPage):
            current_page.run()


if __name__ == "__main__":
    import sys

    app = QApplication(sys.argv)

    w = ProjectWizard()
    w.show()

    app.exec_()
