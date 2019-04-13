# Standard imports
import sys
from PySide2.QtWidgets import *
from PySide2.QtCore import *
from PySide2.QtGui import *

# Custom imports
from cutevariant.gui import MainWindow, FIcon
import cutevariant.commons as cm


def main():
    """The main routine."""

    # Define the names of the organization and the application
    # The value is used by the QSettings class when it is constructed using
    # the empty constructor. This saves having to repeat this information
    # each time a QSettings object is created.
    # The default scope is QSettings::UserScope
    QCoreApplication.setOrganizationName("labsquare")
    QCoreApplication.setApplicationName("cutevariant")

    app = QApplication(sys.argv)
    # Set icons set 
    FIcon.setFontPath("cutevariant/assets/fonts/materialdesignicons-webfont.ttf")

    # Translations
    #load_translations(app)

    # Display
    w = MainWindow()
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


if __name__ == "__main__":

    main()
