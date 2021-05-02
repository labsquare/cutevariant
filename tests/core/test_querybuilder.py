import pytest
from cutevariant.core import querybuilder, sql
from tests.utils import create_conn


def test_filter_to_flat():
    filters = {
        "$and": [
            {"ref": "A"},
            {"alt": "C"},
            {"$or": [{"ann.gene": "CFTR"}]},
        ]
    }

    assert querybuilder.filters_to_flat(filters) == [
        {"ref": "A"},
        {"alt": "C"},
        {"ann.gene": "CFTR"},
    ]


def test_is_annotation_join_required():

    fields = ["chr"]
    filters = {"$and": [{"ann.ref": "A"}]}
    assert querybuilder.is_annotation_join_required(fields, filters)

    fields = ["chr"]
    filters = {"$and": [{"ref": "A"}]}
    assert not querybuilder.is_annotation_join_required(fields, filters)

    fields = ["chr", "ann.gene"]
    filters = {"$and": [{"ref": "A"}]}
    assert querybuilder.is_annotation_join_required(fields, filters)


def test_samples_join_required():

    fields = ["chr", "samples.boby.gt"]
    filters = {}
    assert querybuilder.samples_join_required(fields, filters) == ["boby"]

    fields = ["chr"]
    filters = {"samples.boby.gt": 1}
    assert querybuilder.samples_join_required(fields, filters) == ["boby"]

    fields = ["chr"]
    filters = {}
    assert querybuilder.samples_join_required(fields, filters) == []


# refactor
def test_condition_to_sql():

    assert querybuilder.condition_to_sql({"chr": "chr3"}) == "`variants`.`chr` = 'chr3'"
    assert (
        querybuilder.condition_to_sql({"qual": {"$gte": 4}}) == "`variants`.`qual` >= 4"
    )
    assert (
        querybuilder.condition_to_sql({"qual": {"$in": [1, 2, 3]}})
        == "`variants`.`qual` IN (1,2,3)"
    )
    assert (
        querybuilder.condition_to_sql({"gene": {"$nin": ["CFTR", "GJB2"]}})
        == "`variants`.`gene` NOT IN ('CFTR','GJB2')"
    )

    assert (
        querybuilder.condition_to_sql({"ann.gene": {"$nin": ["CFTR", "GJB2"]}})
        == "`annotations`.`gene` NOT IN ('CFTR','GJB2')"
    )

    assert (
        querybuilder.condition_to_sql({"ann.gene": "CFTR"})
        == "`annotations`.`gene` = 'CFTR'"
    )

    assert (
        querybuilder.condition_to_sql({"samples.boby.dp": 42})
        == "`sample_boby`.`dp` = 42"
    )


def test_fields_to_vql():
    fields = [
        "chr",
        "pos",
        "ref",
        "ann.gene",
        "ann.impact",
        "samples.boby.gt",
        "samples.boby.dp",
        "samples.charles.gt",
    ]

    expected_fields = [
        "chr",
        "pos",
        "ref",
        "ann.gene",
        "ann.impact",
        "sample['boby'].gt",
        "sample['boby'].dp",
        "sample['charles'].gt",
    ]

    assert querybuilder.fields_to_vql(fields) == expected_fields


def test_fields_to_sql():
    fields = [
        "chr",
        "pos",
        "ref",
        "ann.gene",
        "ann.impact",
        "samples.boby.gt",
        "samples.boby.dp",
        "samples.charles.gt",
    ]

    expected_fields = [
        "`variants`.`chr`",
        "`variants`.`pos`",
        "`variants`.`ref`",
        "`annotations`.`gene`",
        "`annotations`.`impact`",
        "`sample_boby`.`gt`",
        "`sample_boby`.`dp`",
        "`sample_charles`.`gt`",
    ]

    assert querybuilder.fields_to_sql(fields) == expected_fields

    expected_fields[3] = "`annotations`.`gene` AS `ann.gene`"
    expected_fields[4] = "`annotations`.`impact` AS `ann.impact`"
    expected_fields[5] = "`sample_boby`.`gt` AS `sample.boby.gt`"
    expected_fields[6] = "`sample_boby`.`dp` AS `sample.boby.dp`"
    expected_fields[7] = "`sample_charles`.`gt` AS `sample.charles.gt`"

    assert querybuilder.fields_to_sql(fields, use_as=True) == expected_fields


# refactor
def test_filters_to_sql():
    filters = {
        "$and": [
            {"chr": "chr1"},
            {"pos": {"$gt": 111}},
            {
                "ann.gene": "CFTR",
            },
            {"ann.gene": {"$gt": "LOW"}},
            {"samples.boby.gt": 1},
            {"$or": [{"pos": {"$gte": 10}}, {"pos": {"$lte": 100}}]},
        ]
    }

    observed = querybuilder.filters_to_sql(filters)

    print(observed)
    expected = "(`variants`.`chr` = 'chr1' AND `variants`.`pos` > 111 AND `annotations`.`gene` = 'CFTR' AND `annotations`.`gene` > 'LOW' AND `sample_boby`.`gt` = 1 AND (`variants`.`pos` >= 10 OR `variants`.`pos` <= 100))"
    assert observed == expected


def test_filters_to_vql():
    filters = {
        "$and": [
            {"chr": "chr1"},
            {"pos": {"$gt": 111}},
            {
                "ann.gene": "CFTR",
            },
            {"ann.gene": {"$gt": "LOW"}},
            {"samples.boby.gt": 1},
            {"$or": [{"pos": {"$gte": 10}}, {"pos": {"$lte": 100}}]},
        ]
    }

    observed = querybuilder.filters_to_vql(filters)

    print(observed)
    expected = "chr = 'chr1' AND pos > 111 AND ann.gene = 'CFTR' AND ann.gene > 'LOW' AND sample['boby'].gt = 1 AND (pos >= 10 OR pos <= 100)"
    assert observed == expected


# def test_build_sql_query():

#     fields = {"variants": ["chr", "pos"], "annotations": ["gene"]}

#     sql = querybuilder.build_sql_query(fields)

#     print(sql)


# Structure: (filter dict, expected SQL, expected VQL)
FILTERS_VS_SQL_VQL = [
    # Empty filter
    ({}, "", ""),
    # Empty filter
    ({"$and": {}}, "()", ""),
    # Standard not nested filter
    (
        {"$and": [{"ref": "A"}, {"alt": "C"}]},
        "(`variants`.`ref` = 'A' AND `variants`.`alt` = 'C')",
        "ref = 'A' AND alt = 'C'",
    ),
    (
        {"$and": [{"qual": {"$gte": 30}}]},
        "(`variants`.`qual` >= 30)",
        "qual >= 30",
    ),
    #  TEST IS NULL
    (
        {"$and": [{"ref": None}]},
        "(`variants`.`ref` IS NULL)",
        "ref = NULL",
    ),
    #  TEST IS NOT NULL
    (
        {"$and": [{"ref": {"$ne": None}}]},
        "(`variants`.`ref` IS NOT NULL)",
        "ref != NULL",
    ),
    # Test composite field
    (
        {"$and": [{"alt": "C"}, {"samples.sacha.gt": 4}]},
        "(`variants`.`alt` = 'C' AND `sample_sacha`.`gt` = 4)",
        "alt = 'C' AND sample['sacha'].gt = 4",
    ),
    # Test nested filters
    (
        {"$and": [{"ref": "A"}, {"$or": [{"alt": "C"}, {"alt": "C"}]}]},
        "(`variants`.`ref` = 'A' AND (`variants`.`alt` = 'C' OR `variants`.`alt` = 'C'))",
        "ref = 'A' AND (alt = 'C' OR alt = 'C')",
    ),
    # Test IN with numeric tuple
    (
        {"$and": [{"chr": {"$in": (11.0, 12.0)}}]},
        "(`variants`.`chr` IN (11.0,12.0))",
        "chr IN (11.0,12.0)",
    ),
    # Test IN with string tuple
    (
        {"$and": [{"chr": {"$in": ("XXX",)}}]},
        "(`variants`.`chr` IN ('XXX'))",
        "chr IN ('XXX')",
    ),
    # Test IN: conservation of not mixed types in the tuple
    (
        {"$and": [{"chr": {"$in": (10.0, 11.0)}}]},
        "(`variants`.`chr` IN (10.0,11.0))",
        "chr IN (10.0,11.0)",
    ),
    # Test IN: conservation of mixed types in the tuple
    (
        {"$and": [{"ann.gene": {"$in": ("CICP23", 2.0)}}]},
        "(`annotations`.`gene` IN ('CICP23',2.0))",
        "ann.gene IN ('CICP23',2.0)",
    ),
    # Test IN: conservation of mixed types in a tuple with str type
    # => Cast via literal_eval
    (
        {"$and": [{"ann.gene": {"$in": ("CICP23", 2.0)}}]},
        "(`annotations`.`gene` IN ('CICP23',2.0))",
        "ann.gene IN ('CICP23',2.0)",
    ),
    # Test WORDSET function
    (
        {"$and": [{"ann.gene": {"$in": {"$wordset": "coucou"}}}]},
        "(`annotations`.`gene` IN (SELECT value FROM wordsets WHERE name = 'coucou'))",
        "ann.gene IN WORDSET['coucou']",
    ),
]


@pytest.mark.parametrize(
    "filter_in, expected_sql, expected_vql",
    FILTERS_VS_SQL_VQL,
    ids=[str(i) for i in range(len(FILTERS_VS_SQL_VQL))],
)
def test_filters(filter_in, expected_sql, expected_vql):

    assert querybuilder.filters_to_sql(filter_in) == expected_sql
    assert querybuilder.filters_to_vql(filter_in) == expected_vql


# @pytest.mark.parametrize(
#     "filter_in, expected_sql, expected_vql",
#     FILTERS_VS_SQL_VQL,
#     ids=[str(i) for i in range(len(FILTERS_VS_SQL_VQL))],
# )
# def test_filters_to_vql(filter_in, expected_sql, expected_vql):
#     assert querybuilder.filters_to_vql(filter_in) == expected_vql


QUERY_TESTS = [
    (
        # Test simple
        {"fields": ["chr", "pos"], "source": "variants"},
        "SELECT DISTINCT `variants`.`id`,`variants`.`chr`,`variants`.`pos` FROM variants LIMIT 50 OFFSET 0",
        "SELECT chr,pos FROM variants",
    ),
    # Test limit offset
    (
        {
            "fields": ["chr", "pos"],
            "source": "variants",
            "limit": 10,
            "offset": 4,
        },
        "SELECT DISTINCT `variants`.`id`,`variants`.`chr`,`variants`.`pos` FROM variants LIMIT 10 OFFSET 4",
        "SELECT chr,pos FROM variants",
    ),
    # Test order by
    (
        {
            "fields": ["chr", "pos"],
            "source": "variants",
            "order_by": ["chr"],
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
                "$and": [
                    {"ref": "A"},
                    {"alt": "C"},
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
            "filters": {"$and": [{"alt": {"$regex": "C"}}]},
        },
        "SELECT DISTINCT `variants`.`id`,`variants`.`chr`,`variants`.`pos` FROM variants WHERE (`variants`.`alt` REGEXP 'C') LIMIT 50 OFFSET 0",
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
    # Test genotype fields 8
    (
        {
            "fields": ["chr", "pos", "samples.TUMOR.gt"],
            "source": "variants",
        },
        (
            "SELECT DISTINCT `variants`.`id`,`variants`.`chr`,`variants`.`pos`,`sample_TUMOR`.`gt` AS `sample.TUMOR.gt` FROM variants"
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
            "filters": {"$and": [{"samples.TUMOR.gt": 1}]},
        },
        (
            "SELECT DISTINCT `variants`.`id`,`variants`.`chr`,`variants`.`pos` FROM variants"
            " INNER JOIN sample_has_variant `sample_TUMOR` ON `sample_TUMOR`.variant_id = variants.id AND `sample_TUMOR`.sample_id = 1"
            " WHERE (`sample_TUMOR`.`gt` = 1) LIMIT 50 OFFSET 0"
        ),
        "SELECT chr,pos FROM variants WHERE sample['TUMOR'].gt = 1",
    ),
    # Test genotype with 2 filters
    (
        {
            "fields": ["chr", "pos"],
            "source": "variants",
            "filters": {
                "$and": [
                    {"samples.TUMOR.gt": 1},
                    {"samples.TUMOR.dp": {"$gt": 10}},
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
            "fields": ["chr", "pos", "samples.TUMOR.gt"],
            "source": "variants",
            "filters": {
                "$and": [
                    {"samples.TUMOR.gt": 1},
                ]
            },
        },
        (
            "SELECT DISTINCT `variants`.`id`,`variants`.`chr`,`variants`.`pos`,`sample_TUMOR`.`gt` AS `sample.TUMOR.gt` FROM variants"
            " INNER JOIN sample_has_variant `sample_TUMOR` ON `sample_TUMOR`.variant_id = variants.id AND `sample_TUMOR`.sample_id = 1"
            " WHERE (`sample_TUMOR`.`gt` = 1)"
            " LIMIT 50 OFFSET 0"
        ),
        "SELECT chr,pos,sample['TUMOR'].gt FROM variants WHERE sample['TUMOR'].gt = 1",
    ),
    # Test IN SET
    (
        {
            "fields": ["chr"],
            "source": "variants",
            "filters": {"$and": [{"chr": {"$in": {"$wordset": "name"}}}]},
        },
        (
            "SELECT DISTINCT `variants`.`id`,`variants`.`chr` FROM variants WHERE (`variants`.`chr` IN (SELECT value FROM wordsets WHERE name = 'name')) LIMIT 50 OFFSET 0"
        ),
        "SELECT chr FROM variants WHERE chr IN WORDSET['name']",
    ),
]


@pytest.mark.parametrize(
    "args, expected_sql, expected_vql",
    QUERY_TESTS,
    ids=[str(i) for i in range(len(QUERY_TESTS))],
)
def test_build_query(args, expected_sql, expected_vql):

    # Create fake database with samples
    # This is necessary because querybuilder need to extract samples id
    conn = sql.get_sql_connection(":memory:")
    sql.create_table_samples(conn)
    sql.insert_sample(conn, "TUMOR")
    sql.insert_sample(conn, "NORMAL")

    # Test SQL query builder
    observed_sql = querybuilder.build_sql_query(conn, **args)
    assert observed_sql == expected_sql

    # Test VQL query builder
    observed_vql = querybuilder.build_vql_query(**args)
    assert observed_vql == expected_vql

    # Test VQL query builder

    # Ugly .. make it better


#     query = querybuilder.build_vql_query(
#         fields=test_input["fields"],
#         source=test_input["source"],
#         filters=test_input["filters"] if "filters" in test_input else [],
#         group_by=test_input["group_by"] if "group_by" in test_input else [],
#         having=test_input["having"] if "having" in test_input else [],
#     )

#     assert query == vql


# from cutevariant.core import sql
# from cutevariant.core.importer import import_reader
# from cutevariant.core.reader import VcfReader

# conn = sql.get_sql_connection(":memory:")
# import_reader(conn, VcfReader(open("examples/test.snpeff.vcf"), "snpeff"))
# conn.execute(query)


##Test VQL


# def test_fields_to_vql():
#     assert querybuilder.fields_to_vql("chr") == "chr"
#     assert querybuilder.fields_to_vql(("sample", "boby", "gt")) == "sample['boby'].gt"

# def test_filters_to_vql():
