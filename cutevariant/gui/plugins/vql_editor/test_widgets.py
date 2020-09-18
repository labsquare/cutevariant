# from cutevariant.gui.plugins.editor.widgets import EditorWidget
# from cutevariant.core.importer import import_file
# import sqlite3


# def test_vql_editor(qtbot):
# conn = sqlite3.connect(":memory:")
# import_file(conn, "examples/test.vcf")

# editor = EditorWidget()
# editor.conn = conn

# editor.set_vql("SELECT chr, pos FROM variants WHERE pos > 3")

# with qtbot.waitSignal(editor.executed):
# editor.run_vql()
# assert editor.columns == ["chr","pos"]
# assert editor.selection == "variants"
# assert editor.filters ==  {"AND": [ {"field": "pos", "operator": ">", "value": 3}]}
