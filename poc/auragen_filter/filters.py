import sqlite3

from PySide2.QtWidgets import (
    QWidget,
    QTabWidget,
    QLineEdit,
    QCompleter,
    QVBoxLayout,
    QListView,
    QFormLayout,
    QSpinBox,
)
from PySide2.QtCore import QStringListModel, Signal

from cutevariant.gui.widgets.pane import PanelListWidget, Pane


class AbstractFilterWidget(QWidget):

    changed = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)

    def setup(self, conn: sqlite3.Connection):
        pass

    def get_filters(self):
        pass

    def reset(self):
        pass


# =========== SOME DEFAULT WIDGETS USED for int, double, string and float


class IntegerFilterWidget(AbstractFilterWidget):
    def __init__(self, field: str, parent=None):
        super().__init__(parent)

        self.field = field
        vlayout = QVBoxLayout()
        vlayout.setContentsMargins(0, 0, 0, 0)
        self.edit = QSpinBox()
        vlayout.addWidget(self.edit)
        self.setLayout(vlayout)

        self.edit.valueChanged.connect(self.changed)

    def setup(self, conn: sqlite3.Connection):
        field_min, field_max = sql.get_field_range(conn, self.field)

        self.edit.setRange(field_min, field_max)

    def get_filters(self):
        name = self.field
        value = self.edit.value()
        return f"({name} == {value})"


class DoubleFilterWidget(AbstractFilterWidget):
    def __init__(self, field: str, parent=None):
        super().__init__(parent)

        self.field = field
        vlayout = QVBoxLayout()
        vlayout.setContentsMargins(0, 0, 0, 0)
        self.edit = QDoubleSpinBox()
        self.edit.valueChanged.connect(self.changed)
        vlayout.addWidget(self.edit)
        self.setLayout(vlayout)

    def setup(self, conn: sqlite3.Connection):
        field_min, field_max = sql.get_field_range(conn, self.field)

        self.edit.setRange(field_min, field_max)

    def get_filters(self):
        name = self.field
        value = self.edit.value()
        return f"({name} == {value})"


class BoolFilterWidget(AbstractFilterWidget):
    def __init__(self, field: str, parent=None):
        super().__init__(parent)

        self.field = field
        vlayout = QVBoxLayout()
        vlayout.setContentsMargins(0, 0, 0, 0)
        self.edit = QCheckBox()
        vlayout.addWidget(self.edit)
        self.setLayout(vlayout)
        # TODO Changed SIGNAL...

    def get_filters(self):
        name = self.field
        value = self.edit.isChecked()
        if not value:
            return None
        else:
            pass


class StringFilterWidget(AbstractFilterWidget):
    def __init__(self, field: str, parent=None):
        super().__init__(parent)

        self.field = field
        vlayout = QVBoxLayout()
        vlayout.setContentsMargins(0, 0, 0, 0)
        self.edit = QLineEdit()
        vlayout.addWidget(self.edit)
        self.setLayout(vlayout)

        self.completer = QCompleter()
        self.completer_model = QStringListModel()
        self.completer.setModel(self.completer_model)

        self.edit.setCompleter(self.completer)

        self.edit.textChanged.connect(self.changed)

    def setup(self, conn: sqlite3.Connection):
        self.completer_model.setStringList(
            sql.get_field_unique_values(conn, self.field)
        )

    def get_filters(self):
        name = self.field
        value = self.edit.text()
        if not value:
            return ""
        else:
            return {"field": name, "operator": "~", "value": value}


class ChoiceFilterWidget(AbstractFilterWidget):
    def __init__(self, field: str, parent=None):
        super().__init__(parent)

        self.field = field
        vlayout = QVBoxLayout()
        vlayout.setContentsMargins(0, 0, 0, 0)
        self.view = QListView()
        self.model = QStringListModel()
        self.view.setModel(self.model)
        vlayout.addWidget(self.view)
        self.setLayout(vlayout)

    def setup(self, conn: sqlite3.Connection):
        self.model.setStringList(sql.get_field_unique_values(conn, self.field))

    def get_filters(self):
        name = self.field
        return ""
        # return f"({name} ~ \"{value}\")"


class FiltersEditor(QTabWidget):

    changed = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)

        self.widgets = []
        self.elements = None

    def setup(self, conn: sqlite3.Connection):
        self.conn = conn

        for widget in self.widgets:
            widget.setup(self.conn)

    def set_layout_elements(self, elements):
        self.elements = elements
        self.build_layout()

    def get_filters(self, join_operator="AND"):
        filters = []
        for widget in self.widgets:
            f = widget.get_filters()
            if f:
                filters.append(widget.get_filters())

        return {"AND": filters}

    def reset(self):
        for widget in self.widgets:
            widget.reset()

    def build_layout(self):

        self.widgets = []
        for tab in self.elements["tabs"]:
            panel = PanelListWidget()
            self.addTab(panel, tab.get("name"))
            for section in tab.get("sections"):
                pane = Pane()
                pane.setTitle(section.get("name"))
                form_widget = QWidget()
                form_layout = QFormLayout()
                for widget in section.get("widgets"):
                    w = widget.get("widget")
                    self.widgets.append(w)
                    w.changed.connect(self.changed)
                    form_layout.addRow(widget.get("name"), w)

                form_widget.setLayout(form_layout)
                pane.setWidget(form_widget)
                panel.add(pane)

    def mousePressEvent(self, event):

        # HACK for testing...
        self.changed.emit()


if __name__ == "__main__":

    from cutevariant.core import sql
    from PySide2.QtWidgets import *
    import sys

    app = QApplication(sys.argv)

    conn = sql.get_sql_connection("C:/sacha/Dev/cutevariant/exome.db")

    all_w = FiltersEditor()

    elements = {
        "tabs": [
            {
                "name": "tab1",
                "sections": [
                    {
                        "name": "section1",
                        "widgets": [
                            {
                                "name": "chr",
                                "description": "editeur de truc",
                                "widget": StringFilterWidget("chr"),
                            },
                            {
                                "name": "gene",
                                "description": "editeur de truc",
                                "widget": StringFilterWidget("gene"),
                            },
                            {
                                "name": "pos",
                                "description": "editeur de truc",
                                "widget": IntegerFilterWidget("pos"),
                            },
                            {
                                "name": "Impact",
                                "description": "editeur de truc",
                                "widget": ChoiceFilterWidget("impact"),
                            },
                            {
                                "name": "consequence",
                                "description": "editeur de truc",
                                "widget": StringFilterWidget("consequence"),
                            },
                        ],
                    }
                ],
            }
        ]
    }

    all_w.set_layout_elements(elements)
    all_w.setup(conn)

    all_w.show()

    app.exec_()
