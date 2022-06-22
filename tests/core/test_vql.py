from pprint import pprint
from cutevariant.core.vql import parse_one_vql

# Test valid VQL cases
VQL_TO_TREE_CASES = {
    # Test 1
    'SELECT chr,pos,samples["sacha"] FROM variants ': {
        "cmd": "select_cmd",
        "fields": ["chr", "pos", "samples.sacha.gt"],
        "filters": {},
        "source": "variants",
        "order_by": [],
    },
    # Test 1 bis
    'SELECT chr,pos,samples["sacha"].gt FROM variants WHERE samples["sacha"].gt = 1': {
        "cmd": "select_cmd",
        "fields": ["chr", "pos", "samples.sacha.gt"],
        "filters": {"$and": [{"samples.sacha.gt": {"$eq": 1.0}}]},
        "source": "variants",
        "order_by": [],
    },
    # Test 2
    "SELECT chr,pos,ref FROM variants WHERE a=3 AND b!=5 AND c<3": {
        "cmd": "select_cmd",
        "fields": ["chr", "pos", "ref"],
        "source": "variants",
        "filters": {
            "$and": [
                {"a": {"$eq": 3}},
                {"b": {"$ne": 5}},
                {"c": {"$lt": 3}},
            ]
        },
        "order_by": [],
    },
    # Test 2 bis avec IS NULL
    "SELECT chr,pos,ref FROM variants WHERE a = NULL": {
        "cmd": "select_cmd",
        "fields": ["chr", "pos", "ref"],
        "source": "variants",
        "filters": {"$and": [{"a": {"$eq": None}}]},
        "order_by": [],
    },
    # Test 3
    "SELECT chr,pos,ref FROM variants WHERE a=3 AND (b=5 OR c=3)": {
        "cmd": "select_cmd",
        "fields": ["chr", "pos", "ref"],
        "source": "variants",
        "filters": {
            "$and": [
                {"a": {"$eq": 3}},
                {
                    "$or": [
                        {"b": {"$eq": 5}},
                        {"c": {"$eq": 3}},
                    ]
                },
            ]
        },
        "order_by": [],
    },
    # Test 4
    'SELECT chr,pos, samples["sacha"] FROM variants # comments are handled': {
        "cmd": "select_cmd",
        "fields": ["chr", "pos", "samples.sacha.gt"],
        "filters": {},
        "source": "variants",
        "order_by": [],
    },
    'SELECT chr,pos, samples["sacha"] FROM variants ORDER BY chr': {
        "cmd": "select_cmd",
        "fields": ["chr", "pos", "samples.sacha.gt"],
        "filters": {},
        "source": "variants",
        "order_by": [("chr", True)],
    },
    'SELECT chr,pos, samples["sacha"] FROM variants ORDER BY chr, pos DESC': {
        "cmd": "select_cmd",
        "fields": ["chr", "pos", "samples.sacha.gt"],
        "filters": {},
        "source": "variants",
        "order_by": [("chr", True), ("pos", False)],
    },
    # Test 7bis - HAS
    "SELECT chr, pos  FROM variants WHERE consequence HAS 'exon'": {
        "cmd": "select_cmd",
        "fields": ["chr", "pos"],
        "filters": {"$and": [{"consequence": {"$has": "exon"}}]},
        "source": "variants",
        "order_by": [],
    },
    # Test 7bis - HAS
    "SELECT chr, pos  FROM variants WHERE consequence !HAS 'exon'": {
        "cmd": "select_cmd",
        "fields": ["chr", "pos"],
        "filters": {"$and": [{"consequence": {"$nhas": "exon"}}]},
        "source": "variants",
        "order_by": [],
    },
    # Test 8
    "SELECT chr FROM variants WHERE some_field IN ('one', 'two')": {
        "cmd": "select_cmd",
        "fields": ["chr"],
        "source": "variants",
        "filters": {"$and": [{"some_field": {"$in": ["one", "two"]}}]},
        "order_by": [],
    },
    # Test 9
    "SELECT chr FROM variants WHERE gene IN WORDSET['test']": {
        "cmd": "select_cmd",
        "fields": ["chr"],
        "source": "variants",
        "filters": {"$and": [{"gene": {"$in": {"$wordset": "test"}}}]},
        "order_by": [],
    },
    # Test 10
    "CREATE denovo FROM variants": {
        "cmd": "create_cmd",
        "source": "variants",
        "filters": {},
        "target": "denovo",
    },
    # Test 11
    "CREATE denovo FROM variants WHERE some_field IN ('one', 'two')": {
        "cmd": "create_cmd",
        "source": "variants",
        "target": "denovo",
        "filters": {"$and": [{"some_field": {"$in": ["one", "two"]}}]},
    },
    # Test 12
    "CREATE denovo = A | B ": {
        "cmd": "set_cmd",
        "first": "A",
        "second": "B",
        "operator": "|",
        "target": "denovo",
    },
    # Test 13
    'CREATE subset FROM variants INTERSECT "/home/sacha/test.bed"': {
        "cmd": "bed_cmd",
        "target": "subset",
        "source": "variants",
        "path": "/home/sacha/test.bed",
    },
    # Test 14
    "COUNT FROM variants": {"cmd": "count_cmd", "source": "variants", "filters": {}},
    # Test 15
    "COUNT FROM variants WHERE a = 3": {
        "cmd": "count_cmd",
        "source": "variants",
        "filters": {"$and": [{"a": {"$eq": 3}}]},
    },
    # Test 16
    "DROP selections subset": {
        "cmd": "drop_cmd",
        "feature": "selections",
        "name": "subset",
    },
    # Test 17 Test Import
    "IMPORT set '/home/truc/test.txt' AS boby": {
        "cmd": "import_cmd",
        "feature": "set",
        "path": "/home/truc/test.txt",
        "name": "boby",
    },
    # Test 18 Test regex
    "SELECT chr,pos,ref,alt FROM variants WHERE ref =~'^[AG]$' AND alt =~'^[CT]$'": {
        "cmd": "select_cmd",
        "fields": ["chr", "pos", "ref", "alt"],
        "filters": {"$and": [{"ref": {"$regex": "^[AG]$"}}, {"alt": {"$regex": "^[CT]$"}}]},
        "source": "variants",
        "order_by": [],
    },
    # Test not regexp
    "SELECT chr,pos,ref,alt FROM variants WHERE ref !~'^[AG]$' AND alt !~'^[CT]$'": {
        "cmd": "select_cmd",
        "fields": ["chr", "pos", "ref", "alt"],
        "filters": {"$and": [{"ref": {"$nregex": "^[AG]$"}}, {"alt": {"$nregex": "^[CT]$"}}]},
        "source": "variants",
        "order_by": [],
    },
    # Test 19 Test ANY
    "SELECT chr,pos,ref,alt FROM variants WHERE samples[ANY].gt > 1": {
        "cmd": "select_cmd",
        "fields": ["chr", "pos", "ref", "alt"],
        "filters": {"$and": [{"samples.$any.gt": {"$gt": 1.0}}]},
        "source": "variants",
        "order_by": [],
    },
    # Test 20 Test ANY
    "SELECT chr,pos,ref,alt FROM variants WHERE samples[?].gt > 1": {
        "cmd": "select_cmd",
        "fields": ["chr", "pos", "ref", "alt"],
        "filters": {"$and": [{"samples.$all.gt": {"$gt": 1.0}}]},
        "source": "variants",
        "order_by": [],
    },
}


def template_test_case(vql_expr: str, expected: dict) -> callable:
    """Return a function that test equivalence between given VQL and expected result"""

    def test_function():
        print("EXPECTED:", ", ".join(sorted(tuple(expected.keys()))))
        found = parse_one_vql(vql_expr)
        print("FOUND:", ", ".join(sorted(tuple(found.keys()))))
        pprint(expected)
        print()
        pprint(found)
        assert found == expected

    return test_function


# generate all test cases
for idx, (vql, expected) in enumerate(VQL_TO_TREE_CASES.items(), start=1):
    globals()[f"test_vql_{idx}"] = template_test_case(vql, expected)
