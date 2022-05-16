from poc.harmonizome import HarmonizomeWordsetDialog
from tests import utils
import pytest

# Qt imports
from PySide6 import QtCore, QtWidgets, QtGui

from cutevariant.gui.plugins.harmonizome_wordset import dialogs
from cutevariant.core import sql


# DO NOT TEST ... TOO LONG.. IT REQUIRED DOWNLOAD ...

# def test_hz_model_load(qtmodeltester, qtbot):
#     dataset_model = dialogs.HZDataSetModel()
#     dataset_model.conn = utils.create_conn()

#     # This test needs Internet connection
#     with qtbot.waitSignal(dataset_model.finished, timeout=5000) as blocker:
#         dataset_model.load()
#     qtmodeltester.check(dataset_model)

#     # Harmonizome currently references 114 databases
#     # assert dataset_model.rowCount() == 114

#     geneset_model = dialogs.HZGeneSetModel()

#     filter_ = QtCore.QSortFilterProxyModel()
#     filter_.setSourceModel(dataset_model)
#     filter_.setFilterRegularExpression("HPO")

#     # There is exactly one database named HPO
#     assert filter_.rowCount() == 1

#     db_endpoint = filter_.index(0, 0, QtCore.QModelIndex()).data(QtCore.Qt.UserRole)
#     db_name = filter_.index(0, 0, QtCore.QModelIndex()).data(QtCore.Qt.DisplayRole)

#     assert "HPO+Gene-Disease+Associations" in db_endpoint

#     with qtbot.waitSignal(geneset_model.finished, timeout=5000):
#         geneset_model.load(db_endpoint, db_name)

#     assert geneset_model.rowCount() > 0
#     qtmodeltester.check(geneset_model)

#     gene_model = dialogs.HZGeneModel()
#     for x in (1, 10, 100):
#         if x < geneset_model.rowCount():
#             selected_geneset = (
#                 geneset_model.index(x).data(QtCore.Qt.UserRole),
#                 geneset_model.index(x).data(QtCore.Qt.DisplayRole),
#             )
#             with qtbot.waitSignal(gene_model.finished, timeout=5000):
#                 gene_model.load(*selected_geneset)

#             # Every geneset has at least one gene
#             assert gene_model.rowCount() > 0
#             print(gene_model.rowCount())

#     qtmodeltester.check(gene_model)


# def test_hz_gene_selection(qtbot):

#     conn = utils.create_conn()
#     dlg: HarmonizomeWordsetDialog = dialogs.HarmonizomeWordsetDialog(conn)
#     qtbot.addWidget(dlg)

#     # Wait for databases to load
#     with qtbot.waitSignal(dlg.harmonizome_widget.dataset_model.finished):
#         qtbot.keyClicks(dlg.harmonizome_widget.dataset_view.search_edit, "HPO")

#     # HPO was searched for in the search bar, and we know there is only one database named HPO
#     assert dlg.harmonizome_widget.dataset_view.tableview.model().rowCount() == 1

#     # Before clicking on HPO, the geneset model must be empty
#     assert dlg.harmonizome_widget.geneset_model.rowCount() == 0
