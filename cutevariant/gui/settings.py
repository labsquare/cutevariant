"""List of classes used for settings window

SettingsWidget: Main widget for settings window that instantiate all subwidgets

BaseWidget: Abstract class for settings widgets.
    Subclasses:
        - TranslationSettingsWidget: Allow to choose a language for the interface
        - ProxySettingsWidget: Allow to configure proxy settings for widgets that
        require internet connection
        - StyleSettingsWidget
        - PluginsSettingsWidget
        - DatabaseSettingsWidget
        - VariantSettingsWidget: Allow to add personal templates to search a
        variant in a third-party database

GroupWidget: Handy class to group similar settings widgets in tabs (used by SettingsWidget).
    Used for:
        - TranslationSettingsWidget
        - ProxySettingsWidget
        - StyleSettingsWidget
"""
# Standard imports
import os
import glob
from abc import abstractmethod

# Qt imports
from PySide2.QtWidgets import *
from PySide2.QtCore import *
from PySide2.QtGui import *  # QIcon
from PySide2.QtNetwork import *

# Custom imports
import cutevariant.commons as cm
from cutevariant.gui.ficon import FIcon


class BaseWidget(QWidget):
    """Abstract class for settings widgets"""

    def __init__(self):
        super().__init__()
        self.settings = QSettings()

    @abstractmethod
    def save(self):
        """Save the current widget settings in QSettings"""
        raise NotImplementedError(self.__class__.__name__)

    @abstractmethod
    def load(self):
        """Load settings from QSettings"""
        raise NotImplementedError(self.__class__.__name__)


class GroupWidget(QTabWidget):
    """Handy class to group similar settings widgets in tabs"""

    def add_settings_widget(self, widget: BaseWidget):
        self.addTab(widget, widget.windowIcon(), widget.windowTitle())

    def save(self):
        """Call save() method of all widgets in the GroupWidget"""
        [self.widget(index).save() for index in range(self.count())]

    def load(self):
        """Call load() method of all widgets in the GroupWidget"""
        [self.widget(index).load() for index in range(self.count())]


################################################################################
class TranslationSettingsWidget(BaseWidget):
    """Allow to choose a language for the interface"""

    def __init__(self):
        super().__init__()
        self.setWindowTitle(self.tr("Translation"))
        self.setWindowIcon(FIcon(0xF5CA))
        self.locales_combobox = QComboBox()
        mainLayout = QFormLayout()
        mainLayout.addRow(self.tr("&Choose a locale:"), self.locales_combobox)

        self.setLayout(mainLayout)
        # self.locales_combobox.currentTextChanged.connect(self.switchTranslator)

    def save(self):
        """Switch qApp translator with the selected one and save it into config

        .. note:: settings are stored in "ui" group
        .. todo:: Handle the propagation the LanguageChange event
            https://doc.qt.io/Qt-5/qcoreapplication.html#installTranslator
            https://wiki.qt.io/How_to_create_a_multi_language_application
        """

        # Remove the old translator
        # qApp.removeTranslator(translator)

        # Load the new translator

        # Save locale setting
        locale_name = self.locales_combobox.currentText()
        self.settings.setValue("ui/locale", locale_name)
        app_translator = QTranslator(qApp)
        if app_translator.load(locale_name, cm.DIR_TRANSLATIONS):
            qApp.installTranslator(app_translator)

    def load(self):
        """Setup widgets in General settings"""
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
        locale_name = self.settings.value("ui/locale", "en")
        self.locales_combobox.setCurrentIndex(available_locales.index(locale_name))


class ProxySettingsWidget(BaseWidget):
    """Allow to configure proxy settings for widgets that require internet connection"""

    PROXY_TYPES = {
        "No Proxy": QNetworkProxy.NoProxy,
        "Default": QNetworkProxy.DefaultProxy,
        "Sock5": QNetworkProxy.Socks5Proxy,
        "Http": QNetworkProxy.HttpProxy,
    }

    def __init__(self):
        super().__init__()
        self.setWindowTitle(self.tr("Proxy"))
        self.setWindowIcon(FIcon(0xF484))

        self.combo_box = QComboBox()
        self.host_edit = QLineEdit()
        self.port_edit = QSpinBox()
        self.user_edit = QLineEdit()
        self.pass_edit = QLineEdit()

        # Load proxy type
        for key in self.PROXY_TYPES:
            self.combo_box.addItem(key, self.PROXY_TYPES[key])

        # edit restriction
        self.pass_edit.setEchoMode(QLineEdit.PasswordEchoOnEdit)

        f_layout = QFormLayout()
        f_layout.addRow("Type", self.combo_box)
        f_layout.addRow("Proxy host", self.host_edit)
        f_layout.addRow("Proxy Port", self.port_edit)
        f_layout.addRow("Username", self.user_edit)
        f_layout.addRow("Password", self.pass_edit)

        self.setLayout(f_layout)

    def save(self):
        """Save settings under "proxy" group"""
        settings = QSettings()
        settings.beginGroup("proxy")
        settings.setValue("type", self.combo_box.currentIndex())
        settings.setValue("host", self.host_edit.text())
        settings.setValue("port", self.port_edit.value())
        settings.setValue("username", self.user_edit.text())
        settings.setValue("password", self.user_edit.text())
        settings.endGroup()

    def load(self):
        """Load "proxy" group settings"""
        settings = QSettings()
        settings.beginGroup("proxy")
        self.combo_box.setCurrentIndex(int(settings.value("type", 0)))
        self.host_edit.setText(settings.value("host"))
        self.port_edit.setValue(int(settings.value("port", 0)))
        self.user_edit.setText(settings.value("username"))
        self.pass_edit.setText(settings.value("password"))
        settings.endGroup()


class StyleSettingsWidget(BaseWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle(self.tr("Styles"))
        self.setWindowIcon(FIcon(0xF3D8))

    def save(self):
        pass

    def load(self):
        pass


class PluginsSettingsWidget(BaseWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle(self.tr("Plugins"))
        self.setWindowIcon(FIcon(0xF3D4))

    def save(self):
        pass

    def load(self):
        pass


class DatabaseSettingsWidget(BaseWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle(self.tr("database"))
        self.setWindowIcon(FIcon(0xF1B8))

    def save(self):
        pass

    def load(self):
        pass


class VariantSettingsWidget(BaseWidget):
    """Allow to add personal templates to search a variant in a third-party database

    .. note:: These templates are used in the right click context menu displayed
        on InfoVariantWidget and ViewQueryWidget.
    """

    def __init__(self):
        super().__init__()
        self.setWindowTitle(self.tr("Variants"))
        self.setWindowIcon(FIcon(0xF683))

        self.view = QListWidget()
        self.add_button = QPushButton(self.tr("Add"))
        self.edit_button = QPushButton(self.tr("Edit"))
        self.remove_button = QPushButton(self.tr("Remove"))

        v_layout = QVBoxLayout()
        v_layout.addWidget(self.add_button)
        v_layout.addWidget(self.edit_button)
        v_layout.addStretch()
        v_layout.addWidget(self.remove_button)

        main_layout = QHBoxLayout()
        main_layout.addWidget(self.view)
        main_layout.addLayout(v_layout)

        self.setLayout(main_layout)

        # Settings key
        self.settings_key = "databases_urls/"

        # Signals
        self.add_button.clicked.connect(self.add_url)
        self.edit_button.clicked.connect(self.edit_item)
        self.view.itemDoubleClicked.connect(self.add_url)
        self.remove_button.clicked.connect(self.remove_item)

        # Load built-in databases first
        [
            self.add_list_widget_item(*db_name_url)
            for db_name_url in cm.WEBSITES_URLS.items()
        ]

    def save(self):
        # TODO : save links from settings
        pass

    def load(self):
        """Load databases URLs from settings"""
        # Get all child keys of the group databases_urls
        self.settings.beginGroup(self.settings_key)

        for db_name in self.settings.childKeys():
            # Add the item to the list
            self.add_list_widget_item(db_name, self.settings.value(db_name))

        self.settings.endGroup()

    def add_list_widget_item(self, db_name: str, url: str):
        """Add an item to the QListWidget of the current view"""
        # Key is the name of the database, value is its url
        item = QListWidgetItem(db_name)
        item.setData(Qt.UserRole, url)
        self.view.addItem(item)

    def edit_list_widget_item(self, item: QListWidgetItem, db_name: str, url: str):
        """Modify the given item"""
        item.setText(db_name)
        item.setData(Qt.UserRole, url)

    def add_url(self, item=None):
        """Allow the user to insert and save custom database URL"""
        # Display dialog box to let the user enter it's own url
        dialog = QDialog()
        name = QLineEdit()
        url = QLineEdit()
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(dialog.accept)
        buttons.rejected.connect(dialog.reject)
        layout = QFormLayout()
        layout.addRow(self.tr("Name"), name)
        layout.addRow(self.tr("Url"), url)
        layout.addWidget(buttons)

        dialog.setLayout(layout)

        if item:
            # Called by itemDoubleClicked or edit_item
            # Fill forms with item data
            name.setText(item.text())
            url.setText(item.data(Qt.UserRole))

        # Also do a minimal check on the data inserted
        if dialog.exec_() == QDialog.Accepted and name.text() and url.text():

            if item:
                # Edit the current item in the list
                self.edit_list_widget_item(item, name.text(), url.text())
            else:
                # Add the item to the list
                self.add_list_widget_item(name.text(), url.text())

            # Save the item in settings
            # (Here to limit the friction with Save all button)
            self.settings.setValue(self.settings_key + name.text(), url.text())

    def edit_item(self):
        """Edit the selected item

        .. note:: This function uses add_url to display the edit window
        """
        # Get selected item
        # Always use the first selected item returned
        self.add_url(self.view.selectedItems()[0])

    def remove_item(self):
        """Remove the selected item

        .. todo:: removeItemWidget() is not functional?
        """
        # Get selected item
        item = self.view.selectedItems()[0]

        # Delete key in settings
        self.settings.remove(self.settings_key + item.text())

        # Delete the item
        self.view.takeItem(self.view.row(item))
        del item  # Is it mandatory in Python ?


class SettingsWidget(QDialog):
    """Main widget for settings window

    Subwidgets are intantiated on panels; a GroupWidget groups similar widgets
    in tabs.
    """

    def __init__(self):
        super().__init__()
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
        general_settings = GroupWidget()
        general_settings.setWindowTitle(self.tr("General"))
        general_settings.setWindowIcon(FIcon(0xF493))

        general_settings.add_settings_widget(TranslationSettingsWidget())
        general_settings.add_settings_widget(ProxySettingsWidget())
        general_settings.add_settings_widget(StyleSettingsWidget())

        # Specialized widgets on panels
        self.addPanel(general_settings)
        self.addPanel(PluginsSettingsWidget())
        self.addPanel(VariantSettingsWidget())
        self.addPanel(DatabaseSettingsWidget())

        self.resize(800, 400)

        self.button_box.button(QDialogButtonBox.SaveAll).clicked.connect(self.save_all)
        self.button_box.button(QDialogButtonBox.Reset).clicked.connect(self.load_all)
        self.button_box.button(QDialogButtonBox.Cancel).clicked.connect(self.close)

        # Connection events
        self.list_widget.currentRowChanged.connect(self.stack_widget.setCurrentIndex)

        # Load settings
        self.load_all()

    def addPanel(self, widget: BaseWidget):
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

    def load_all(self):
        """Call load() method of all widgets"""
        [widget.load() for widget in self.widgets]
