import duckdb
from xopen import xopen


def extract_samples(filename):
    with xopen(filename) as file:
        for line in file:
            line = line.strip()
            if line.startswith("#"):
                if line.startswith("#CHROM"):
                    return line.split("\t")[9:]

            else:
                return []


def create_tables(conn):
    conn.sql(
        "CREATE TABLE IF NOT EXISTS variants(id UINT64 PRIMARY KEY, chrom VARCHAR, pos UINT64, ref VARCHAR, alt VARCHAR)"
    )


def import_variant(conn, filename: str):
    q = f"""
    INSERT OR IGNORE INTO variants
    SELECT hash(CHROM,POS,REF,ALT) as ID, CHROM, POS, REF, ALT FROM 
    (SELECT "#CHROM" as CHROM, POS,REF, unnest(split(ALT,',')) AS ALT FROM read_csv_auto('{filename}'))
    """
    conn.sql(q)


def create_genotype(name: str, filename: str, output: str):
    q = f"""
    COPY (
    SELECT hash(CHROM,POS,REF,ALT) as hash, l2[list_position(l1,'GT')] AS gt, l2[list_position(l1,'DP')] AS dp, split(l2[list_position(l1,'AD')],',') AS ad  FROM (
    SELECT "#CHROM" as chrom, pos,ref, unnest(split(ALT,',')) AS alt, split(FORMAT,':') as l1, split({name},':') as l2 FROM read_csv_auto('{filename}'))
    WHERE GT SIMILAR TO '[01][/|][01]') TO '{output}' """

    duckdb.sql(q)


if __name__ == "__main__":
    from glob import glob

    conn = duckdb.connect("demo.db")

    duckdb.sql("SET enable_progress_bar=true")

    filename = (
        "./ALL.chr1.shapeit2_integrated_snvindels_v2a_27022019.GRCh38.phased.vcf.gz"
    )

    print("extract samples ")
    samples = extract_samples(filename)

    print("create tables")
    create_tables(conn)
    print("import variants")
    import_variant(conn, filename)
    print("create genotypes")
    create_genotype("NA20127", filename, f"genotypes/NA20127.parquet")
