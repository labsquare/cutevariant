import sys
import json

from PySide2.QtWidgets import *
from PySide2.QtCore import *
from PySide2.QtGui import *


class NiceSlider(QWidget):
    """
    Just a wrapper around a slider widget to display its value on the right
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self.slider = QSlider()
        self.slider.setOrientation(Qt.Horizontal)

        self.label = QLabel(str(self.slider.value()), self)

        self.slider.valueChanged.connect(lambda value: self.label.setText(str(value)))

        layout = QHBoxLayout(self)
        layout.addWidget(self.slider)
        layout.addWidget(self.label)

    def value(self):
        return self.slider.value()

    def setRange(self, min_val=0, max_val=100):
        self.slider.setRange(min_val, max_val)

    def setOrientation(self, orientation: Qt.Orientation):
        self.slider.setOrientation(orientation)


class DictFormWidget(QWidget):
    """
    Simple form widget generated from an input list of fields.
    The fields are then accessible in a dictionnary through the :data: method
    """

    FIELD_EDITORS = {
        "combobox": (QComboBox, lambda combo: combo.currentData()),
        "lineedit": (QLineEdit, lambda lineedit: lineedit.text()),
        "checkbox": (QCheckBox, lambda checkbox: checkbox.isChecked()),
        "slider": (NiceSlider, lambda slider: slider.value()),
    }

    MAP_STR_TO_BOOL = {"True": True, "False": False}

    def __init__(self, input_fields, parent: QWidget = None):
        r"""
        input_fields looks like:
        [
            {
                "name" : "separator",
                "prompt" : "Separator",
                "description" : "What separator to use in the CSV",
                "widget" : "combobox",
                "values" : [(";",";"),("TAB","\t")],
                "category" : "general"
            },
            ...
        ]
        """
        super().__init__(parent)

        self.tab_widget = QTabWidget()
        self.widgets_by_category = {}

        for field in input_fields:
            name = field["name"]

            # If prompt (the field's label) is not specified, use the name instead (fallback)
            prompt = field.get("prompt", field["name"])

            # If no description provided, use the prompt instead (fallback)
            description = field.get("description", prompt)

            if field["widget"] in DictFormWidget.FIELD_EDITORS:

                # Create the widget from field info
                widget = DictFormWidget.FIELD_EDITORS[field["widget"]][0](self)

                # Keep a callable to retrieve value from widget
                field_access = DictFormWidget.FIELD_EDITORS[field["widget"]][1]

                # Add the widget to a category (will be in the general category if not set)
                category = field.get("category", "general")

                # Save the fieldname and its associated widget in a dictionnary at its respective category
                if self.widgets_by_category.get(category):
                    self.widgets_by_category[category].append(
                        (name, prompt, description, field_access, widget)
                    )
                else:
                    self.widgets_by_category[category] = [
                        (name, prompt, description, field_access, widget)
                    ]

                # Initialize the widget according to their type

                if field["widget"] == "combobox":
                    DictFormWidget.init_combobox(widget, field.get("values", []))

                if field["widget"] == "slider":
                    DictFormWidget.init_slider(
                        widget, field.get("min", 0), field.get("max", 100)
                    )

                if field["widget"] == "checkbox":
                    DictFormWidget.init_checkbox(
                        widget,
                        DictFormWidget.MAP_STR_TO_BOOL.get(field["value"], False),
                    )

        # For each category, create a tab and add the appropriate widgets
        for category in self.widgets_by_category:
            tab = QWidget(self.tab_widget)
            self.tab_widget.addTab(tab, QIcon(), category)
            formlayout = QFormLayout(tab)
            for (
                name,
                prompt,
                description,
                field_access,
                widget,
            ) in self.widgets_by_category[category]:
                formlayout.addRow(prompt, widget)
                widget.setWhatsThis(description)

        self.button_save = QPushButton(self.tr("Export to JSON"), self)
        self.button_save.clicked.connect(self.save_to_json)

        layout = QVBoxLayout(self)
        layout.addWidget(self.tab_widget)
        layout.addWidget(self.button_save)

    def data(self):
        result = {}
        for category in self.widgets_by_category:
            result[category] = {}
            for (
                name,
                prompt,
                description,
                field_access,
                widget,
            ) in self.widgets_by_category[category]:
                result[category][name] = field_access(widget)
        return result

    def save_to_json(self):
        filename = QFileDialog.getSaveFileName(
            self,
            self.tr("Please choose where you want to save the JSON"),
            QDir.homePath(),
        )[0]
        if filename:
            with open(filename, "w+") as device:
                json.dump(self.data(), device)

    def init_combobox(combobox: QComboBox, values):
        combobox.clear()
        for value in values:
            combobox.addItem(*value)

    def init_slider(slider: QSlider, min_val, max_val):
        slider.setRange(min_val, max_val)
        slider.setOrientation(Qt.Horizontal)

    def init_checkbox(checkbox: QCheckBox, value=True):
        checkbox.setChecked(value)


if __name__ == "__main__":
    app = QApplication(sys.argv)

    test = DictFormWidget(
        [
            {
                "name": "separator",
                "prompt": "Which separator to use for your CSV ?",
                "description": "A separator that will be used in the CSV file",
                "widget": "combobox",
                "values": [[";", ";"], ["TAB", "\t"], ["NEW LINE", "\n"]],
                "category": "Write CSV",
            },
            {
                "name": "wants_coffee",
                "prompt": "Coffee ?",
                "description": "Do you want some coffee ?",
                "widget": "checkbox",
                "value": "True",
                "category": "After lunch time",
            },
            {
                "name": "is_happy",
                "prompt": "Are you happy in your life ?",
                "description": "Come on, you can tell me",
                "widget": "checkbox",
                "value": "True",
                "category": "Special",
            },
            {
                "name": "the_answer",
                "prompt": "The Ultimate Question of Life, the Universe and Everything ?",
                "description": "Didn't you read The Hitchhiker's Guide to the Galaxy ? Yeah, me neither.",
                "widget": "slider",
                "min": 0,
                "max": 42,
                "category": "Special",
            },
        ]
    )
    test.show()
    if app.exec_() == 0:
        print(test.data())

        exit(0)
    else:
        exit(1)
