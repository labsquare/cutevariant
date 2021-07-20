from poc.harmonizome import HarmonizomeWordsetDialog
from tests import utils
import pytest

# Qt imports
from PySide2 import QtCore, QtWidgets, QtGui

from cutevariant.gui.plugins.harmonizome_wordset import dialogs
from cutevariant.core import sql


@pytest.fixture
def conn():
    return utils.create_conn()


def test_hz_model_load(qtmodeltester, qtbot, conn):
    dataset_model = dialogs.HZDataSetModel()
    dataset_model.conn = conn

    # This test needs Internet connection
    with qtbot.waitSignal(dataset_model.finished, timeout=5000) as blocker:
        dataset_model.load()
    qtmodeltester.check(dataset_model)

    # Harmonizome currently references 114 databases
    assert dataset_model.rowCount() == 114

    geneset_model = dialogs.HZGeneSetModel()

    filter_ = QtCore.QSortFilterProxyModel()
    filter_.setSourceModel(dataset_model)
    filter_.setFilterRegExp("HPO")

    # There is exactly one database named HPO
    assert filter_.rowCount() == 1

    db_endpoint = filter_.index(0, 0, QtCore.QModelIndex()).data(QtCore.Qt.UserRole)
    db_name = filter_.index(0, 0, QtCore.QModelIndex()).data(QtCore.Qt.DisplayRole)

    assert "HPO+Gene-Disease+Associations" in db_endpoint

    with qtbot.waitSignal(geneset_model.finished, timeout=5000):
        geneset_model.load(db_endpoint, db_name)

    assert geneset_model.rowCount() > 0
    qtmodeltester.check(geneset_model)

    gene_model = dialogs.HZGeneModel()
    for x in (1, 10, 100):
        if x < geneset_model.rowCount():
            selected_geneset = (
                geneset_model.index(x).data(QtCore.Qt.UserRole),
                geneset_model.index(x).data(QtCore.Qt.DisplayRole),
            )
            with qtbot.waitSignal(gene_model.finished, timeout=5000):
                gene_model.load(*selected_geneset)

            # Every geneset has at least one gene
            assert gene_model.rowCount() > 0
            print(gene_model.rowCount())

    qtmodeltester.check(gene_model)


def test_hz_gene_selection(qtbot, conn):
    dlg: HarmonizomeWordsetDialog = dialogs.HarmonizomeWordsetDialog(conn)
    qtbot.addWidget(dlg)

    # Wait for databases to load
    with qtbot.waitSignal(dlg.harmonizome_widget.dataset_model.finished):
        qtbot.keyClicks(dlg.harmonizome_widget.dataset_view.search_edit, "HPO")

    # HPO was searched for in the search bar, and we know there is only one database named HPO
    assert dlg.harmonizome_widget.dataset_view.tableview.model().rowCount() == 1

    # Before clicking on HPO, the geneset model must be empty
    assert dlg.harmonizome_widget.geneset_model.rowCount() == 0

    # --------------------------------------------------------------------------------Doesn't click on HPO item...
    # hpo_index = dlg.harmonizome_widget.dataset_view.tableview.model().index(
    #     0, 0, QtCore.QModelIndex()
    # )
    # hpo_rect = dlg.harmonizome_widget.dataset_view.tableview.visualRect(
    #     dlg.harmonizome_widget.dataset_view.proxy.mapToSource(hpo_index)
    # )
    # with qtbot.waitSignal(dlg.harmonizome_widget.geneset_model.finished):
    #     # Click on HPO
    #     qtbot.mouseClick(
    #         dlg.harmonizome_widget.dataset_view.tableview,
    #         QtCore.Qt.LeftButton,
    #         pos=QtCore.QPoint(hpo_rect.x() + 5, hpo_rect.y() + 12),
    #     )
    # After clicking on HPO, assume that there is at least a hundred genesets (this is HPO, at last!)
    # assert dlg.harmonizome_widget.geneset_model.rowCount() > 100
