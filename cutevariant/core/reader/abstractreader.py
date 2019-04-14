from abc import ABC, abstractclassmethod


class AbstractReader(ABC):
    """ 
    This is the base class for all Reader required to import variants into database.


    """

    def __init__(self, device):
        super(AbstractReader, self).__init__()
        self.device = device
        self.file_size = 0

    @abstractclassmethod
    def parse_variants(self):
        """
        This abstract method must return variants as a list of dictionnary. 
        
        Minimum output:
        ===============
        [
        {"chr": "chr3","pos": 3244,"ref": "A","alt":"C"},
        {"chr": "chr4","pos": 3244,"ref": "A","alt":"C"},
        {"chr": "chr5","pos": 3244,"ref": "A","alt":"C"}
        ]

        Full output:
        ============
        [
        {"chr": "chr3",
        "pos": 3244,
        "ref": "A",
        "alt":"C", 
        "field_n": "value_n",
        "annotations": [ 
            {"gene": "GJB2", "transcripts": "NM_00232.1", "field_n": "value_n"},
            {"gene": "GJB2", "transcripts": "NM_00232.2", "field_n": "value_n"}
            ],
        "samples": [
            {"name":"boby", "gt": 1, "field_n":"value_n"},
            {"name":"kevin", "gt": 1, "field_n":"value_n"}
            ]}
        ]
        """
        raise NotImplemented()

    @abstractclassmethod
    def parse_fields(self):
        """
        This abstract methods must return fields description defined from parse_variant output.
        You must define sqlite type for each field (text, integer, bool)

        Full output:
        ==============
        [
        {"name": "chr", "type": "text", "category": "variant", "description": "description"}, 
        {"name": "pos", "type": "text", "category": "variant", "description": "description"}, 
        {"name": "ref", "type": "text", "category": "variant", "description": "description"}, 
        {"name": "alt", "type": "text", "category": "variant", "description": "description"}, 
        {"name": "field_n", "type": "text", "category": "variant", "description": "description"},
        {"name": "name", "type": "text", "category": "annotations", "samples": "description"},
        {"name": "gt", "type": "text", "category": "annotations", "samples": "description"}
        ]
       """
        raise NotImplemented()

    def get_variants_count(self):
        """ 
        Return variant count. You can overload this method to make it faster
        """
        count = 0
        for v in self.get_variants():
            count += 1
        return count

    def get_samples(self):
        return []

    def get_fields(self):
        """decorator for get_fields"""
        yield from self.parse_fields()
        yield {
            "name": "description",
            "type": "text",
            "category": "extra",
            "description": "description of variant",
        }
        yield {
            "name": "favoris",
            "type": "bool",
            "category": "extra",
            "description": "is favoris",
            "default": False,
        }

    def get_variants(self):
        """decorator for get_fields"""
        yield from self.parse_variants()
