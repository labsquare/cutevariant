import pytest
from cutevariant.core import querybuilder


DEFAULT_TABLES = {
    "chr": "variants",
    "pos": "variants",
    "ref": "variants",
    "alt": "variants",
    "gene": "annotations",
    "gt": "sample_has_variant",
}


SAMPLES_ID = {"TUMOR": 1, "NORMAL": 2}


def test_filter_to_flat():
    filters = {
        "AND": [
            {"field": "ref", "operator": "=", "value": "A"},
            {"field": "alt", "operator": "=", "value": "C"},
        ]
    }


def test_field_function_to_sql():
    assert (
        querybuilder.field_function_to_sql(("genotype", "boby", "GT"))
        == "`genotype_boby`.`GT`"
    )
    assert (
        querybuilder.field_function_to_sql(("phenotype", "sacha", ""))
        == "`phenotype_sacha`"
    )
    assert (
        querybuilder.field_function_to_sql(("genotype", "sacha", "gt"), use_as=True)
        == "`genotype_sacha`.`gt` AS 'genotype.sacha.gt'"
    )


def test_set_function_to_sql():
    assert (
        querybuilder.set_function_to_sql(("SET", "sacha"))
        == "(SELECT value FROM sets WHERE name = 'sacha')"
    )


def test_fields_to_sql():

    assert (
        querybuilder.fields_to_sql("variants.chr", DEFAULT_TABLES) == "`variants`.`chr`"
    )
    assert querybuilder.fields_to_sql("gene", DEFAULT_TABLES) == "`annotations`.`gene`"
    assert (
        querybuilder.fields_to_sql("annotations.gene", DEFAULT_TABLES)
        == "`annotations`.`gene`"
    )

    assert (
        querybuilder.fields_to_sql("variants.gene", DEFAULT_TABLES)
        == "`variants`.`gene`"
    )
    assert (
        querybuilder.fields_to_sql(("sample", "sacha", "gt"), DEFAULT_TABLES)
        == "`sample_sacha`.`gt`"
    )


def test_filters_to_sql():

    filter_in = {
        "AND": [
            {"field": "ref", "operator": "=", "value": "A"},
            {"field": "alt", "operator": "=", "value": "C"},
        ]
    }
    filter_out = "(`variants`.`ref` = 'A' AND `variants`.`alt` = 'C')"
    assert querybuilder.filters_to_sql(filter_in, DEFAULT_TABLES) == filter_out

    filter_in = {
        "AND": [
            {"field": ("sample", "sacha", "gt"), "operator": "=", "value": 4},
            {"field": "alt", "operator": "=", "value": "C"},
        ]
    }
    filter_out = "(`sample_sacha`.`gt` = 4 AND `variants`.`alt` = 'C')"
    assert querybuilder.filters_to_sql(filter_in, DEFAULT_TABLES) == filter_out

    filter_in = {
        "AND": [
            {"field": "ref", "operator": "=", "value": "A"},
            {
                "OR": [
                    {"field": "alt", "operator": "=", "value": "C"},
                    {"field": "alt", "operator": "=", "value": "C"},
                ]
            },
        ]
    }

    filter_out = "(`variants`.`ref` = 'A' AND (`variants`.`alt` = 'C' OR `variants`.`alt` = 'C'))"
    assert querybuilder.filters_to_sql(filter_in, DEFAULT_TABLES) == filter_out


def test_filters_to_vql():
    filter_in = {
        "AND": [
            {"field": "ref", "operator": "=", "value": "A"},
            {"field": "alt", "operator": "=", "value": "C"},
        ]
    }

    assert querybuilder.filters_to_vql(filter_in) == "ref = 'A' AND alt = 'C'"

    filter_in = {
        "AND": [
            {"field": "ref", "operator": "=", "value": "A"},
            {
                "OR": [
                    {"field": "alt", "operator": "=", "value": "C"},
                    {"field": "alt", "operator": "=", "value": "C"},
                ]
            },
        ]
    }

    assert (
        querybuilder.filters_to_vql(filter_in)
        == "ref = 'A' AND (alt = 'C' OR alt = 'C')"
    )


QUERY_TESTS = [
    (
        # Test simple
        {"fields": ["chr", "pos"], "source": "variants"},
        "SELECT DISTINCT `variants`.`id`,`variants`.`chr`,`variants`.`pos` FROM variants LIMIT 50 OFFSET 0",
        "SELECT chr,pos FROM variants",
    ),
    (
        # Test GROUPBY
        {"fields": ["chr", "pos"], "source": "variants", "group_by": ["chr"]},
        "SELECT DISTINCT `variants`.`id`,`variants`.`chr`,`variants`.`pos` FROM variants GROUP BY chr LIMIT 50 OFFSET 0",
        "SELECT chr,pos FROM variants GROUP BY chr",
    ),
    # Test limit offset
    (
        {"fields": ["chr", "pos"], "source": "variants", "limit": 10, "offset": 4},
        "SELECT DISTINCT `variants`.`id`,`variants`.`chr`,`variants`.`pos` FROM variants LIMIT 10 OFFSET 4",
        "SELECT chr,pos FROM variants",
    ),
    # Test order by
    (
        {
            "fields": ["chr", "pos"],
            "source": "variants",
            "order_by": "chr",
            "order_desc": True,
        },
        "SELECT DISTINCT `variants`.`id`,`variants`.`chr`,`variants`.`pos` FROM variants ORDER BY `variants`.`chr` DESC LIMIT 50 OFFSET 0",
        "SELECT chr,pos FROM variants",
    ),
    # Test filters
    (
        {
            "fields": ["chr", "pos"],
            "source": "variants",
            "filters": {
                "AND": [
                    {"field": "ref", "operator": "=", "value": "A"},
                    {"field": "alt", "operator": "=", "value": "C"},
                ]
            },
        },
        "SELECT DISTINCT `variants`.`id`,`variants`.`chr`,`variants`.`pos` FROM variants WHERE (`variants`.`ref` = 'A' AND `variants`.`alt` = 'C') LIMIT 50 OFFSET 0",
        "SELECT chr,pos FROM variants WHERE ref = 'A' AND alt = 'C'",
    ),
    (
        {
            "fields": ["chr", "pos"],
            "source": "variants",
            "filters": {
                "AND": [
                    {"field": "ref", "operator": "has", "value": "A"},
                    {"field": "alt", "operator": "~", "value": "C"},
                ]
            },
        },
        "SELECT DISTINCT `variants`.`id`,`variants`.`chr`,`variants`.`pos` FROM variants WHERE (`variants`.`ref` LIKE '%A%' AND `variants`.`alt` REGEXP 'C') LIMIT 50 OFFSET 0",
        "SELECT chr,pos FROM variants WHERE ref has 'A' AND alt ~ 'C'",
    ),
    # Test different source
    (
        {"fields": ["chr", "pos"], "source": "other"},
        (
            "SELECT DISTINCT `variants`.`id`,`variants`.`chr`,`variants`.`pos` FROM variants "
            "INNER JOIN selection_has_variant sv ON sv.variant_id = variants.id "
            "INNER JOIN selections s ON s.id = sv.selection_id AND s.name = 'other' LIMIT 50 OFFSET 0"
        ),
        "SELECT chr,pos FROM other",
    ),
    # Test genotype fields
    (
        {"fields": ["chr", "pos", ("sample", "TUMOR", "gt")], "source": "variants"},
        (
            "SELECT DISTINCT `variants`.`id`,`variants`.`chr`,`variants`.`pos`,`sample_TUMOR`.`gt` AS 'sample.TUMOR.gt' FROM variants"
            " INNER JOIN sample_has_variant `sample_TUMOR` ON `sample_TUMOR`.variant_id = variants.id AND `sample_TUMOR`.sample_id = 1"
            " LIMIT 50 OFFSET 0"
        ),
        "SELECT chr,pos,sample['TUMOR'].gt FROM variants",
    ),
    # Test genotype in filters
    (
        {
            "fields": ["chr", "pos"],
            "source": "variants",
            "filters": {
                "AND": [
                    {"field": ("sample", "TUMOR", "gt"), "operator": "=", "value": 1}
                ]
            },
        },
        (
            "SELECT DISTINCT `variants`.`id`,`variants`.`chr`,`variants`.`pos` FROM variants"
            " INNER JOIN sample_has_variant `sample_TUMOR` ON `sample_TUMOR`.variant_id = variants.id AND `sample_TUMOR`.sample_id = 1"
            " WHERE `sample_TUMOR`.`gt` = 1"
            " LIMIT 50 OFFSET 0"
        ),
        "SELECT chr,pos FROM variants WHERE sample['TUMOR'].gt = 1",
    ),


    # Test genotype with 2 filters 
    (
        {
            "fields": ["chr", "pos"],
            "source": "variants",
            "filters": {
                "AND": [
                    {"field": ("sample", "TUMOR", "gt"), "operator": "=", "value": 1},
                    {"field": ("sample", "TUMOR", "dp"), "operator": ">", "value": 10}

                ]
            },
        },
        (
            "SELECT DISTINCT `variants`.`id`,`variants`.`chr`,`variants`.`pos` FROM variants"
            " INNER JOIN sample_has_variant `sample_TUMOR` ON `sample_TUMOR`.variant_id = variants.id AND `sample_TUMOR`.sample_id = 1"
            " WHERE (`sample_TUMOR`.`gt` = 1 AND `sample_TUMOR`.`dp` > 10)"
            " LIMIT 50 OFFSET 0"
        ),
        "SELECT chr,pos FROM variants WHERE sample['TUMOR'].gt = 1 AND sample['TUMOR'].dp > 10",
    ),





    # Test genotype in both filters and fields
    (
        {
            "fields": ["chr", "pos", ("sample", "TUMOR", "gt")],
            "source": "variants",
            "filters": {
                "AND": [
                    {"field": ("sample", "TUMOR", "gt"), "operator": "=", "value": 1}
                ]
            },
        },
        (
            "SELECT DISTINCT `variants`.`id`,`variants`.`chr`,`variants`.`pos`,`sample_TUMOR`.`gt` AS 'sample.TUMOR.gt' FROM variants"
            " INNER JOIN sample_has_variant `sample_TUMOR` ON `sample_TUMOR`.variant_id = variants.id AND `sample_TUMOR`.sample_id = 1"
            " WHERE `sample_TUMOR`.`gt` = 1"
            " LIMIT 50 OFFSET 0"
        ),
        "SELECT chr,pos,sample['TUMOR'].gt FROM variants WHERE sample['TUMOR'].gt = 1",
    ),

    # Test IN SET   
    (

        {
        "fields": ["chr"],
        "source": "variants",
        "filters": {
            "AND": [
                {"field": "chr", "operator":"IN", "value": ("SET","name")}
            ]
        }
        }, 
        (
        "SELECT DISTINCT `variants`.`id`,`variants`.`chr` FROM variants WHERE `variants`.`chr` IN (SELECT value FROM sets WHERE name = 'name') LIMIT 50 OFFSET 0"
        ),

        "SELECT chr FROM variants WHERE chr IN SET['name']"
    )
]


@pytest.mark.parametrize(
    "test_input, test_output,vql",
    QUERY_TESTS,
    ids=[str(i) for i in range(len(QUERY_TESTS))],
)
def test_build_query(test_input, test_output, vql):

    # Test SQL query builder
    query = querybuilder.build_query(
        **test_input, default_tables=DEFAULT_TABLES, samples_ids=SAMPLES_ID
    )

    assert query == test_output

    # Test VQL query builder

    # Ugly .. make it better
    query = querybuilder.build_vql_query(
        fields=test_input["fields"],
        source=test_input["source"],
        filters=test_input["filters"] if "filters" in test_input else [],
        group_by=test_input["group_by"] if "group_by" in test_input else [],
        having=test_input["having"] if "having" in test_input else [],
    )

    assert query == vql

    # from cutevariant.core import sql
    # from cutevariant.core.importer import import_reader
    # from cutevariant.core.reader import VcfReader
    # conn = sql.get_sql_connexion(":memory:")
    # import_reader(conn, VcfReader(open("examples/test.snpeff.vcf"),"snpeff"))
    # conn.execute(query)


##Test VQL


# def test_fields_to_vql():
#     assert querybuilder.fields_to_vql("chr") == "chr"
#     assert querybuilder.fields_to_vql(("sample", "boby", "gt")) == "sample['boby'].gt"

# def test_filters_to_vql():
