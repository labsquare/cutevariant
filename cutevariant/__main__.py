from pathlib import Path
from cutevariant.core.project import DataLake

# Dossier core:
#  - datalake.py
#  - crud.py
#  - vql.py
# Dossier reader
# Dossier writer

if __name__ == "__main__":
    conn = DataLake(Path("/home/charles/Projets-Cutevariant/Maladies-rares"))

    # Crée le dossier du projet avec son architecture:
    # Dossier genotypes:
    #  - BySample:
    #     - sampleA.genotypes.parquet
    #     - sampleA2.genotypes.parquet
    #     - sampleB.genotypes.parquet
    #     - ...
    #  - ByPartition:
    #     - part0.genotypes.parquet
    #     - part1.genotypes.parquet
    #     - ...
    # Dossier annotations:
    #  - gnomad.parquet
    #  - clinvar.parquet
    #  - ...
    # Dossier aggregates:
    #  - variants.parquet (hash, chrom, pos, ref, alt, hom_count, het_count)
    # Un fichier de base de données:
    #  - datalake.db
    #    - table variants: hash, favorites, comments, tags, ...
    #    - table samples: sample_hash, sample_name, father, mother, sex, affected, tags, ...
    #    - table projects: projectID, name, description, list_of_samples
    # Si on ajoute un VCF:
    # COPY (SELECT DISTINCT hash, chrom, pos, ref, alt FROM [variants.parquet, incoming.parquet]) TO .variants.parquet
    # Rename .variants.parquet to variants.parquet

    # Crée le dossier du projet avec son architecture telle que décrite plus haut
    conn.init()

    conn.import_vcf(
        Path("/home/charles/Bioinfo/SampleVCFs/Pneumo230111/filteredvcf/all.vcf.gz")
    )

    # Exemple de requête traduite en DuckDB:
    # """
    # SELECT chr, pos, ref, alt , c.gt, b.gt, s.affected
    # FROM aggregates/variants.parquet v
    # JOIN genotypes/papa.parquet papa ON papa.id = v.id
    # JOIN genotypes/maman.parquet maman ON maman.id = v.id
    # JOIN genotypes/sacha.parquet sacha ON sacha.id = v.id
    # JOIN samples on s.name = ‘boby’ OR s.name = ‘charles’
    # JOIN annotations/bed/ENS_OK.parquet bed ON bed.chrom = v.chrom bed.start < v.pos AND bed.end > v.pos
    # WHERE c.gt > 0 AND s.affected = True
    # """

    # SELECT chrom, sample['papa'].gt, pos, ref, alt, hom_count, het_count
    # FROM 'Famille Rousseau'
    # WHERE chrom = 'chr1' AND pos > 100000000 AND pos < 1000000000 AND hom_count > 0 AND sample['papa'].gt = 1 AND sample['$all'].gt = 1

    # df = conn.query(
    #     fields=[
    #         "chrom",
    #         "sample['papa'].gt",
    #         "pos",
    #         "ref",
    #         "alt",
    #         "hom_count",
    #         "het_count",
    #     ],
    #     filters={
    #         "$and": [
    #             {"chrom": {"$eq": "chr1"}},
    #             {"pos": {"$gt": 100000000}},
    #             {"pos": {"$lt": 1000000000}},
    #             {"hom_count": {"$gt": 0}},
    #             {"sample['papa'].gt": {"$eq": 1}},
    #             {"sample['$all'].gt": {"$eq": 1}},
    #         ]
    #     },
    #     samples=["papa", "maman", "sacha"],
    #     limit=50,
    #     offset=0,
    #     order_by=[("pos", "asc"), ("chrom", "desc")],
    # )
