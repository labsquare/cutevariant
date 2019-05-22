# Cutevariant is a light standalone viewer of genetic variation written
# in Python for Qt. It allows to view and filter VCF and other format files.
# Copyright (C) 2018-2019  Labsquare.org
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
import os
from PySide2.QtCore import (
    QCoreApplication,
    QSettings,
    QTranslator,
    QCommandLineParser,
    QCommandLineOption,
)
from PySide2.QtWidgets import QApplication

# Custom imports
from cutevariant.gui import MainWindow, setFontPath, style
import cutevariant.commons as cm
from cutevariant import __version__


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

    app = QApplication(sys.argv)
    # Process command line arguments
    process_arguments(app)

    # apply dark style 
    style.dark(app)



    # Set icons set
    setFontPath(os.path.join(cm.DIR_FONTS, "materialdesignicons-webfont.ttf"))

    # Translations
    load_translations(app)

    # debug settings
    # from cutevariant.gui.settings import *
    # w = SettingsWidget()
    # w.show()

    # Display
    w = MainWindow()

    STYLES = cm.DIR_STYLES + "frameless.qss"
    with open(STYLES,"r") as file:
        w.setStyleSheet(file.read())

    w.show()
    app.exec_()


def load_translations(app):
    """Load translations

    .. note:: Init ui/locale setting
    """

    # Load locale setting if exists
    # English is the default language
    app_settings = QSettings()
    locale_name = app_settings.value("ui/locale", "en")
    app_translator = QTranslator(app)

    if app_translator.load(locale_name, directory=cm.DIR_TRANSLATIONS):
        app.installTranslator(app_translator)
    else:
        # Init setting
        app_settings.setValue("ui/locale", "en")


def process_arguments(app):
    """Arguments parser"""
    parser = QCommandLineParser()
    # -h, --help, -? (on windows)
    parser.addHelpOption()
    # --version
    show_version = QCommandLineOption(
        ["version"],
        QCoreApplication.translate(
            "main", "Display the version of Cutevariant and exit."
        ),
    )
    parser.addOption(show_version)
    # -v, --verbose
    modify_verbosity = QCommandLineOption(
        ["v", "verbose"],
        QCoreApplication.translate("main", "Modify verbosity."),
        "notset|debug|info|error",  # options available (value name)
        "notset",  # default value
    )
    parser.addOption(modify_verbosity)

    # Process the actual command line arguments given by the user
    parser.process(app)
    # args = parser.positionalArguments()

    if parser.isSet(show_version):
        print("Cutevariant " + __version__)
        exit()

    if parser.isSet(modify_verbosity):
        # Set log level
        cm.log_level(parser.value(modify_verbosity).upper())


if __name__ == "__main__":

    main()
