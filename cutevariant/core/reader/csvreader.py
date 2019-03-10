from .abstractreader import AbstractReader
import csv


class CsvReader(AbstractReader):
    def __init__(self, device):
        super(CsvReader, self).__init__(device)

    def __del__(self):
        del (self.device)

    def get_samples(self):
        return ["boby", "sacha", "olivier"]

    def parse_fields(self):
        self.device.seek(0)
        csvreader = csv.reader(self.device, delimiter="\t")
        rows = next(csvreader)
        for row in rows:
            row = row.replace("#", "")
            yield {"name": row, "type": "text", "category": None, "description": None}

    def parse_variants(self):
        self.device.seek(0)
        csvreader = csv.reader(self.device, delimiter="\t")
        next(csvreader)
        for row in csvreader:
            variant = {}
            variant["chr"] = row[0]
            variant["pos"] = row[1]
            variant["ref"] = row[2]
            variant["alt"] = row[3]

            # testing purpose
            variant["samples"] = [
                {"name": "boby", "gt": 0},
                {"name": "sacha", "gt": 1},
                {"name": "olivier", "gt": 2},
            ]

            yield variant


if __name__ == "__main__":
    print("yello")
