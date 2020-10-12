# Standard imports
import tempfile

# Qt imports
from PySide2.QtCore import (
    Qt,
    QAbstractTableModel,
    QAbstractItemModel,
    QModelIndex,
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
            "Sexe",
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
            for sample in self.samples_data:
                # Replace None or empty strings to 0 (unknown PED ID)
                clean_sample = [item if item else 0 for item in sample]
                # Convert all items to string
                file.write("\t".join(map(str, clean_sample)) + "\n")

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
        """ overrided """
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

        return

    def setData(self, index: QModelIndex, value, role=Qt.EditRole):
        """ overrided """

        if not index.isValid():
            return None

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

        return None

    def flags(self, index: QModelIndex):
        """ overrided """
        if not index.isValid():
            return None

        if index.column() > 0:
            return Qt.ItemIsSelectable | Qt.ItemIsEditable | Qt.ItemIsEnabled

        return Qt.ItemIsSelectable | Qt.ItemIsEnabled


class PedDelegate(QItemDelegate):
    def createEditor(
        self, parent: QWidget, option: QStyleOptionViewItem, index: QModelIndex
    ):

        # index.model refer to SampleModel

        if index.column() < 2:
            return super().createEditor(parent, option, index)

        widget = QComboBox(parent)
        if index.column() == 2 or index.column() == 3:
            # father_id or mother_id columns
            widget.addItems([""] + index.model().get_data_list(1))
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

        if isinstance(editor, QComboBox):
            model.setData(index, editor.currentData())
            return

        return super().setModelData(editor, model, index)


class PedView(QTableView):
    """View to display a PED file content

    Expose properties binding for QWizardPage.registerFields

    Attributes:
        samples(list): List of PED fields
        pedfile(str): PED filepath
    """

    def __init__(self):
        super().__init__()
        self.model = PedModel()
        self.delegate = PedDelegate()
        self.setModel(self.model)
        self.horizontalHeader().setStretchLastSection(True)
        self.setAlternatingRowColors(True)
        self.verticalHeader().hide()
        self.setItemDelegate(self.delegate)
        self.setEditTriggers(QAbstractItemView.CurrentChanged)
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

    @property
    def pedfile(self):
        """Return the filepath of the PED file associated to the current model"""
        if not self.get_samples():
            return

        if not self.outfile:
            # Same file but reused at each call
            self.outfile = tempfile.mkstemp(suffix=".ped", text=True)[1]
        # Export the PED data
        self.model.to_pedfile(self.outfile)
        return self.outfile
