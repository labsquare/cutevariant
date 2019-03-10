from abc import ABC, abstractclassmethod




class AbstractReader(ABC):
    def __init__(self, device):
        super(AbstractReader, self).__init__()
        self.device = device
        self.file_size = 0

    @abstractclassmethod
    def parse_variants(self):
        """
        Must return list of variant items . 
        exemple: {"chr": "chr3", "pos": 234 ....}
        """
        raise NotImplemented()

    @abstractclassmethod
    def parse_fields(self):
        """
        must return list of field item with name, sqlite type, category and description 
        exemple: {"name": "chr", "type": "text", "category": None, "description": None} 
        """

        raise NotImplemented()

    def get_variants_count(self):
        count = 0
        for v in self.get_variants():
            count += 1
        return count



    def get_samples(self):
        return []


    def get_fields(self):
        """decorator for get_fields""" 
        yield from self.parse_fields()
        yield  {"name": "description", "type": "text", "category": "extra", "description": "description of variant"} 
        yield  {"name": "favoris", "type": "bool", "category": "extra", "description": "is favoris", "default": False} 


    def get_variants(self):
        """decorator for get_fields""" 
        yield from self.parse_variants()
           



    


