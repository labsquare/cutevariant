
import sqlite3 
import random 
import os
from string import ascii_letters
import time


VARIANT_COUNT = 300_000
ANNOTATION_COUNT_PER_VARIANT = 4

ANNOTAION_FIELD_COUNT = 10


def generate_field_name(size=5):
    return "".join(random.sample(ascii_letters,size))


def generate_annotation(count = ANNOTATION_COUNT_PER_VARIANT):
    for i in range(count):
        item = {}
        for j in range(ANNOTAION_FIELD_COUNT):
            item[f"field{j}"] = "value" + str(random.randint(1,10))

        yield item


def generate_variant(count=10):
    for i in range(count):
        yield {
        "chr": "chr"+str(random.choice(range(1,22))),
        "pos": random.randint(1000, 100000),
        "ref":random.choice(list("ACGT")),
        "alt": random.choice(list("ACGT")),
        "annotations" : list(generate_annotation())
        }


try:
    os.remove("/tmp/benchmark.db")
except:
    pass 

conn = sqlite3.connect("/tmp/benchmark.db")

print("create database")

cursor = conn.cursor()
cursor.execute("CREATE TABLE variants (chr TEXT, pos INT, ref TEXT, alt TEXT)")

schema = ",".join(["variant_id INT"] + [f"field{j} TEXT" for j in range(ANNOTAION_FIELD_COUNT)])


cursor.execute(f"CREATE TABLE annotations ({schema})") 


cache_size = 500
count = 0
for variant in generate_variant(VARIANT_COUNT):
    count += 1
    cursor.execute('INSERT INTO variants VALUES (:chr,:pos,:ref,:alt)', variant)
    variant_id = cursor.lastrowid

    for annotation in variant["annotations"]:
        annotation["variant_id"] = variant_id

        schema = ",".join([":variant_id"] + [f":field{j}" for j in range(ANNOTAION_FIELD_COUNT)])

        cursor.execute(f"INSERT INTO annotations VALUES ({schema})", annotation)



    # Commit cache
    if count > cache_size:
        conn.commit()
        count = 0


conn.commit()
cursor.execute("CREATE INDEX annotation_idx ON annotations (variant_id)") 

print("run query")


start = time.time()
cursor.execute("SELECT * FROM variants LEFT JOIN annotations ON annotations.variant_id = variants.rowid LIMIT 0,100")
end = time.time()

print("query executed in ", (end-start) * 1000, "ms")