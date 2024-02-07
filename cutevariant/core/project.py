import os
import duckdb as db
from pathlib import Path


from cutevariant.core.reader.vcf_import import import_vcf


class DataLake:
    def __init__(self, path: Path):
        self.path = path

    def init(self):
        if not os.path.isdir(self.path):
            os.makedirs(self.path)

        os.makedirs(self.path / "genotypes", exist_ok=True)
        os.makedirs(self.path / "variants", exist_ok=True)
        os.makedirs(self.path / "annotations", exist_ok=True)
        os.makedirs(self.path / "aggregates", exist_ok=True)

        if not os.path.isfile(self.path / "datalake.db"):
            self.conn = db.connect(str(self.path / "datalake.db"))
            self.conn.execute(
                "CREATE TABLE variants (hash TEXT, favorites TEXT, comments TEXT, tags STRING[])"
            )
            self.conn.execute(
                "CREATE TABLE samples (hash TEXT, name TEXT, father TEXT, mother TEXT, sex TEXT, affected BOOLEAN, tags STRING[])"
            )
            self.conn.execute(
                "CREATE TABLE projects (projectID TEXT, name TEXT, description TEXT, list_of_samples STRING[])"
            )

    def import_vcf(self, path: Path):
        import_vcf(self.path, path)
