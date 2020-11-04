import os
import csv

import cutevariant.commons as cm

LOGGER = cm.logger()


class PedReader:
    r"""PED \*.tfam file (PLINK sample information file) parser

    Data has the same structure of a tfam file object
    https://www.cog-genomics.org/plink/1.9/formats#fam
    http://zzz.bwh.harvard.edu/plink/data.shtml

    Format description:
        A tabular/white space separated text file with no header line, and one
        line per sample with the following six fields:

        - Family ID (str): ('FID'); ex: "Valse"
        - Within-family ID (str): ('IID'; cannot be '0'); ex: "Emmanuel"
        - Within-family ID of father (str): ('0' if father isn't in dataset)
        - Within-family ID of mother (str): ('0' if mother isn't in dataset)
        - Sex code (int): ('1' = male, '2' = female, '0' or other = unknown)
        - Phenotype value (int): ('1' = control, '2' = case, '-9'/'0'/non-numeric = missing data if case/control)
            We expect '0' for this last one.

    Notes:
        Comments are lines starting with a # character.
        The rest of that line will be ignored.

    Recall, DB structure:
        - id INTEGER PRIMARY KEY ASC,
        - name TEXT,
        - family_id TEXT DEFAULT 'fam',
        - father_id INTEGER DEFAULT 0,
        - mother_id INTEGER DEFAULT 0,
        - sex INTEGER DEFAULT 0,
        - phenotype INTEGER DEFAULT 0

    TODO:
        Detect if an individual has unknown sex but appears in mother_id or
        father_id of a family.
    """

    def __init__(self, filepath: str, samples: dict, raw_samples=True, *args, **kwargs):
        """

        Args:
            filepath (str): PED filepath
            samples (dict): Database current samples. Each key is a field
                of the table named "samples". We use this dict to apply unicity
                constraints over family_id vs individual_id, father_id and
                mother_id.
                Must be not empty if `raw_samples` is `False`.
            raw_samples (boolean):
                - If raw_samples are activated (default), samples are lists of fields.
                - If raw_samples are not activated, samples are dict of fields
                  ready to be inserted in the database according to the given samples.

        """
        assert os.path.isfile(filepath)
        assert (samples and not raw_samples) or raw_samples, \
            "If raw_samples are deactivated, database samples must be given"

        self.filepath = filepath
        self.samples = samples
        self.raw_samples = raw_samples

    def __iter__(self):
        """Generator on PED file

        PED file is opened as a tabulated or white space separated file.
        """
        with open(self.filepath, "r") as stream:
            # Sniff dialect of CSV file
            dialect = csv.Sniffer().sniff(stream.read(10000), delimiters="\t ")
            stream.seek(0)

            reader = csv.reader(
                (row for row in stream if not row.startswith('#')),  # Remove comments
                dialect
            )

            yield from self.get_samples(reader)

    def get_samples(self, reader):
        """Yield samples from PED file

        Notes:
            The following problems with samples are detected:
                - Not digit sex/phenotype: Exception raised
                - Sex/phenotype not expected (0,1,2): Individual skipped
                - Unknown individual_id: Individual skipped
                - If samples are given, not found family_id, individual_id couple:
                  Individual skipped.
                  i.e.: And individual not already in DB is skipped.
                - If samples are given, not found family_id, father_id/mother_id:
                  Added as unknown.

        Returns:
            (generator[dict/list]): Generator of samples.
                - If raw_samples are activated (default), samples are lists of fields.
                - If raw_samples are not activated, samples are dict of fields
                  ready to be inserted in the database according to the given samples.

            Example::

                `[family_id, individual_id, father_id, mother_id, sex, phenotype]`
                Or
                `["id": _, "family_id": _, "father_id": _, "mother_id": _, "sex": _, "phenotype": ]`
        """
        samples_mapping = {
            (sample["family_id"], sample["name"]): sample["id"] for sample in self.samples
        }

        for index, line in enumerate(reader, 1):
            if len(line) < 6:
                LOGGER.error(
                    "PED file conformity line <%s>; too few fields; expected at least 6",
                    index,
                )
                continue

            # Extract and validate data
            family_id = line[0]
            individual_id = line[1]
            father_id = line[2]
            mother_id = line[3]
            sex = int(line[4]) if line[4].isdigit() else 0
            phenotype = int(line[5]) if line[5].isdigit() else 0

            if sex not in (0, 1, 2):
                LOGGER.error(
                    "PED file conformity line <%s>; sex code <%s> not expected",
                    index,
                    sex,
                )
                continue

            if phenotype not in (0, 1, 2):
                LOGGER.error(
                    "PED file conformity line <%s>; phenotype code <%s> not expected",
                    index,
                    sex,
                )
                continue

            if individual_id == "0":
                LOGGER.error(
                    "PED file conformity line <%s>; Within-family ID/Sample name can't be '0'",
                    index,
                )
                continue

            # Test presence of sample in DB
            individual_key = (family_id, individual_id)
            if samples_mapping and individual_key not in samples_mapping.keys():
                LOGGER.error(
                    "PED file conformity line <%s>; sample (family_id, individual_id):"
                    "<%s, %s> not found in database",
                    index, family_id, individual_id,
                )
                continue

            # Test presence of parents in DB
            father_key = (family_id, father_id)
            mother_key = (family_id, mother_id)
            if samples_mapping and {father_key, mother_key} - samples_mapping.keys():
                # If set not empty: 1 tuple is not found in DB
                # => will be replaced by 0 (unknown)
                LOGGER.warning(
                    "PED file conformity line <%s>; parent sample (family_id, parent_id),"
                    "father: <%s> or mother: <%s> not found in database",
                    index, father_key, mother_key,
                )

            if self.raw_samples:
                new_sample = [
                    family_id,
                    individual_id,
                    father_id,
                    mother_id,
                    sex,
                    phenotype,
                ]

            else:

                new_sample = {
                    "id": samples_mapping[individual_key],  # Get DB sample id
                    "family_id": family_id,
                    "father_id": samples_mapping.get(father_key, 0),
                    "mother_id": samples_mapping.get(mother_key, 0),
                    "sex": sex,
                    "phenotype": phenotype,
                }

            # print(new_sample)
            yield new_sample
