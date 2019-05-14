from cutevariant.core import vql 



a = next(vql.execute_vql("SELECT chr FROM variants WHERE some_field IN (43,4)"))

print(a)

