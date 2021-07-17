import jinja2
import os
import re

from PySide2.QtGui import *
from PySide2.QtCore import *
from PySide2.QtWidgets import *

from cutevariant.commons import camel_to_snake, snake_to_camel
from cutevariant import LOGGER

PLUGIN_TEMPLATE = "plugin_template.txt"
DIALOG_PLUGIN_TEMPLATE = "plugin_dialog_template.txt"
INIT_TEMPLATE = "init_template.txt"


def clean_human_text(words: str) -> str:
    """Returns clean, space separated words from input string
    with punctuation.

    Example:
        >>> clean_human_text("My plugin, with commas and exclamation point!")
        'My plugin with commas and exclamation point'

    Args:
        words (str): String with words and punctuation

    Returns:
        str: String with only words, separated by space
    """
    return re.sub(r"\W+", " ", words).strip()


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


def generate_file(file_type: str, **kwargs):
    """Writes all the files required for a plugin to work.
    This function should be called twice per plugin, once for the plugin itself, and once for the __init__.py file.

    Args:
        file_type (str): One of PLUGIN_TEMPLATE, DIALOG_TEMPLATE, or INIT_TEMPLATE
    """
    template_loader = jinja2.FileSystemLoader(searchpath="./")
    TEMPLATE_FILE = file_type
    if not os.path.isfile(f"./{TEMPLATE_FILE}"):
        LOGGER.debug("Template %s not found!", TEMPLATE_FILE)
        return
    template_env = jinja2.Environment(loader=template_loader)
    template = template_env.get_template(TEMPLATE_FILE)
    plugin_path = os.path.join(os.path.dirname(__file__), "plugins")
    file_destination = os.path.join(plugin_path, camel_to_snake(kwargs["name"]))
    try:
        output_text = template.render(**kwargs)
        if output_text:
            with open(file_destination, "w") as file:
                file.write(output_text)
    except Exception as e:
        LOGGER.error("%s\n%s", e.args)


def create_dialog_plugin(**kwargs):
    pass


def create_plugin(**kwargs):

    template_loader = jinja2.FileSystemLoader(searchpath="./")
    TEMPLATE_FILE = "plugin_template.txt"
    if not os.path.isfile(f"./{TEMPLATE_FILE}"):
        return
    template_env = jinja2.Environment(loader=template_loader)
    template = template_env.get_template(TEMPLATE_FILE)
    plugin_path = os.path.join(os.path.dirname(__file__), "plugins")
    os.path.join(plugin_path, kwargs["name"])
    output_text = template.render(**kwargs)


def create_dialog_plugin(**kwargs):
    template_loader = jinja2.FileSystemLoader(searchpath="./")
    TEMPLATE_FILE = "plugin_dialog_template.txt"
    if not os.path.isfile(f"./{TEMPLATE_FILE}"):
        return
    template_env = jinja2.Environment(loader=template_loader)
    template = template_env.get_template(TEMPLATE_FILE)
    plugin_path = os.path.join(os.path.dirname(__file__), "plugins")
    output_text = template.render(**kwargs)


def create_init_file(**kwargs):
    template_loader = jinja2.FileSystemLoader(searchpath="./")
    TEMPLATE_FILE = "init_template.txt"
    if not os.path.isfile(f"./{TEMPLATE_FILE}"):
        return
    template_env = jinja2.Environment(loader=template_loader)
    template = template_env.get_template(TEMPLATE_FILE)
    plugin_path = os.path.join(os.path.dirname(__file__), "plugins")
    output_text = template.render(**kwargs)


class PluginCreator(QDialog):
    def __init__(self, parent: QWidget) -> None:
        super().__init__(parent=parent)

        vlayout = QVBoxLayout(self)
        self.form_layout = QFormLayout()
        self.le_name = QLineEdit()
        self.le_title = QLineEdit()
        self.le_description = QLineEdit()
        self.le_long_description = QLineEdit()
        self.le_author = QLineEdit()
        self.le_version = QLineEdit()

        self.buttons = QDialogButtonBox(self)
        self.buttons.button(QDialogButtonBox.Ok).clicked.connect(self.accept)
        self.buttons.button(QDialogButtonBox.Cancel).clicked.connect(self.reject)

        self.form_layout.addRow(self.tr("Plugin name"), self.le_name)
        self.form_layout.addRow(self.tr("Plugin title"), self.le_title)
        self.form_layout.addRow(self.tr("Description"), self.le_description)
        self.form_layout.addRow(self.tr("Long description"), self.le_long_description)
        self.form_layout.addRow(self.tr("Author"), self.le_author)
        self.form_layout.addRow(self.tr("Version"), self.le_version)

        vlayout.addLayout(self.form_layout)
        vlayout.addWidget(self.buttons)

        self.plugin_info = {}

    def accept(self) -> None:
        self.plugin_info = {
            "name": human_to_camel(clean_human_text(self.le_name.text())),
            "title": self.le_title.text(),
            "description": self.le_description.text(),
            "long_description": self.le_long_description.text(),
            "author": self.le_author.text(),
            "version": self.le_version.text(),
        }
        return super().accept()
