"""Plugin to Display genotypes variants 
"""
import typing
from functools import cmp_to_key, partial
import time
import copy
import re

# Qt imports
from PySide6.QtWidgets import *
from PySide6.QtCore import *
from PySide6.QtGui import *


# Custom imports
from cutevariant.core import sql, command
from cutevariant.core.reader import BedReader
import cutevariant.core.querybuilder as qb
from cutevariant.gui import plugin, FIcon, style
from cutevariant.gui.style import SAMPLE_VARIANT_CLASSIFICATION
from cutevariant.commons import DEFAULT_SELECTION_NAME
from cutevariant.config import Config


from cutevariant.gui.widgets import (
    ChoiceWidget,
    create_widget_action,
    SampleDialog,
    SampleVariantDialog,
    PresetAction,
)


from cutevariant import LOGGER
from cutevariant.gui.sql_thread import SqlThread

from cutevariant.gui.style import (
    GENOTYPE,
    CLASSIFICATION,
    SAMPLE_CLASSIFICATION,
    SAMPLE_VARIANT_CLASSIFICATION,
)

from cutevariant.gui import FormatterDelegate
from cutevariant.gui.formatters.cutestyle import CutestyleFormatter


from PySide6.QtWidgets import *
import sys
from functools import partial


class VariantVerticalHeader(QHeaderView):

    # COLOR = {0: "gray", 1: "orange", 2: "green"}

    def __init__(self, parent=None):
        super().__init__(Qt.Vertical, parent)

    def sizeHint(self):
        return QSize(30, super().sizeHint().height())

    def paintSection(self, painter: QPainter, rect: QRect, section: int):

        if painter is None:
            return

        painter.save()
        super().paintSection(painter, rect, section)

        # default color
        default_color = "lightgray"

        # sample
        valid = self.model().item(section)["valid"]
        sample_color = style.SAMPLE_CLASSIFICATION[valid].get("color")
        sample_icon = style.SAMPLE_CLASSIFICATION[valid].get("icon")
        sample_blurred = style.SAMPLE_CLASSIFICATION[valid].get("blurred")

        # sample variant
        classification = self.model().item(section)["classification"] or 0
        sample_variant_color = style.SAMPLE_VARIANT_CLASSIFICATION[classification].get(
            "color"
        )
        sample_variant_icon = style.SAMPLE_VARIANT_CLASSIFICATION[classification].get(
            "icon"
        )
        sample_variant_blurred = style.SAMPLE_VARIANT_CLASSIFICATION[
            classification
        ].get("blurred")

        if sample_variant_color != "":
            sample_color = sample_variant_color

        if sample_blurred or sample_variant_blurred:
            sample_variant_color = style.BLURRED_COLOR
            sample_color = style.BLURRED_COLOR

        painter.restore()
        pen = QPen(QColor(sample_variant_color))
        pen.setWidth(6)
        painter.setPen(pen)
        painter.setBrush(QBrush(sample_variant_color))
        painter.drawLine(rect.left(), rect.top() + 1, rect.left(), rect.bottom() - 1)

        # pix = FIcon(sample_icon, sample_color).pixmap(20, 20)
        pix = FIcon(sample_icon, sample_color).pixmap(20, 20)

        target = rect.center() - pix.rect().center() + QPoint(1, 0)

        painter.drawPixmap(target, pix)


# pix = FIcon(0xF00C1 if favorite else 0xF00C3, color).pixmap(20, 20)
# target = rect.center() - pix.rect().center() + QPoint(1, 0)

# painter.drawPixmap(target, pix)


class SamplesModel(QAbstractTableModel):

    samples_are_loading = Signal(bool)
    error_raised = Signal(str)
    load_started = Signal()
    load_finished = Signal()
    interrupted = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.conn = None
        self.items = []
        self.fields = []

        self.selected_samples = []
        self.selected_families = []
        self.selected_genotypes = []
        self.selected_tags = []

        self._headers = []
        self.fields_descriptions = {}

        # Creates the samples loading thread
        self._load_samples_thread = SqlThread(self.conn)

        # Connect samples loading thread's signals (started, finished, error, result ready)
        self._load_samples_thread.started.connect(
            lambda: self.samples_are_loading.emit(True)
        )
        self._load_samples_thread.finished.connect(
            lambda: self.samples_are_loading.emit(False)
        )
        self._load_samples_thread.result_ready.connect(self.on_samples_loaded)
        self._load_samples_thread.error.connect(self.error_raised)

        self._user_has_interrupt = False

    def rowCount(self, parent: QModelIndex = QModelIndex) -> int:
        """override"""
        return len(self.items)

    def columnCount(self, parent: QModelIndex = QModelIndex) -> int:
        """override"""
        return len(self._headers)

    def item(self, row: int):
        return self.items[row]

    def data(self, index: QModelIndex, role: Qt.ItemDataRole) -> typing.Any:
        """override"""
        if not index.isValid():
            return None

        item = self.items[index.row()]
        key = self._headers[index.column()]

        if role == Qt.DisplayRole and key != "valid":
            return item[key]

        if role == Qt.DecorationRole:
            if key == "valid":
                hex_icon = 0xF139A if item[key] == 1 else 0xF0FC7
                return QIcon(FIcon(hex_icon))

        # if role == Qt.DecorationRole:
        #     if index.column() == 0:
        #         return QIcon(FIcon(SEX_ICON.get(item["sex"], 0xF02D6)))
        #     if field == "gt":
        #         icon = style.GENOTYPE.get(item[field], style.GENOTYPE[-1])["icon"]
        #         return QIcon(FIcon(icon))

        # if role == Qt.ToolTipRole:
        #     if index.column() == 0:
        #         return f"""{item['name']} (<span style="color:{PHENOTYPE_COLOR.get(item['phenotype'],'lightgray')}";>{PHENOTYPE_STR.get(item['phenotype'],'Unknown phenotype')}</span>)"""

        #     else:
        #         description = self.fields_descriptions.get(field, "")
        #         return f"<b>{field}</b><br/> {description} "

        # if role == Qt.ForegroundRole and index.column() == 0:
        #     phenotype = self.items[index.row()]["phenotype"]
        #     return QColor(PHENOTYPE_COLOR.get(phenotype, "#FF00FF"))

    def headerData(self, section: int, orientation: Qt.Orientation, role: int):

        if orientation == Qt.Horizontal and role == Qt.DisplayRole:
            if section == 0:
                return ""

            if section < len(self._headers):
                return self._headers[section]

        return None

    def on_samples_loaded(self):

        self.beginResetModel()
        self.items.clear()

        self.items = self._load_samples_thread.results

        if len(self.items) > 0:
            self._headers = [
                i for i in self.items[0].keys() if i not in ("sample_id", "variant_id")
            ]

        if "classification" not in self.fields:
            self._headers.remove("classification")

        if "valid" not in self.fields:
            self._headers.remove("valid")

        if "valid" in self._headers:
            self._headers.remove("valid")

        if "classification" in self._headers:
            self._headers.remove("classification")

        self.endResetModel()

        # # Save cache
        # self._load_variant_cache[
        #     self._sample_hash
        # ] = self._load_variant_thread.results.copy()

        self._end_timer = time.perf_counter()
        self.elapsed_time = self._end_timer - self._start_timer
        self.load_finished.emit()

    def load(self, variant_id):
        """Start async queries to get sample fields for the selected variant

        Called by:
            - on_change_query() from the view.
            - sort() and setPage() by the model.

        See Also:
            :meth:`on_samples_loaded`
        """
        if self.conn is None:
            return

        if self.is_running():
            LOGGER.debug(
                "Cannot load data. Thread is not finished. You can call interrupt() "
            )
            self.interrupt()

        if "classification" not in self.fields:
            self.fields.append("classification")

        # Create load_func to run asynchronously: load samples
        load_samples_func = partial(
            sql.get_sample_annotations_by_variant,
            variant_id=variant_id,
            fields=self.fields,
            samples=self.selected_samples,
            families=self.selected_families,
            tags=self.selected_tags,
            genotypes=self.selected_genotypes,
            valid=self.selected_valid,
            classification=self.selected_classification,
        )

        # Start the run
        self._start_timer = time.perf_counter()

        # # Create function HASH for CACHE
        # self._sample_hash = hash(load_samples_func.func.__name__ + str(load_samples_func.keywords))

        self.load_started.emit()

        # # Launch the first thread "count" or by pass it using the cache
        # if self._sample_hash in self._load_count_cache:
        #     self._load_variant_thread.results = self._load_count_cache[self._count_hash]
        #     self.on_samples_loaded()
        # else:
        self._load_samples_thread.conn = self.conn
        self._load_samples_thread.start_function(
            lambda conn: list(load_samples_func(conn))
        )

    def sort(self, column: int, order: Qt.SortOrder) -> None:
        self.beginResetModel()

        sorting_key = self.headerData(column, Qt.Horizontal, Qt.DisplayRole)

        # Compare items from self.items based on the sorting key given by the header
        def field_sort(i1, i2):
            # The one of i1 or i2 that is None should always be considered lower
            if i1[sorting_key] is None:
                return -1
            if i2[sorting_key] is None:
                return 1

            if i1[sorting_key] < i2[sorting_key]:
                return -1
            elif i1[sorting_key] == i2[sorting_key]:
                return 0
            else:
                return 1

        self.items = sorted(
            self.items,
            key=cmp_to_key(field_sort),
            reverse=order == Qt.DescendingOrder,
        )
        self.endResetModel()

    def interrupt(self):
        """Interrupt current query if active

        This is a blocking function...

        call interrupt and wait for the error_raised signals ...
        If nothing happen after 1000 ms, by pass and continue
        If I don't use the dead time, it is waiting for an infinite time
        at startup ... Because at startup, loading is called 2 times.
        One time by the register_plugin and a second time by the plugin.show_event
        """

        interrupted = False

        if self._load_samples_thread:
            if self._load_samples_thread.isRunning():
                self._user_has_interrupt = True
                self._load_samples_thread.interrupt()
                self._load_samples_thread.wait(1000)
                interrupted = True

        if interrupted:
            self.interrupted.emit()

    def is_running(self):
        if self._load_samples_thread:
            return self._load_samples_thread.isRunning()
        return False

    def edit(self, row: int, data: dict):
        """Edit current item
        Args:
            row (int): Description
            data (dict): Description
        """

        # change from memory
        self.items[row].update(data)

        # print("EDIT", self.items[row])

        # Persist in SQL
        data["variant_id"] = self.items[row]["variant_id"]
        data["sample_id"] = self.items[row]["sample_id"]
        sql.update_sample_has_variant(self.conn, data)
        self.dataChanged.emit(self.index(row, 0), self.index(row, self.columnCount()))
        self.headerDataChanged.emit(Qt.Vertical, row, row)


class SamplesView(QTableView):
    def __init__(self, parent=None):
        super().__init__(parent)

        self.delegate = FormatterDelegate()
        self.delegate.set_formatter(CutestyleFormatter())

        self.setItemDelegate(self.delegate)

        self.setVerticalHeader(VariantVerticalHeader())

    def paintEvent(self, event: QPaintEvent):
        if self.model().rowCount() == 0:
            painter = QPainter(self.viewport())
            painter.drawText(self.viewport().rect(), Qt.AlignCenter, "No Sample found")

        else:
            super().paintEvent(event)


class ValidationWidget(plugin.PluginWidget):
    """Widget displaying the list of avaible selections.
    User can select one of them to update Query::selection
    """

    ENABLE = True
    REFRESH_STATE_DATA = {"current_variant"}

    def __init__(self, parent=None, conn=None):
        """
        Args:
            parent (QWidget)
            conn (sqlite3.connexion): sqlite3 connexion
        """
        super().__init__(parent)

        self.toolbar = QToolBar()
        self.toolbar.setIconSize(QSize(16, 16))
        self.view = SamplesView()
        self.view.setShowGrid(False)
        self.view.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.view.setSortingEnabled(True)
        self.view.setIconSize(QSize(16, 16))
        self.view.horizontalHeader().setHighlightSections(False)
        self.model = SamplesModel()

        self.error_label = QLabel()
        self.error_label.setStyleSheet(
            "QWidget{{background-color:'{}'; color:'{}'}}".format(
                style.WARNING_BACKGROUND_COLOR, style.WARNING_TEXT_COLOR
            )
        )

        self.field_selector = ChoiceWidget()
        self.field_selector.accepted.connect(self.on_refresh)
        self.sample_selector = ChoiceWidget()
        self.sample_selector.accepted.connect(self.on_refresh)
        self.family_selector = ChoiceWidget()
        self.family_selector.accepted.connect(self.on_refresh)
        self.tag_selector = ChoiceWidget()
        self.tag_selector.accepted.connect(self.on_refresh)
        self.geno_selector = ChoiceWidget()
        self.geno_selector.accepted.connect(self.on_refresh)
        self.valid_selector = ChoiceWidget()
        self.valid_selector.accepted.connect(self.on_refresh)
        self.classification_selector = ChoiceWidget()
        self.classification_selector.accepted.connect(self.on_refresh)

        self.setWindowIcon(FIcon(0xF0A8C))

        self.view.setModel(self.model)

        vlayout = QVBoxLayout()
        vlayout.setContentsMargins(0, 0, 0, 0)
        vlayout.addWidget(self.toolbar)
        vlayout.addWidget(self.view)
        vlayout.addWidget(self.error_label)
        vlayout.setSpacing(0)
        self.setLayout(vlayout)

        self.view.doubleClicked.connect(self._on_double_clicked)
        self.model.error_raised.connect(self.show_error)
        self.model.load_finished.connect(self.on_load_finished)

        self.setup_actions()

    def setup_actions(self):

        # sample action
        sample_action = create_widget_action(self.toolbar, self.sample_selector)
        sample_action.setIcon(FIcon(0xF0013))
        sample_action.setText("Samples ")
        sample_action.setToolTip("Filter by samples")

        # family action
        fam_action = create_widget_action(self.toolbar, self.family_selector)
        fam_action.setIcon(FIcon(0xF0B58))
        fam_action.setText("Family")
        fam_action.setToolTip("Filter by family")

        # tags action
        tag_action = create_widget_action(self.toolbar, self.tag_selector)
        tag_action.setIcon(FIcon(0xF04FC))
        tag_action.setText("Tags ")
        tag_action.setToolTip("Filter by tags")

        # geno action
        geno_action = create_widget_action(self.toolbar, self.geno_selector)
        geno_action.setIcon(FIcon(0xF0902))
        geno_action.setText("Genotype")
        geno_action.setToolTip("Filter by genotype")

        # valid lock/unlock action
        valid_action = create_widget_action(self.toolbar, self.valid_selector)
        valid_action.setIcon(FIcon(0xF139A))
        valid_action.setText("Validation")
        valid_action.setToolTip("Filter by sample Validation")

        # classification action
        classification_action = create_widget_action(
            self.toolbar, self.classification_selector
        )
        classification_action.setIcon(FIcon(0xF00C1))
        classification_action.setText("Classification")
        classification_action.setToolTip("Filter by variant classification on sample")

        # Clear filters
        self.toolbar.addAction(
            FIcon(0xF01FE), self.tr("Clear all filters"), self._on_clear_filters
        )

        # Spacer
        spacer = QWidget()
        spacer.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.toolbar.addWidget(spacer)

        # Fields to display
        field_action = create_widget_action(self.toolbar, self.field_selector)
        field_action.setIcon(FIcon(0xF0835))
        field_action.setText("Fields")
        field_action.setToolTip("Select fields to display")

        # Presets list
        self.preset_menu = QMenu()
        self.preset_button = QPushButton()
        self.preset_button.setToolTip(self.tr("Presets"))
        self.preset_button.setIcon(FIcon(0xF035C))
        self.preset_button.setMenu(self.preset_menu)
        self.preset_button.setFlat(True)
        self.toolbar.addWidget(self.preset_button)

        self.load_presets()

    def load_presets(self):

        self.preset_menu.clear()

        config = Config("samples")

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

    def delete_preset(self):
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

        config = Config("samples")
        presets = config["presets"]
        if name in presets:
            del presets[name]
            config.save()
            self.load_presets()

    def save_preset(self):
        name, success = QInputDialog.getText(
            self, self.tr("Create new preset"), self.tr("Preset name:")
        )

        if success and name:
            config = Config("samples")
            presets = config["presets"] or {}
            # if preset name exists ...
            if name in presets:
                ret = QMessageBox.warning(
                    self,
                    self.tr("Overwrite preset"),
                    self.tr(
                        f"Preset {name} already exists. Do you want to overwrite it ?"
                    ),
                    QMessageBox.Yes | QMessageBox.No,
                )

                if ret == QMessageBox.No:
                    return

            presets[name] = self.model.fields
            config["presets"] = presets

            config.save()

        self.load_presets()

    def _on_select_preset(self):
        config = Config("samples")
        presets = config["presets"]
        key = self.sender().data()
        if key in presets:
            self.field_selector.set_checked(presets[key])

        self.on_refresh()

    def _on_double_clicked(self):
        self._show_sample_variant_dialog()

    def contextMenuEvent(self, event: QContextMenuEvent):

        menu = QMenu(self)
        var_name = (
            self.current_variant["chr"]
            + ":"
            + self.current_variant["ref"]
            + ">"
            + self.current_variant["alt"]
        )
        if len(var_name) > 25:
            var_name = var_name[0:15] + " ... " + var_name[-10:]
        menu.addSection("Variant " + var_name)

        # Validation
        row = self.view.selectionModel().currentIndex().row()
        sample = self.model.item(row)
        valid_form = True
        valid_form_text = "Validation"
        if style.SAMPLE_CLASSIFICATION[sample["valid"]].get("lock"):
            valid_form = False
            valid_form_text = "Validation locked"

        cat_menu = menu.addMenu(valid_form_text)
        cat_menu.setEnabled(valid_form)

        for key, value in SAMPLE_VARIANT_CLASSIFICATION.items():
            # action = cat_menu.addAction(value["name"])
            action = cat_menu.addAction(
                FIcon(value["icon"], value["color"]), value["name"]
            )
            action.setData(key)
            action.triggered.connect(self._on_classification_changed)

        menu.addMenu(cat_menu)
        menu.addAction("Edit variant validation ...", self._show_sample_variant_dialog)

        menu.addSection("Sample")
        menu.addAction(QIcon(), "Edit sample ...", self._show_sample_dialog)

        menu.addAction(QIcon(), "Add a filter based on selected sample(s)", self.on_add_filter)

        menu.addAction(
            QIcon(), "Select a source from selected sample(s)", self.on_select_source
        )

        menu.addAction(
            QIcon(), "Create a source from selected sample(s)", self.on_add_source
        )

        menu.addAction(
            QIcon(), "Create a source from each selected sample", self.on_add_each_source
        )

        menu.exec_(event.globalPos())

    def _show_sample_dialog(self):

        row = self.view.selectionModel().currentIndex().row()
        sample = self.model.item(row)
        if sample:

            dialog = SampleDialog(self._conn, sample["sample_id"])

            if dialog.exec_() == QDialog.Accepted:
                # self.load_all_filters()
                self.on_refresh()

    def _show_sample_variant_dialog(self):

        row = self.view.selectionModel().currentIndex().row()
        sample = self.model.item(row)
        if sample:

            dialog = SampleVariantDialog(
                self._conn, sample["sample_id"], self.current_variant["id"]
            )

            if dialog.exec_() == QDialog.Accepted:
                # self.load_all_filters()
                self.on_refresh()

    def _toggle_column(self, col: int, show: bool):
        """hide/show columns"""
        if show:
            self.view.showColumn(col)
        else:
            self.view.hideColumn(col)

    def _on_classification_changed(self):
        """triggered from menu"""
        if not self.sender():
            return

        value = self.sender().data()
        text = self.sender().text()

        row = self.view.selectionModel().currentIndex().row()
        self.model.edit(row, {"classification": value})

    def _on_clear_filters(self):

        self.sample_selector.uncheck_all()
        self.family_selector.uncheck_all()
        self.geno_selector.uncheck_all()
        self.valid_selector.uncheck_all()
        self.classification_selector.uncheck_all()
        self.tag_selector.uncheck_all()

        self.on_refresh()

    def _create_filters(self, copy_existing_filters: bool = True, sample_list: list = []) -> dict:
        """
        The function creates a dictionary of filters based on a list of filters and existing filters (or not)

        Args:
            copy_existing_filters (bool, optional)

        Returns:
            dict: A dictionary of filters
        """

        indexes = self.view.selectionModel().selectedRows()
        if copy_existing_filters:
            filters = copy.deepcopy(self.mainwindow.get_state_data("filters"))
        else:
            filters = {}

        if not filters:
            root = "$or"
            filters["$or"] = []

        else:
            root = list(filters.keys())[0]
            filters[root] = [
                i for i in filters[root] if not list(i.keys())[0].startswith("samples")
            ]

        for index in indexes:
            # sample_name = index.siblingAtColumn(1).data()
            sample_name = index.siblingAtColumn(0).data()
            # Add sample in filters
            if sample_name and (sample_name in sample_list or sample_list == []):
                key = f"samples.{sample_name}.gt"
                condition = {key: {"$gte": 1}}
                filters[root].append(condition)

        return filters

    def on_add_source(self, input_name=None, select=False, overwrite=None, sample_list=[]):
        """
        This function is called when the user clicks on the "Add Source" button in the "Source" tab

        Args:
            input_name (string, optional): source name
            select (bool, optional): if source selected after creation
            overwrite (bool, optional): if source created/overwrite
            sample_list (list, optional): list of sample to add in the source

        Returns:
            None
        """

        # Create filter from selected list or a sample list (if not empty)
        filters=self._create_filters(False, sample_list=sample_list)

        # Created sources
        # Get sources
        sources=sql.get_selections(self._conn)
        # Create list and dict of source information 
        sources_name_list=[]
        sources_query_list=[]
        sources_query_dict={}
        for s in sources:
            sources_name_list.append(s["name"])
            sources_query_list.append(s["query"])
            sources_query_dict[s["query"]]=s["name"]

        # Query source
        source_query = qb.build_vql_query(fields=["id"], source="variants", filters=filters)
 
        # Selected samples
        indexes = self.view.selectionModel().selectedRows()

        # Input source name if uniq sample and for selection
        if select and len(indexes)==1: 
            input_name=indexes[0].siblingAtColumn(0).data()

        # Source name
        if input_name != None:
            # source name is in input
            name=input_name
            success=True
        else:
            # Auto detection of source name
            if len(indexes)==1:
                # source name is the name of the uniq sample
                source_name=indexes[0].siblingAtColumn(0).data()
            elif source_query in sources_query_list:
                # source name is found by query
                source_name=sources_query_dict[source_query]
            else:
                # source name is a new source (not detected)
                source_name="new source name"
            # Check if source name already created/exists
            if source_name in sources_name_list:
                msg=f"""\n(source '{source_name}' already exists)"""
            else:
                msg=""
            # Ask for source name
            name, success = QInputDialog.getText(
                self, self.tr("Source Name"), self.tr("Get a source name "+msg),
                text=source_name
            )
            
        # Success of source name
        if success and name:

            # Check if need to overwrite source
            if name in sources_name_list and not select and overwrite == None:
                # Ask for overwriting
                ret = QMessageBox.warning(
                    self,
                    self.tr("Overwrite source"),
                    self.tr(
                        f"Source {name} already exists. Do you want to overwrite it?"
                    ),
                    QMessageBox.Yes | QMessageBox.No,
                )
                if ret == QMessageBox.No:
                    # Exit if not overwrite source
                    overwrite=False
                else:
                    # Overwrite source
                    overwrite=True
                

            # Check if create/overwrite source 
            if name not in sources_name_list or (not select and overwrite):
                # Create/overwrite source 
                sql.insert_selection_from_source(
                    self._conn, name, "variants", filters
                )

            # Check for selecting source
            if input_name == None and not select:
                msg = QMessageBox(icon=QMessageBox.Warning)
                msg.setText(self.tr("Do you want to use this source?"))
                msg.setStandardButtons(QMessageBox.Yes | QMessageBox.No)

            # Check if select source
            if select or (input_name == None and msg.exec_() == QMessageBox.Yes):
                # Select source
                self.mainwindow.set_state_data("source", name)

            # Check if refresh source editor
            if "source_editor" in self.mainwindow.plugins:
                # Refresh source editor
                self.mainwindow.refresh_plugin("source_editor")

            # Return name
            return None

        else:

            # Return None
            return None

    def on_select_source(self):
        """
        This function is called when the user clicks on the "Add Source" button in the "Source" tab
        """

        # Created sources
        sources=sql.get_selections(self._conn)
        sources_name_list=[]
        sources_query_list=[]
        sources_query_dict={}
        for s in sources:
            sources_name_list.append(s["name"])
            sources_query_list.append(s["query"])
            sources_query_dict[s["query"]]=s["name"]

        # Query source
        source_query = qb.build_vql_query(fields=["id"], source="variants", filters=self._create_filters(False))

        # Search for existing source name
        source_name=None
        if source_query in sources_query_list:
            source_name=sources_query_dict[source_query]

        self.on_add_source(select=True, input_name=source_name)

    def on_add_each_source(self):
        """
        This function is called when the user clicks on the "Add Source" button in the "Source" tab
        """

        # Selected samples
        indexes = self.view.selectionModel().selectedRows()

        # Created sources
        sources=sql.get_selections(self._conn)
        sources_list=[]
        for s in sources:
            sources_list.append(s["name"])

        # Search for existing source name
        existing_sources=[]
        for index in indexes:
            name=index.siblingAtColumn(0).data()
            if name in sources_list:
                existing_sources.append(name)

        # Overwrite option
        overwrite=False
        if len(existing_sources)>0:
            msg = QMessageBox(icon=QMessageBox.Warning)
            msg.setText(self.tr(f"""Do you want to overwrite existing sources?\n{existing_sources}"""))
            msg.setStandardButtons(QMessageBox.Yes | QMessageBox.No)
            if msg.exec_() == QMessageBox.Yes:
                overwrite=True

        # Add each source
        for index in indexes:
            name=index.siblingAtColumn(0).data()
            self.on_add_source(input_name=name, overwrite=overwrite, sample_list=[name])
            

    def on_add_filter(self):
        """
        This function is called when the user clicks on the "Add Filter" button
        """

        self.mainwindow.set_state_data("filters", self._create_filters())
        self.mainwindow.refresh_plugins(sender=self)

    def on_open_project(self, conn):
        self._conn = conn
        self.model.conn = conn
        self.load_all_filters()

    def _is_selectors_checked(self):
        """Return False if selectors is not checked"""

        return (
            self.sample_selector.checked()
            or self.family_selector.checked()
            or self.tag_selector.checked()
        )

    def load_all_filters(self):
        self.load_samples()
        self.load_tags()
        self.load_fields()
        self.load_family()
        self.load_genotype()
        self.load_valid()
        self.load_classification()

    def load_samples(self):

        self.sample_selector.clear()
        for sample in sql.get_samples(self._conn):
            self.sample_selector.add_item(
                FIcon(0xF0B55), sample["name"], data=sample["name"]
            )

    def load_tags(self):

        self.tag_selector.clear()
        if Config("validation")["sample_tags"] != None:
            for tag in [tag["name"] for tag in Config("validation")["sample_tags"]]:
                self.tag_selector.add_item(FIcon(0xF04FD), tag, data=tag)

    def load_fields(self):
        self.field_selector.clear()
        for field in sql.get_field_by_category(self._conn, "samples"):
            if field["name"] != "classification":
                self.field_selector.add_item(
                    FIcon(0xF0835),
                    field["name"],
                    field["description"],
                    data=field["name"],
                )

    def load_family(self):
        self.family_selector.clear()
        for fam in sql.get_samples_family(self._conn):
            self.family_selector.add_item(FIcon(0xF036E), fam, data=fam)

    def load_genotype(self):
        self.geno_selector.clear()

        for key, value in GENOTYPE.items():
            self.geno_selector.add_item(FIcon(value["icon"]), value["name"], data=key)

    def load_valid(self):
        self.valid_selector.clear()

        for key, value in SAMPLE_CLASSIFICATION.items():
            self.valid_selector.add_item(FIcon(value["icon"]), value["name"], data=key)

    def load_classification(self):
        self.classification_selector.clear()

        for key, value in SAMPLE_VARIANT_CLASSIFICATION.items():
            self.classification_selector.add_item(
                FIcon(value["icon"]), value["name"], data=key
            )

    def on_refresh(self):

        # Get fields
        self.current_variant = self.mainwindow.get_state_data("current_variant")
        variant_id = self.current_variant["id"]

        self.model.fields = [i["name"] for i in self.field_selector.selected_items()]

        self.model.selected_samples = [
            i["name"] for i in self.sample_selector.selected_items()
        ]
        self.model.selected_families = [
            i["name"] for i in self.family_selector.selected_items()
        ]
        self.model.selected_tags = [
            i["name"] for i in self.tag_selector.selected_items()
        ]
        self.model.selected_genotypes = [
            i["data"] for i in self.geno_selector.selected_items()
        ]
        self.model.selected_valid = [
            i["data"] for i in self.valid_selector.selected_items()
        ]
        self.model.selected_classification = [
            i["data"] for i in self.classification_selector.selected_items()
        ]

        self.model.load(variant_id)

        # self.view.horizontalHeader().setSectionResizeMode(
        #     0, QHeaderView.ResizeToContents
        # )
        # self.view.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeToContents)
        # self.view.horizontalHeader().setSectionResizeMode(0, QHeaderView.Minimum)
        # self.view.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)

    def show_error(self, message):
        self.error_label.setText(message)
        self.error_label.setVisible(bool(message))

    def on_load_finished(self):
        self.show_error("")

        self.view.horizontalHeader().setSectionResizeMode(QHeaderView.Interactive)


# self.view.horizontalHeader().setSectionResizeMode(
#     0, QHeaderView.ResizeToContents
# )
# self.view.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)


if __name__ == "__main__":

    import sqlite3
    import sys
    from PySide6.QtWidgets import QApplication

    app = QApplication(sys.argv)

    # conn = sqlite3.connect("/home/sacha/test3.db")
    conn = sqlite3.connect("C:/Users/Ichtyornis/Projects/cutevariant/test2.db")
    conn.row_factory = sqlite3.Row

    view = ValidationWidget()
    view.on_open_project(conn)
    view.show()

    app.exec()
