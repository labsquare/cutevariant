from PySide2.QtWidgets import *
from PySide2.QtCore import *


class BaseWidget(QTabWidget):
    def __init__(self):
        super().__init__()

    def save(self):
        raise NotImplemented()

    def load(self):
        raise NotImplemented()


class GeneralSettingsWidget(BaseWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("General")

    def save(self):
        pass

    def load(self):
        pass


class PluginsSettingsWidget(BaseWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Plugins")

    def save(self):
        pass

    def load(self):
        pass


class SettingsWidget(QDialog):
    def __init__(self):
        super().__init__()
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
