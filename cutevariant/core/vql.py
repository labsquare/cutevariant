"""Proof of concept for the VQL DSL.

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

        # escape if quoted
        if isinstance(val, str):
            val = f"'{val}'"

        return {"field": field, "operator": self.op, "value": val}


class FilterExpression(metaclass=model_class):
    @property
    def value(self):
        out = []
        key = "AND"  #  By default
        for i in self.op:
            if isinstance(i, str):
                if i in ("AND", "OR"):
                    key = i
                else:
                    out.append(i)
            else:
                out.append(i.value)
        return {key: out}


class FilterOperand(metaclass=model_class):
    @property
    def value(self):
        return self.op.value


class Function(metaclass=model_class):
    @property
    def value(self):
        return (self.func, self.arg, "gt")


class Tuple(metaclass=model_class):
    @property
    def value(self):
        return tuple(self.items)


class SelectCmd(metaclass=model_class):
    @property
    def value(self):
        output = {
            "cmd": "select_cmd",
            "columns": [
                col.value if hasattr(col, "value") else col for col in self.columns
            ],
            "source": self.source,
        }

        if self.filter:
            output["filter"] = self.filter.value

        return output


class CreateCmd(metaclass=model_class):
    @property
    def value(self):
        return {
            "cmd": "create_cmd",
            "source": self.source,
            "fitler": self.filter.value if self.filter else None,
        }


# class SetCmd(metaclass=model_class):
#     @property
#     def value(self):
#         return {
#         "cmd": "set_cmd",
#         "source": self.source,
#         "fitler": self.filter.value if self.filter else None
#         }


METAMODEL = textx.metamodel_from_str(
    resource_string(__name__, "vql.tx").decode(),  # grammar extraction from vql.tx
    classes=model_class.classes,
    debug=False,
    ignore_case=True,
)


def execute_vql(raw_vql: str) -> list:
    """Execute multiline VQL statement separated by ";"

    :return: yield 1 dictionnary per command
        .. example :: {'cmd': 'select_cmd', 'columns': ['chr','pos'], 'source':'variants', 'filter': 'None'}
    """
    try:
        raw_model = METAMODEL.model_from_str(raw_vql)
    except textx.exceptions.TextXSyntaxError as err:
        raise VQLSyntaxError(*error_message_from_err(err, raw_vql))

    yield from (command.value for command in raw_model.commands)


def model_from_string(raw_vql: str) -> dict:
    """Obsolete : retro compatibility"""
    return next(execute_vql(raw_vql))
