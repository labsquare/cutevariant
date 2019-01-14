"""Proof of concept for the VQL DSL.

See test_vql.py for usage and features.

"""

import textx
import operator
import itertools
from pprint import pprint


CLAUSES = ('select', 'from', 'where', 'using')
AND = operator.and_
OR = operator.or_
EQ = operator.eq
NE = operator.ne
LT = operator.lt
GT = operator.gt
LE = operator.le
GE = operator.ge
XOR = operator.xor
OPENED = '('
CLOSED = ')'
OPERATOR_FROM_LEXEM = {
    '=': EQ,
    '==': EQ,
    '!=': NE,
    '=/=': NE,
    '>': GT,
    '<': LT,
    '>=': GE,
    '<=': LE,
    'OR': OR,
    'XOR': XOR,
    'AND': AND,
}
OPERATOR_PRECEDENCE = {
    OR: 1,
    AND: 2,
    XOR: 3,
    EQ: 4,
    NE: 4,
    LT: 4,
    GT: 4,
    LE: 4,
    GE: 4,
}
def precedence(one:operator, two:operator) -> operator:
    return one if OPERATOR_PRECEDENCE[one] <= OPERATOR_PRECEDENCE[two] else two

# classes used to build the raw model
class RawCondition:
    def __init__(self, parent, id, op, val):
        self.parent = parent
        self.id, self.op, self.val = id, op, val
    @property
    def value(self):
        return {
            'field': self.id.id,
            'operator': OPERATOR_FROM_LEXEM[self.op.op],
            'value': self.val if isinstance(self.val, int) else self.val.id
        }

class ParenExpr:
    def __init__(self, parent, expression):
        self.parent = parent
        self.expression = expression
    @property
    def value(self):
        return self.expression.value
class BaseExpr:
    def __init__(self, parent, left, operations):
        self.parent = parent
        self.left, self.operations = left, operations
    @property
    def value(self):
        # get the infix tree describing the expression
        #  NB: expressions are nested instead of parenthesed
        stack = [self.left.value]
        for operation in self.operations:
            stack.extend(operation.value)
        return stack

class Operation:
    def __init__(self, parent, op, remaining):
        self.parent = parent
        self.op, self.remaining = op, remaining
        print('REMAINING:', type(remaining))
    @property
    def value(self):
        return (self.op.value, self.remaining.value)

class BoolOperator:
    def __init__(self, parent, op):
        self.parent = parent
        self.op = op
    @property
    def value(self):
        return OPERATOR_FROM_LEXEM[self.op]

METAMODEL = textx.metamodel_from_file('vql.tx', classes=[RawCondition, ParenExpr, BaseExpr, Operation, BoolOperator],
                                      debug=False)


class VQLSyntaxError(ValueError):
    pass




def model_from_string(raw_vql:str) -> dict:
    raw_model = METAMODEL.model_from_str(raw_vql)
    model = {}
    for clause in CLAUSES:
        value = getattr(raw_model, clause)
        if value is not None:
            model[clause] = globals()[f'compile_{clause}_from_raw_model'](value)
    print('MODEL:', model)
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


def dicttree_from_infix_nested_stack(stack:list) -> dict:
    "Return the dict tree computed from the infix nested stack yielded by metamodel"
    # Algorithm:
    #   expand nested structure, place parens
    #   build the postfix representation
    #   build tree as dict from postfix
    def expand(obj:list or tuple or ...) -> list:
        if isinstance(obj, (list, tuple)):
            return ('(', *itertools.chain(*map(expand, obj)), ')')
        return obj,

    def as_postfix(tokens:list) -> iter:
        "Yield the output describing the postfix notation of given list"
        operators = []  # stack of operator
        for token in tokens:
            print('TOKEN:', type(token), token)
            if isinstance(token, dict):  # it's a condition, like a=3
                yield token
            elif token in OPERATOR_PRECEDENCE:  # it's an operator
                while operators and operators[-1] != '(' and precedence(token, operators[-1]):
                    yield operators.pop()
                operators.append(token)
            elif token == '(':
                operators.append(token)
            elif token == ')':
                while operators and operators[-1] != '(':
                    yield operators.pop()
                if operators[-1] == '(':  operators.pop()
            else:
                raise VQLSyntaxError(f"Unexpected token: {token}")
        yield from operators

    def as_tree(postfix:list) -> dict:
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
                    assert isinstance(left[last_operator], (tuple, list))
                    left[last_operator] = tuple(left[last_operator]) + (right,)
                    operandes.append(left)
                else:
                    operandes.append({token: (left, right)})
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
