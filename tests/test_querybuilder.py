
from cutevariant.core import querybuilder 


DEFAULT_TABLES = {
    "chr": "variants",
    "pos": "variants",
    "ref": "variants",
    "alt": "variants",
    "gene": "annotations",
    "gt": "sample_has_variant"
    }

def test_filter_to_flat():
    filters = {'AND': [
        {'field': 'ref', 'operator': '=', 'value': "A"},
        {'field': 'alt', 'operator': '=', 'value': "C"}
        ]}


    print(list(querybuilder.filters_to_flat(filters)))



def test_field_function_to_sql():
    assert querybuilder.field_function_to_sql(("genotype", "boby", "GT"))  == "`genotype_boby`.`GT`"
    assert querybuilder.field_function_to_sql(("phenotype", "sacha", ""))  == "`phenotype_sacha`"


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