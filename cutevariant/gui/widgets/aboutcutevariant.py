"""Expose AboutCutevariant class to show information about the project"""
# Qt imports
from PySide2.QtCore import Qt, QRect, QUrl
from PySide2.QtWidgets import (
    QDialog,
    QTabWidget,
    QLabel,
    QDialogButtonBox,
    QVBoxLayout,
    QPlainTextEdit,
    QFrame,
    QApplication,
)
from PySide2.QtGui import (
    QIcon,
    QPixmap,
    QPainter,
    QBrush,
    QFont,
    QPen,
    QFontMetrics,
    QDesktopServices,
)

# Custom imports
from cutevariant.gui.ficon import FIcon
from cutevariant import commons as cm
from cutevariant import __version__


class AboutCutevariant(QDialog):
    """Display a dialog window with information about the project

    The window is mainly about the project license, authors, history of changes.
    """

    def __init__(self, parent=None):
        super().__init__(parent)

        self.setWindowTitle(self.tr("About Cutevariant"))
        self.setWindowIcon(QIcon(cm.DIR_ICONS + "app.png"))

        self.tab_widget = QTabWidget()
        self.header_lbl = QLabel()
        self.button_box = QDialogButtonBox()

        github_button = self.button_box.addButton("GitHub", QDialogButtonBox.HelpRole)
        twitter_button = self.button_box.addButton("Twitter", QDialogButtonBox.HelpRole)

        self.button_box.addButton(QDialogButtonBox.Ok)
        github_button.setIcon(FIcon(0xF02A4))
        twitter_button.setIcon(FIcon(0xF0544))

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
        github_button.clicked.connect(self.open_github_page)
        twitter_button.clicked.connect(self.open_twitter_page)

        self.resize(600, 400)

    def addTab(self, filename):
        """Read the given text file and load it in a new tab

        Files must be stored in `cutevariant/assets/`.
        """
        text_edit = QPlainTextEdit()
        text_edit.setFrameShape(QFrame.NoFrame)
        text_edit.setReadOnly(True)

        text = ""
        if filename == "LICENSE":
            # Add license header
            text = self.tr(
                "Copyright (C) 2018-2020  Labsquare.org\n\n"
                "This program is distributed under the terms of the GNU "
                "General Public License v3.\n\n"
            )

        with open(cm.DIR_ASSETS + filename, "r") as f_d:
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
        painter.setPen(QPen(QApplication.instance().palette().text().color()))
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
            f"Version %s\nGPL3 Copyright (C) 2018-2020\nLabsquare.org" % __version__,
        )

        self.header_lbl.setPixmap(pixmap)

        # Painting is finished !
        # Avoid Segfault:
        # QPaintDevice: Cannot destroy paint device that is being painted
        painter.end()

    def open_github_page(self):
        """Open the project page on GitHub"""
        QDesktopServices.openUrl(QUrl("https://github.com/labsquare/cutevariant"))

    def open_twitter_page(self):
        """Open the labsquare page on Twitter"""
        QDesktopServices.openUrl(QUrl("https://twitter.com/labsquare"))
