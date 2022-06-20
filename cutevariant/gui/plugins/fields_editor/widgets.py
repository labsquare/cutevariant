import functools
from typing import List
import sqlite3
import json
import os
from functools import lru_cache
import typing
import copy
import re

from PySide6.QtWidgets import *
from PySide6.QtCore import *
from PySide6.QtGui import *
from cutevariant.config import Config

from cutevariant.gui import plugin, FIcon, style
from cutevariant.gui.mainwindow import MainWindow
from cutevariant.core import sql


from cutevariant.gui.widgets import PresetAction, FieldsWidget

from cutevariant import LOGGER
from cutevariant.gui.widgets.filters_widget import FilterDialog


class SortFieldDialog(QDialog):

    """A dialog box to dispay and order fields from a preset config

    dialog = SortFieldDialog()
    dialog.load()

    """

    def __init__(self, preset_name="test_preset", parent=None):
        super().__init__()

        self.setWindowTitle(self.tr("Sort fields order"))

        self.header = QLabel(self.tr("You can sort fields by drag and drop"))
        self.view = QListWidget()
        self.view.setDragDropMode(QAbstractItemView.InternalMove)
        self.view.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

        self.button_box = QDialogButtonBox(QDialogButtonBox.Cancel | QDialogButtonBox.Ok)
        self.up_button = QToolButton()
        self.up_button.setText("▲")
        self.up_button.setIcon(FIcon(0xF0143))
        self.up_button.setAutoRaise(True)
        self.up_button.clicked.connect(self.move_up)

        self.down_button = QToolButton()
        self.down_button.setText("▼")
        self.down_button.setIcon(FIcon(0xF0140))
        self.down_button.setAutoRaise(True)
        self.down_button.clicked.connect(self.move_down)

        vLayout = QVBoxLayout()
        tool_layout = QHBoxLayout()

        tool_layout.addStretch()
        tool_layout.addWidget(self.up_button)
        tool_layout.addWidget(self.down_button)

        vLayout.addWidget(self.header)
        vLayout.addWidget(self.view)
        vLayout.addLayout(tool_layout)
        vLayout.addWidget(self.button_box)
        self.setLayout(vLayout)

        self.button_box.accepted.connect(self.accept)
        self.button_box.rejected.connect(self.reject)

    @property
    def fields(self):
        return [self.view.item(row).text() for row in range(self.view.count())]

    @fields.setter
    def fields(self, fields):
        self.view.clear()
        self.view.addItems(fields)

    def move_up(self):
        row = self.view.currentRow()
        if row <= 0:
            return
        item = self.view.takeItem(row - 1)
        self.view.insertItem(row, item)

    def move_down(self):
        row = self.view.currentRow()
        if row > self.view.count() - 1:
            return
        item = self.view.takeItem(row + 1)
        self.view.insertItem(row, item)


class FieldsEditorWidget(plugin.PluginWidget):
    """Display all fields according categories

    Usage:

     view = FieldsWidget
     (conn)
     view.columns = ["chr","pos"]

    """

    ENABLE = True
    REFRESH_STATE_DATA = {"fields", "samples"}

    DEFAULT_FIELDS = ["chr", "pos", "ref", "alt"]

    def __init__(self, conn=None, parent=None):
        super().__init__(parent)

        self.setWindowIcon(FIcon(0xF08DF))
        # self.setToolTip(self.)

        # Create toolbar with search
        self.tool_layout = QHBoxLayout()

        self.toolbar = QToolBar()
        self.toolbar.setIconSize(QSize(16, 16))

        # ## Create fields view
        self.widget_fields = FieldsWidget(conn, parent)
        self.widget_fields.fields_changed.connect(self.update_fields_button)

        # # setup button_layout
        main_layout = QVBoxLayout(self)
        # layout.setContentsMargins(0, 0, 0, 0)
        # main_layout.addLayout(self.tool_layout)
        main_layout.addWidget(self.toolbar)
        main_layout.addWidget(self.widget_fields)
        main_layout.setSpacing(0)
        main_layout.setContentsMargins(0, 0, 0, 0)

        # self.setFocusPolicy(Qt.ClickFocus)

        self._setup_actions()

    def _setup_actions(self):

        ## apply action
        apply_action = self.toolbar.addAction(FIcon(0xF040A), "apply")
        apply_action.setToolTip(
            self.tr("Apply<hr>Apply current checked fields to the variant table")
        )
        apply_action.triggered.connect(self.on_apply)

        ## auto action
        auto_icon = QIcon()
        auto_icon.addPixmap(FIcon(0xF04E6).pixmap(16, 16), QIcon.Normal, QIcon.On)
        auto_icon.addPixmap(FIcon(0xF04E8).pixmap(16, 16), QIcon.Normal, QIcon.Off)
        self.auto_action = self.toolbar.addAction("Auto apply")
        self.auto_action.setIcon(auto_icon)
        self.auto_action.setCheckable(True)
        self.auto_action.setToolTip(
            self.tr("Auto Apply<hr>Enable/Disable Auto Apply when fields are checked")
        )
        self.auto_action.toggled.connect(apply_action.setDisabled)

        self.toolbar.addSeparator()

        ## check only action
        check_action = self.toolbar.addAction(FIcon(0xF0C51), "check only")
        check_action.setCheckable(True)
        check_action.setToolTip(
            self.tr("Show checked fields<hr>Only already checked fields will be shown")
        )
        check_action.toggled.connect(self.toggle_checked)

        spacer = QWidget()
        spacer.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.toolbar.addWidget(spacer)

        ## sort button
        self.sort_action = self.toolbar.addAction(FIcon(0xF04BA), "NA fields")
        self.sort_action.triggered.connect(self.show_fields_dialog)
        self.sort_action.setToolTip(
            self.tr(
                "Fields order<hr>Drag and drop checked fields to order them in the variant table"
            )
        )

        ## make sort action with text
        self.toolbar.widgetForAction(self.sort_action).setToolButtonStyle(
            Qt.ToolButtonTextBesideIcon
        )

        ## general menu

        self.preset_menu = QMenu()
        self.preset_button = QPushButton()
        self.preset_button.setToolTip(
            self.tr(
                "Presets<hr>- Load a existing preset<br>- Save the current preset<br>- Delete an existing preset<br>- Reload configured presets"
            )
        )
        self.preset_button.setIcon(FIcon(0xF035C))
        self.preset_button.setMenu(self.preset_menu)
        self.preset_button.setFlat(True)
        # self.preset_button.setPopupMode(QToolButton.InstantPopup)
        # self.preset_button.setToolButtonStyle(Qt.ToolButtonIconOnly)
        self.toolbar.addWidget(self.preset_button)

    def contextMenuEvent(self, event: QContextMenuEvent) -> None:
        menu = QMenu(self)
        menu.addAction(QIcon(), "Add filter", self.on_add_filter)
        menu.exec(event.globalPos())

    def on_add_filter(self):
        dlg = FilterDialog(self.widget_fields.conn, self)
        current_index = self.widget_fields.view.currentIndex()
        selected_field = current_index.data(Qt.UserRole + 2)
        dlg.set_field(selected_field)
        if dlg.exec() == QDialog.Accepted:
            one_filter = dlg.get_filter()
            filters = copy.deepcopy(self.mainwindow.get_state_data("filters"))
            if not filters:
                filters = {"$and": []}

            if "$and" in filters:
                filters["$and"].append(one_filter)
            if "$or" in filters:
                filters["$or"].append(one_filter)

            self.mainwindow.set_state_data("filters", filters)
            self.mainwindow.refresh_plugins(sender=self)

    @property
    def fields(self):
        return self.widget_fields.get_fields()

    @fields.setter
    def fields(self, fields):
        self.widget_fields.set_fields(fields)
        # self.update_fields_button()

    def update_fields_button(self):
        """Update fields button with the count selected fields"""
        field_count = len(self.fields)

        self.sort_action.setText(f"{field_count} fields")

        if self.auto_action.isChecked():
            self.on_apply()

    def save_preset(self):
        """Save current fields as new preset"""

        name, success = QInputDialog.getText(
            self, self.tr("Create new preset"), self.tr("Preset name:")
        )

        if success and name:
            config = Config("fields_editor")

            presets = config["presets"] or {}

            # if preset name exists ...
            if name in presets:
                ret = QMessageBox.warning(
                    self,
                    self.tr("Overwrite preset"),
                    self.tr(f"Preset {name} already exists. Do you want to overwrite it ?"),
                    QMessageBox.Yes | QMessageBox.No,
                )

                if ret == QMessageBox.No:
                    return

            presets[name] = self.fields
            config["presets"] = presets
            config.save()

        self.load_presets()

    def delete_preset(self):
        """Remove selected preset from combobox"""

        if not self.sender():
            return

        name = self.sender().data()

        ret = QMessageBox.warning(
            self,
            self.tr("Remove preset"),
            self.tr(f"Are you sure you want to delete preset {name}"),
            QMessageBox.Yes | QMessageBox.No,
        )

        if ret == QMessageBox.No:
            return

        config = Config("fields_editor")
        presets = config["presets"]
        if name in presets:
            del presets[name]
            config.save()
            self.load_presets()

    def load_presets(self, current_preset=None):
        """Load preset in the combobox
        This method should be called by __init__ and on refresh
        """
        self.preset_menu.clear()

        config = Config("fields_editor")

        self.preset_menu.addAction("Save preset", self.save_preset)
        self.preset_menu.addSeparator()

        if "presets" in config:
            presets = config["presets"]
            for name, fields in presets.items():
                action = PresetAction(name, name, self)
                action.set_close_icon(FIcon(0xF05E8, "red"))
                action.triggered.connect(self._on_select_preset)
                action.removed.connect(self.delete_preset)
                self.preset_menu.addAction(action)

        self.preset_menu.addSeparator()
        self.preset_menu.addAction("Reload presets", self.load_presets)

    def show_fields_dialog(self):

        w = SortFieldDialog()
        w.fields = self.widget_fields.get_fields()
        if w.exec_():
            self.fields = w.fields
            print(w.fields, self.fields)
            self.on_apply()

    # def toggle_search_bar(self, show=True):
    #     """Make search bar visible or not

    #     Args:
    #         show (bool, optional): If true, search bar is visible
    #     """
    #     self.search_edit.setVisible(show)
    #     if not show:
    #         self.search_edit.clear()
    #     else:
    #         self.search_edit.setFocus(Qt.PopupFocusReason)

    def toggle_checked(self, show=True):
        """Make only checked fields visible or not

        Args:
            show (bool, optional): if true, only checked fields are visibles
        """
        self.widget_fields.show_checked_only(show)

    def _on_select_preset(self):
        """Activate when preset has changed from preset_combobox"""
        # TODO Should be
        # self.mainwindow.set_state_data("fields",action.data())
        # self.mainwindow.refresh_plugins(sender=self)

        config = Config("fields_editor")
        presets = config["presets"]

        key = self.sender().data()

        if key in presets:
            self.fields = presets[key]
        else:
            self.fields = ["chr", "pos", "ref", "alt"]
        self.on_apply()

    def on_open_project(self, conn):
        """Overrided from PluginWidget"""
        self.widget_fields.conn = conn
        self.widget_fields.load()
        self.on_refresh()

    def on_close_project(self):
        self.widget_fields.clear()

    def on_refresh(self):
        """overrided from PluginWidget"""
        if self.mainwindow:
            self._is_refreshing = True

            # Reload fields if there are new samples
            samples = self.mainwindow.get_state_data("samples")
            if self.widget_fields.get_samples() != samples:
                self.widget_fields.set_samples(samples)
                self.widget_fields.load()

            self.fields = self.mainwindow.get_state_data("fields")
            self._is_refreshing = False
            self.load_presets()
            self.update_fields_button()

    def on_apply(self):
        if self.mainwindow is None or self._is_refreshing:
            """
            Debugging (no window)
            """
            LOGGER.debug(self.fields)
            return

        self.mainwindow.set_state_data("fields", self.fields)
        self.mainwindow.refresh_plugins(sender=self)


if __name__ == "__main__":
    import sys
    from cutevariant.core.reader import FakeReader

    app = QApplication(sys.argv)

    conn = sql.get_sql_connection(":memory:")
    sql.import_reader(conn, FakeReader())
    # import_file(conn, "examples/test.snpeff.vcf")

    widget = FieldsEditorWidget()
    widget.on_open_project(conn)

    # view.changed.connect(lambda : print(view.columns))

    widget.show()

    # w = SortFieldDialog()
    # w.show()

    app.exec_()
