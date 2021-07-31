"""List of classes used for settings window

A SettingsDialog is a collection of section ( SectionWidget ) 
which contains multiple page ( AbstractSettingsWidget ) to save and load settings thanks to QSettings.

* SettingsDialog: 
Main widget for settings window that instantiate all subsection widget

* SectionWidget: 
Handy class to group similar settings widgets in tabs (used by SettingsDialog).

* AbstractSettingsWidget:
Abstract class for build a page settings
    
    Subclasses:
        - TranslationSettingsWidget: Allow to choose a language for the interface
        - ProxySettingsWidget: Allow to configure proxy settings for widgets that require internet connection
        - StyleSettingsWidget
        - PluginsSettingsWidget
        - VariantSettingsWidget: Allow to add personal templates to search a variant in a third-party database

Exemples: 

    # Create sub-section  

    class MemorySettings(BaseSettings):
        def save():
            settings = self.create_settings()
            settings.setValue("value", 10)    

        def load():
            settings = self.create_settings()
            value = settings.value("value")
               

    class DiskSettings(BaseSettings):
        def save():
            settings = self.create_settings()
            settings.setValue("value", 10)    

        def load():
            settings = self.create_settings()
            value = settings.value("value")

    # create one section 
    performance_section = SectionWidget()
    performance_section.add_setting_widget(MemorySettings)
    performance_section.add_setting_widget(DiskSettings)

    # add section to the main settings widge 
    widget = SettingsWidget()
    widget.add_section(widget)

    widget.save_all()

"""
# Standard imports
import os
import glob
from abc import abstractmethod
from logging import DEBUG
from PySide2.QtNetwork import QNetworkProxy

# Qt imports
from PySide2.QtWidgets import *
from PySide2.QtCore import *  # QApplication.instance()
from PySide2.QtGui import *  # QIcon, QPalette

# Custom imports
import cutevariant.commons as cm
from cutevariant.config import Config
from cutevariant.gui.ficon import FIcon
from cutevariant.gui import network, style, widgets

from cutevariant import LOGGER


class AbstractSettingsWidget(QWidget):
    """Abstract class for settings widgets

    User must reimplement load() and save()

    """

    def __init__(self):
        super().__init__()
        self.setWindowTitle("base")
        self.setWindowIcon(FIcon(0xF5CA))
        self.section_widget = None

    @abstractmethod
    def save(self):
        """Save the current widget settings in QSettings"""
        raise NotImplementedError(self.__class__.__name__)

    @abstractmethod
    def load(self):
        """Load settings from QSettings"""
        raise NotImplementedError(self.__class__.__name__)


class SectionWidget(QTabWidget):
    """Handy class to group similar settings page in tabs"""

    def __init__(self, parent=None):
        super().__init__(parent)

    def add_page(self, widget: AbstractSettingsWidget):
        widget.section_widget = self
        self.addTab(widget, widget.windowIcon(), widget.windowTitle())

    def save(self):
        """Call save() method of all widgets in the SectionWidget"""
        [self.widget(index).save() for index in range(self.count())]

    def load(self):
        """Call load() method of all widgets in the SectionWidget"""
        [self.widget(index).load() for index in range(self.count())]


################################################################################
# class TranslationSettingsWidget(AbstractSettingsWidget):
#     """Allow to choose a language for the interface"""

#     def __init__(self):
#         super().__init__()
#         self.setWindowTitle(self.tr("Translation"))
#         self.setWindowIcon(FIcon(0xF05CA))
#         self.locales_combobox = QComboBox()
#         mainLayout = QFormLayout()
#         mainLayout.addRow(self.tr("&Choose a locale:"), self.locales_combobox)

#         self.setLayout(mainLayout)
#         # self.locales_combobox.currentTextChanged.connect(self.switchTranslator)

#     def save(self):
#         """Switch QApplication.instance() translator with the selected one and save it into config

#         .. note:: settings are stored in "ui" group
#         .. todo:: Handle the propagation the LanguageChange event
#             https://doc.qt.io/Qt-5/qcoreapplication.html#installTranslator
#             https://wiki.qt.io/How_to_create_a_multi_language_application
#         """

#         # Remove the old translator
#         # QApplication.instance().removeTranslator(translator)

#         # Load the new translator

#         # Save locale setting
#         locale_name = self.locales_combobox.currentText()

#         app_translator = QTranslator(QApplication.instance())
#         if app_translator.load(locale_name, cm.DIR_TRANSLATIONS):
#             QApplication.instance().installTranslator(app_translator)

#     def load(self):
#         """Setup widgets in TranslationSettingsWidget"""
#         self.locales_combobox.clear()
#         # Get names of locales based on available files
#         available_translations = {
#             os.path.basename(os.path.splitext(file)[0]): file
#             for file in glob.glob(cm.DIR_TRANSLATIONS + "*.qm")
#         }
#         # English is the default language
#         available_locales = list(available_translations.keys()) + ["en"]
#         self.locales_combobox.addItems(available_locales)

#         # Display current locale
#         settings = self.create_settings()
#         locale_name = settings.value("ui/locale", "en")

#         self.locales_combobox.setCurrentIndex(available_locales.index(locale_name))


class ProxySettingsWidget(AbstractSettingsWidget):
    """Allow to configure proxy settings for widgets that require internet connection
    These settings will apply application-wide (i.e. every QNetworkAccessManager will have these as defaults)
    """

    def __init__(self):
        super().__init__()
        self.setWindowTitle(self.tr("Network"))
        self.setWindowIcon(FIcon(0xF0484))

        self.combo_box = QComboBox()
        self.host_edit = QLineEdit()
        self.port_edit = QSpinBox()
        # Port number is a 16-bits unsigned integer
        self.port_edit.setRange(0, 65535)
        self.user_edit = QLineEdit()
        self.pass_edit = QLineEdit()

        # Load proxy type
        self.combo_box.clear()
        self.combo_box.addItems(list(network.PROXY_TYPES.keys()))

        # edit restriction
        self.pass_edit.setEchoMode(QLineEdit.PasswordEchoOnEdit)

        f_layout = QFormLayout()
        f_layout.addRow(self.tr("Type"), self.combo_box)
        f_layout.addRow(self.tr("Proxy host"), self.host_edit)
        f_layout.addRow(self.tr("Proxy Port"), self.port_edit)
        f_layout.addRow(self.tr("Username"), self.user_edit)
        f_layout.addRow(self.tr("Password"), self.pass_edit)

        self.combo_box.currentTextChanged.connect(self.on_combo_changed)

        self.setLayout(f_layout)

    def save(self):
        """Save settings under "proxy" group"""
        config = Config("app")
        _network = {}
        _network["type"] = self.combo_box.currentText()
        _network["host"] = self.host_edit.text()
        _network["port"] = self.port_edit.value()
        _network["username"] = self.user_edit.text()
        _network["password"] = self.pass_edit.text()

        config["network"] = _network

        try:
            proxy = QNetworkProxy(
                network.PROXY_TYPES.get(
                    self.combo_box.currentText(), QNetworkProxy.NoProxy
                ),
                self.host_edit.text(),
                self.port_edit.value(),
                self.user_edit.text(),
                self.pass_edit.text(),
            )
        except Exception as e:
            LOGGER.error(
                "Could not build valid proxy with current settings\nType:%s\nHost:%s\nPort:%s\nUser name:%s",
                self.combo_box.currentText(),
                self.host_edit.text(),
                self.port_edit.text(),
                self.user_edit.text(),
            )
        QNetworkProxy.setApplicationProxy(proxy)
        config.save()

    def load(self):
        """Load "proxy" group settings"""

        config = Config("app")

        network = config.get("network", {})

        s_type = network.get("type", "No Proxy")
        self.combo_box.setCurrentText(str(s_type))
        # We need to call disable form manually because setCurrentIndex(0) won't trigger currentIndexChanged
        if self.combo_box.currentText() == "No Proxy":
            self._disable_form()

        self.host_edit.setText(network.get("host", ""))

        s_port = network.get("port", 0)
        self.port_edit.setValue(int(s_port))

        self.user_edit.setText(network.get("username", ""))
        self.pass_edit.setText(network.get("password", ""))

    def on_combo_changed(self, text):
        """disable formular when No proxy"""
        if text == "No Proxy":
            self._disable_form(True)
        else:
            self._disable_form(False)

    def _disable_form(self, disabled=True):
        """Disabled formular"""
        self.host_edit.setDisabled(disabled)
        self.port_edit.setDisabled(disabled)
        self.user_edit.setDisabled(disabled)
        self.pass_edit.setDisabled(disabled)


class StyleSettingsWidget(AbstractSettingsWidget):
    """Allow to choose a style for the interface"""

    def __init__(self):
        """Init StyleSettingsWidget

        Args:
            mainwindow (QMainWindow): Current main ui of cutevariant;
                Used to refresh the plugins
        """
        super().__init__()
        self.setWindowTitle(self.tr("Styles"))
        self.setWindowIcon(FIcon(0xF03D8))

        self.styles_combobox = QComboBox()
        mainLayout = QFormLayout()
        mainLayout.addRow(self.tr("&Choose a style:"), self.styles_combobox)

        self.setLayout(mainLayout)

    def save(self):
        """Save the selected style in config"""
        # Get previous style

        config = Config("app")
        style = config.get("style", {})

        old_style_name = style.get("theme", cm.BASIC_STYLE)

        # Save style setting
        style_name = self.styles_combobox.currentText()
        if old_style_name == style_name:
            return

        style["theme"] = style_name

        config["style"] = style
        config.save()

        QMessageBox.information(
            self, "restart", self.tr("Please restart application to apply theme")
        )

        # Clear pixmap cache
        QPixmapCache.clear()

    def load(self):
        """Setup widgets in StyleSettingsWidget"""
        self.styles_combobox.clear()

        # Get names of styles based on available files
        available_styles = {
            os.path.basename(os.path.splitext(file)[0]).title(): file
            for file in glob.glob(cm.DIR_STYLES + "*.qss")
            if "frameless" not in file
        }
        # Display available styles
        available_styles = list(available_styles.keys()) + [cm.BASIC_STYLE]
        self.styles_combobox.addItems(available_styles)

        print(available_styles)

        # Display current style
        # Dark is the default style
        config = Config("app")
        style = config.get("style", {})
        style_name = style.get("theme", cm.BASIC_STYLE)
        self.styles_combobox.setCurrentIndex(available_styles.index(style_name))


# class PathSettingsWidget(AbstractSettingsWidget):
#     """ Path settings where to store shared data """

#     def __init__(self):
#         super().__init__()
#         self.setWindowTitle(self.tr("Global settings"))
#         self.setWindowIcon(FIcon(0xF1080))

#         self.edit = widgets.FileEdit()
#         self.edit.set_path_type("dir")
#         main_layout = QFormLayout()
#         main_layout.addRow("Preset path", self.edit)

#         self.setLayout(main_layout)

#     def save(self):
#         settings = QSettings()
#         if self.edit.exists():
#             settings.setValue("preset_path", self.edit.text())

#     def load(self):

#         settings = QSettings()
#         path = settings.value(
#             "preset_path",
#             QStandardPaths.writableLocation(QStandardPaths.GenericDataLocation),
#         )

#         self.edit.setText(path)


class SettingsDialog(QDialog):
    """Main widget for settings window

    Subwidgets are intantiated on panels; a SectionWidget groups similar widgets
    in tabs.

    Signals:
        uiSettingsChanged(Signal): Emitted when some settings of the GUI are
            modified and need a reload of all widgets to take effect.
    """

    uiSettingsChanged = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle(self.tr("Cutevariant - Settings"))
        self.setWindowIcon(QIcon(cm.DIR_ICONS + "app.png"))

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

        # Instantiate subwidgets on panels
        # Similar widgets for general configuration
        general_settings = SectionWidget()  #  Not a title !
        general_settings.setWindowTitle(self.tr("General"))
        general_settings.setWindowIcon(FIcon(0xF0614))

        # general_settings.add_page(PathSettingsWidget())

        # Cutevariant is  not yet translated ..
        # general_settings.add_page(TranslationSettingsWidget())

        general_settings.add_page(ProxySettingsWidget())
        general_settings.add_page(StyleSettingsWidget())

        # Specialized widgets on panels
        self.add_section(general_settings)
        self.load_plugins()

        self.resize(800, 400)

        self.button_box.button(QDialogButtonBox.SaveAll).clicked.connect(self.save_all)
        self.button_box.button(QDialogButtonBox.Reset).clicked.connect(self.load_all)
        self.button_box.button(QDialogButtonBox.Cancel).clicked.connect(self.close)

        # Connection events
        self.list_widget.currentRowChanged.connect(self.stack_widget.setCurrentIndex)

        # Load settings
        self.load_all()

        self.accepted.connect(self.close)

    def add_section(self, widget: SectionWidget):
        """Add a widget on the widow via a QStackedWidget; keep a reference on it
        for later connection/activation"""
        # Used to load/save all widgets on demand
        self.widgets.append(widget)
        # Used for ui positionning and connection events
        self.list_widget.addItem(
            QListWidgetItem(widget.windowIcon(), widget.windowTitle())
        )
        self.stack_widget.addWidget(widget)

    def save_all(self):
        """Call save() method of all widgets"""
        [widget.save() for widget in self.widgets]
        self.accept()

    def load_all(self):
        """Call load() method of all widgets"""
        [widget.load() for widget in self.widgets]

    def load_plugins(self):
        """Add plugins settings"""
        from cutevariant.gui import plugin

        for extension in plugin.find_plugins():

            if "setting" in extension:
                settings_widget_class = extension["setting"]
                if not settings_widget_class.ENABLE:
                    # Skip disabled plugins
                    continue

                widget = settings_widget_class()
                # Create rprefix settings ! For instance [VariantView]
                # widget.prefix_settings = widget.__class__.__name__.replace(
                #     "SettingsWidget", ""
                # )

                if not widget.windowTitle():
                    widget.setWindowTitle(extension["name"])

                if not widget.windowIcon():
                    widget.setWindowIcon(FIcon(0xF0431))

                self.add_section(widget)


if __name__ == "__main__":
    import sys

    app = QApplication(sys.argv)

    d = SettingsDialog()
    d.show()

    app.exec_()
