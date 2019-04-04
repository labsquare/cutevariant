# Standard imports
import os
import glob
from PySide2.QtWidgets import *
from PySide2.QtCore import *
from PySide2.QtGui import * # QIcon

# Custom imports
import cutevariant.commons as cm

class BaseWidget(QTabWidget):
    """Abstract class for settings widgets"""
    def __init__(self):
        super().__init__()
        self.setWindowIcon(QIcon.fromTheme("system-run")) # temporary for now 

    def save(self):
        raise NotImplemented()

    def load(self):
        raise NotImplemented()


class GeneralSettingsWidget(BaseWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle(self.tr("General"))

    def save(self):
        pass

    def load(self):
        """Setup widgets in General settings"""
        self.settings = QSettings()
        self.setup_ui_tab()

    def setup_ui_tab(self):
        """Setup widgets in General/Interface tab"""

        page = QWidget()
        mainLayout = QFormLayout()

        # Locales combobox
        self.locales_combobox = QComboBox()
        # Get names of locales based on available files
        available_translations = {
            os.path.basename(os.path.splitext(file)[0]): file
            for file in glob.glob(cm.DIR_TRANSLATIONS + '*.qm')
        }
        # English is the default language
        available_locales = list(available_translations.keys()) + ["en"]
        self.locales_combobox.addItems(available_locales)

        # Display current locale
        locale_name = self.settings.value("ui/locale", "en")
        self.locales_combobox.setCurrentIndex(available_locales.index(locale_name))

        mainLayout.addRow(self.tr("&Choose a locale:"), self.locales_combobox)

        page.setLayout(mainLayout)
        self.addTab(page, "Interface")

        self.locales_combobox.currentTextChanged.connect(self.switchTranslator)

    def switchTranslator(self, locale_name):
        """Switch qApp translator with the selected one and save it into config

        .. todo:: Handle the propagation the LanguageChange event
            https://doc.qt.io/Qt-5/qcoreapplication.html#installTranslator
            https://wiki.qt.io/How_to_create_a_multi_language_application

        :param locale_name: Locale identifier. Ex: 'en_US', 'en'.
        :type locale_name: <str>
        """

        # Remove the old translator
        #qApp.removeTranslator(translator)

        # Load the new translator
        app_translator = QTranslator(qApp)

        if app_translator.load(locale_name, cm.DIR_TRANSLATIONS):
            qApp.installTranslator(app_translator)

        # Save locale setting
        locale_name = self.settings.setValue("ui/locale", locale_name)


class PluginsSettingsWidget(BaseWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle(self.tr("Plugins"))

    def save(self):
        pass

    def load(self):
        pass


class SettingsWidget(QDialog):
    def __init__(self):
        super().__init__()
        self.setWindowTitle(self.tr("Cutevariant - Settings"))
        self.widgets = []

        self.list_widget = QListWidget()
        self.stack_widget = QStackedWidget()
        self.button_box = QDialogButtonBox(
            QDialogButtonBox.SaveAll | QDialogButtonBox.Cancel | QDialogButtonBox.Reset
        )

        self.list_widget.setFixedWidth(200)
        self.list_widget.setIconSize(QSize(32, 32))

        h_layout = QHBoxLayout()
        h_layout.addWidget(self.list_widget)
        h_layout.addWidget(self.stack_widget)

        v_layout = QVBoxLayout()
        v_layout.addLayout(h_layout)
        v_layout.addWidget(self.button_box)
        self.setLayout(v_layout)

        self.addPanel(GeneralSettingsWidget())
        self.addPanel(PluginsSettingsWidget())

        self.resize(800, 400)

        self.button_box.button(QDialogButtonBox.SaveAll).clicked.connect(self.save_all)
        self.button_box.button(QDialogButtonBox.Reset).clicked.connect(self.load_all)
        self.button_box.button(QDialogButtonBox.Cancel).clicked.connect(self.close)

        self.list_widget.currentRowChanged.connect(self.stack_widget.setCurrentIndex)

        self.load_all()

    def addPanel(self, widget: BaseWidget):
        self.widgets.append(widget)
        self.list_widget.addItem(
            QListWidgetItem(widget.windowIcon(), widget.windowTitle())
        )
        self.stack_widget.addWidget(widget)

    def save_all(self):
        for widget in self.widgets:
            widget.save()

    def load_all(self):
        for widget in self.widgets:
            widget.load()
