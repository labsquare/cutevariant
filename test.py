from textx import metamodel_from_file



mm = metamodel_from_file("test.tx")

model = mm.model_from_file("test.txt")

print(model)