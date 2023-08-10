# Cutevariant is a light standalone viewer of genetic variation written
# in Python for Qt. It allows to view and filter VCF and other format files.
# Copyright (C) 2018-2020  Labsquare.org
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.
#
# Please send bugreports with examples or suggestions to
# https://github.com/labsquare/cutevariant/issues

# Standard imports
import sys
from pkg_resources import parse_version

import cachetools  # Force pyinstaller to import cache tools

from PySide6.QtCore import (
    QCoreApplication,
    QSettings,
    QTranslator,
    QCommandLineParser,
    QCommandLineOption,
    QLibraryInfo,
    Qt,
    QTimer,
)
from PySide6.QtWidgets import QApplication, QSplashScreen, QStyleFactory, QColorDialog
from PySide6.QtGui import QPixmap, QColor
from PySide6.QtNetwork import QNetworkProxy

from cutevariant import __version__
import os


def main():
    """The main routine."""
    # Define the names of the organization and the application
    # The value is used by the QSettings class when it is constructed using
    # the empty constructor. This saves having to repeat this information
    # each time a QSettings object is created.
    # The default scope is QSettings::UserScope

    QCoreApplication.setOrganizationName("labsquare")
    QCoreApplication.setApplicationName("cutevariant")
    QCoreApplication.setApplicationVersion(__version__)
    QCoreApplication.setAttribute(Qt.AA_EnableHighDpiScaling, True)
    QCoreApplication.setAttribute(Qt.AA_ShareOpenGLContexts, True)
    QCoreApplication.setAttribute(Qt.AA_UseHighDpiPixmaps, True)

    # # Process command line arguments
    # app = QApplication(sys.argv)
    # # process_arguments(app)

    # # # Load app network settings
    # # load_network_settings()

    # # # Load app styles
    # # load_styles(app)

    # # # Translations
    # # load_translations(app)

    # # # debug settings
    # # # from cutevariant.gui.settings import *
    # # # w = SettingsWidget()
    # # # w.show()

    # # # Splash screen

    # # app.processEvents()

    # # # Check version
    # # settings = QSettings()
    # # settings_version = settings.value("version", None)
    # # if settings_version is None or parse_version(settings_version) < parse_version(__version__):
    # #     settings.clear()
    # #     settings.setValue("version", __version__)

    # # # Display

    # return app.exec()


if __name__ == "__main__":
    main()
