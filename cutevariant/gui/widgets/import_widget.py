# Qt imports
from PySide2.QtCore import (
    QLine,
    Qt,
    QAbstractTableModel,
    QAbstractItemModel,
    QModelIndex,
    Property,
    Signal,
    QThread,
    Slot,
)

from PySide2.QtGui import QFont, QColor
from PySide2.QtWidgets import (
    QLineEdit,
    QStyle,
    QFrame,
    QTableView,
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

from cutevariant.gui.ficon import FIcon
from cutevariant.core.reader.vcfreader import VcfReader
from cutevariant.core.readerfactory import detect_vcf_annotation, create_reader
from cutevariant.core import sql
from cutevariant import LOGGER


class ReaderModel(QAbstractTableModel):

    MANDATORY_FIELDS = ["chr", "pos", "ref", "alt", "gt"]

    NAME_COL = 0
    INDEX_COL = 1
    CATEGORY_COL = 2
    TYPE_COL = 3
    DESC_COL = 4

    def __init__(self, parent=None):
        super().__init__(parent=parent)
        self._items = []
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
                return qApp.style().standardIcon(QStyle.SP_DialogApplyButton)
            else:
                return qApp.style().standardIcon(QStyle.SP_DialogCancelButton)

        if role == Qt.CheckStateRole:
            if index.column() == self.NAME_COL:
                return Qt.Checked if item["enabled"] else Qt.Unchecked

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
            return 0

        if index.column() == self.NAME_COL or index.column() == self.INDEX_COL:
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


class VcfImportWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__()

        self.setWindowTitle(self.tr("Select a file"))

        # Create widgets
        self.file_path_edit = QLineEdit()
        self.annotation_box = QComboBox()
        self.lock_button = QPushButton(self.tr("Edit"))
        self.anotation_detect_label = QLabel()
        self.button = QPushButton(self.tr("Browse"))

        self.check_button = QPushButton(self.tr("Check"))
        self.uncheck_button = QPushButton(self.tr("Uncheck"))

        self.check_index_button = QPushButton(self.tr("Set index"))
        self.uncheck_index_button = QPushButton(self.tr("Unset index"))

        self.view = QTableView()
        self.model = ReaderModel()
        self.view.setModel(self.model)

        self.check_button.clicked.connect(lambda x: self.check_fields(True))
        self.uncheck_button.clicked.connect(lambda x: self.check_fields(False))

        self.check_index_button.clicked.connect(lambda x: self.check_index(True))
        self.uncheck_index_button.clicked.connect(lambda x: self.check_index(False))

        self.view.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.view.setSelectionMode(QAbstractItemView.SingleSelection)
        self.view.setAlternatingRowColors(True)
        self.view.horizontalHeader().setStretchLastSection(True)
        self.view.verticalHeader().hide()
        self.view.setSelectionMode(QAbstractItemView.ContiguousSelection)

        self.button.setIcon(FIcon(0xF0DCF))
        self.button.clicked.connect(self._browse)

        self.lock_button.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Preferred)
        self.lock_button.setCheckable(True)
        self.lock_button.setIcon(FIcon(0xF08EE))
        self.lock_button.toggled.connect(lambda x: self.annotation_box.setEnabled(x))

        self.annotation_box.setEnabled(False)

        self.file_path_edit.setToolTip(
            self.tr("Path to a supported input file. (e.g: VCF  file ) ")
        )

        # Create layout
        main_layout = QVBoxLayout()
        h_layout = QHBoxLayout()
        h_layout.addWidget(self.file_path_edit)
        h_layout.addWidget(self.button)

        h2_layout = QHBoxLayout()
        h2_layout.addWidget(self.annotation_box)
        h2_layout.addWidget(self.lock_button)

        check_layout = QVBoxLayout()
        check_layout.addWidget(self.check_button)
        check_layout.addWidget(self.uncheck_button)
        check_layout.addStretch()
        check_layout.addWidget(self.check_index_button)
        check_layout.addWidget(self.uncheck_index_button)

        self.v_layout = QFormLayout()
        self.v_group = QGroupBox()
        self.v_group.setTitle("Select file")
        self.v_layout.addRow("Input File", h_layout)
        self.v_layout.addRow("Annotation", h2_layout)
        self.v_group.setLayout(self.v_layout)

        self.central_box = QGroupBox()
        self.central_box.setTitle(self.tr("Select fields to import"))
        central_layout = QHBoxLayout()
        central_layout.addWidget(self.view)
        central_layout.addLayout(check_layout)
        self.central_box.setLayout(central_layout)

        main_layout.addWidget(self.v_group)
        main_layout.addWidget(self.central_box)

        self.setLayout(main_layout)

        # self.file_path_edit.textChanged.connect(self.completeChanged)
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
        # app_settings = QSettings()

        last_directory = ""

        filepath, filetype = QFileDialog.getOpenFileName(
            self,
            self.tr("Open a file"),
            last_directory,
            self.tr("VCF file (*.vcf *.vcf.gz);; CSV file (*.csv *.tsv *.txt)"),
        )

        if filepath:
            # Display and save directory
            self.file_path_edit.setText(filepath)

            if "vcf" in filepath:
                # TODO: detect annotations on other tyes of files...
                annotation_type = detect_vcf_annotation(filepath)
                if annotation_type == None:
                    self.annotation_box.setCurrentIndex(0)
                else:
                    self.annotation_box.setCurrentText(annotation_type)

                self.model.load(filepath)

    @Slot()
    def check_fields(self, toggle=True):
        for index in self.view.selectionModel().selectedRows(self.model.NAME_COL):
            self.model.setData(index, toggle, Qt.CheckStateRole)

    @Slot()
    def check_index(self, toggle=True):
        for index in self.view.selectionModel().selectedRows(self.model.INDEX_COL):
            print(index.column())
            self.model.setData(index, toggle)

    def filename(self):
        return self.file_path_edit.text()


class ProgressDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__()

        self.label = QLabel("Progression ... ")
        self.progress = QProgressBar()
        self.cancel_button = QPushButton(self.tr("Cancel"))
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
        self.setFixedSize(self.sizeHint())

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

        self.db_filename = ""
        # File top open
        self.filename = ""
        # Ignored fields
        self.ignored_fields = None
        # Fields with index
        self.index_fields = None
        # annotation parser
        self.annotation_parser = None

    def progress(self, progress: int, message: str):
        self.progress_changed.emit(progress, message)
        return self._stop

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
            self.progress(0, "**Import Variants**")
            with create_reader(self.filename, self.annotation_parser) as reader:
                sql.import_reader(self.conn, reader, progress_callback=self.progress)

            # Update count
            self.progress(0, "**Compute variant count**")
            sql.update_variants_counts(self.conn)

            # Update Index
            self.progress(0, "**Create indexes**")
        # sql.create_indexes(
        #     self.conn,
        #     self.indexed_variant_fields,
        #     self.indexed_annotation_fields,
        #     self.indexed_sample_fields,
        # )
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


class VcfImportDialog(QDialog):
    def __init__(self, db_filename: str, parent=None):
        super().__init__(parent)

        self.widget = VcfImportWidget()
        self.thread = ImportThread()
        self.thread.db_filename = db_filename

        self.progress_dialog = ProgressDialog()

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

    def start_import(self):

        self.progress_dialog.reset()
        self.thread.filename = self.widget.filename()

        self.thread.start()
        self.progress_dialog.exec_()

    # def show_progress(self, value: float, message: str):

    #     self.progress.setValue(value)
    #     if "Step" in message:
    #         self.label.setText(message)

    #     self.text.appendPlainText(message)


if __name__ == "__main__":
    import sys
    from PySide2.QtWidgets import QApplication

    app = QApplication(sys.argv)

    #    dialog = VcfImportDialog(conn)
    dialog = VcfImportDialog("/home/sacha/test.db")
    dialog.exec_()
