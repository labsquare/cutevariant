"""Proof of concept for the VQL DSL.

See test_vql.py for usage and features.

"""


import textx
import operator
import itertools
from pprint import pprint
from pkg_resources import resource_string


CLAUSES = ("select", "from", "where", "using")
OPERATOR_PRECEDENCE = {
    op: (precedence, subprecedence)
    for precedence, ops in enumerate(
        map(
            str.split,
            """
    ||
    *    /    %
    +    -
    <<   >>   &    |
    <    <=   >    >=
    =    ==   !=   <>   IS   IS NOT   IN   LIKE   GLOB   MATCH   REGEXP
    AND  XOR
    OR
""".splitlines(),
        )
    )
    for subprecedence, op in enumerate(ops)
}


def precedence(one: operator, two: operator) -> operator:
    return one if OPERATOR_PRECEDENCE[one] >= OPERATOR_PRECEDENCE[two] else two


OPERATOR_FROM_LEXEM = {"==": "=", "=/=": "!=", "and": "AND", "or": "OR", "xor": "XOR"}


def model_class(name: str, bases: tuple, attrs: dict) -> type:
    """Metaclass to automatically build the __init__ to get the properties,
    and register the class for metamodel
    """
    if "__init__" not in attrs:

        def __init__(self, *args, **kwargs):
            for field, value in kwargs.items():
                setattr(self, field, value)

        attrs["__init__"] = __init__
    cls = type(name, bases, attrs)
    model_class.classes.append(cls)
    return cls


model_class.classes = []


# classes used to build the raw model
class RawCondition(metaclass=model_class):
    @property
    def value(self):
        return {
            "field": self.id.id,
            "operator": OPERATOR_FROM_LEXEM.get(self.op.op, self.op.op),
            "value": self.val if isinstance(self.val, (str, int)) else self.val.id,
        }


class ParenExpr(metaclass=model_class):
    @property
    def value(self):
        return self.expression.value


class BaseExpr(metaclass=model_class):
    @property
    def value(self):
        # get the infix tree describing the expression
        #  NB: expressions are nested instead of parenthesed
        stack = [self.left.value]
        for operation in self.operations:
            stack.extend(operation.value)
        return stack


class Operation(metaclass=model_class):
    @property
    def value(self):
        return (self.op.value, self.remaining.value)


class BoolOperator(metaclass=model_class):
    @property
    def value(self):
        return OPERATOR_FROM_LEXEM.get(self.op, self.op)


class Tuple(metaclass=model_class):
    @property
    def id(self):
        return "({})".format(", ".join(item.id for item in self.items))


METAMODEL = textx.metamodel_from_str(
    resource_string(__name__, "vql.tx").decode(),  # grammar extraction from vql.tx
    classes=model_class.classes,
    debug=False,
)


class VQLSyntaxError(ValueError):
    pass


def model_from_string(raw_vql: str) -> dict:
    try:
        raw_model = METAMODEL.model_from_str(raw_vql)
    except textx.exceptions.TextXSyntaxError as err:
        raise VQLSyntaxError(*error_message_from_err(err, raw_vql))
    model = {}
    for clause in CLAUSES:
        value = getattr(raw_model, clause)
        if value is not None:
            model[clause] = globals()[f"compile_{clause}_from_raw_model"](value)
    print("MODEL:", model)
    return model


def compile_select_from_raw_model(raw_model) -> dict or tuple:
    return tuple(column.id for column in raw_model.columns)


def compile_from_from_raw_model(raw_model) -> dict or tuple:
    return raw_model.source.id


def compile_where_from_raw_model(raw_model) -> dict or tuple:
    expr = raw_model.expression
    # print('EXPRESSION:', expr.value)
    tree = dicttree_from_infix_nested_stack(expr.value)
    # print('TREE:', tree)
    return tree


def compile_using_from_raw_model(raw_model) -> dict or tuple:
    return (raw_model.filename.id,)


def error_message_from_err(
    err: textx.exceptions.TextXSyntaxError, raw_vql: str
) -> (str, int):
    """Return human-readable information and index in raw_sql query
    about the given exception"""
    # print(err)
    # print(dir(err))
    # print(err.args)
    # print(err.err_type)
    # print(err.line, err.col)
    # print(err.message)
    # print(err.filename)
    # print(err.expected_rules)
    if "'SELECT'" in err.message:  # was awaiting for a SELECT clause
        return "no SELECT clause", -1
    if err.message.endswith("=> 's,ref FROM*'."):
        return "empty 'FROM' clause", err.col
    if (
        ",*," in err.message
        and len(err.expected_rules) == 1
        and type(err.expected_rules[0]).__name__ == "RegExMatch"
    ):
        return "invalid empty identifier in SELECT clause", err.col
    if "Expected INT " in err.message and len(err.expected_rules) == 3:
        return "invalid value in WHERE clause", err.col
    if "Expected '==|>=|<=|!=" in err.message and len(err.expected_rules) == 1:
        return "invalid operator in WHERE clause", err.col

    raise err  # error not handled. Just raise it


def dicttree_from_infix_nested_stack(stack: list) -> dict:
    "Return the dict tree computed from the infix nested stack yielded by metamodel"
    # Algorithm:
    #   expand nested structure, place parens
    #   build the postfix representation
    #   build tree as dict from postfix
    def expand(obj: list or tuple or ...) -> list:
        if isinstance(obj, (list, tuple)):
            return ("(", *itertools.chain(*map(expand, obj)), ")")
        return (obj,)

    def as_postfix(tokens: list) -> iter:
        "Yield the output describing the postfix notation of given list"
        operators = []  # stack of operator
        for token in tokens:
            print("TOKEN:", type(token), token)
            if isinstance(token, dict):  # it's a condition, like a=3
                yield token
            elif token in OPERATOR_PRECEDENCE:  # it's an operator
                while (
                    operators
                    and operators[-1] != "("
                    and precedence(token, operators[-1])
                ):
                    yield operators.pop()
                operators.append(token)
            elif token == "(":
                operators.append(token)
            elif token == ")":
                while operators and operators[-1] != "(":
                    yield operators.pop()
                if operators[-1] == "(":
                    operators.pop()
            else:
                raise VQLSyntaxError(f"Unexpected token: {token}")
        yield from operators

    def as_tree(postfix: list) -> dict:
        "Return the dict describing the n-ary syntax tree"
        tree = {}
        operandes = []
        last_operator = None
        for token in postfix:
            if isinstance(token, dict):  # it's a condition, like a=3
                operandes.append(token)
            elif token in OPERATOR_PRECEDENCE:  # it's an operator
                assert len(operandes) >= 2
                right, left = operandes.pop(), operandes.pop()
                if last_operator == token:  # let's merge everything
                    assert isinstance(left, dict)
                    assert len(left) == 1
                    assert isinstance(left[last_operator], list)
                    left[last_operator].append(right)
                    operandes.append(left)
                else:
                    operandes.append({token: [left, right]})
                last_operator = token
            else:
                raise VQLSyntaxError(f"Unexpected token: {token}")
        assert len(operandes) == 1, operandes
        return operandes[0]

    # print('STACK:', stack)
    infix = expand(stack)
    # print('INFIX:', infix)
    postfix = tuple(as_postfix(infix))
    # print('POSTFIX:', postfix)
    return as_tree(postfix)
