from textx import metamodel_from_file



class FilterTerm(object):
    def __init__(self, **kwargs):
        self.field = kwargs["field"]
        self.op = kwargs["op"]
        self.val = kwargs["val"]

    def __str__(self):
        return f"{self.field} {self.op} {self.val}"

    @property
    def value(self):
        return {"field": self.field, "op": self.op, "value": self.val}
    


class FilterExpression(object):
    def __init__(self, **kwargs):
        self.op = kwargs["op"]
        self.parent = kwargs["parent"]

    @property
    def value(self):
        out = []
        key = None
        for i in self.op:
            if type(i) == str:
                if i in ("AND","OR"):
                    key = i
                else:
                    out.append(i)
            else:
                out.append(i.value)
        return {key: out}

    
class FilterOperand(object):
    def __init__(self, **kwargs):
        super().__init__()
        self.op = kwargs["op"]


    def __str__(self):
        return str(self.op)

    @property
    def value(self):
        return self.op.value
    



mm = metamodel_from_file("test.tx",  classes=[FilterTerm,FilterOperand, FilterExpression])

model = mm.model_from_file("test.txt")

print(model.filter.value)