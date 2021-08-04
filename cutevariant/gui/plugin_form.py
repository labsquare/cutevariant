from jinja2.defaults import LINE_STATEMENT_PREFIX
from cutevariant.gui import plugin
import jinja2
import os
import re

from PySide2.QtGui import *
from PySide2.QtCore import *
from PySide2.QtWidgets import *

from cutevariant.commons import camel_to_snake, snake_to_camel
from cutevariant import LOGGER

WIDGET_TEMPLATE = "plugin_widget_template.py.j2"
DIALOG_TEMPLATE = "plugin_dialog_template.py.j2"
INIT_TEMPLATE = "plugin_init_template.py.j2"
SETTINGS_TEMPLATE = "plugin_settings_template.py.j2"


def human_to_camel(words: str) -> str:
    """Convert a human-readable noun group into
    camelCase symbol.

    Example:
        >>> human_to_camel("my awesome Plugin")
        'MyAwesomePlugin'

    Args:
        words (str): Noun group to convert to camel_case

    Returns:
        str: camelCase string from input noun group
    """
    return "".join([w.capitalize() for w in words.split()])


def generate_file(template_file: str, **kwargs):
    """Writes all the files required for a plugin to work.
    This function should be called twice per plugin, once for the plugin itself, and once for the __init__.py file.

    Args:
        file_type (str): One of PLUGIN_TEMPLATE, DIALOG_TEMPLATE, or INIT_TEMPLATE
    """

    # Maps a template type to its resulting file name once rendered
    template_to_file_name = {
        WIDGET_TEMPLATE: "widgets.py",
        DIALOG_TEMPLATE: "dialogs.py",
        SETTINGS_TEMPLATE: "settings.py",
        INIT_TEMPLATE: "__init__.py",
    }

    # name (the plugin name in camelCase) is required. Should be something like: MySample
    if "name" not in kwargs:
        LOGGER.debug("Missing required field 'name'")
        return

    # module name (the plugin name in snake_case) is required. Should be something like: my_sample
    if "module_name" not in kwargs:
        LOGGER.debug("Missing required field 'module_name'")
        return

    # So that we can safely map a template name to its end target
    if template_file not in template_to_file_name.keys():
        return

    module_name = kwargs["module_name"]

    template_loader = jinja2.PackageLoader("cutevariant", "assets/templates")

    template_env = jinja2.Environment(loader=template_loader)
    template_env.filters["camel_to_snake"] = camel_to_snake

    try:
        template = template_env.get_template(template_file)
    except Exception as e:
        LOGGER.error("Cannot find template %s", template_file, exc_info=True)

    # Find path to this plugin (directory to store generated file in)
    plugin_path = os.path.join(os.path.dirname(__file__), "plugins", module_name)

    if not os.path.isdir(plugin_path):
        os.mkdir(plugin_path)
    file_destination = os.path.join(plugin_path, template_to_file_name[template_file])

    try:
        output_text = template.render(**kwargs)
        if output_text:
            with open(file_destination, "w") as file:
                file.write(output_text)
    except Exception as e:
        LOGGER.error(e, exc_info=True)


class PluginCreator(QDialog):
    def __init__(self, parent: QWidget = None) -> None:
        super().__init__(parent=parent)

        vlayout = QVBoxLayout(self)
        self.form_layout = QFormLayout()

        # Setup name QLineEdit
        self.le_name = QLineEdit()
        self.le_name.setPlaceholderText(
            self.tr("The plugin name, as a space-separated class name")
        )
        self.le_name.setToolTip(self.le_name.placeholderText())
        self.name_validator = QRegularExpressionValidator()
        # Allow letters only
        self.name_validator.setRegularExpression(QRegularExpression(r"([a-zA-Z ])+"))
        self.le_name.setValidator(self.name_validator)

        # Setup the read-only, resulting module name QLineEdit
        self.le_resulting_module = QLineEdit("")
        self.le_resulting_module.setReadOnly(True)
        self.le_name.textChanged.connect(
            lambda s: self.le_resulting_module.setText(
                camel_to_snake(human_to_camel(s))
            )
        )
        self.le_resulting_module.setPlaceholderText(
            self.tr(
                "The name of the resulting python module (generated from plugin name)"
            )
        )
        self.le_resulting_module.setToolTip(self.le_resulting_module.placeholderText())

        # Setup the description QLineEdit
        self.le_description = QLineEdit()
        self.le_description.setPlaceholderText(
            self.tr("A short description of the plugin (why is it used for?)")
        )
        self.le_description.setToolTip(self.le_description.placeholderText())

        # Setup the long description QLineEdit
        self.te_long_description = QTextEdit()
        self.te_long_description.setPlaceholderText(
            self.tr(
                """A longer description of the plugin, as a short documentation.
Try answering:
- Why does the user need this plugin?
- How to use this plugin?
- What should the user expect from this plugin?"""
            )
        )
        self.te_long_description.setToolTip(self.te_long_description.placeholderText())

        # Setup the author QLineEdit
        self.le_author = QLineEdit()
        # Pre-fill user's name
        self.le_author.setText(QDir.home().dirName().capitalize())
        self.le_author.setPlaceholderText(self.tr("Author name for this plugin"))
        self.le_author.setToolTip(self.le_author.placeholderText())

        # Setup the checkboxes that select generated file types (widgets.py, dialogs.py, settings.py)
        self.frame_plugin_type = QFrame(self)

        # Layout these checkboxes vertically
        frame_layout = QVBoxLayout(self.frame_plugin_type)

        # So that the checkbox always prints 'Widget plugin (MyTestWidget)
        self.le_name.textChanged.connect(
            lambda s: self.check_add_widget.setText(
                f"{self.tr('Widget plugin ')}({human_to_camel(s)}Widget)"
            )
        )

        # So that the checkbox always prints 'Dialog plugin (MyTestDialog)
        self.le_name.textChanged.connect(
            lambda s: self.check_add_dialog.setText(
                f"{self.tr('Dialog plugin ')}({human_to_camel(s)}Dialog)"
            )
        )

        # So that the checkbox always prints 'Dialog plugin (MyTestSettingsWidget)
        self.le_name.textChanged.connect(
            lambda s: self.check_add_settings.setText(
                f"{self.tr('Plugin settings ')}({human_to_camel(s)}SettingsWidget)"
            )
        )

        self.check_add_widget = QCheckBox(self.tr("Widget plugin"), self)
        self.check_add_dialog = QCheckBox(self.tr("Dialog plugin"), self)
        self.check_add_settings = QCheckBox(self.tr("Plugin settings"), self)
        frame_layout.addWidget(self.check_add_widget)
        frame_layout.addWidget(self.check_add_dialog)
        frame_layout.addWidget(self.check_add_settings)

        self.dialog_box = QDialogButtonBox(
            QDialogButtonBox.Ok | QDialogButtonBox.Cancel
        )
        self.dialog_box.button(QDialogButtonBox.Ok).clicked.connect(self.accept)
        self.dialog_box.button(QDialogButtonBox.Cancel).clicked.connect(self.reject)

        # Disable the OK button as long as the name is empty
        self.le_name.textChanged.connect(
            lambda s: self.dialog_box.button(QDialogButtonBox.Ok).setEnabled(bool(s))
        )
        # Start disabled
        self.dialog_box.button(QDialogButtonBox.Ok).setEnabled(False)

        self.form_layout.addRow(self.tr("Name:"), self.le_name)
        self.form_layout.addRow(self.tr("Module name:"), self.le_resulting_module)
        self.form_layout.addRow(self.tr("Description:"), self.le_description)
        self.form_layout.addRow(self.tr("Long description:"), self.te_long_description)
        self.form_layout.addRow(self.tr("Author:"), self.le_author)
        self.form_layout.addRow(self.tr("Type:"), self.frame_plugin_type)

        vlayout.addLayout(self.form_layout)
        vlayout.addWidget(self.dialog_box)

        self.plugin_info = {}

        self.resize(680, 480)

    def accept(self) -> None:
        """Sets the result dictionnary, with all the format fields needed in the plugin templates.
        name: plugin name, in camelCase. Example: MySample (note there is no 'Plugin' suffix)
        title: same as plugin name, but space separated. Example: My sample
        module_name: same as plugin name, but in snake_case. Example: my_sample
        description: a single-line string
        long_description: a longer description string, that can contain some line returns
        author: a string
        add_settings: Whether to generate a settings.py module
        add_widget: Whether to generate a widgets.py module
        add_dialog: Whether to generate a dialogs.py module

        """
        self.plugin_info = {
            "name": human_to_camel(self.le_name.text()),
            "module_name": camel_to_snake(human_to_camel(self.le_name.text())),
            "title": self.le_name.text(),
            "description": self.le_description.text(),
            "long_description": self.te_long_description.toPlainText(),
            "author": self.le_author.text(),
            "add_settings": self.check_add_settings.isChecked(),
            "add_widget": self.check_add_widget.isChecked(),
            "add_dialog": self.check_add_dialog.isChecked(),
            "refresh_state_data": ["fields", "filters"],
        }
        return super().accept()


def create_dialog_plugin():
    dialog = PluginCreator()
    if dialog.exec_() == QDialog.Accepted:
        plugin_info = dialog.plugin_info
        if "add_settings" in plugin_info and plugin_info["add_settings"]:
            generate_file(SETTINGS_TEMPLATE, **plugin_info)
        if "add_widget" in plugin_info and plugin_info["add_widget"]:
            generate_file(WIDGET_TEMPLATE, **plugin_info)
        if "add_dialog" in plugin_info and plugin_info["add_dialog"]:
            generate_file(DIALOG_TEMPLATE, **plugin_info)

        generate_file(INIT_TEMPLATE, **plugin_info)  # Mandatory!


if __name__ == "__main__":
    import sys

    app = QApplication(sys.argv)
    create_dialog_plugin()
