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

    flaty = querybuilder.filters_to_flat(filters)

    assert flaty == [
        {"field": "ref", "operator": "=", "value": "A"},
        {"field": "alt", "operator": "=", "value": "C"},
    ]


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
        querybuilder.field_function_to_sql(("sample", "sacha", "gt"), use_as=True)
        == "`sample_sacha`.`gt` AS \"sample('sacha').gt\""
    )


def test_wordset_function_to_sql():
    assert (
        querybuilder.wordset_function_to_sql(("WORDSET", "sacha"))
        == "(SELECT value FROM wordsets WHERE name = 'sacha')"
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


# Structure: (filter dict, expected SQL, expected VQL)
FILTERS_VS_SQL_VQL = [
    # Standard not nested filter
    (
        {
            "AND": [
                {"field": "ref", "operator": "=", "value": "A"},
                {"field": "alt", "operator": "=", "value": "C"},
            ]
        },
        "(`variants`.`ref` = 'A' AND `variants`.`alt` = 'C')",
        "ref = 'A' AND alt = 'C'",
    ),
    # Test composite field
    (
        {
            "AND": [
                {"field": ("sample", "sacha", "gt"), "operator": "=",
                 "value": 4},
                {"field": "alt", "operator": "=", "value": "C"},
            ]
        },
        "(`sample_sacha`.`gt` = 4 AND `variants`.`alt` = 'C')",
        "sample['sacha'].gt = 4 AND alt = 'C'",
    ),
    # Test nested filters
    (
        {
            "AND": [
                {"field": "ref", "operator": "=", "value": "A"},
                {
                    "OR": [
                        {"field": "alt", "operator": "=", "value": "C"},
                        {"field": "alt", "operator": "=", "value": "C"},
                    ]
                },
            ]
        },
        "(`variants`.`ref` = 'A' AND (`variants`.`alt` = 'C' OR `variants`.`alt` = 'C'))",
        "ref = 'A' AND (alt = 'C' OR alt = 'C')",
    ),
    # Test IN
    (
        {'field': 'chr', 'operator': 'in', 'value': (11.0,)},
        "`variants`.`chr` IN (11.0)",
        "chr IN (11.0)",
    ),
    # Test IN: conservation of not mixed types in the tuple
    (
        {'field': 'chr', 'operator': 'in', 'value': (10.0, 11.0)},
        '`variants`.`chr` IN (10.0,11.0)',
        'chr IN (10.0, 11.0)',
    ),
    # Test IN: conservation of not mixed types in a tuple with str type
    # => Cast via literal_eval
    (
        {'field': 'chr', 'operator': 'in', 'value': '(10.0, 11.0)'},
        '`variants`.`chr` IN (10.0,11.0)',
        'chr IN (10.0, 11.0)',
    ),
    # Test IN: conservation of mixed types in the tuple
    (
        {'field': 'gene', 'operator': 'in', 'value': ('CICP23', 2.0)},
        '`annotations`.`gene` IN ("CICP23",2.0)',
        "gene IN ('CICP23', 2.0)",
    ),
    # Test IN: conservation of mixed types in a tuple with str type
    # => Cast via literal_eval
    (
        {'field': 'gene', 'operator': 'in', 'value': "('CICP23', 2.0)"},
        '`annotations`.`gene` IN ("CICP23",2.0)',
        "gene IN ('CICP23', 2.0)",
    ),
    # Test IN: Just elements separated by comas
    (
        {'field': 'chr', 'operator': 'in', 'value': '100, 11'},
        '`variants`.`chr` IN (100,11)',
        "chr IN (100, 11)",
    ),
    # Test normal operator (not IN) with tuple
    (
        {'field': 'chr', 'operator': '<', 'value': '(10.0, 11.0)'},
        "`variants`.`chr` < '(10.0, 11.0)'",
        "chr < '(10.0, 11.0)'",
    ),
    # Test WORDSET function
    (
        {'field': 'gene', 'operator': 'in', 'value': ('WORDSET', 'coucou')},
        "`annotations`.`gene` IN (SELECT value FROM wordsets WHERE name = 'coucou')",
        "gene IN WORDSET['coucou']"
    ),
]


@pytest.mark.parametrize(
    "filter_in, expected_sql, expected_vql",
    FILTERS_VS_SQL_VQL,
    ids=[str(i) for i in range(len(FILTERS_VS_SQL_VQL))],
)
def test_filters_to_sql(filter_in, expected_sql, expected_vql):
    assert querybuilder.filters_to_sql(filter_in, DEFAULT_TABLES) == expected_sql


@pytest.mark.parametrize(
    "filter_in, expected_sql, expected_vql",
    FILTERS_VS_SQL_VQL,
    ids=[str(i) for i in range(len(FILTERS_VS_SQL_VQL))],
)
def test_filters_to_vql(filter_in, expected_sql, expected_vql):
    assert querybuilder.filters_to_vql(filter_in) == expected_vql


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
        "SELECT DISTINCT `variants`.`id`,`variants`.`chr`,`variants`.`pos` FROM variants GROUP BY `variants`.`chr` LIMIT 50 OFFSET 0",
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
                    {"field": "alt", "operator": "~", "value": "C"},
                ]
            },
        },
        "SELECT DISTINCT `variants`.`id`,`variants`.`chr`,`variants`.`pos` FROM variants WHERE `variants`.`alt` REGEXP 'C' LIMIT 50 OFFSET 0",
        "SELECT chr,pos FROM variants WHERE alt ~ 'C'",
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
            "SELECT DISTINCT `variants`.`id`,`variants`.`chr`,`variants`.`pos`,`sample_TUMOR`.`gt` AS \"sample('TUMOR').gt\" FROM variants"
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
                    {"field": ("sample", "TUMOR", "dp"), "operator": ">", "value": 10},
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
            "SELECT DISTINCT `variants`.`id`,`variants`.`chr`,`variants`.`pos`,`sample_TUMOR`.`gt` AS \"sample('TUMOR').gt\" FROM variants"
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
                    {"field": "chr", "operator": "IN", "value": ("WORDSET", "name")}
                ]
            },
        },
        (
            "SELECT DISTINCT `variants`.`id`,`variants`.`chr` FROM variants WHERE `variants`.`chr` IN (SELECT value FROM wordsets WHERE name = 'name') LIMIT 50 OFFSET 0"
        ),
        "SELECT chr FROM variants WHERE chr IN WORDSET['name']",
    ),
]


@pytest.mark.parametrize(
    "test_input, test_output,vql",
    QUERY_TESTS,
    ids=[str(i) for i in range(len(QUERY_TESTS))],
)
def test_build_query(test_input, test_output, vql):

    # Test SQL query builder
    query = querybuilder.build_sql_query(
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
    # conn = sql.get_sql_connection(":memory:")
    # import_reader(conn, VcfReader(open("examples/test.snpeff.vcf"),"snpeff"))
    # conn.execute(query)


##Test VQL


# def test_fields_to_vql():
#     assert querybuilder.fields_to_vql("chr") == "chr"
#     assert querybuilder.fields_to_vql(("sample", "boby", "gt")) == "sample['boby'].gt"

# def test_filters_to_vql():
