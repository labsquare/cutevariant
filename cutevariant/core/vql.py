"""Proof of concept for the VQL DSL.

From this module, you only need to use parse_vql or parse_one_vql.
For instance::

    cmd = parse_one_vql("SELECT chr, pos FROM variants")
    print(cmd)

See test_vql.py for usage and features.

"""
import textx
from pkg_resources import resource_string


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


class VQLSyntaxError(ValueError):
    def __init__(self, message, col=None, *args, **kwargs):
        super().__init__(message, col, *args, **kwargs)
        self.message = message
        self.col = col

    def __repr__(self):
        if self.col:
            return "VQLSyntaxError: '%s' at position %s" % (self.message, self.col)
        return "VQLSyntaxError: '%s'" % self.message

    def __str__(self):
        return self.__repr__()


# ============ Error handle ==================================
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


# ============ Different class to map with VQL model


class FilterTerm(metaclass=model_class):
    @property
    def value(self):
        field = self.field.value if hasattr(self.field, "value") else self.field
        val = self.val.value if hasattr(self.val, "value") else self.val
        return {"field": field, "operator": self.op, "value": val}


class FilterExpression(metaclass=model_class):
    @property
    def value(self):
        out = []
        key = "AND"  # By default
        for i in self.op:
            if isinstance(i, str):
                if i in ("AND", "OR"):
                    key = i
                else:
                    out.append(i)
            else:
                out.append(i.value)
        return {key: out}


class SetExpression(metaclass=model_class):
    @property
    def value(self):
        return "test"


class FilterOperand(metaclass=model_class):
    @property
    def value(self):
        return self.op.value


class Function(metaclass=model_class):
    @property
    def value(self):
        if not self.extra:
            self.extra = "gt"
        return (self.func, self.arg, self.extra)


class Tuple(metaclass=model_class):
    @property
    def value(self):
        return tuple(self.items)


class WordSetIdentifier(metaclass=model_class):
    @property
    def value(self):
        return ("WORDSET", self.arg)


class SelectCmd(metaclass=model_class):
    @property
    def value(self):
        output = {
            "cmd": "select_cmd",
            "fields": [
                col.value if hasattr(col, "value") else col for col in self.fields
            ],
            "source": self.source,
        }

        if self.filter:
            output["filters"] = self.filter.value
        else:
            output["filters"] = {}

        if self.group_by:
            output["group_by"] = [
                i.value if isinstance(i, Function) else i for i in self.group_by
            ]

        else:
            output["group_by"] = []

        if self.having_op and self.having_val:
            output["having"] = {"op": self.having_op, "value": self.having_val}
        else:
            output["having"] = {}

        return output


class CreateCmd(metaclass=model_class):
    @property
    def value(self):
        return {
            "cmd": "create_cmd",
            "source": self.source,
            "filters": self.filter.value if self.filter else {},
            "target": self.target,
        }


class SetCmd(metaclass=model_class):
    @property
    def value(self):
        return {
            "cmd": "set_cmd",
            "target": self.target,
            "first": self.first,
            "operator": self.op,
            "second": self.second,
        }


class BedCmd(metaclass=model_class):
    @property
    def value(self):
        return {
            "cmd": "bed_cmd",
            "target": self.target,
            "source": self.source,
            "path": self.path,
        }


class CopyCmd(metaclass=model_class):
    @property
    def value(self):
        return {
            "cmd": "create_cmd",
            "source": self.source,
            "filters": {},
            "target": self.target,
        }


class CountCmd(metaclass=model_class):
    @property
    def value(self):
        obj = {
            "cmd": "count_cmd",
            "source": self.source,
            "filters": self.filters.value if self.filters else {},
        }

        return obj


class DropCmd(metaclass=model_class):
    @property
    def value(self):
        return {"cmd": "drop_cmd", "feature": self.feature, "name": self.name}


class ShowCmd(metaclass=model_class):
    @property
    def value(self):
        return {"cmd": "show_cmd", "feature": self.feature}


class ImportCmd(metaclass=model_class):
    @property
    def value(self):
        return {
            "cmd": "import_cmd",
            "feature": self.feature,
            "path": self.path,
            "name": self.name,
        }


METAMODEL = textx.metamodel_from_str(
    resource_string(__name__, "vql.tx").decode(),  # grammar extraction from vql.tx
    classes=model_class.classes,
    debug=False,
    ignore_case=True,
)


def parse_vql(raw_vql: str) -> list:
    """Execute multiline VQL statement separated by ";"

    Returns:
         (generator[dict]): yield 1 VQL object (a dictionnary) per command

    Example of VQL object::

        {
            'cmd': 'select_cmd',
            'columns': ['chr','pos'],
            'source':'variants',
            'filter': 'None'
        }
    """
    try:
        raw_model = METAMODEL.model_from_str(raw_vql)
    except textx.exceptions.TextXSyntaxError as err:
        raise VQLSyntaxError(*error_message_from_err(err, raw_vql))

    yield from (command.value for command in raw_model.commands)


def parse_one_vql(raw_vql: str) -> dict:
    """Execute 1 VQL statement

    Returns:
        (dict): 1 VQL object

    Examples of VQL object::

        {
            'cmd': 'select_cmd',
            'columns': ['chr','pos'],
            'source':'variants',
            'filter': 'None'
        }
    """
    return next(parse_vql(raw_vql))
