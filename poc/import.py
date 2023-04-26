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

    return []


def create_tables(conn):
    q = """
    CREATE TABLE IF NOT EXISTS variants(
    id UINT64 PRIMARY KEY,
    chrom VARCHAR,
    pos UINT64,
    ref VARCHAR,
    alt VARCHAR,
    count_het UINT32 DEFAULT 0,
    count_hom UINT32 DEFAULT 0,
    count_var AS (count_het + count_hom)

    )
    """

    conn.sql(q)


def vcf_to_parquet(filename: str, output: str):
    samples = extract_samples(filename)

    gt_field = """
    {{
    "gt": CAST(list_aggr(CAST(split(replace(replace(split("{0}",':')[1],'.','0'),'|','/'),'/') AS UINT8[]),'sum') AS UINT8),
    }} AS "{0}"

    """
    gt_field = ",".join([gt_field.format(sample) for sample in samples])

    q = f"""
    COPY (
    SELECT 
    "#CHROM" as CHROM,
    POS,REF,
    unnest(split(ALT,',')) AS ALT,
    {gt_field} 
    FROM read_csv_auto('{filename}',   delim='\t',types={{'#CHROM':'VARCHAR'}})
    ) TO '{output}'
    """
    print(q)
    duckdb.sql(q)


def insert_variant(conn, filename, sample):
    conn.sql(
        f"""
        INSERT INTO variants(id,chrom,pos,ref,alt, count_het,count_hom) 
        SELECT 
        hash(chrom,pos,ref,alt) as id,
        chrom,
        pos,
        ref,
        alt,
        CAST ({sample}['gt']=1 AS INT) as count_het,
        CAST({sample}['gt']=2 AS INT) as count_hom 
        FROM '{filename}' 
        ON CONFLICT DO UPDATE SET count_hom = count_hom + excluded.count_hom, count_het = count_het + excluded.count_het
        """
    )

    conn.sql("SELECT * FROM variants").show()


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

    duckdb.sql("SET enable_progress_bar=1")

    create_tables(conn)
    filename = "./M48.snps.vcf"

    print("extract samples ")
    samples = extract_samples(filename)

    vcf_to_parquet("./M46.snps.vcf", "M46.parquet")
    vcf_to_parquet("./M48.snps.vcf", "M48.parquet")

    insert_variant(conn, "./M46.parquet", "M46")
    insert_variant(conn, "./M48.parquet", "M48")

    # vcf_to_parquet("./subset.vcf", "subset.parquet")

    # vcf_to_parquet(
    #     "./ALL.chr1.shapeit2_integrated_snvindels_v2a_27022019.GRCh38.phased.vcf.gz",
    #     "huge.parquet",
    # )

    # print("create tables")
    # create_tables(conn)
    # print("import variants")
    # import_variant(conn, filename)
    # import_variant(conn, "./M46.snps.vcf")

    # print("create genotypes")
    # create_genotype("NA20127", filename, f"genotypes/NA20127.parquet")
