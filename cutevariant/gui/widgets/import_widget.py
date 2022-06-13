# Qt imports
from PySide6.QtCore import (
    QLine,
    Qt,
    QAbstractTableModel,
    QAbstractItemModel,
    QModelIndex,
    Property,
    Signal,
    QThread,
    Slot,
    QDir,
)

from PySide6.QtGui import QFont, QColor
from PySide6.QtWidgets import (
    QLineEdit,
    QStyle,
    QFrame,
    QTabWidget,
    QTableView,
    QApplication,
    QPlainTextEdit,
    QDialog,
    QHeaderView,
    QPushButton,
    QLabel,
    QFileDialog,
    QSizePolicy,
    QVBoxLayout,
    QHBoxLayout,
    QFormLayout,
    QGroupBox,
    QItemDelegate,
    QWidget,
    QStyleOptionViewItem,
    QComboBox,
    QProgressBar,
    QAbstractItemView,
)

import sqlite3
import time
import tempfile
import os
from cutevariant.gui.ficon import FIcon
from cutevariant.core.reader.vcfreader import VcfReader
from cutevariant.core.reader import PedReader
from cutevariant.core.readerfactory import detect_vcf_annotation, create_reader
from cutevariant.core import sql
from cutevariant import LOGGER

from cutevariant.gui.model_view import PedView


class FieldsModel(QAbstractTableModel):

    MANDATORY_FIELDS = ["chr", "pos", "ref", "alt", "gt"]

    NAME_COL = 0
    INDEX_COL = 1
    CATEGORY_COL = 2
    TYPE_COL = 3
    DESC_COL = 4

    def __init__(self, parent=None):
        super().__init__(parent=parent)
        self._items = []
        self._samples = []
        self._headers = {
            self.NAME_COL: "name",
            self.CATEGORY_COL: "category",
            self.TYPE_COL: "type",
            self.DESC_COL: "description",
            self.INDEX_COL: "use index",
        }

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

            if index.column() == self.NAME_COL:
                return item["name"]
            if index.column() == self.CATEGORY_COL:
                return item["category"]
            if index.column() == self.DESC_COL:
                return item["description"]
            if index.column() == self.TYPE_COL:
                return item["type"]
            if index.column() == self.INDEX_COL:
                return "yes" if item["index"] else "no"

        if role == Qt.ForegroundRole:
            if not item["enabled"]:
                return QColor("darkgray")

        if role == Qt.TextAlignmentRole:
            if index.column() == self.INDEX_COL:
                return Qt.AlignCenter

        if role == Qt.FontRole and index.column() == self.NAME_COL:
            font = QFont()
            font.setBold(True)
            if item["index"] is True:
                font.setUnderline(True)

            return font

        if role == Qt.DecorationRole and index.column() == self.INDEX_COL:
            if item["index"] is True:
                return QApplication.style().standardIcon(QStyle.SP_DialogApplyButton)
            else:
                return QApplication.style().standardIcon(QStyle.SP_DialogCancelButton)

        if role == Qt.CheckStateRole:
            if index.column() == self.NAME_COL:
                return int(Qt.Checked) if item["enabled"] else int(Qt.Unchecked)

        if role == Qt.ToolTipRole:
            return item["description"]

    def headerData(self, section: int, orientation: Qt.Orientation, role: int):

        if orientation == Qt.Horizontal and role == Qt.DisplayRole:
            return self._headers[section]

        return None

    def setData(self, index: QModelIndex, value, role: int = Qt.EditRole) -> bool:
        """override"""
        if role == Qt.CheckStateRole and index.column() == self.NAME_COL:
            self._items[index.row()]["enabled"] = bool(value)
            self.dataChanged.emit(index.siblingAtColumn(0), index.siblingAtColumn(4))
            return True

        if role == Qt.EditRole and index.column() == self.INDEX_COL:
            self._items[index.row()]["index"] = bool(value)
            self.dataChanged.emit(index.siblingAtColumn(0), index.siblingAtColumn(4))
            return True

        return False

    def get_ignored_fields(self) -> set:
        """Returns a set of ignored fields, as a set of tuples (field_name,field_category)
        Why return tuple instead of dict ? Well, dicts are not hashable because they are mutable. So they cannot be put in a set.

        Returns:
            set: A set with every ignored field (i.e. every field that was ticked off in self's model)
        """
        return [field for field in self._items if field["enabled"] == False]

    def get_indexed_fields(self):
        return [field for field in self._items if field["index"] == True]

    def flags(self, index: QModelIndex) -> Qt.ItemFlags:

        item = self._items[index.row()]

        if item["name"] in self.MANDATORY_FIELDS:
            return Qt.NoItemFlags

        if index.column() == self.NAME_COL or index.column() == self.INDEX_COL:
            return Qt.ItemIsSelectable | Qt.ItemIsEnabled | Qt.ItemIsUserCheckable

        return Qt.ItemIsSelectable | Qt.ItemIsEnabled

    def load(self, filename: str):
        """load fields"""
        self.beginResetModel()
        self._items.clear()

        with create_reader(filename) as reader:
            self._samples = reader.get_samples()
            for field in reader.get_fields():
                field["enabled"] = True
                field["index"] = True
                self._items.append(field)

        self.endResetModel()


class FieldsWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__()

        self.model = FieldsModel()
        self.view = QTableView()

        self.check_button = QPushButton(self.tr("Check"))
        self.check_button.clicked.connect(lambda x: self.check_fields(True))

        self.uncheck_button = QPushButton(self.tr("Uncheck"))
        self.uncheck_button.clicked.connect(lambda x: self.check_fields(False))

        self.check_index_button = QPushButton(self.tr("Set index"))
        self.check_index_button.clicked.connect(lambda x: self.check_index(True))

        self.uncheck_index_button = QPushButton(self.tr("Unset index"))
        self.uncheck_index_button.clicked.connect(lambda x: self.check_index(False))

        self.view.setModel(self.model)
        self.view.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.view.setSelectionMode(QAbstractItemView.SingleSelection)
        self.view.setAlternatingRowColors(True)
        self.view.horizontalHeader().setStretchLastSection(True)
        self.view.verticalHeader().hide()
        self.view.setSelectionMode(QAbstractItemView.ContiguousSelection)

        check_layout = QVBoxLayout()
        check_layout.addWidget(self.check_button)
        check_layout.addWidget(self.uncheck_button)
        check_layout.addStretch()
        check_layout.addWidget(self.check_index_button)
        check_layout.addWidget(self.uncheck_index_button)

        main_layout = QHBoxLayout()
        main_layout.addWidget(self.view)
        main_layout.addLayout(check_layout)

        self.setLayout(main_layout)

    @Slot()
    def check_fields(self, toggle=True):
        for index in self.view.selectionModel().selectedRows(self.model.NAME_COL):
            self.model.setData(index, toggle, Qt.CheckStateRole)

    @Slot()
    def check_index(self, toggle=True):
        for index in self.view.selectionModel().selectedRows(self.model.INDEX_COL):
            print(index.column())
            self.model.setData(index, toggle)


class SamplesWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__()

        self.view = PedView()
        self.load_button = QPushButton(self.tr("Ped file ..."))
        self.load_button.clicked.connect(self.on_import_clicked)

        vlayout = QVBoxLayout()
        vlayout.addWidget(self.load_button)
        vlayout.addStretch()

        main_layout = QHBoxLayout()
        main_layout.addWidget(self.view)
        main_layout.addLayout(vlayout)

        self.setLayout(main_layout)

    def set_samples(self, samples: list):
        self.samples = samples
        self.view.samples = [["fam", i, "0", "0", "0", "0", "0"] for i in samples]

    def on_import_clicked(self):
        """Slot called when import PED file is clicked

        We open PED file (ped, tfam) to get the their samples that will
        be associated to the current samples of the project.
        """
        # Reload last directory used

        filepath, filetype = QFileDialog.getOpenFileName(
            self,
            self.tr("Open PED file"),
            QDir.home().path(),
            self.tr("PED files (*.ped *.tfam)"),
        )

        if not filepath:
            return

        # LOGGER.info("vcf samples: %s", self.vcf_samples)
        # Get samples of individual_ids that are already on the VCF file
        self.view.samples = [
            # samples argument is empty dict since its not
            sample
            for sample in PedReader(filepath, dict())
            if sample[1] in self.samples
        ]


class VcfImportWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__()

        self.setWindowTitle(self.tr("Select a file"))

        # Create top formular
        self.anotation_detect_label = QLabel()
        self.annotation_box = QComboBox()
        self.annotation_box.setEnabled(False)

        self.file_path_edit = QLineEdit()
        self.file_path_edit.setToolTip(
            self.tr("Path to a supported input file. (e.g: VCF  file ) ")
        )
        self.import_id = QLineEdit()
        self.lock_button = QPushButton(self.tr("Edit"))
        self.lock_button.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Preferred)
        self.lock_button.setCheckable(True)
        self.lock_button.setIcon(FIcon(0xF08EE))
        self.lock_button.toggled.connect(lambda x: self.annotation_box.setEnabled(x))

        self.button = QPushButton(self.tr("Browse"))
        self.button.setIcon(FIcon(0xF0DCF))
        self.button.clicked.connect(self._browse)

        # Create content
        self.tabwidget = QTabWidget()
        self.fields_widget = FieldsWidget()
        self.samples_widget = SamplesWidget()

        # Create layout
        main_layout = QVBoxLayout()

        # top formular
        h_layout = QHBoxLayout()
        h_layout.addWidget(self.file_path_edit)
        h3_layout = QHBoxLayout()
        h3_layout.addWidget(self.import_id)
        h_layout.addWidget(self.button)
        h2_layout = QHBoxLayout()
        h2_layout.addWidget(self.annotation_box)
        h2_layout.addWidget(self.lock_button)

        self.file_group = QGroupBox()
        self.v_layout = QFormLayout(self.file_group)
        self.v_layout.addRow("Input File", h_layout)
        self.v_layout.addRow("Annotation", h2_layout)
        self.v_layout.addRow("Import ID", h3_layout)

        # Create content
        self.tabwidget.addTab(self.fields_widget, "Fields")
        self.tabwidget.addTab(self.samples_widget, "Samples")

        main_layout.addWidget(self.file_group)
        main_layout.addWidget(self.tabwidget)
        self.setLayout(main_layout)

        # Fill available parser
        self.annotation_box.addItem(FIcon(0xF13CF), "No Annotation detected", userData=None)

        for parser in VcfReader.ANNOTATION_PARSERS:
            self.annotation_box.addItem(FIcon(0xF08BB), parser, userData=parser)

    @Slot()
    def _browse(self):
        """Open a dialog box to set the data file

        The file is opened and we show an alert if annotations are detected.
        """
        # Reload last directory used
        # app_settings = QSettings()

        last_directory = ""

        filepath, filetype = QFileDialog.getOpenFileName(
            self,
            self.tr("Open a file"),
            last_directory,
            self.tr("VCF file (*.vcf *.vcf.gz);; CSV file (*.csv *.tsv *.txt)"),
        )

        self.set_filename(filepath)

    def set_filename(self, filepath: str):
        if filepath:
            # Display and save directory
            self.file_path_edit.setText(filepath)
            self.import_id.setText(os.path.basename(filepath))

            if "vcf" in filepath:
                # TODO: detect annotations on other tyes of files...
                annotation_type = detect_vcf_annotation(filepath)
                if annotation_type == None:
                    self.annotation_box.setCurrentIndex(0)
                else:
                    self.annotation_box.setCurrentText(annotation_type)

                self.fields_widget.model.load(filepath)
                self.samples_widget.set_samples(self.fields_widget.model._samples)

    def filename(self):
        return self.file_path_edit.text()

    def get_import_id(self):
        return self.import_id.text()

    def pedfile(self):
        _, filename = tempfile.mkstemp()
        self.samples_widget.view.model.to_pedfile(filename)
        return filename

    def get_ignored_fields(self):
        return self.fields_widget.model.get_ignored_fields()

    def get_indexed_fields(self):
        return self.fields_widget.model.get_indexed_fields()


class ProgressDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__()

        self.label = QLabel("Progression ... ")
        self.progress = QProgressBar()
        self.cancel_button = QPushButton(self.tr("Cancel"))
        self.ok_button = QPushButton(self.tr("Ok"))
        self.detail_button = QPushButton(self.tr("Show Details ..."))
        self.text = QPlainTextEdit()
        self.line = QFrame()

        self.line.setVisible(False)
        self.line.setFrameShape(QFrame.HLine)
        self.line.setFrameShadow(QFrame.Sunken)

        self.text.setVisible(False)

        self.label.setAlignment(Qt.AlignCenter)
        self.label.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Minimum)

        button_layout = QHBoxLayout()
        button_layout.addWidget(self.detail_button)
        button_layout.addStretch()
        button_layout.addWidget(self.cancel_button)
        button_layout.addWidget(self.ok_button)

        main_layout = QVBoxLayout(self)
        main_layout.addWidget(self.label)
        main_layout.addWidget(self.progress)
        main_layout.addLayout(button_layout)
        main_layout.addWidget(self.line)
        main_layout.addWidget(self.text)

        self.detail_button.setCheckable(True)
        self.detail_button.setChecked(False)
        self.detail_button.clicked.connect(self.toggle_detail)
        self.cancel_button.clicked.connect(self.reject)
        self.ok_button.clicked.connect(self.accept)

        self.setFixedSize(self.sizeHint())

        self.reset()

    def toggle_detail(self, show: bool = True):
        self.text.setVisible(show)
        self.line.setVisible(show)
        self.setFixedSize(self.sizeHint())

    def show_progress(self, value: int, message: str):

        self.progress.setValue(value)
        if "**" in message:
            title = message.replace("**", "")
            self.label.setText(title)

        self.text.appendPlainText(message)

    def reset(self):
        self.progress.setValue(0)
        self.label.setText("")
        self.text.clear()
        self.set_complete(False)

    def set_complete(self, complete: bool):

        self.ok_button.setEnabled(complete)
        self.cancel_button.setEnabled(not complete)


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

        self.db_filename = None
        # File top open
        self.filename = None
        # Import ID
        self.import_id = None
        # pedfile
        self.pedfile = None
        # Ignored fields
        self.ignored_fields = None
        # Fields with index
        self.indexed_fields = None
        # annotation parser
        self.annotation_parser = None

        self._reader = None

    def emit_progress(self, message: str):

        if self._reader:
            progress = self._reader.progress()
            self.progress_changed.emit(progress, message)

        else:
            self.progress_changed.emit(-1, message)

    def run(self):
        """Overrided QThread method

        .. warning:: This method is the only one to be executed in the thread.
            SQLite objects created in a thread can only be used in that same
            thread; so no use of self.conn is allowed elsewhere.
        """

        if not self.db_filename:
            LOGGER.error("No Connection set")
            return

        self.conn = sql.get_sql_connection(self.db_filename)

        self._stop = False

        #  start timer
        start = time.perf_counter()

        try:

            # Import VARIANT FILE
            self.finished_status.emit(False)
            self.emit_progress("**Import Variants**")
            import_id = self.import_id
            with create_reader(self.filename, self.annotation_parser) as reader:
                self._reader = reader
                sql.import_reader(
                    self.conn,
                    reader,
                    pedfile=self.pedfile,
                    import_id=import_id,
                    ignored_fields=self.ignored_fields,
                    indexed_fields=self.indexed_fields,
                    progress_callback=self.emit_progress,
                )

            self.conn.close()

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
        self.emit_progress("**Import has been stopped by the user**")


class VcfImportDialog(QDialog):
    def __init__(self, db_filename: str, parent=None):
        super().__init__(parent)

        self.widget = VcfImportWidget()
        self.thread = ImportThread()
        self.thread.db_filename = db_filename

        self.progress_dialog = ProgressDialog()
        self.progress_dialog.setWindowTitle(db_filename)

        self.import_button = QPushButton(self.tr("Import"))
        self.cancel_button = QPushButton(self.tr("Cancel"))

        self.import_button.clicked.connect(self.start_import)
        self.import_button.clicked.connect(self.thread.stop)

        button_layout = QHBoxLayout()
        button_layout.addWidget(self.cancel_button)
        button_layout.addStretch()
        button_layout.addWidget(self.import_button)

        main_layout = QVBoxLayout(self)
        main_layout.addWidget(self.widget)
        main_layout.addLayout(button_layout)
        self.resize(700, 500)

        self.thread.progress_changed.connect(self.progress_dialog.show_progress)
        self.thread.finished_status.connect(self.progress_dialog.set_complete)

    def start_import(self):

        self.progress_dialog.reset()
        self.thread.filename = self.widget.filename()
        self.thread.import_id = self.widget.get_import_id()

        # create pedfile
        self.thread.pedfile = self.widget.pedfile()

        self.thread.ignored_fields = self.widget.get_ignored_fields()
        self.thread.indexed_fields = self.widget.get_indexed_fields()

        self.thread.start()

        if self.progress_dialog.exec_() == QDialog.Accepted:
            self.accept()

    def db_filename(self):
        return self.thread.db_filename

    # def show_progress(self, value: float, message: str):

    #     self.progress.setValue(value)
    #     if "Step" in message:
    #         self.label.setText(message)

    #     self.text.appendPlainText(message)


if __name__ == "__main__":
    import sys
    from PySide6.QtWidgets import QApplication
    import os

    app = QApplication(sys.argv)

    try:
        os.remove("/home/sacha/test.db")
    except:
        pass

    #    dialog = VcfImportDialog(conn)
    dialog = VcfImportDialog("/home/sacha/test.db")
    dialog.exec_()

    print(dialog.widget.get_ignored_fields())
    print(dialog.widget.get_indexed_fields())
