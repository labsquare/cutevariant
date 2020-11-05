# Standard imports
import tempfile

# Qt imports
from PySide2.QtCore import (
    Qt,
    QAbstractTableModel,
    QAbstractItemModel,
    QModelIndex,
    Property,
    Signal,
)

from PySide2.QtWidgets import (
    QTableView,
    QItemDelegate,
    QWidget,
    QStyleOptionViewItem,
    QComboBox,
    QAbstractItemView,
)

# Custom imports
from cutevariant.core.reader import PedReader
from cutevariant.core.writer import PedWriter


class PedModel(QAbstractTableModel):
    """
    Attributes:

        samples_data (list[list]): List of samples; Each sample is composed of
            the following terms:

            `[family_id, individual_id, father_id, mother_id, sex, genotype]`

    """

    def __init__(self):
        super().__init__()

        self.samples_data = []
        self.headers = (
            "Family",
            "Sample",
            "Father_id",
            "Mother_id",
            "Sex",
            "Phenotype",
        )

        self.sex_map = {"1": "Male", "2": "Female", "0": ""}

        self.phenotype_map = {"1": "Unaffected", "2": "Affected", "0": ""}

    def rowCount(self, index=QModelIndex()):
        """ override """
        return len(self.samples_data)

    def columnCount(self, index=QModelIndex()):
        """ override """
        if index == QModelIndex():
            return len(self.headers)

        return 0

    def get_data_list(self, column: int):
        """Get unique list of items at the given column of all samples

        Notes:
            `samples_data` is composed of the following terms:
            `[family_id, individual_id, father_id, mother_id, sex, genotype]`

        Examples:
            If column 1 is given, we return a list of unique individual_ids.
        """
        return list({sample[column] for sample in self.samples_data})

    def clear(self):
        self.beginResetModel()
        self.samples_data.clear()
        self.endResetModel()

    def from_pedfile(self, filename: str):
        """Fill model with NEW samples from PED file"""
        samples = dict()
        self.beginResetModel()
        self.samples_data.clear()
        self.samples_data = list(PedReader(filename, samples))
        self.endResetModel()

    def to_pedfile(self, filename: str):
        """Export the model to a tabulated PED file

        Notes:
            Replace None or empty strings to 0 (unknown PED ID)
        """
        with open(filename, "w") as file:
            writer = PedWriter(file)
            writer.save_from_list(self.samples_data)

    def set_samples(self, samples: list):
        """Fill model with NEW samples

        Example:
            samples = [family_id, individual_id, father_id, mother_id, sex, genotype]
        """
        self.beginResetModel()
        self.samples_data.clear()
        self.samples_data = list(samples)
        self.endResetModel()

    def data(self, index: QModelIndex, role=Qt.DisplayRole):
        """Overrided

        Notes:
            Default values of different sample fields are empty strings
        """
        if not index.isValid():
            return

        if role == Qt.DisplayRole or role == Qt.EditRole:
            value = self.samples_data[index.row()][index.column()]

            if index.column() == 2 or index.column() == 3:  # father_id, mother_id
                return value if value != "0" else ""

            if index.column() == 4:  # Sex
                return self.sex_map.get(value, "")

            if index.column() == 5:  # Phenotype
                return self.phenotype_map.get(value, "")

            return value

    def setData(self, index: QModelIndex, value, role=Qt.EditRole):
        """ overrided """

        if not index.isValid():
            return

        if role == Qt.EditRole:
            self.samples_data[index.row()][index.column()] = value
            return True

        return False

    def headerData(
        self, section: int, orientation: Qt.Orientation, role: Qt.DisplayRole
    ):
        """ overrided """
        if orientation == Qt.Horizontal:
            if role == Qt.DisplayRole:
                return self.headers[section]

    def flags(self, index: QModelIndex):
        """ overrided """
        if not index.isValid():
            return

        if index.column() > 1:
            # Family ids & Individual ids are NOT editable (we must fit with the VCF file)
            return Qt.ItemIsSelectable | Qt.ItemIsEditable | Qt.ItemIsEnabled

        return Qt.ItemIsSelectable | Qt.ItemIsEnabled


class PedDelegate(QItemDelegate):
    """Allow the way items of data are rendered and edited to be customized

    Signals:
        parthenogenesis_detected(str): Emit message about the sample that has
            the same father and mother ids.
    """

    parthenogenesis_detected = Signal(str)

    def __init__(self):
        super().__init__()
        # Keep the rows of erroneous samples (same father/mother ids)
        self.erroneous_samples = set()

    def createEditor(
        self, parent: QWidget, option: QStyleOptionViewItem, index: QModelIndex
    ):
        """Return editor widget for columns of PedView

        Notes:
            Family ids & Individual ids are NOT editable (we must fit with the VCF file)
        """
        # PS: index.model refer to SampleModel

        if index.column() < 2:
            # Family ids & Individual ids are NOT editable (we must fit with the VCF file)
            return

        widget = QComboBox(parent)
        if index.column() == 2 or index.column() == 3:
            # Forge a list of available individual ids except the current one
            # Get individual_id of the current row/sample
            current_individual_id = index.model().samples_data[index.row()][1]
            # Remove current individual_id from propositions
            individual_ids = set(index.model().get_data_list(1))
            individual_ids.remove(current_individual_id)
            # father_id or mother_id columns
            widget.addItem("", "0")
            for individual_id in individual_ids:
                widget.addItem(individual_id, individual_id)

            return widget

        if index.column() == 4:
            # Sex column
            widget.addItem("Male", "1")
            widget.addItem("Female", "2")
            widget.addItem("", "0")
            return widget

        if index.column() == 5:
            # Genotype column
            widget.addItem("Unaffected", "1")
            widget.addItem("Affected", "2")
            widget.addItem("", "0")
            return widget

        return super().createEditor(parent, option, index)

    def setModelData(
        self, editor: QWidget, model: QAbstractItemModel, index: QModelIndex
    ):
        """Set the data for the item at the given index in the model to the
        contents of the given editor.
        """
        if isinstance(editor, QComboBox):
            model.setData(index, editor.currentData())

            if index.column() == 2 or index.column() == 3:
                row = index.row()
                model = index.model()
                # Detect parthenogenesis: same mother and father
                father_id = model.samples_data[row][2]
                # Only for not unknown parents
                if father_id != "0" and father_id == model.samples_data[row][3]:
                    self.erroneous_samples.add(row)
                elif row in self.erroneous_samples:
                    # Reset interface
                    self.parthenogenesis_detected.emit("")
                    self.erroneous_samples.remove(row)

            for row in self.erroneous_samples:
                self.parthenogenesis_detected.emit(
                    self.tr(
                        "<b>Same father and mother for sample '{}'</b>").format(
                        model.samples_data[row][1]
                    )
                )
            return

        # Basic text not editable
        return super().setModelData(editor, model, index)


class PedView(QTableView):
    """View to display a PED file content

    Expose properties binding for QWizardPage.registerFields

    Attributes:
        samples(list): List of PED fields
        pedfile(str): PED filepath
    """

    message = Signal(str)

    def __init__(self):
        super().__init__()
        self.model = PedModel()
        self.delegate = PedDelegate()
        self.setModel(self.model)
        self.horizontalHeader().setStretchLastSection(True)
        self.setAlternatingRowColors(True)
        self.verticalHeader().hide()
        self.setItemDelegate(self.delegate)
        self.setEditTriggers(QAbstractItemView.CurrentChanged | QAbstractItemView.DoubleClicked)
        self.delegate.parthenogenesis_detected.connect(self.message)
        # PED file for the model
        self.outfile = None

    def clear(self):
        self.model.clear()

    @property
    def samples(self):
        """Get samples (list of PED fields)"""
        return self.model.samples_data

    @samples.setter
    def samples(self, samples):
        """Set samples

        Args:
            samples(list): PED fields
        """
        self.model.set_samples(samples)

    @Property(str)  # Qt property for QWizardPage.registerFields
    def pedfile(self):
        """Return the filepath of the PED file associated to the current model"""
        if not self.samples:
            return

        if not self.outfile:
            # Same file but reused at each call
            self.outfile = tempfile.mkstemp(suffix=".ped", text=True)[1]
        # Export the PED data
        self.model.to_pedfile(self.outfile)
        return self.outfile
