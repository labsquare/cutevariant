# Standard imports
from cutevariant.core.reader.vcfreader import VcfReader
import os
import copy
import time

# Qt imports
from PySide2.QtWidgets import *
from PySide2.QtCore import (
    QAbstractListModel,
    QAbstractTableModel,
    QModelIndex,
    QThread,
    Signal,
    QDir,
    QSettings,
    QFile,
    Slot,
    Qt,
)
from PySide2.QtGui import QIcon, QStandardItem, QStandardItemModel, QColor, QFont

# Custom imports
from cutevariant.core.importer import async_import_file
from cutevariant.core import get_sql_connection
import cutevariant.commons as cm
from cutevariant.core.readerfactory import detect_vcf_annotation, create_reader
from cutevariant.core.reader import PedReader, annotationparser
from cutevariant.gui.model_view import PedView
from cutevariant.gui.ficon import FIcon

from cutevariant import LOGGER


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

        self.registerField("project_name", self.project_name_edit, "text")
        self.registerField("project_path", self.project_path_edit, "text")

        v_layout = QFormLayout()

        browse_layout = QHBoxLayout()
        browse_layout.addWidget(self.project_path_edit)
        browse_layout.addWidget(self.browse_button)
        browse_layout.setContentsMargins(0, 0, 0, 0)

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
            self.last_directory = path  # If you change your mind after this point, it's good to have the last directory you selected

    def validatePage(self):
        name = self.project_name_edit.text()
        filepath = QDir(self.project_path_edit.text()).filePath(name) + ".db"

        if os.path.exists(filepath):
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
                os.remove(filepath)
                return True
            else:
                return False

        return True

    def initializePage(self):
        """Overridden: Prepare the page just before it is shown"""
        # Adjust the focus of project name field
        self.project_name_edit.setFocus()

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
        self.annotation_box = QComboBox()
        self.lock_button = QPushButton(self.tr("Edit"))
        self.anotation_detect_label = QLabel()
        self.button = QPushButton(self.tr("Browse"))
        self.button.setIcon(FIcon(0xF0DCF))
        h_layout = QHBoxLayout()

        self.lock_button.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Preferred)
        self.lock_button.setCheckable(True)
        self.lock_button.setIcon(FIcon(0xF08EE))

        self.annotation_box.setEnabled(False)
        self.lock_button.toggled.connect(lambda x: self.annotation_box.setEnabled(x))

        self.file_path_edit.setToolTip(
            self.tr("Path to a supported input file. (e.g: VCF  file ) ")
        )

        h_layout.addWidget(self.file_path_edit)
        h_layout.addWidget(self.button)

        h2_layout = QHBoxLayout()
        h2_layout.addWidget(self.annotation_box)
        h2_layout.addWidget(self.lock_button)

        self.v_layout = QFormLayout()
        self.v_layout.addRow("Input File", h_layout)
        self.v_layout.addRow("Annotation", h2_layout)
        self.setLayout(self.v_layout)

        self.button.clicked.connect(self._browse)
        self.file_path_edit.textChanged.connect(self.completeChanged)

        self.registerField("filename", self.file_path_edit, "text")
        # annotation ? should be an option or not ?
        self.registerField("annotation_parser", self.annotation_box, "currentData")

        # Fill supported format
        self.annotation_box.addItem(
            FIcon(0xF13CF), "No Annotation detected", userData=None
        )
        for parser in VcfReader.ANNOTATION_PARSERS:
            self.annotation_box.addItem(FIcon(0xF08BB), parser, userData=parser)

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
                if annotation_type == None:
                    self.annotation_box.setCurrentIndex(0)
                else:
                    self.annotation_box.setCurrentText(annotation_type)

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
        self.setSubTitle(self.tr("Add sample descriptions or skip this step."))
        self.help_text = QLabel(
            self.tr(
                "You can edit the relationships between genomes found in the VCF\n"
                "manually or via a PED/PLINK file (sample pedigree information and "
                "genotype calls).\nBy default the fields are those found in the VCF; "
                "the unknown fields are empty.\nDouble click to edit them."
            )
        )
        self.view = PedView()
        self.import_button = QPushButton(self.tr("Import PED file (facultative)"))
        self.ped_message = QLabel()
        v_layout = QVBoxLayout()
        v_layout.addWidget(self.help_text)
        v_layout.addWidget(self.view)
        v_layout.addWidget(self.import_button)
        v_layout.addWidget(self.ped_message)
        self.setLayout(v_layout)

        self.vcf_samples = list()  # Raw individual_ids from VCF
        # PED data built from VCF ids (other fields than individual_id are default)
        # used as a reference to detect user changes
        self.vcf_default_ped_samples = list()

        self.import_button.clicked.connect(self.on_import_clicked)
        self.view.message.connect(self.on_display_message)

        # Share PedView.pedfile accross Wizard pages
        self.registerField("pedfile", self.view, "pedfile")

    def initializePage(self):
        """Overridden: Prepare the page just before it is shown

        We open variant file (vcf, etc.) to get the current samples that will
        be eventually associated to a PED file later.
        """
        self.view.clear()
        # Open variant file of the project and read its headers
        filename = self.field("filename")
        with create_reader(filename) as reader:
            # Get samples of the vcf project
            self.vcf_samples = reader.get_samples()

            self.vcf_default_ped_samples = [
                # family_id, individual_id, father_id, mother_id, sex, genotype
                ["fam", name, "0", "0", "0", "0", "0"]
                for name in self.vcf_samples
            ]
            # Deepcopy to avoid further modifications of this list of reference
            self.view.samples = copy.deepcopy(self.vcf_default_ped_samples)

    def validatePage(self):
        """Overrided: Called when a user clicks on next button"""
        # Check if PedView contains the same default data
        # print("default", self.vcf_default_ped_samples)
        # print("vs", self.view.samples)
        if set(map(tuple, self.vcf_default_ped_samples)) == set(
            map(tuple, self.view.samples)
        ):
            # Reset samples => will set pedfile field to None
            self.view.samples = list()

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
            self.tr("Open PED file"),
            last_directory,
            self.tr("PED files (*.ped *.tfam)"),
        )

        if not filepath:
            return

        LOGGER.info("vcf samples: %s", self.vcf_samples)

        # Get samples of individual_ids that are already on the VCF file
        self.view.samples = [
            # samples argument is empty dict since its not
            sample
            for sample in PedReader(filepath, dict())
            if sample[1] in self.vcf_samples
        ]

    def on_display_message(self, message):
        """Display messages about data validation from the delegate"""
        self.ped_message.setText(message)


class FieldsModel(QAbstractTableModel):

    MANDATORY_FIELDS = ["chr", "pos", "ref", "alt", "gt"]

    def __init__(self, parent=None):
        super().__init__(parent=parent)
        self._items = []
        self._headers = ["name", "category", "description", "type", "use index"]

    def rowCount(self, parent: QModelIndex) -> int:
        """override"""
        return len(self._items)

    def columnCount(self, parent: QModelIndex) -> int:
        """override"""
        return len(self._headers)

    def data(self, index: QModelIndex, role: int):
        """override"""
        if not index.isValid():
            return None

        item = self._items[index.row()]
        if role == Qt.DisplayRole:

            if index.column() == 0:
                return item["name"]
            if index.column() == 1:
                return item["category"]
            if index.column() == 2:
                return item["description"]
            if index.column() == 3:
                return item["type"]

        if role == Qt.ForegroundRole:
            if not item["enabled"]:
                return QColor("darkgray")

        if role == Qt.TextAlignmentRole:
            if index.column() == 4:
                return Qt.AlignCenter

        if role == Qt.FontRole:
            if item["name"] in self.MANDATORY_FIELDS:
                font = QFont()
                font.setBold(True)
                return font

        if role == Qt.CheckStateRole:

            if index.column() == 0:
                return Qt.Checked if item["enabled"] else Qt.Unchecked
            if index.column() == 4:
                return Qt.Checked if item["index"] else Qt.Unchecked
        return None

    def headerData(self, section: int, orientation: Qt.Orientation, role: int):

        if orientation == Qt.Horizontal and role == Qt.DisplayRole:
            return self._headers[section]

        return None

    def setData(self, index: QModelIndex, value, role: int) -> bool:
        """override"""
        if role == Qt.CheckStateRole and index.column() == 0:
            self._items[index.row()]["enabled"] = bool(value)
            self._items[index.row()]["index"] = bool(value)
            self.dataChanged.emit(index.siblingAtColumn(0), index.siblingAtColumn(4))
            return True

        if role == Qt.CheckStateRole and index.column() == 4:
            self._items[index.row()]["index"] = bool(value)
            self.dataChanged.emit(index, index)
            return True

        return False

    def get_ignore_fields(self) -> set:
        """Returns a set of ignored fields, as a set of tuples (field_name,field_category)
        Why return tuple instead of dict ? Well, dicts are not hashable because they are mutable. So they cannot be put in a set.

        Returns:
            set: A set with every ignored field (i.e. every field that was ticked off in self's model)
        """
        return {
            (field["name"], field["category"])
            for field in self._items
            if field["enabled"] == False
        }

    def get_indexed_fields(self):
        return [field for field in self._items if field["index"] == True]

    def flags(self, index: QModelIndex) -> Qt.ItemFlags:

        item = self._items[index.row()]

        if item["name"] in self.MANDATORY_FIELDS:
            return Qt.ItemIsSelectable

        if index.column() == 0 or index.column() == 4:
            return Qt.ItemIsSelectable | Qt.ItemIsEnabled | Qt.ItemIsUserCheckable

        return Qt.ItemIsSelectable | Qt.ItemIsEnabled

    def load(self, filename: str):
        """load fields"""
        self.beginResetModel()
        self._items.clear()

        with create_reader(filename) as reader:
            for field in reader.get_fields():
                field["enabled"] = True
                field["index"] = True
                self._items.append(field)

        self.endResetModel()


class FieldsPage(QWizardPage):
    """Allow user to skip too import some fields"""

    def __init__(self):
        super().__init__()

        self.setTitle(self.tr("Fields"))
        self.setSubTitle(
            self.tr(
                "Select fields you want to import. Mandatory fields cannot be edited.\n Indexed fields will improve query execution but database will takes more space"
            )
        )
        self.help_text = QLabel(self.tr("Check fields you want to import "))
        self.select_button = QPushButton(self.tr("(Un)Select all"))
        self.view = QTableView()
        self.model = FieldsModel()
        self.view.setModel(self.model)
        self.view.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.view.setSelectionMode(QAbstractItemView.SingleSelection)
        self.view.setAlternatingRowColors(True)

        # main layout
        main_layout = QHBoxLayout()
        main_layout.addWidget(self.view)

        self.setLayout(main_layout)

    def initializePage(self):
        """overload"""

        # Open variant file of the project and read its headers
        filename = self.field("filename")
        self.model.load(filename)

        self.view.horizontalHeader().setSectionResizeMode(2, QHeaderView.Stretch)

    def validatePage(self):
        """override"""

        # Loop over fields a create a ignored fields set e.g (("qual","variants"))

        config = {}
        config["ignored_fields"] = self.model.get_ignore_fields()

        config["indexed_variant_fields"] = {
            i["name"]
            for i in self.model.get_indexed_fields()
            if i["category"] == "variants"
        }

        config["indexed_annotation_fields"] = {
            i["name"]
            for i in self.model.get_indexed_fields()
            if i["category"] == "annotations"
        }

        config["indexed_sample_fields"] = {
            i["name"]
            for i in self.model.get_indexed_fields()
            if i["category"] == "samples"
        }

        self.wizard().config.update(config)

        return True


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
        # Facultative PED file
        self.pedfile = None
        # Ignored fields
        self.ignored_fields = None
        # Fields with index
        self.indexed_variant_fields = None
        self.indexed_annotation_fields = None
        self.indexed_sample_fields = None

        # annotation parser
        self.annotation_parser = None

        self.project_settings = dict()

    def run(self):
        """Overrided QThread method

        .. warning:: This method is the only one to be executed in the thread.
            SQLite objects created in a thread can only be used in that same
            thread; so no use of self.conn is allowed elsewhere.
        """
        self._stop = False

        #  start timer
        start = time.perf_counter()

        if os.path.exists(self.db_filename):
            os.remove(self.db_filename)
        self.conn = get_sql_connection(self.db_filename)

        try:
            # Import the file
            for value, message in async_import_file(
                self.conn,
                self.filename,
                pedfile=self.pedfile,
                ignored_fields=self.ignored_fields,
                indexed_variant_fields=self.indexed_variant_fields,
                indexed_annotation_fields=self.indexed_annotation_fields,
                indexed_sample_fields=self.indexed_sample_fields,
                project=self.project_settings,
                vcf_annotation_parser=self.annotation_parser,
            ):
                if self._stop:
                    self.conn.close()
                    break
                # Send progression
                self.progress_changed.emit(value, message)

        except BaseException as e:
            self.progress_changed.emit(0, str(e))
            self._stop = True
            LOGGER.exception(e)
            raise e
        finally:
            # Send status (Send True when there is no error)
            # end timer
            end = time.perf_counter()
            elapsed_time = end - start
            self.progress_changed.emit(100, str("Elapsed time: %.2gs" % (end - start)))
            self.finished_status.emit(not self._stop)

    def stop(self):
        """Stop the import process"""
        self._stop = True


class ImportPage(QWizardPage):
    """Page: Creation of the database"""

    completeChanged = Signal()

    def __init__(self):
        super().__init__()

        self.setTitle(self.tr("Import file"))
        self.setSubTitle(
            self.tr("Please click on Import/Stop to start or stop the process.")
        )
        self.text_buttons = [self.tr("Import"), self.tr("Stop")]

        # Async stuff
        self.thread_finished = False  # True if import process is correctly finished
        self.thread: ImportThread = ImportThread()
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
        # Database filename; see initializePage()
        self.db_filename = None

        # Ignored field from previous page; see initializePage()
        self.ignored_fields = set()

        self.annotation_parser = None

        self.thread.started.connect(
            lambda: self.log_edit.appendPlainText(self.tr("Started"))
        )

        # Note: self.run is automatically launched when ImportPage is displayed
        # See initializePage()
        self.import_button.clicked.connect(self.run)
        self.thread.progress_changed.connect(self.progress_changed)
        self.thread.finished.connect(self.import_thread_finished)
        self.thread.finished_status.connect(self.import_thread_finished_status)

    def initializePage(self):
        """Overridden: Prepare the page just before it is shown

        Launch import process if currentPage is ImportPage
        """
        # print("Current PED file", self.field("pedfile"))
        self.db_filename = (
            self.field("project_path")
            + QDir.separator()
            + self.field("project_name")
            + ".db"
        )

        self.run()
        self.import_button.setDisabled(False)

    def cleanupPage(self):
        """Called when back button is clicked: stop the import thread"""
        self.thread_stop()

        if self.thread_finished:
            # The import process is not finished corretly
            # Delete file
            os.remove(self.db_filename)

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
        try:
            self.completeChanged.emit()
        except RuntimeError:
            # When closing the wizard, the thread is stopped via cleanupPage()
            # and finished signal is emitted after the deletion of the wizard.
            pass

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
            self.thread_stop()
        else:
            # init thread
            config = self.wizard().config
            self.thread.filename = self.field("filename")
            self.thread.db_filename = self.db_filename
            self.thread.pedfile = self.field("pedfile")
            self.thread.ignored_fields = config["ignored_fields"]

            self.thread.indexed_variant_fields = config["indexed_variant_fields"]
            self.thread.indexed_annotation_fields = config["indexed_annotation_fields"]
            self.thread.indexed_sample_fields = config["indexed_sample_fields"]

            self.thread.annotation_parser = self.field("annotation_parser")
            self.thread.project_settings = {"name": self.field("project_name")}

            self.log_edit.appendPlainText(
                "Annotation parser: " + str(self.field("annotation_parser"))
            )

            self.log_edit.appendPlainText(self.tr("Import ") + self.thread.filename)

            show_ignored_fields = ",".join([i[0] for i in self.thread.ignored_fields])

            self.log_edit.appendPlainText("Ignored fields: " + show_ignored_fields)
            # display stop on the button
            self.import_button.setText(self.text_buttons[1])
            self.thread.start()

    def thread_stop(self):
        """Stop the thread and refresh the UI"""
        LOGGER.debug("ImportPage:run: stop thread")
        self.import_button.setDisabled(True)
        self.thread.stop()
        self.progress.setValue(0)
        self.import_button.setDisabled(False)
        self.import_button.setText(self.text_buttons[0])

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
        self.addPage(FieldsPage())
        self.addPage(ImportPage())

        # Stored all data filled by the wizard
        # Better than using cumberstome setField...
        self.config = {}
        self.resize(600, 400)


if __name__ == "__main__":
    import sys

    app = QApplication(sys.argv)

    w = ProjectWizard()
    w.show()

    app.exec_()
