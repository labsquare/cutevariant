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
import cutevariant.core.querybuilder as qb
import json


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
    if not process_arguments(app):
        exit()

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

    # Help
    # -h, --help, -? (on windows)
    parser.addHelpOption()
    
    # Version
    # --version
    show_version = QCommandLineOption(
        ["version"],
        QCoreApplication.translate(
            "main", "Display the version of Cutevariant and exit."
        ),
    )
    parser.addOption(show_version)

    # Config
    # -c, --config
    config_option = QCommandLineOption(
        ["c", "config"],
        QCoreApplication.translate("config path", "Set the config path"),
        "config",
    )
    parser.addOption(config_option)

    # Verbose
    # -v, --verbose
    modify_verbosity = QCommandLineOption(
        ["v", "verbose"],
        QCoreApplication.translate("main", "Modify verbosity."),
        "notset|debug|info|error",  # options available (value name)
        "debug",  # default value
    )
    parser.addOption(modify_verbosity)

    # Project DB
    # -p, --project_db
    # open a specific project db to query, inport VCF...
    project_db_option = QCommandLineOption(
        ["p", "project_db"],
        QCoreApplication.translate("Project VCF", 
            f"""Connexion to a project DB\n(e.g. import VCF, query in VQL or SQL...)"""
        ),
        "project.db",
    )
    parser.addOption(project_db_option)

    # Import VCF into project DB
    # -i, --import_vcf
    # Import a VCF file into a project DB
    import_vcf_option = QCommandLineOption(
        ["i", "import_vcf"],
        QCoreApplication.translate("import VCF", 
            f"""Import VCF file\nVCF file will be imported to the project DB (mandatory)\n(NB: Choose annotations type)"""
        ),
        "file.vcf",
    )
    parser.addOption(import_vcf_option)

    # VCF annotation type
    # -a, --vcf_annotations
    # Annotation type for the VCF import
    vcf_annotations_option = QCommandLineOption(
        ["a", "vcf_annotations"],
        QCoreApplication.translate("VCF annotations", 
            f"""VCF annotations type\nChoose annotation type provided by the VCF file\n(either 'snpeff' or 'vep')\n(default '')"""
        ),
        "annotations_type",
    )
    parser.addOption(vcf_annotations_option)

    # VQL Query
    # -q, --query_vql
    # Query a project DB in VQL format
    query_vql_option = QCommandLineOption(
        ["q", "query_vql"],
        QCoreApplication.translate("Query VQL", 
            f"""Query in VQL format\nQuery a project DB in VQL format\nMultiple queries allowed\nSee CuteVariant VQL query format\nExamples:\n- 'SELECT favorite, classification, chr, pos, ref, alt FROM variants'- 'SELECT favorite, classification, chr, pos, ref, alt, ann.gene, ann.hgvs_p FROM variants WHERE samples['ANY'].gt>=1'"""
        ),
        "vql",
    )
    parser.addOption(query_vql_option)

    # SQL Query
    # -s, --query_sql
    # Query a project DB in SQL format
    query_sql_option = QCommandLineOption(
        ["s", "query_sql"],
        QCoreApplication.translate("Query SQL", "Query a project DB in SQL format\nSee SQL query format\nExamples:\n- 'SELECT favorite, classification, chr, pos, ref, alt FROM variants'\n- SELECT * FROM samples"),
        "sql",
    )
    parser.addOption(query_sql_option)

    # Query results
    # -r, --query_results
    # Query results in JSON format file
    query_results_option = QCommandLineOption(
        ["r", "query_results"],
        QCoreApplication.translate("Query Results", "Query results in JSON format file\nStandard output by default"),
        "results.json",
    )
    parser.addOption(query_results_option)


    # Process the actual command line arguments given by the user
    parser.process(app)
    # args = parser.positionalArguments()


    # Check options

    # Version
    if parser.isSet(show_version):
        print("Cutevariant " + __version__)
        return False

    # Verbose
    # Set log level
    # if parser.isSet(modify_verbosity):
    LOGGER.setLevel(parser.value(modify_verbosity).upper())

    # Config
    if parser.isSet(config_option):
        config_path = parser.value(config_option)
        if os.path.isfile(config_path):
            Config.DEFAULT_CONFIG_PATH = config_path
        else:
            LOGGER.error(f"{config_path} doesn't exists. Ignoring config")

    # Project DB
    # Init 
    conn=None
    if parser.isSet(project_db_option):
        # Option values
        project_db_option_path = parser.value(project_db_option)
         # Check if project DB file exists
        if os.path.isfile(project_db_option_path):
            # Create connexion to project DB
            conn = sql.get_sql_connection(project_db_option_path)

    # Import VCF into project DB
    if parser.isSet(import_vcf_option):
        # Check if project DB connected
        if conn:
            # Option values
            import_vcf_option_path = parser.value(import_vcf_option)
            vcf_annotations_option_value = parser.value(vcf_annotations_option)
            # Check if VCF file exists
            if os.path.isfile(import_vcf_option_path):
                # Import VCF into project DB
                sql.import_reader(conn, VcfReader(import_vcf_option_path, vcf_annotations_option_value))
                # Log success
                LOGGER.info(f"Import VCF {import_vcf_option_path} in project DB {project_db_option_path}")
            else:
                # Log ierror if VCF file
                LOGGER.error(f"Import VCF {import_vcf_option_path} in project DB {project_db_option_path} FAILED!!! No Input VCF")
        else:
            # Log error if project DB not connected
            LOGGER.error(f"Import VCF in project DB FAILED!!! No Connexion to project database")
        return False


    # VQL Query
    # example: SELECT favorite,classification,chr,pos,ref,alt FROM variants
    # example: SELECT favorite,classification,chr,pos,ref,alt,ann.gene,ann.hgvs_p FROM variants
    # example: SELECT favorite,classification,chr,pos,ref,alt,ann.gene,ann.hgvs_p FROM variants WHERE samples['ANY'].gt>=1
    if parser.isSet(query_vql_option):
        # Check if project DB connected
        if conn:
            # Option values
            query_vql_option_query = parser.value(query_vql_option)
            query_results_option_file = parser.value(query_results_option) or None
            # Check if query not empty
            if query_vql_option_query != "":
                # Init
                results={}  # results in dict format
                cmd_nb=0    # number of queries
                # Create VQL command for each each queries
                for cmd in vql.parse_vql(query_vql_option_query):
                    # increment number of queries
                    cmd_nb+=1
                    # Translate VQL command to SQL query
                    sql_query = qb.build_sql_query(
                        conn,
                        fields=cmd["fields"],
                        source=cmd["source"],
                        filters=cmd["filters"],
                        limit=None,
                    )
                    # Create results as a List
                    cursor=conn.cursor()
                    data = [dict(i) for i in cursor.execute(sql_query)]
                    conn.commit()
                    # Add results list to final results Dict
                    results[cmd_nb]=data
                # Translate final results Dict into JSON format
                results_json = json.dumps(results, indent = 4)
                # Check if result file is provided
                if query_results_option_file:
                    # Write into result file
                    with open(query_results_option_file, 'w') as f:
                        print(results_json, file=f)
                    # Log success
                    LOGGER.info(f"Query SQL {query_vql_option_query} in project DB {project_db_option_path} to {query_results_option_file}")
                else:
                    # Print results into standard output 
                    print(results_json)
            else:
                # Log error if no VQL query
                LOGGER.error(f"Query VQL {query_vql_option_query} in project DB {project_db_option_path} FAILED!!! Input VQL not OK")
        else:
            # Log error if project DB not connected
            LOGGER.error(f"Query VQL FAILED!!! No Connexion to project database")
        return False

    # query in SQL
    # example: SELECT favorite,classification,chr,pos,ref,alt FROM variants
    # example: SELECT * FROM samples
    if parser.isSet(query_sql_option):
        # Check if project DB connected
        if conn:
            # Option values
            query_sql_option_query = parser.value(query_sql_option)
            query_results_option_file = parser.value(query_results_option) or None
            # Check if query not empty
            if query_sql_option_query != "":
                # Init
                results={}
                # Create results as a List
                cursor=conn.cursor()
                data = [dict(i) for i in cursor.execute(query_sql_option_query)]
                conn.commit()
                # Add results list to final results Dict
                results[1]=data
                # Translate final results Dict into JSON format
                results_json = json.dumps(results, indent = 4)
                # Check if result file is provided
                if query_results_option_file != None:
                    # Write into result file
                    with open(query_results_option_file, 'w') as f:
                        print(results_json, file=f)
                    # Log success
                    LOGGER.info(f"Query SQL {query_sql_option_query} in project DB {project_db_option_path} to {query_results_option_file}")
                else:
                    # Print results into standard output 
                    print(results_json)
            else:
                # Log error if no SQL query
                LOGGER.error(f"Query SQL {query_sql_option_query} in project DB {project_db_option_path} FAILED!!! Input SQL not OK")
        else:
            # Log error if project DB not connected
            LOGGER.error(f"Query SQL FAILED!!! No Connexion to project database")
        return False

    return True

if __name__ == "__main__":
    main()
