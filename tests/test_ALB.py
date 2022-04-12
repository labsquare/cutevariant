conn = sql.create_sql_connection("/tmp/test.db")

sql.import_reader(conn, VcfReader("test1.vcf"))

# Faire des tests : 
assert len(sql.get_variants(conn)) ==  2

sql.import_reader(conn, VcfReader("test2.vcf"))

# Faire des tests 
sql.import_reader(conn, VcfReader("test3.vcf"))

# Faire des tests