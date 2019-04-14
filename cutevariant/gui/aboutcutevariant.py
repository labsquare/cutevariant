# Standard imports
from pkg_resources import resource_filename

# Qt imports
from PySide2.QtCore import *
from PySide2.QtWidgets import *
from PySide2.QtGui import *

# Custom imports
from cutevariant.gui.ficon import FIcon
from cutevariant import commons as cm


class AboutCutevariant(QDialog):
    def __init__(self, parent=None):

        super(AboutCutevariant, self).__init__()

        self.setWindowTitle(self.tr("About Cutevariant"))

        self.tab_widget = QTabWidget()
        self.header_lbl = QLabel()
        self.button_box = QDialogButtonBox()

        githubButton = self.button_box.addButton("Github", QDialogButtonBox.HelpRole)
        twitterButton = self.button_box.addButton("Twitter", QDialogButtonBox.HelpRole)

        self.button_box.addButton(QDialogButtonBox.Ok)
        githubButton.setIcon(FIcon(0xF2A4))
        twitterButton.setIcon(FIcon(0xF546))

        vLayout = QVBoxLayout()
        vLayout.addWidget(self.header_lbl)
        vLayout.addWidget(self.tab_widget)
        vLayout.addWidget(self.button_box)

        self.setLayout(vLayout)

        self.addTab("LICENSE")
        # self.addTab("AUTHORS")
        # self.addTab("CREDITS")
        # self.addTab("CHANGELOG")

        self.drawHeader()

        # Connexions
        self.button_box.button(QDialogButtonBox.Ok).clicked.connect(self.close)
        githubButton.clicked.connect(self.openGithub)
        twitterButton.clicked.connect(self.openTwitter)

        self.resize(600, 400)

    def addTab(self, filename):
        """Read the given text file and load it in a new tab"""

        # Get file at the project's root directory
        filepath = resource_filename(__name__, "../../" + filename)

        text_edit = QPlainTextEdit()
        text_edit.setFrameShape(QFrame.NoFrame)
        text_edit.setReadOnly(True)

        text = ""
        if filename == "LICENSE":
            # Add license header
            text = self.tr(
                "Copyright (C) 2018-2019  labsquare.org\n\n"
                "This program is distributed under the terms of the GNU "
                "General Public License v3.\n\n"
            )

        with open(filepath, "r") as f_d:
            text_edit.setPlainText(text + f_d.read())
            self.tab_widget.addTab(text_edit, filename)

    def drawHeader(self):
        """Draw logo/copyright in the header"""

        pHeight = 90
        pMargin = 15
        icon_path = cm.DIR_ICONS + "app.png"

        self.header_lbl.setMinimumHeight(pHeight)
        self.header_lbl.setFrameShape(QFrame.StyledPanel)
        self.header_lbl.setContentsMargins(0, 0, 0, 0)

        pixmap = QPixmap(450, pHeight)
        pixmap.fill(Qt.transparent)

        iconY = (pHeight - 64) / 2
        logoRect = QRect(pMargin, iconY, 64, 64)

        painter = QPainter(pixmap)
        painter.setBrush(QBrush(Qt.red))
        painter.drawPixmap(
            logoRect,
            QPixmap(icon_path).scaled(
                logoRect.width(),
                logoRect.height(),
                Qt.KeepAspectRatio,
                Qt.SmoothTransformation,
            ),
        )

        titleRect = QRect(logoRect.right() + 10, iconY, 200, pHeight)

        font = QFont()
        font.setBold(True)
        font.setPixelSize(16)
        painter.setFont(font)
        painter.setPen(QPen(QColor("#555753")))
        painter.drawText(titleRect, Qt.AlignTop, "Cutevariant")

        font_metrics = QFontMetrics(font)
        font.setBold(False)
        font.setPixelSize(12)
        painter.setFont(font)
        painter.setPen(QPen(Qt.darkGray))
        titleRect.setY(titleRect.y() + font_metrics.height())

        painter.drawText(
            titleRect,
            Qt.AlignTop,
            f"Version %s\nGPL3 Copyright (C) 2019\nLabsquare.org"
            % qApp.applicationVersion(),
        )

        self.header_lbl.setPixmap(pixmap)

        # Painting is finished !
        # Avoid Segfault:
        # QPaintDevice: Cannot destroy paint device that is being painted
        painter.end()

    @Slot()
    def openGithub(self):
        QDesktopServices.openUrl(QUrl("https://github.com/labsquare/cutevariant"))

    @Slot()
    def openTwitter(self):
        QDesktopServices.openUrl(QUrl("https://twitter.com/labsquare"))
