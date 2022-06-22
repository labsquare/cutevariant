import sqlite3
from cutevariant.core import sql
from cutevariant.core.querybuilder import build_vql_query
from cutevariant.core.vql import parse_one_vql
from cutevariant.gui import mainwindow, plugin
from cutevariant.gui import MainWindow
from cutevariant.gui.widgets import CodeEdit
from cutevariant.gui.settings import Config
from cutevariant.gui import FIcon, style

from PySide6.QtWidgets import *
from PySide6.QtGui import *
from PySide6.QtCore import *


class QueryWidget(QWidget):
    def __init__(self, parent: QWidget = None, conn: sqlite3.Connection = None) -> None:
        super().__init__(parent)

        self.line_edit = QLineEdit()
        self.desc_edit = QTextEdit()
        self.code_edit = CodeEdit()

        self.tab_widget = QTabWidget()
        self.info_tab = QWidget()
        form_box = QGroupBox()
        form_layout = QFormLayout(form_box)
        form_layout.addRow("Title", self.line_edit)
        form_layout.addRow("Description", self.desc_edit)

        self.tab_widget.addTab(form_box, "Information")
        self.tab_widget.addTab(self.code_edit, "VQL query")
        self.tab_widget.tabBar().setDocumentMode(True)
        self.tab_widget.tabBar().setExpanding(True)

        main_layout = QVBoxLayout(self)
        main_layout.addWidget(self.tab_widget)

        self.conn = conn

        self._fill_completer()

    def _fill_completer(self):
        """Create Completer with his model

        Fill the model with the SQL keywords and database fields
        """
        if self.conn:
            # preload samples , selection and wordset
            samples = [i["name"] for i in sql.get_samples(self.conn)]
            selections = [i["name"] for i in sql.get_selections(self.conn)]
            wordsets = [i["name"] for i in sql.get_wordsets(self.conn)]

            # keywords = []
            self.code_edit.completer.model.clear()
            self.code_edit.completer.model.beginResetModel()

            # register keywords
            for keyword in self.code_edit.syntax.sql_keywords:
                self.code_edit.completer.model.add_item(
                    keyword, "VQL keywords", FIcon(0xF0169), "#f6ecf0"
                )

            for selection in selections:
                self.code_edit.completer.model.add_item(
                    selection, "Source table", FIcon(0xF04EB), "#f6ecf0"
                )

            for wordset in wordsets:
                self.code_edit.completer.model.add_item(
                    f"WORDSET['{wordset}']", "WORDSET", FIcon(0xF04EB), "#f6ecf0"
                )

            for field in sql.get_fields(self.conn):
                name = field["name"]
                description = "<b>{}</b> ({}) from {} <br/><br/> {}".format(
                    field["name"],
                    field["type"],
                    field["category"],
                    field["description"],
                )
                color = style.FIELD_TYPE.get(field["type"], "str")["color"]
                icon = FIcon(style.FIELD_TYPE.get(field["type"], "str")["icon"], "white")

                if field["category"] == "variants":
                    self.code_edit.completer.model.add_item(name, description, icon, color)

                if field["category"] == "annotations":
                    self.code_edit.completer.model.add_item(f"ann.{name}", description, icon, color)

                if field["category"] == "samples":

                    # Add AnySamples special keywords
                    # samples["*"].gt
                    name = "samples[ANY].{}".format(field["name"])
                    self.code_edit.completer.model.add_item(name, description, icon, color)

                    name = "samples[ALL].{}".format(field["name"])
                    self.code_edit.completer.model.add_item(name, description, icon, color)

                    # Overwrite name
                    for sample in samples:
                        name = "samples['{}'].{}".format(sample, field["name"])
                        description = "<b>{}</b> ({}) from {} {} <br/><br/> {}".format(
                            field["name"],
                            field["type"],
                            field["category"],
                            sample,
                            field["description"],
                        )
                        self.code_edit.completer.model.add_item(name, description, icon, color)

            self.code_edit.completer.model.endResetModel()

    def set_item(self, item: dict):
        self.line_edit.setText(item.get("name", ""))
        self.desc_edit.setText(item.get("description", ""))
        self.code_edit.setText(item.get("query", ""))

    def get_item(self) -> dict:
        return {
            "name": self.line_edit.text(),
            "description": self.desc_edit.toPlainText(),
            "query": self.code_edit.toPlainText(),
        }


class QueryDialog(QDialog):
    def __init__(self, parent: QWidget = None, conn: sqlite3.Connection = None):
        super().__init__(parent)

        self.widget = QueryWidget(parent=self, conn=conn)
        self.button_box = QDialogButtonBox(QDialogButtonBox.Save | QDialogButtonBox.Cancel)

        layout = QVBoxLayout(self)
        layout.addWidget(self.widget)
        layout.addWidget(self.button_box)

        self.button_box.button(QDialogButtonBox.Save).clicked.connect(self.accept)
        self.button_box.button(QDialogButtonBox.Cancel).clicked.connect(self.reject)

    def get_item(self):
        return self.widget.get_item()

    def set_item(self, item: dict):
        self.widget.set_item(item)


class QueryListModel(QAbstractListModel):
    def __init__(self) -> None:
        super().__init__()
        self._presets = []

    def load(self):
        self.beginResetModel()
        config = Config("vql_editor")
        _presets = config["presets"] or []
        _presets.sort(key=lambda x: x["name"].lower())
        self._presets = _presets
        self.endResetModel()

    def clear(self):
        self.beginResetModel()
        self._presets.clear()
        self.endResetModel()

    def save(self):
        config = Config("vql_editor")
        config["presets"] = self._presets
        config.save()

    def add_preset(self, name: str, description: str, query: str):
        self.beginInsertRows(QModelIndex(), len(self._presets), len(self._presets))
        self._presets.append({"name": name, "description": description, "query": query})
        self.endInsertRows()

    def edit_preset(self, name: str, description: str, query: str, previous_name: str = None):
        if self.contains_preset(previous_name):
            print("contain preset")
            index = self.get_preset_index(previous_name)
            self._presets[index.row()] = {
                "name": name,
                "description": description,
                "query": query,
            }
            self.dataChanged.emit(index, index, Qt.DisplayRole)
            self.dataChanged.emit(index, index, Qt.UserRole)
            self.dataChanged.emit(index, index, Qt.ToolTipRole)

    def remove_preset(self, index: QModelIndex):
        row = index.row()
        self.beginRemoveRows(QModelIndex(), row, row)
        del self._presets[row]
        self.endRemoveRows()

    def get_presets(self):
        return self._presets

    def get_preset(self, index: QModelIndex):
        if index.parent() == QModelIndex():
            return self._presets[index.row()]
        else:
            return dict()

    def contains_preset(self, preset_name: str):
        return any(p["name"] == preset_name for p in self._presets)

    def get_preset_index(self, preset_name):
        for i, p in enumerate(self._presets):
            if p["name"] == preset_name:
                return self.index(i)
        return QModelIndex()

    def data(self, index: QModelIndex, role: int) -> str:
        row = index.row()
        col = index.column()
        name = self._presets[row]["name"]
        description = self._presets[row]["description"]
        query = self._presets[row]["query"]
        if role == Qt.DisplayRole:
            if col == 0:
                return name
        if role == Qt.ToolTipRole:
            return description
        if role == Qt.UserRole:
            return query
        if role == Qt.SizeHintRole:
            return QSize(30, 30)

    def rowCount(self, parent: QModelIndex = QModelIndex()) -> int:
        if parent == QModelIndex():
            return len(self._presets)
        else:
            return 0


class QueryListWidget(plugin.PluginWidget):

    # Location of the plugin in the mainwindow
    # Can be : DOCK_LOCATION, CENTRAL_LOCATION, FOOTER_LOCATION
    LOCATION = plugin.DOCK_LOCATION
    # Make the plugin enable. Otherwise, it will be not loaded
    ENABLE = True

    # Refresh the plugin only if the following state variable changed.
    # Can be : fields, filters, source

    REFRESH_STATE_DATA = set()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.model = QueryListModel()
        self.model.load()

        self.tool_bar = QToolBar()
        self.view = QListView()
        self.view.setModel(self.model)
        self.setWindowIcon(FIcon(0xF0EBF))

        main_layout = QVBoxLayout(self)
        main_layout.addWidget(self.tool_bar)
        main_layout.addWidget(self.view)
        main_layout.setContentsMargins(0, 0, 0, 0)

        self._setup_actions()

        self.view.doubleClicked.connect(self._run_query)
        self.view.setContextMenuPolicy(Qt.ActionsContextMenu)

        self.tool_bar.setIconSize(QSize(16, 16))

        self.setContentsMargins(0, 0, 0, 0)

    def _setup_actions(self):

        self.run_action = self.tool_bar.addAction(FIcon(0xF040A), "Apply")
        self.run_action.triggered.connect(self._run_query)
        self.run_action.setToolTip(
            self.tr("Apply Query<hr>Apply query to filter variants and show selected fields")
        )

        self.tool_bar.addSeparator()

        self.add_action = self.tool_bar.addAction(FIcon(0xF0415), "Add")
        self.add_action.triggered.connect(self._add_query)
        self.add_action.setToolTip(
            self.tr(
                "Add Query<hr>Add query to the list.<br>Current query is automatically selected"
            )
        )

        self.remove_action = self.tool_bar.addAction(FIcon(0xF0A7A), "Remove")
        self.remove_action.triggered.connect(self._remove_query)
        self.remove_action.setToolTip(
            self.tr("Remove Query<hr>Remove existing query from the list")
        )

        self.edit_action = self.tool_bar.addAction(FIcon(0xF064F), "Edit")
        self.edit_action.triggered.connect(self._edit_query)
        self.edit_action.setToolTip(
            self.tr(
                "Edit Query<hr>Edit existing query, by changing name, description or query itself"
            )
        )

        self.view.addActions([self.remove_action, self.edit_action])

    def on_register(self, mainwindow: MainWindow):
        """This method is called when the plugin is registered from the mainwindow.

        This is called one time at the application startup.

        Args:
            mainwindow (MainWindow): cutevariant Mainwindow
        """
        self.mainwindow: MainWindow = mainwindow

    def on_open_project(self, conn: sqlite3.Connection):
        """This method is called when a project is opened

                Do your initialization here.
        You may want to store the conn variable to use it later.

        Args:
            conn (sqlite3.connection): A connection to the sqlite project
        """
        self.conn = conn

    def on_close_project(self):
        self.model.clear()

    def on_refresh(self):
        """This method is called from mainwindow.refresh_plugins()

        You may want to overload this method to update the plugin state
        when query changed
        """
        pass

    def _run_query(self):
        index = self.view.currentIndex()
        query = self.model.data(index, Qt.UserRole)
        query_params = parse_one_vql(query)

        self.mainwindow.set_state_data("fields", query_params.get("fields", []))
        self.mainwindow.set_state_data("source", query_params.get("source", "variants"))
        self.mainwindow.set_state_data("filters", query_params.get("filters", []))
        self.mainwindow.set_state_data("order_by", query_params.get("order_by", []))

        self.mainwindow.refresh_plugins(sender=self)

    def _add_query(self):
        current_query = {
            k: self.mainwindow.get_state_data(k)
            for k in ("fields", "source", "filters", "order_by")
        }
        query = build_vql_query(**current_query)
        dialog = QueryDialog(self, self.conn)
        dialog.set_item({"query": query})
        if dialog.exec() == QDialog.Accepted:
            new_preset = dialog.get_item()

            saved_query = new_preset.get("query")
            try:
                _ = parse_one_vql(saved_query)
            except:
                QMessageBox.warning(
                    self, self.tr("Aborting"), self.tr("Invalid query, won't save!")
                )
                return

            if "name" in new_preset and new_preset["name"]:
                if self.model.contains_preset(new_preset.get("name")):
                    if (
                        QMessageBox.question(
                            self,
                            self.tr("Warning"),
                            self.tr(f"Preset {new_preset.get('name')} already exists. Overwrite?"),
                            QMessageBox.Yes | QMessageBox.No,
                        )
                        == QMessageBox.No
                    ):
                        return
                else:
                    self.model.add_preset(**new_preset)
                    self.model.save()
            else:
                QMessageBox.warning(
                    "Aborting", self.tr("Cannot save preset with no name, won't save!")
                )
                return

    def _remove_query(self):
        if (
            QMessageBox.question(
                self,
                self.tr("Warning"),
                self.tr("Do you really want to delete this preset?\nYou can't undo this!"),
            )
            == QMessageBox.Yes
        ):
            self.model.remove_preset(self.view.currentIndex())
            self.model.save()

    def _edit_query(self):
        index = self.view.currentIndex()
        name = index.data(Qt.DisplayRole)
        description = index.data(Qt.ToolTipRole)
        query = index.data(Qt.UserRole)

        dialog = QueryDialog(self, self.conn)

        dialog.set_item(
            {"name": name, "description": description, "query": query, "previous_name": name}
        )

        if dialog.exec() == QDialog.Accepted:
            self.model.edit_preset(**dialog.get_item(), previous_name=name)
            self.model.save()
            self.model.load()


if __name__ == "__main__":
    import sys

    app = QApplication(sys.argv)
    w = QueryDialog()
    res = w.show()
    exit(app.exec())
