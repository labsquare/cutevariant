import pytest
from pprint import pprint
from cutevariant.core.vql import execute_vql, VQLSyntaxError

# Test valid VQL cases
VQL_TO_TREE_CASES = {
    'SELECT chr,pos,genotype("sacha") FROM variants': {
        "cmd":"select_cmd",
        "columns": ["chr", "pos", ('genotype','sacha','gt')],
        "filters": {},
        "source": "variants",
    },
    "SELECT chr,pos,ref FROM variants WHERE a=3 AND b!=5 AND c<3": {
        "cmd":"select_cmd",
        "columns": ["chr", "pos", "ref"],
        "source": "variants",
        "filters": {
            "AND": [
                {"field": "a", "operator": "=", "value": 3},
                {"field": "b", "operator": "!=", "value": 5},
                {"field": "c", "operator": "<", "value": 3},
            ]
        },
    },
    "SELECT chr,pos,ref FROM variants WHERE a=3 AND (b=5 OR c=3)": {
        "cmd":"select_cmd",
        "columns": ["chr", "pos", "ref"],
        "source": "variants",
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
    'SELECT chr,pos, genotype("sacha") FROM variants # comments are handled': {
        "cmd":"select_cmd",
        "columns": ["chr", "pos", ('genotype','sacha','gt')],
        "filters": {},
        "source": "variants"
        },
    "SELECT chr FROM variants WHERE some_field IN ('one', 'two')": {
        "cmd":"select_cmd",
        "columns": ["chr"],
        "source": "variants",
        "filters": {'AND': [{'field': 'some_field', 'operator': 'IN', 'value': ('one', 'two')}]},
    },

    "CREATE denovo FROM variants": {
        "cmd":"create_cmd",
        "source": "variants",
        "filters": {},
        "target": "denovo"
    },

    "CREATE denovo FROM variants WHERE some_field IN ('one', 'two')": {
        "cmd":"create_cmd",
        "source": "variants",
        "target":"denovo",
        "filters": {'AND': [{'field': 'some_field', 'operator': 'IN', 'value': ('one', 'two')}]},
    },


    "CREATE denovo = A + B " : {
    "cmd": "set_cmd",
    "first": "A",
    "second": "B",
    "operator":"+", 
    "target": "denovo"
    }

#    "CREATE denovo = boby & alex": {
#         "cmd":"create_cmd",
#         "target": "denovo",
#         "expression":"todo"
#         },

}


def template_test_case(vql_expr: str, expected: dict) -> callable:
    """Return a function that test equivalence between given VQL and expected result"""

    def test_function():
        print("EXPECTED:", ", ".join(sorted(tuple(expected.keys()))))
        found = next(execute_vql(vql_expr))
        print("FOUND:", ", ".join(sorted(tuple(found.keys()))))
        pprint(expected)
        print()
        pprint(found)
        assert found == expected

    return test_function


# generate all test cases
for idx, (vql, expected) in enumerate(VQL_TO_TREE_CASES.items(), start=1):
    globals()[f"test_vql_{idx}"] = template_test_case(vql, expected)


