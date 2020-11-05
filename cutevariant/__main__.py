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
from PySide2.QtCore import (
    QCoreApplication,
    QSettings,
    QTranslator,
    QCommandLineParser,
    QCommandLineOption,
    QLibraryInfo,
)
from PySide2.QtWidgets import QApplication, QSplashScreen
from PySide2.QtGui import QPixmap

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

    # Process command line arguments
    app = QApplication(sys.argv)
    process_arguments(app)

    # Load app styles
    load_styles(app)

    # Set icons set
    setFontPath(cm.FONT_FILE)

    # Translations
    load_translations(app)

    # Load default external links
    load_default_external_links()

    # debug settings
    # from cutevariant.gui.settings import *
    # w = SettingsWidget()
    # w.show()

    # Splash screen
    splash = QSplashScreen()
    splash.setPixmap(QPixmap(cm.DIR_ICONS + "splash.png"))
    splash.showMessage(f"Version {__version__}")
    splash.show()
    app.processEvents()

    # Display
    w = MainWindow()

    # STYLES = cm.DIR_STYLES + "frameless.qss"
    # with open(STYLES,"r") as file:
    #     w.setStyleSheet(file.read())

    w.show()
    splash.finish(w)
    app.exec_()


def load_styles(app):
    """Apply styles to the application and its windows
    """
    # Set fusion style
    # The Fusion style is a platform-agnostic style that offers a
    # desktop-oriented look'n'feel.
    # The Fusion style is not a native desktop style.
    # The style runs on any platform, and looks similar everywhere
    app.setStyle("fusion")

    # Load style from settings if exists
    app_settings = QSettings()
    # Display current style
    style_name = app_settings.value("ui/style", cm.BASIC_STYLE)

    # Apply selected style by calling on the method in style module based on its
    # name; equivalent of style.dark(app)
    getattr(style, style_name.lower())(app)


def load_translations(app):
    """Load translations

    .. note:: Init ui/locale setting
    """
    # Load locale setting if exists
    # English is the default language
    app_settings = QSettings()
    locale_name = app_settings.value("ui/locale", "en")

    # site-packages/PySide2/Qt/translations
    lib_info = QLibraryInfo.location(QLibraryInfo.TranslationsPath)

    # Qt translations
    qt_translator = QTranslator(app)
    if qt_translator.load("qt_" + locale_name, directory=lib_info):
        app.installTranslator(qt_translator)

    # qtbase_translator = QTranslator(app)
    # if qtbase_translator.load("qtbase_" + locale_name, directory=lib_info):
    #     app.installTranslator(qtbase_translator)

    # App translations
    app_translator = QTranslator(app)
    if app_translator.load(locale_name, directory=cm.DIR_TRANSLATIONS):
        app.installTranslator(app_translator)
    else:
        # Init setting
        app_settings.setValue("ui/locale", "en")


def load_default_external_links():
    """Load default external DB links if the list is empty"""
    app_settings = QSettings()
    app_settings.beginGroup("plugins/variant_view/links")

    # If no value: add default values
    if not app_settings.childKeys():
        for db_name, db_url in cm.WEBSITES_URLS.items():
            app_settings.setValue(db_name, db_url)
    app_settings.endGroup()


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


