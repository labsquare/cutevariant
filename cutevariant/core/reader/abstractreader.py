from abc import ABC, abstractclassmethod


class AbstractReader(ABC):
    def __init__(self, device):
        super(AbstractReader, self).__init__()
        self.device = device
        self.file_size = 0

    @abstractclassmethod
    def get_variants(self):
        """
        Must return list of variant items . 
        exemple: {"chr": "chr3", "pos": 234 ....}
        """
        raise NotImplemented()

    def get_variants_count(self):
        count = 0
        for v in self.get_variants():
            count += 1
        return count

    @abstractclassmethod
    def get_fields(self):
        """
        must return list of field item with name, sqlite type, category and description 
        exemple: {"name": "chr", "type": "text", "category": None, "description": None} 
        """

        raise NotImplemented()

    def get_samples(self):
        return []
