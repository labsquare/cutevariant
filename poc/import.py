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
    replace("#CHROM",'chr','') as CHROM,
    POS,REF,
    unnest(split(ALT,',')) AS ALT,
    {gt_field} 
    FROM read_csv_auto('{filename}',   delim='\t',types={{'#CHROM':'VARCHAR'}})
    ) TO '{output}'
    """
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
        CAST ("{sample}"['gt']=1 AS INT) as count_het,
        CAST("{sample}"['gt']=2 AS INT) as count_hom 
        FROM '{filename}' 
        ON CONFLICT DO UPDATE SET count_hom = count_hom + excluded.count_hom, count_het = count_het + excluded.count_het
        """
    )


def create_genotype(input, output):
    columns = duckdb.sql(f"DESCRIBE SELECT * FROM '{input}'").fetchall()
    columns = [col[0] for col in columns]
    samples = columns[4:]

    for s in samples:
        q = f"""
        COPY (
        SELECT hash(CHROM,POS,REF,ALT) as id, "{s}"['gt'] as gt FROM '{input}' WHERE gt > 0
        ) TO '{output}/{s}.parquet'"""
        duckdb.sql(q)


if __name__ == "__main__":
    from glob import glob
    import os

    conn = duckdb.connect("demo.db")

    duckdb.sql("SET enable_progress_bar=1")

    create_tables(conn)

    try:
        os.mkdir("genotypes")
    except:
        pass

    # Met des fichiers VCF ici
    files = [
        "./M48.snps.vcf",
        "./M46.snps.vcf",
        "./JAS_N36.GATK.snp.vcf",
        "./JAS_P18.GATK.snp.vcf",
    ]

    for file in files:
        print(f"===== {file} =====")
        pfile = file + ".parquet"
        samples = extract_samples(file)

        print("conversion du VCF en parquet ")
        vcf_to_parquet(file, pfile)
        print("Extraction des genotypes")
        create_genotype(pfile, "genotypes/")
        print("Insertions des variants à la bases")
        for sample in samples:
            insert_variant(conn, pfile, sample)
