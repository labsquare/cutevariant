from cutevariant.gui import plugin
import jinja2
import os
import re

from PySide2.QtGui import *
from PySide2.QtCore import *
from PySide2.QtWidgets import *

from cutevariant.commons import camel_to_snake, snake_to_camel
from cutevariant import LOGGER

WIDGET_TEMPLATE = "plugin_template.txt"
DIALOG_TEMPLATE = "plugin_dialog_template.txt"
INIT_TEMPLATE = "init_template.txt"
SETTINGS_TEMPLATE = "plugin_settings_template.txt"


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


def generate_file(template_file: str, name: str, **kwargs):
    """Writes all the files required for a plugin to work.
    This function should be called twice per plugin, once for the plugin itself, and once for the __init__.py file.

    Args:
        file_type (str): One of PLUGIN_TEMPLATE, DIALOG_TEMPLATE, or INIT_TEMPLATE
    """
    template_path = os.path.abspath(os.path.join(f"{os.path.dirname(__file__)}/../"))
    template_loader = jinja2.FileSystemLoader(searchpath=template_path)

    template_to_file_name = {
        WIDGET_TEMPLATE: "widgets.py",
        DIALOG_TEMPLATE: "dialogs.py",
        SETTINGS_TEMPLATE: "settings.py",
        INIT_TEMPLATE: "__init__.py",
    }

    if not os.path.isfile(os.path.join(template_path, template_file)):
        LOGGER.debug("Template %s not found!", template_file)
        return
    template_env = jinja2.Environment(loader=template_loader)
    template_env.filters["camel_to_snake"] = camel_to_snake
    template = template_env.get_template(template_file)
    plugin_path = os.path.join(os.path.dirname(__file__), "plugins")
    plugin_path = os.path.join(plugin_path, camel_to_snake(name))
    if not os.path.isdir(plugin_path):
        os.mkdir(plugin_path)
    file_destination = os.path.join(
        plugin_path, template_to_file_name.get(template_file, "error.py")
    )
    try:
        output_text = template.render(**kwargs, name=name)
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

        self.le_name = QLineEdit()
        self.name_validator = QRegularExpressionValidator()
        # Allow letters only
        self.name_validator.setRegularExpression(QRegularExpression(r"([a-zA-Z ])+"))
        self.le_name.setValidator(self.name_validator)

        self.label_resulting_name = QLabel("")
        self.le_name.textChanged.connect(
            lambda s: self.label_resulting_name.setText(f"{human_to_camel(s)}Plugin")
        )

        self.label_resulting_module = QLabel("")
        self.le_name.textChanged.connect(
            lambda s: self.label_resulting_module.setText(
                camel_to_snake(human_to_camel(s))
            )
        )

        self.le_title = QLineEdit()
        self.le_description = QLineEdit()
        self.te_long_description = QTextEdit()
        self.le_author = QLineEdit()

        self.frame_plugin_type = QFrame(self)
        frame_layout = QVBoxLayout(self.frame_plugin_type)
        self.check_add_dialog = QCheckBox(self.tr("Dialog plugin"), self)
        self.check_add_widget = QCheckBox(self.tr("Widget plugin"), self)
        self.check_add_settings = QCheckBox(self.tr("Add plugin settings"), self)
        frame_layout.addWidget(self.check_add_dialog)
        frame_layout.addWidget(self.check_add_widget)
        frame_layout.addWidget(self.check_add_settings)

        self.dialog_box = QDialogButtonBox(
            QDialogButtonBox.Ok | QDialogButtonBox.Cancel
        )
        self.dialog_box.button(QDialogButtonBox.Ok).clicked.connect(self.accept)
        self.dialog_box.button(QDialogButtonBox.Cancel).clicked.connect(self.reject)

        self.form_layout.addRow(self.tr("Plugin name (space separated)"), self.le_name)
        self.form_layout.addRow(
            self.tr("Resulting class name:"), self.label_resulting_name
        )
        self.form_layout.addRow(
            self.tr("Resulting module name:"), self.label_resulting_module
        )
        self.form_layout.addRow(self.tr("Plugin title"), self.le_title)
        self.form_layout.addRow(self.tr("Description"), self.le_description)
        self.form_layout.addRow(self.tr("Long description"), self.te_long_description)
        self.form_layout.addRow(self.tr("Author"), self.le_author)
        self.form_layout.addRow(self.tr("Plugin type"), self.frame_plugin_type)

        vlayout.addLayout(self.form_layout)
        vlayout.addWidget(self.dialog_box)

        self.plugin_info = {}

    def accept(self) -> None:
        self.plugin_info = {
            "name": human_to_camel(self.le_name.text()),
            "title": self.le_title.text(),
            "description": self.le_description.text(),
            "long_description": self.te_long_description.toPlainText(),
            "author": self.le_author.text(),
            "add_settings": self.check_add_settings.isChecked(),
            "add_widget": self.check_add_widget.isChecked(),
            "add_dialog": self.check_add_dialog.isChecked(),
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
