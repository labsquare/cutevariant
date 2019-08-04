import pytest
from pprint import pprint
from cutevariant.core.vql import execute_vql, VQLSyntaxError


# Test valid VQL cases
VQL_TO_TREE_CASES = {
    'SELECT chr,pos,genotype("sacha") FROM variants': {
        "cmd":"select_cmd",
        "columns": ["chr", "pos", ('genotype','sacha','gt')],
        "source": "variants",
    },
    "SELECT chr,pos,ref FROM variants WHERE a=3 AND b!=5 AND c<3": {
        "cmd":"select_cmd",
        "columns": ["chr", "pos", "ref"],
        "source": "variants",
        "filter": {
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
        "filter": {
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
        "source": "variants"
        },
    "SELECT chr FROM variants WHERE some_field IN ('one', 'two')": {
        "cmd":"select_cmd",
        "columns": ["chr"],
        "source": "variants",
        "filter": {'AND': [{'field': 'some_field', 'operator': 'IN', 'value': ('one', 'two')}]},
    },
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


def test_vql_function():
    q = "SELECT chr, pos, genotype('test').g FROM variants"

    found = next(execute_vql(q))

    print(found)


# # test exceptions returned by VQL
# MALFORMED_VQL_CASES = {
#     "": ("no SELECT clause", -1),
#     "SELECT chr,pos,ref FROM": ("empty 'FROM' clause", 24),
#     #"SELECT chr,,ref FROM": ("invalid empty identifier in SELECT clause", 12),
#     #"SELECT c FROM v WHERE a=": ("invalid value in WHERE clause", 25),
#     #"SELECT c FROM v WHERE a?=3": ("invalid operator in WHERE clause", 24),
# }


# def template_test_malformed_case(vql_expr: str, expected: tuple) -> callable:
#     "Return a function that test equivalence between given VQL and expected result"

#     def test_function():
#         print("test function")
#         with pytest.raises(VQLSyntaxError) as excinfo:
#             model_from_string(vql_expr)
#         assert excinfo.value.args == expected

#     return test_function


# # generate all test cases
# for idx, (vql, expected) in enumerate(MALFORMED_VQL_CASES.items(), start=1):
#     globals()[f"test_malformed_vql_{idx}"] = template_test_malformed_case(vql, expected)
