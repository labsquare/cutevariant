from PySide2.QtWidgets import * 
from PySide2.QtCore import * 

from cutevariant.core.importer import import_file
from cutevariant.gui.plugins.columns.widget import ColumnsModel, ColumnsWidget
import sqlite3


def test_columns_model(qtbot):
    conn = sqlite3.connect(":memory:")
    import_file(conn, "examples/test.vcf")
    
    model = ColumnsModel(conn)
    model.load()

    # assert model.rowCount(QModelIndex()) == 2

    # first_root = model.index(0,0, QModelIndex())
    # second_root = model.index(1,0, QModelIndex())

    # assert first_root.data(Qt.DisplayRole) == "variants"
    # assert second_root.data(Qt.DisplayRole) == "samples"
    
    # assert model.rowCount(first_root) == 30

    # # model.columns is a property : test setter and getter 
    # # ensure itemChanged is not emited because it will raise an infinite loop with query_widget
    # with qtbot.assertNotEmitted(model.itemChanged):
    #     checked_columns = ["chr","pos","ref","alt"]
    #     model.columns = checked_columns
    #     assert model.columns == checked_columns

    #qtmodeltester.check(model)

def test_columns_widget(qtbot):
    conn = sqlite3.connect(":memory:")
    import_file(conn, "examples/test.vcf")

    view = ColumnsWidget()
    view.conn = conn 

    checked_columns = ["chr","pos","ref","alt"]

    with qtbot.waitSignal(view.changed):
        # get first level index 
        parent_index = view.model.index(0,0,QModelIndex())
        parent_name = parent_index.data(Qt.DisplayRole)
        assert parent_name == "variants"

        # get first columns ( 'chr' )
        chr_item = view.model.itemFromIndex(view.model.index(0,0,parent_index))
        assert chr_item.text() == "chr"
        # check the column. It must raise the signal changed
        chr_item.setCheckState(Qt.Checked)
        # get checked columns 
        assert view.columns == ["chr"]
        

        


  





    




    