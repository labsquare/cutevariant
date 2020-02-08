import pytest

from cutevariant.core import sql
from cutevariant.core.reader.bedreader import BedTool
from .utils import table_exists, table_count

FIELDS = [
    {"name": "chr", "category": "variants","type": "text", "description": "chromosome", },
    {"name": "pos", "category": "variants", "type": "int", "description": "position"},
    {"name": "ref", "category": "variants", "type": "text", "description": "reference"},
    { "name": "alt", "category": "variants","type": "text","description": "alternative",},
    {"name": "extra1", "category": "variants","type": "float","description": "annotation 1",},
    {"name": "extra2","category": "variants", "type": "int","description": "annotation 2",},
    {"name": "gene","category": "annotations","type": "str","description": "gene name",},
    {"name": "transcript","category": "annotations","type": "str","description": "transcript name"},
    {"name": "gt","category": "samples","type": "int","description": "sample genotype"},
    {"name": "dp","category": "samples","type": "int","description": "sample dp"}
]

SAMPLES = ["sacha","boby"]

VARIANTS = [
    {"chr": "chr1", "pos": 10, "ref": "G", "alt": "A", "extra1": 10, "extra2": 100,
    "annotations":[{"gene": "gene1", "transcript": "transcript1"},{"gene": "gene1", "transcript": "transcript2"}],
    "samples": [{"name": "sacha", "gt": 1, "dp": 70},{"name": "boby", "gt": 1, "dp": 10}]
    },

    {"chr": "chr1", "pos": 45, "ref": "G", "alt": "A", "extra1": 20, "extra2": 100,
    "annotations":[{"gene": "gene2", "transcript": "transcript2"}],
    "samples": [{"name": "sacha", "gt": 0, "dp": 30},{"name": "boby", "gt": 0, "dp": 70}]
    }
]


FILTERS = {
            "AND": [
                {"field": "chr", "operator": "=", "value": "chr1"},
                {
                    "OR": [
                        {"field": "gene", "operator": "=", "value": "gene1"},
                        {"field": "pos", "operator": "=", "value": 10},
                    ]
                },
            ]
        }


@pytest.fixture
def conn():
    conn = sql.get_sql_connexion(":memory:")
    sql.create_project(conn, "test","hg19")
    sql.create_table_fields(conn)
    sql.insert_many_fields(conn, FIELDS)
    sql.create_table_selections(conn)
    sql.create_table_annotations(conn, sql.get_field_by_category(conn,"annotations"))
    sql.create_table_samples(conn,sql.get_field_by_category(conn,"samples"))
    sql.insert_many_samples(conn, SAMPLES)
    sql.create_table_variants(conn, sql.get_field_by_category(conn,"variants"))
    sql.insert_many_variants(conn, VARIANTS)
    return conn

def test_create_connexion(conn):
    assert conn != None

def test_get_table_of_column(conn):
    
    assert sql.QueryBuilder(conn).get_table_of_column("gene") == "annotations"
    assert sql.QueryBuilder(conn).get_table_of_column("annotations.gene") == "annotations"
    assert sql.QueryBuilder(conn).get_table_of_column("chr") == "variants"
    assert sql.QueryBuilder(conn).get_table_of_column("variants.chr") == "variants"
    assert sql.QueryBuilder(conn).get_table_of_column(("genotype","TUMOR","af")) == "samples"
    
def test_headers(conn):

    predicted_headers = ["chr","pos","ref","alt"]
    builder = sql.QueryBuilder(conn, columns = predicted_headers)
    assert list(builder.headers()) == ["id"] + predicted_headers

def test_filters_to_flat(conn):
    """ convert filters to flatten list """
    names = list([i["field"] for i in sql.QueryBuilder(conn)._filters_to_flat(FILTERS)])
    assert names == ["chr","gene","pos"]

def test_filters_to_sql(conn):
    """ convert filters to sql where clause """
    assert sql.QueryBuilder(conn)._filters_to_sql(FILTERS) == "(`variants`.`chr` = 'chr1' AND (`annotations`.`gene` = 'gene1' OR `variants`.`pos` = 10))"

@pytest.mark.parametrize("args,expected", 
[
    (
        {},
        "SELECT `variants`.`id`,`variants`.`chr`,`variants`.`pos`,`variants`.`ref`,`variants`.`alt` FROM variants LIMIT 20 OFFSET 0"
    ),
    (
        {"columns": ["chr","pos","gene"]},
        "SELECT `variants`.`id`,`variants`.`chr`,`variants`.`pos`,`annotations`.`gene` FROM variants LEFT JOIN annotations ON annotations.variant_id = variants.id LIMIT 20 OFFSET 0"
    ),
    (
        {"columns": ["chr","pos"], "filters": FILTERS},
        ("SELECT `variants`.`id`,`variants`.`chr`,`variants`.`pos` " 
         "FROM variants LEFT JOIN annotations ON annotations.variant_id = variants.id "
         "WHERE (`variants`.`chr` = 'chr1' AND (`annotations`.`gene` = 'gene1' OR `variants`.`pos` = 10)) LIMIT 20 OFFSET 0")
    ),
    (
        {"columns": ["chr","pos"], "filters": FILTERS, "selection" : "other"},
        ("SELECT `variants`.`id`,`variants`.`chr`,`variants`.`pos` FROM variants "
         "LEFT JOIN annotations ON annotations.variant_id = variants.id "
         "INNER JOIN selection_has_variant sv ON sv.variant_id = variants.id "
         "INNER JOIN selections s ON s.id = sv.selection_id AND s.name = 'other' "
         "WHERE (`variants`.`chr` = 'chr1' AND (`annotations`.`gene` = 'gene1' OR `variants`.`pos` = 10)) LIMIT 20 OFFSET 0")
    ),
    (
        {"columns": ["chr","pos", ("genotype","boby","gt")]},
        ("SELECT `variants`.`id`,`variants`.`chr`,`variants`.`pos`,`gt_boby`.`gt` AS `gt_boby.gt` FROM variants "
         "LEFT JOIN sample_has_variant `gt_boby` ON `gt_boby`.variant_id = variants.id "
         "AND `gt_boby`.sample_id = 2 LIMIT 20 OFFSET 0")
    )
])
def test_build_variant_query(conn, args, expected):
    """ Test get variants with differents parameters """ 
    assert sql.QueryBuilder(conn, **args).sql() == expected


def test_select_tree(conn):
    args = {}
    args["columns"] = ["chr","pos","ref","gene"]
    variants = list(sql.QueryBuilder(conn,**args).trees()) 
    assert len(variants) == 2

def test_select_children(conn):
        assert len(list(sql.QueryBuilder(conn).children(variant_id = 1))) == len(VARIANTS[0]["annotations"])
        assert len(list(sql.QueryBuilder(conn).children(variant_id = 2))) == len(VARIANTS[1]["annotations"])


@pytest.mark.parametrize("args,expected",
[
    (
        {"columns": ["chr","pos"]},
        "SELECT chr,pos FROM variants"
    ),
    (
        {"columns": ["chr","pos",("genotype","boby","gt")]},
        "SELECT chr,pos,genotype(\"boby\").gt FROM variants"
    ),
    (
        {
            "columns": ["chr","pos"],
            "filters":{"AND": [{"field": "chr", "operator": ">", "value": 4}]}
        },
        "SELECT chr,pos FROM variants WHERE chr > 4"
    ),
    (
        {
            "columns": ["chr","pos"],
            "filters":{"AND": [{"field": ("genotype","boby","gt"), "operator":"=" , "value": 1}]}
        },
        "SELECT chr,pos FROM variants WHERE genotype(\"boby\").gt = 1"
    )
])
def test_to_vql(conn, args, expected):
    selector = sql.QueryBuilder(conn, **args)
    assert selector.vql() == expected






def test_column_to_sql(conn):

    selector = sql.QueryBuilder(conn)
    assert selector.column_to_sql("variants.id") == "`variants`.`id`"
    assert selector.column_to_sql("annotations.id") == "`annotations`.`id`"
    assert selector.column_to_sql("chr") == "`variants`.`chr`"
    assert selector.column_to_sql("gene") == "`annotations`.`gene`"
    assert selector.column_to_sql(("genotype","boby","gt")) == "`gt_boby`.`gt` AS `gt_boby.gt`"


def test_filters_to_flat(conn):
    """ convert filters to flatten list """
    names = list([i["field"] for i in sql.QueryBuilder(conn)._filters_to_flat(FILTERS)])
    assert names == ["chr","gene","pos"]

def test_filters_to_sql(conn):
    """ convert filters to sql where clause """
    assert sql.QueryBuilder(conn)._filters_to_sql(FILTERS) == "(`variants`.`chr` = 'chr1' AND (`annotations`.`gene` = 'gene1' OR `variants`.`pos` = 10))"

def test_from_vql(conn):
    q  = sql.QueryBuilder(conn)
    q.set_from_vql("SELECT chr, pos FROM variants WHERE pos > 3 ")
    assert q.columns == ["chr","pos"]
    assert q.selection == "variants"
    assert q.filters == {'AND':[{'field': 'pos', 'operator': '>', 'value': 3}]}


def test_count(conn):
    assert sql.QueryBuilder(conn).count() == 2

def test_save(conn):
    selector = sql.QueryBuilder(conn)
    selector.filters = {"AND": [ {"field": "pos", "operator": "=", "value": 45}]}
    selector.save("denovo")
    selections = list(sql.get_selections(conn))

    assert selections[0]["name"] == "variants"
    assert selections[1]["name"] == "denovo"
    assert selector.count() == 1

    selector.selection = "denovo"
    selector.filters = None
    assert selector.count() == 1

