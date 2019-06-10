from PySide2.QtWidgets import *
from PySide2.QtCore import *
from PySide2.QtGui import *


import sys
from cutevariant.gui import style


class FieldView(QDialog):
    """docstring for FieldViewQDialog"""

    def __init__(self, parent=None):
        super().__init__(parent)

        self.label = QLabel(
            """ 
		<font style='font-size:12pt; font-weight:bold'>Chromosome <br/>
		 <font style='font-size:10pt;font-weight:normal'>
		 Lorem  ipsum dolor sit amet ipsum dolor sit ameti ipsum dolor sit amet 
		 ipsum dolor sit ametpsum dolor sit amet
		 </font>
		 """
        )
        self.label.setAlignment(Qt.AlignTop)
        self.label.setWordWrap(True)
        self.label.setAutoFillBackground(True)
        self.label.setFrameShape(QFrame.StyledPanel)
        self.label.setBackgroundRole(QPalette.AlternateBase)
        self.label.setFixedHeight(90)
        v_layout = QVBoxLayout()
        v_layout.addWidget(self.label)
        # v_layout.setContentsMargins(0,0,0,0)

        self.operator = QComboBox()
        self.value = QSpinBox()

        self.operator.setEditable(True)

        self.form_layout = QFormLayout()
        self.form_layout.addRow("field", QComboBox())
        self.form_layout.addRow("operator", self.operator)
        self.form_layout.addRow("value", self.value)
        self.form_layout.setFormAlignment(Qt.AlignHCenter | Qt.AlignCenter)

        v_layout.addSpacing(20)
        v_layout.addLayout(self.form_layout)

        v_layout.addStretch()

        self.button_box = QDialogButtonBox(
            QDialogButtonBox.Ok | QDialogButtonBox.Cancel
        )
        v_layout.addWidget(self.button_box)

        font = QFont()
        font.setPixelSize(29)
        self.label.setFont(font)

        self.setLayout(v_layout)

        self.resize(500, 400)


if __name__ == "__main__":
    app = QApplication(sys.argv)

    app.setStyle("fusion")
    # apply dark style
    style.dark(app)
    d = TestWidget()
    d.show()

    app.exec_()


# from cutevariant.core.model import *
