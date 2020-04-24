
import pytest 
from cutevariant.core import querybuilder 


DEFAULT_TABLES = {
    "chr": "variants",
    "pos": "variants",
    "ref": "variants",
    "alt": "variants",
    "gene": "annotations",
    "gt": "sample_has_variant"
    }


SAMPLES_ID = {
    "TUMOR": 1, 
    "NORMAL": 2
    }

def test_filter_to_flat():
    filters = {'AND': [
        {'field': 'ref', 'operator': '=', 'value': "A"},
        {'field': 'alt', 'operator': '=', 'value': "C"}
        ]}



def test_field_function_to_sql():
    assert querybuilder.field_function_to_sql(("genotype", "boby", "GT"))  == "`genotype_boby`.`GT`"
    assert querybuilder.field_function_to_sql(("phenotype", "sacha", ""))  == "`phenotype_sacha`"
    assert querybuilder.field_function_to_sql(("genotype", "sacha", "gt"), use_as =True)  == "`genotype_sacha`.`gt` AS 'genotype.sacha.gt'"


def test_fields_to_sql():

    assert querybuilder.fields_to_sql("variants.chr", DEFAULT_TABLES) == "`variants`.`chr`"
    assert querybuilder.fields_to_sql("gene", DEFAULT_TABLES) == "`annotations`.`gene`"
    assert querybuilder.fields_to_sql("annotations.gene", DEFAULT_TABLES) == "`annotations`.`gene`"

    assert querybuilder.fields_to_sql("variants.gene", DEFAULT_TABLES) == "`variants`.`gene`"
    assert querybuilder.fields_to_sql(("genotype","sacha","gt"), DEFAULT_TABLES) == "`genotype_sacha`.`gt`"


def test_filters_to_sql():

    filter_in = {'AND': [{'field': 'ref', 'operator': '=', 'value': "A"}, {'field': 'alt', 'operator': '=', 'value': "C"} ]}
    filter_out =  "(`variants`.`ref` = 'A' AND `variants`.`alt` = 'C')"
    assert querybuilder.filters_to_sql(filter_in, DEFAULT_TABLES) == filter_out 

    filter_in = {'AND': [{'field': ('genotype','sacha','gt'), 'operator': '=', 'value': 4}, {'field': 'alt', 'operator': '=', 'value': "C"} ]}
    filter_out =  "(`genotype_sacha`.`gt` = 4 AND `variants`.`alt` = 'C')"
    assert querybuilder.filters_to_sql(filter_in, DEFAULT_TABLES) == filter_out 

    filter_in = {'AND':
        [{'field': 'ref', 'operator': '=', 'value': "A"}, 
        {'OR': 
            [{'field': 'alt', 'operator': '=', 'value': "C"},{'field': 'alt', 'operator': '=', 'value': "C"}]}]}

    filter_out =  "(`variants`.`ref` = 'A' AND (`variants`.`alt` = 'C' OR `variants`.`alt` = 'C'))"
    assert querybuilder.filters_to_sql(filter_in, DEFAULT_TABLES) == filter_out



QUERY_TESTS = [ 
        (
        # Test simple 
        {"fields": ["chr","pos"], "source": "variants"},
        "SELECT `variants`.`id`,`variants`.`chr`,`variants`.`pos` FROM variants LIMIT 50 OFFSET 0"
        ), 

        # Test limit offset 
        (
        {"fields": ["chr","pos"], "source": "variants", "limit": 10, "offset": 4},
        "SELECT `variants`.`id`,`variants`.`chr`,`variants`.`pos` FROM variants LIMIT 10 OFFSET 4"
        ), 

        # Test order by 
        (
        {"fields": ["chr","pos"], "source": "variants", "order_by": "chr", "order_desc": True},
        "SELECT `variants`.`id`,`variants`.`chr`,`variants`.`pos` FROM variants ORDER BY `variants`.`chr` DESC LIMIT 50 OFFSET 0"
        ), 

        # Test filters  
        (
        {"fields": ["chr","pos"], "source": "variants", "filters": {'AND': [{'field': 'ref', 'operator': '=', 'value': "A"}, {'field': 'alt', 'operator': '=', 'value': "C"} ]}},
        "SELECT `variants`.`id`,`variants`.`chr`,`variants`.`pos` FROM variants WHERE (`variants`.`ref` = 'A' AND `variants`.`alt` = 'C') LIMIT 50 OFFSET 0"
        ),

        (
        {"fields": ["chr","pos"], "source": "variants", "filters": {'AND': [{'field': 'ref', 'operator': 'has', 'value': "A"}, {'field': 'alt', 'operator': '~', 'value': "C"} ]}},
        "SELECT `variants`.`id`,`variants`.`chr`,`variants`.`pos` FROM variants WHERE (`variants`.`ref` LIKE '%A%' AND `variants`.`alt` REGEXP 'C') LIMIT 50 OFFSET 0"
        ),

        # Test different source 
        (
        {"fields": ["chr","pos"], "source": "other"},
        
         (
         "SELECT `variants`.`id`,`variants`.`chr`,`variants`.`pos` FROM variants " 
         "INNER JOIN selection_has_variant sv ON sv.variant_id = variants.id " 
         "INNER JOIN selections s ON s.id = sv.selection_id AND s.name = 'other' LIMIT 50 OFFSET 0"
         ) 
        ),

        # Test genotype fields 
        (
        {"fields": ["chr","pos",("sample","TUMOR","gt")], "source": "variants"},

            (
            "SELECT `variants`.`id`,`variants`.`chr`,`variants`.`pos`,`sample_TUMOR`.`gt` AS 'sample.TUMOR.gt' FROM variants" 
            " INNER JOIN sample_has_variant `sample_TUMOR` ON `sample_TUMOR`.variant_id = variants.id AND `sample_TUMOR`.sample_id = 1"
            " LIMIT 50 OFFSET 0"
            )
        )

    ]

@pytest.mark.parametrize("test_input, test_output", QUERY_TESTS, ids = [str(i) for i in range(len(QUERY_TESTS))])
def test_build_query(test_input, test_output):
    query = querybuilder.build_query(**test_input, default_tables=DEFAULT_TABLES, samples_ids = SAMPLES_ID ) 
    
    assert query == test_output
  

    # from cutevariant.core import sql
    # from cutevariant.core.importer import import_reader
    # from cutevariant.core.reader import VcfReader 
    # conn = sql.get_sql_connexion(":memory:")
    # import_reader(conn, VcfReader(open("examples/test.snpeff.vcf"),"snpeff"))
    # conn.execute(query)

