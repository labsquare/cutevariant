from pprint import pprint
from cutevariant.core.vql import parse_one_vql

# Test valid VQL cases
VQL_TO_TREE_CASES = {
    # Test 1
    'SELECT chr,pos,sample["sacha"] FROM variants': {
        "cmd": "select_cmd",
        "fields": ["chr", "pos", ("sample", "sacha", "gt")],
        "filters": {},
        "group_by": [],
        "having": {},
        "source": "variants",
    },
    # Test 2
    "SELECT chr,pos,ref FROM variants WHERE a=3 AND b!=5 AND c<3": {
        "cmd": "select_cmd",
        "fields": ["chr", "pos", "ref"],
        "source": "variants",
        "group_by": [],
        "having": {},
        "filters": {
            "AND": [
                {"field": "a", "operator": "=", "value": 3},
                {"field": "b", "operator": "!=", "value": 5},
                {"field": "c", "operator": "<", "value": 3},
            ]
        },
    },
    # Test 3
    "SELECT chr,pos,ref FROM variants WHERE a=3 AND (b=5 OR c=3)": {
        "cmd": "select_cmd",
        "fields": ["chr", "pos", "ref"],
        "source": "variants",
        "group_by": [],
        "having": {},
        "filters": {
            "AND": [
                {"field": "a", "operator": "=", "value": 3},
                {
                    "OR": [
                        {"field": "b", "operator": "=", "value": 5},
                        {"field": "c", "operator": "=", "value": 3},
                    ]
                },
            ]
        },
    },
    # Test 4
    'SELECT chr,pos, sample["sacha"] FROM variants # comments are handled': {
        "cmd": "select_cmd",
        "fields": ["chr", "pos", ("sample", "sacha", "gt")],
        "filters": {},
        "group_by": [],
        "having": {},
        "source": "variants",
    },
    # Test 4bis GROUP BY
    "SELECT chr, pos, ref, alt FROM variants GROUP BY chr,pos": {
        "cmd": "select_cmd",
        "fields": ["chr", "pos", "ref", "alt"],
        "filters": {},
        "source": "variants",
        "group_by": ["chr", "pos"],
        "having": {},
    },
    # Test 4bis GROUP BY HAVING
    "SELECT chr, pos, ref, alt FROM variants GROUP BY chr HAVING count > 3": {
        "cmd": "select_cmd",
        "fields": ["chr", "pos", "ref", "alt"],
        "filters": {},
        "source": "variants",
        "group_by": ["chr"],
        "having": {"op": ">", "value": 3},
    },
    # Test 4bisbis GROUP BY on genotypes
    "SELECT chr, pos, sample['sacha'].gt FROM variants GROUP BY sample['sacha'].gt": {
        "cmd": "select_cmd",
        "fields": ["chr", "pos", ("sample", "sacha", "gt")],
        "filters": {},
        "source": "variants",
        "group_by": [("sample", "sacha", "gt")],
        "having": {},
    },
    # Test 5
    "SELECT chr FROM variants WHERE some_field IN ('one', 'two')": {
        "cmd": "select_cmd",
        "fields": ["chr"],
        "source": "variants",
        "group_by": [],
        "having": {},
        "filters": {
            "AND": [{"field": "some_field", "operator": "IN", "value": ("one", "two")}]
        },
    },
    "SELECT chr FROM variants WHERE gene IN WORDSET['test']": {
        "cmd": "select_cmd",
        "fields": ["chr"],
        "source": "variants",
        "group_by": [],
        "having": {},
        "filters": {
            "AND": [{"field": "gene", "operator": "IN", "value": ("WORDSET", "test")}]
        },
    },
    # Test 6
    "CREATE denovo FROM variants": {
        "cmd": "create_cmd",
        "source": "variants",
        "filters": {},
        "target": "denovo",
    },
    # Test 7
    "CREATE denovo FROM variants WHERE some_field IN ('one', 'two')": {
        "cmd": "create_cmd",
        "source": "variants",
        "target": "denovo",
        "filters": {
            "AND": [{"field": "some_field", "operator": "IN", "value": ("one", "two")}]
        },
    },
    # Test 8
    "CREATE denovo = A + B ": {
        "cmd": "set_cmd",
        "first": "A",
        "second": "B",
        "operator": "+",
        "target": "denovo",
    },
    # Test 9
    'CREATE subset FROM variants INTERSECT "/home/sacha/test.bed"': {
        "cmd": "bed_cmd",
        "target": "subset",
        "source": "variants",
        "path": "/home/sacha/test.bed",
    },
    # Test 10
    "COUNT FROM variants": {"cmd": "count_cmd", "source": "variants", "filters": {}},
    # Test 110
    "COUNT FROM variants WHERE a = 3": {
        "cmd": "count_cmd",
        "source": "variants",
        "filters": {"AND": [{"field": "a", "operator": "=", "value": 3}]},
    },
    # Test 110
    "DROP selections subset": {
        "cmd": "drop_cmd",
        "feature": "selections",
        "name": "subset",
    },
    #  Test Import
    "IMPORT set '/home/truc/test.txt' AS boby": {
        "cmd": "import_cmd",
        "feature": "set",
        "path": "/home/truc/test.txt",
        "name": "boby",
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
