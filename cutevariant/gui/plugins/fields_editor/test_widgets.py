
from cutevariant.gui.plugins.columns.widgets import ColumnsModel
from cutevariant.core.importer import import_reader
from cutevariant.core.readerfactory import create_reader
import sqlite3

def test_model(qtbot, qtmodeltester):


    conn = sqlite3.connect(":memory:")

    with create_reader("examples/test.snpeff.vcf") as reader: 
        import_reader(conn, reader)

  
    model = ColumnsModel(conn)
    model.load()
    #qtmodeltester.check(model)
    model.columns = ["chr","pos"]
    assert model.columns == ["chr","pos"]

    with qtbot.assertNotEmitted(model.itemChanged):
        model.columns = ["chr","pos","ref"]


