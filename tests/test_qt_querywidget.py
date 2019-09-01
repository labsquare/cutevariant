
import pytest
import sqlite3 
from cutevariant.core.importer import import_file
from cutevariant.core import sql
#from cutevariant.gui.querywidget import QueryModel, QueryWidget

@pytest.fixture
def conn():
    conn = sqlite3.connect(":memory:")
    import_file(conn, "examples/test.snpeff.vcf")
    return conn


# def test_query_model(conn,qtmodeltester):
#     # Test without nested tree 
#     model = QueryModel(conn)
#     model.columns = ["chr","pos","ref","alt"]
#     model.load()
#     #qtmodeltester.check(model)

#     assert model.rowCount() == sql.get_variants_count(conn)
#     assert model.columnCount() == 4 + 1  # 4 annotation + 1 child count

#     # Test pagination 
#     model.limit = 6
#     model.page = 0
#     model.load()
#     assert model.rowCount() == 6

#     model.page = 1 
#     model.load()
#     assert model.rowCount() == 5

#     # Test content
#     index = model.index(0,0) 
#     assert model.variant(index) == (10,11,125005,"T","A",1)
    


    # Test model content 

    # Test with nested tree by adding gene
    #model.columns = ["chr","pos","ref","alt", "gene"]
    #model.load()
    #qtmodeltester.check(model)  ?? TODO improve this 

    



    
