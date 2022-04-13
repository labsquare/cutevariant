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
)
from PySide6.QtWidgets import QApplication, QSplashScreen, QStyleFactory
from PySide6.QtGui import QPixmap
from PySide6.QtNetwork import QNetworkProxy

# Custom imports
from cutevariant.config import Config
from cutevariant.gui import MainWindow, network, setFontPath, style
import cutevariant.commons as cm
from cutevariant import LOGGER
from cutevariant import __version__
import faulthandler
import os
from cutevariant.core import command, sql, vql
from cutevariant.core.reader import VcfReader
import csv

faulthandler.enable()


def main():
    """The main routine."""
    # Define the names of the organization and the application
    # The value is used by the QSettings class when it is constructed using
    # the empty constructor. This saves having to repeat this information
    # each time a QSettings object is created.
    # The default scope is QSettings::UserScope

    LOGGER.info("Starting cutevariant")
    QCoreApplication.setOrganizationName("labsquare")
    QCoreApplication.setApplicationName("cutevariant")
    QCoreApplication.setApplicationVersion(__version__)
    QCoreApplication.setAttribute(Qt.AA_EnableHighDpiScaling, True)
    QCoreApplication.setAttribute(Qt.AA_ShareOpenGLContexts, True)
    QCoreApplication.setAttribute(Qt.AA_UseHighDpiPixmaps, True)

    # Process command line arguments
    app = QApplication(sys.argv)
    process_arguments(app)

    # Load app network settings
    LOGGER.info("Load network settings")
    load_network_settings()

    # Load app styles
    LOGGER.info("Load style")
    app.setStyle(QStyleFactory.create("Fusion"))
    load_styles(app)

    # # Uncomment those line to clear settings
    # settings = QSettings()
    # settings.clear()

    # Set icons set
    LOGGER.info("Load font")
    setFontPath(cm.FONT_FILE)

    # Translations
    LOGGER.info("Load translation")
    load_translations(app)

    # debug settings
    # from cutevariant.gui.settings import *
    # w = SettingsWidget()
    # w.show()

    LOGGER.info("Starting the GUI...")
    # Splash screen
    splash = QSplashScreen()
    splash.setPixmap(QPixmap(cm.DIR_ICONS + "splash.png"))
    splash.showMessage(f"Version {__version__}")
    splash.show()
    app.processEvents()

    #  Drop settings if old version
    settings = QSettings()
    settings_version = settings.value("version", None)
    if settings_version is None or parse_version(settings_version) < parse_version(
        __version__
    ):
        settings.clear()
        settings.setValue("version", __version__)

    # Display
    w = MainWindow()

    # STYLES = cm.DIR_STYLES + "frameless.qss"
    # with open(STYLES,"r") as file:
    #     w.setStyleSheet(file.read())

    w.show()
    splash.finish(w)
    app.exec()


def load_network_settings():
    config = Config("app")
    if "network" in config:
        _network = config.get("network", {})
        proxy_type = network.PROXY_TYPES.get(
            _network.get("type"), QNetworkProxy.NoProxy
        )
        host_name = _network.get("host", "")
        port_number = _network.get("port", "")
        user_name = _network.get("username", "")
        password = _network.get("password", "")
        proxy = QNetworkProxy(proxy_type, host_name, port_number, user_name, password)
        LOGGER.debug(
            "Setting application proxy to\nType:%s\nHost:%s\nPort:%s\nUser name:%s",
            proxy.type(),
            proxy.hostName(),
            proxy.port(),
            proxy.user(),
        )
        QNetworkProxy.setApplicationProxy(proxy)
        proxy = QNetworkProxy.applicationProxy()
        # Make sure the application proxy was set successfully
        LOGGER.debug(
            "Application proxy set to\nType:%s\nHost:%s\nPort:%s\nUser name:%s",
            proxy.type(),
            proxy.hostName(),
            proxy.port(),
            proxy.user(),
        )


def load_styles(app):
    """Apply styles to the application and its windows"""
    # Set fusion style
    # The Fusion style is a platform-agnostic style that offers a
    # desktop-oriented look'n'feel.
    # The Fusion style is not a native desktop style.
    # The style runs on any platform, and looks similar everywhere
    # app.setStyle("fusion")

    # Load style from settings if exists
    config = Config("app")
    # Display current style
    style_config = config.get("style", {})
    theme = style_config.get("theme", cm.BASIC_STYLE)
    # Apply selected style by calling on the method in style module based on its
    # name; equivalent of style.dark(app)
    getattr(style, theme.lower())(app)


def load_translations(app):
    """Load translations

    .. note:: Init ui/locale setting
    """
    # Load locale setting if exists
    # English is the default language
    app_settings = QSettings()
    locale_name = app_settings.value("ui/locale", "en")

    # site-packages/PySide6/Qt/translations
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

    # Config
    config_option = QCommandLineOption(
        ["c", "config"],
        QCoreApplication.translate("config path", "Set the config path"),
        "config",
    )

    parser.addOption(config_option)

    # -v, --verbose
    modify_verbosity = QCommandLineOption(
        ["v", "verbose"],
        QCoreApplication.translate("main", "Modify verbosity."),
        "notset|debug|info|error",  # options available (value name)
        "debug",  # default value
    )
    parser.addOption(modify_verbosity)

    # import_vcf
    import_vcf_option = QCommandLineOption(
        ["i", "import_vcf"],
        QCoreApplication.translate("import VCF", "Import VCF file"),
        "import_vcf",
    )

    parser.addOption(import_vcf_option)

    # vcf_annotations
    vcf_annotations_option = QCommandLineOption(
        ["a", "vcf_annotations"],
        QCoreApplication.translate("VCF annotations", "VCF annotations type"),
        "vcf_annotations",
    )

    parser.addOption(vcf_annotations_option)

    # project_db
    project_db_option = QCommandLineOption(
        ["p", "project_db"],
        QCoreApplication.translate("Project VCF", "Connexion to a project DB"),
        "project_db",
    )

    parser.addOption(project_db_option)

    # Process the actual command line arguments given by the user
    parser.process(app)
    # args = parser.positionalArguments()

    if parser.isSet(show_version):
        print("Cutevariant " + __version__)
        exit()

     # Set log level
    # if parser.isSet(modify_verbosity):
    LOGGER.setLevel(parser.value(modify_verbosity).upper())


    if parser.isSet(config_option):
        config_path = parser.value(config_option)
        if os.path.isfile(config_path):
            Config.DEFAULT_CONFIG_PATH = config_path
        else:
            LOGGER.error(f"{config_path} doesn't exists. Ignoring config")

   
    # import VCF into DB
    if parser.isSet(import_vcf_option) and parser.isSet(project_db_option):
        import_vcf_option_path = parser.value(import_vcf_option)
        project_db_option_path = parser.value(project_db_option)
        vcf_annotations_option_value = parser.value(vcf_annotations_option)
        if os.path.isfile(project_db_option_path):
            conn = sql.get_sql_connection(project_db_option_path)
            if os.path.isfile(import_vcf_option_path):
                sql.import_reader(conn, VcfReader(import_vcf_option_path, vcf_annotations_option_value))
                LOGGER.info(f"Import VCF {import_vcf_option_path} in project DB {project_db_option_path}")
            else:
                LOGGER.error(f"Import VCF {import_vcf_option_path} in project DB {project_db_option_path} FAILED!!!")
        else:
            LOGGER.error(f"Import VCF {import_vcf_option_path} in project DB {project_db_option_path} FAILED!!!")
        exit()



if __name__ == "__main__":
    main()
