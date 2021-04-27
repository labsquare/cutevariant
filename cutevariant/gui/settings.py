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

# Qt imports
from PySide2.QtWidgets import *
from PySide2.QtCore import *  # QApplication.instance()
from PySide2.QtGui import *  # QIcon, QPalette

# Custom imports
import cutevariant.commons as cm
from cutevariant.gui.ficon import FIcon
from cutevariant.gui import network, style, widgets

LOGGER = cm.logger()


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

    @property
    def prefix_settings(self) -> str:
        """Return prefix settings from section parent
        Returns:
            str
        """
        if self.section_widget:
            return self.section_widget.prefix_settings
        return None

    def create_settings(self):
        settings = QSettings()
        settings.beginGroup(self.prefix_settings)
        return settings


class SectionWidget(QTabWidget):
    """Handy class to group similar settings page in tabs"""

    def __init__(self, prefix_settings="", parent=None):
        super().__init__(parent)
        self.prefix_settings = prefix_settings

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
class TranslationSettingsWidget(AbstractSettingsWidget):
    """Allow to choose a language for the interface"""

    def __init__(self):
        super().__init__()
        self.setWindowTitle(self.tr("Translation"))
        self.setWindowIcon(FIcon(0xF05CA))
        self.locales_combobox = QComboBox()
        mainLayout = QFormLayout()
        mainLayout.addRow(self.tr("&Choose a locale:"), self.locales_combobox)

        self.setLayout(mainLayout)
        # self.locales_combobox.currentTextChanged.connect(self.switchTranslator)

    def save(self):
        """Switch QApplication.instance() translator with the selected one and save it into config

        .. note:: settings are stored in "ui" group
        .. todo:: Handle the propagation the LanguageChange event
            https://doc.qt.io/Qt-5/qcoreapplication.html#installTranslator
            https://wiki.qt.io/How_to_create_a_multi_language_application
        """

        # Remove the old translator
        # QApplication.instance().removeTranslator(translator)

        # Load the new translator

        # Save locale setting
        locale_name = self.locales_combobox.currentText()
        settings = self.create_settings()
        settings.setValue("ui/locale", locale_name)
        app_translator = QTranslator(QApplication.instance())
        if app_translator.load(locale_name, cm.DIR_TRANSLATIONS):
            QApplication.instance().installTranslator(app_translator)

    def load(self):
        """Setup widgets in TranslationSettingsWidget"""
        self.locales_combobox.clear()
        # Get names of locales based on available files
        available_translations = {
            os.path.basename(os.path.splitext(file)[0]): file
            for file in glob.glob(cm.DIR_TRANSLATIONS + "*.qm")
        }
        # English is the default language
        available_locales = list(available_translations.keys()) + ["en"]
        self.locales_combobox.addItems(available_locales)

        # Display current locale
        settings = self.create_settings()
        locale_name = settings.value("ui/locale", "en")

        self.locales_combobox.setCurrentIndex(available_locales.index(locale_name))


class ProxySettingsWidget(AbstractSettingsWidget):
    """Allow to configure proxy settings for widgets that require internet connection"""

    def __init__(self):
        super().__init__()
        self.setWindowTitle(self.tr("Network"))
        self.setWindowIcon(FIcon(0xF0484))

        self.combo_box = QComboBox()
        self.host_edit = QLineEdit()
        self.port_edit = QSpinBox()
        self.user_edit = QLineEdit()
        self.pass_edit = QLineEdit()

        # Load proxy type
        for key in network.PROXY_TYPES:
            self.combo_box.addItem(key, network.PROXY_TYPES[key])

        # edit restriction
        self.pass_edit.setEchoMode(QLineEdit.PasswordEchoOnEdit)

        f_layout = QFormLayout()
        f_layout.addRow(self.tr("Type"), self.combo_box)
        f_layout.addRow(self.tr("Proxy host"), self.host_edit)
        f_layout.addRow(self.tr("Proxy Port"), self.port_edit)
        f_layout.addRow(self.tr("Username"), self.user_edit)
        f_layout.addRow(self.tr("Password"), self.pass_edit)

        self.combo_box.currentIndexChanged.connect(self.on_combo_changed)

        self.setLayout(f_layout)

    def save(self):
        """Save settings under "proxy" group"""
        settings = self.create_settings()
        settings.beginGroup("proxy")
        settings.setValue("type", self.combo_box.currentIndex())
        settings.setValue("host", self.host_edit.text())
        settings.setValue("port", self.port_edit.value())
        settings.setValue("username", self.user_edit.text())
        settings.setValue("password", self.user_edit.text())
        settings.endGroup()

    def load(self):
        """Load "proxy" group settings"""

        settings = self.create_settings()

        settings.beginGroup("proxy")

        s_type = settings.value("type", 0)
        if s_type:
            self.combo_box.setCurrentIndex(int(s_type))

        self.host_edit.setText(settings.value("host"))

        s_port = settings.value("port", 0)
        if s_port:
            self.port_edit.setValue(int(s_port))

        self.user_edit.setText(settings.value("username"))
        self.pass_edit.setText(settings.value("password"))
        settings.endGroup()

    def on_combo_changed(self, index):
        """ disable formular when No proxy """
        if index == 0:
            self._disable_form(True)
        else:
            self._disable_form(False)

    def _disable_form(self, disabled=True):
        """ Disabled formular """
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

        settings = self.create_settings()
        old_style_name = settings.value("ui/style", cm.BASIC_STYLE)

        # Save style setting
        style_name = self.styles_combobox.currentText()
        if old_style_name == style_name:
            return

        settings.setValue("ui/style", style_name)

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

        # Display current style
        # Dark is the default style
        settings = self.create_settings()
        style_name = settings.value("ui/style", cm.BASIC_STYLE)
        self.styles_combobox.setCurrentIndex(available_styles.index(style_name))


class PluginsSettingsWidget(AbstractSettingsWidget):
    """Display a list of found plugin and their status (enabled/disabled)"""

    registerPlugin = Signal(dict)
    deregisterPlugin = Signal(dict)

    def __init__(self):
        super().__init__()
        self.setWindowTitle(self.tr("Plugins"))
        self.setWindowIcon(FIcon(0xF0431))
        self.view = QTreeWidget()
        self.view.setColumnCount(3)
        self.view.setHeaderLabels(["Name", "Description", "Version"])
        self.view.header().setSectionResizeMode(QHeaderView.ResizeToContents)

        main_layout = QVBoxLayout()
        main_layout.addWidget(self.view)
        self.setLayout(main_layout)

    def save(self):
        """Save the check status of enabled plugins in app settings and update UI

        Emit a `register_plugin` or `deregister_plugin` signal for the mainwindow.

        Notes:
            Called only if the user clicks on "save all" button.
        """
        for iterator in QTreeWidgetItemIterator(
            self.view, QTreeWidgetItemIterator.Enabled
        ):
            item = iterator.value()
            # Get extension and check state
            extension = item.data(0, Qt.UserRole)
            check_state = item.checkState(0) == Qt.Checked
            # Save status

            settings = self.create_settings()
            settings.setValue(f"plugins/{extension['name']}/status", check_state)

            # Set the enable status of the extension
            for sub_extension_type in {
                "widget",
                "dialog",
                "setting",
            } & extension.keys():
                extension[sub_extension_type].ENABLE = check_state

            if check_state:
                # Register plugin in UI
                self.registerPlugin.emit(extension)
            else:
                # Deregister plugin in UI
                self.deregisterPlugin.emit(extension)

    def load(self):
        """Display the plugins and their status"""
        self.view.clear()
        from cutevariant.gui import plugin

        settings = self.create_settings()

        settings_keys = set(settings.allKeys())

        for extension in plugin.find_plugins():
            displayed_title = (
                extension["name"]
                if LOGGER.getEffectiveLevel() == DEBUG
                else extension["title"]
            )
            item = QTreeWidgetItem()
            item.setText(0, displayed_title)
            item.setText(1, extension["description"])
            item.setText(2, extension["version"])

            # Is an extension enabled ?
            is_enabled = False

            # Get activation status
            # Only disabled extensions can be in settings
            key = f"plugins/{extension['name']}/status"
            activated_by_user = (
                settings.value(key) == "true" if key in settings_keys else None
            )

            for sub_extension_type in {
                "widget",
                "dialog",
                "setting",
            } & extension.keys():
                if activated_by_user is None and extension[sub_extension_type].ENABLE:
                    is_enabled = True
                    # Only disabled plugins can be reactivated by the user
                    item.setDisabled(True)
                    break
                if activated_by_user:
                    is_enabled = True
                    break

            item.setCheckState(0, Qt.Checked if is_enabled else Qt.Unchecked)
            # Attach the extension for its further activation/desactivation
            item.setData(0, Qt.UserRole, extension)

            self.view.addTopLevelItem(item)


class PathSettingsWidget(AbstractSettingsWidget):
    """ Path settings where to store shared data """

    def __init__(self):
        super().__init__()
        self.setWindowTitle(self.tr("Global settings"))
        self.setWindowIcon(FIcon(0xF1080))

        self.edit = widgets.FileEdit()
        self.edit.set_path_type("dir")
        main_layout = QFormLayout()
        main_layout.addRow("Preset path", self.edit)

        self.setLayout(main_layout)

    def save(self):
        settings = QSettings()
        if self.edit.exists():
            settings.setValue("preset_path", self.edit.text())

    def load(self):

        settings = QSettings()
        path = settings.value(
            "preset_path",
            QStandardPaths.writableLocation(QStandardPaths.GenericDataLocation),
        )

        self.edit.setText(path)


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

        general_settings.add_page(PathSettingsWidget())

        # Cutevariant is  not yet translated ..
        # general_settings.add_page(TranslationSettingsWidget())

        general_settings.add_page(ProxySettingsWidget())
        general_settings.add_page(StyleSettingsWidget())

        # Activation status of plugins
        plugin_settings = PluginsSettingsWidget()

        #  BOF...
        if parent:
            plugin_settings.registerPlugin.connect(parent.register_plugin)
            plugin_settings.deregisterPlugin.connect(parent.deregister_plugin)

        # Specialized widgets on panels
        self.add_section(general_settings)
        # self.add_section(plugin_settings)
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
        self.accepted.emit()

    def load_all(self):
        """Call load() method of all widgets"""
        [widget.load() for widget in self.widgets]

    def load_plugins(self):
        """ Add plugins settings """
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
