from PySide6.QtWidgets import *
from PySide6.QtCore import *
from PySide6.QtGui import *

from cutevariant.gui import FIcon

from cutevariant import LOGGER

class SortFieldDialog(QDialog):

    """A dialog box to dispay and order fields from a preset config

    dialog = SortFieldDialog()
    dialog.load()

    """

    def __init__(self, preset_name="test_preset", parent=None):
        super().__init__()

        self.setWindowTitle(self.tr("Sort fields order"))

        self.header = QLabel(self.tr("You can sort fields by drag and drop"))
        self.view = QListWidget()
        self.view.setDragDropMode(QAbstractItemView.InternalMove)
        self.view.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

        self.button_box = QDialogButtonBox(QDialogButtonBox.Cancel | QDialogButtonBox.Ok)
        self.up_button = QToolButton()
        self.up_button.setText("▲")
        self.up_button.setIcon(FIcon(0xF0143))
        self.up_button.setAutoRaise(True)
        self.up_button.clicked.connect(self.move_up)

        self.down_button = QToolButton()
        self.down_button.setText("▼")
        self.down_button.setIcon(FIcon(0xF0140))
        self.down_button.setAutoRaise(True)
        self.down_button.clicked.connect(self.move_down)

        vLayout = QVBoxLayout()
        tool_layout = QHBoxLayout()

        tool_layout.addStretch()
        tool_layout.addWidget(self.up_button)
        tool_layout.addWidget(self.down_button)

        vLayout.addWidget(self.header)
        vLayout.addWidget(self.view)
        vLayout.addLayout(tool_layout)
        vLayout.addWidget(self.button_box)
        self.setLayout(vLayout)

        self.button_box.accepted.connect(self.accept)
        self.button_box.rejected.connect(self.reject)

    @property
    def fields(self):
        return [self.view.item(row).text() for row in range(self.view.count())]

    @fields.setter
    def fields(self, fields):
        self.view.clear()
        self.view.addItems(fields)

    def move_up(self):
        row = self.view.currentRow()
        if row <= 0:
            return
        item = self.view.takeItem(row - 1)
        self.view.insertItem(row, item)

    def move_down(self):
        row = self.view.currentRow()
        if row > self.view.count() - 1:
            return
        item = self.view.takeItem(row + 1)
        self.view.insertItem(row, item)