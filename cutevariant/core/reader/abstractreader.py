from abc import ABC, abstractclassmethod


class AbstractReader(ABC):
    """ 
    This is the base class for all Reader required to import variants into database.
    Subclass it if you want a new file parser .

    Attributes:
        device : a file object typically returned by open()
        file_size: file size in bytes ( todo : for progress bar )

    Example: 
        with open(filename,"r") as file: 
            reader = Reader()
            reader.get_variants()
    """

    def __init__(self, device):
        super(AbstractReader, self).__init__()
        self.device = device
        self.file_size = 0

    @abstractclassmethod
    def get_variants(self):
        """
        This abstract method must return variants as a list of dictionnary. 

        :return: a generator of variants 
        
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
    def get_fields(self):
        """
        This abstract methods must return fields description defined from parse_variant output.
        You must define sqlite type for each field (text, integer, bool)

        :return: a generator of fields 

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


    def get_fields_by_category(self, category:str):
        """ 
        Suggar to get fields according it category

        :param category can be usually variants, samples, annotations  

        """ 
        for field in self.get_fields():
            if field["category"] == category:
                yield field


    def get_variants_count(self) -> int:
        """ 
        Return variant count from the device . 
        You can overload this method to make it faster
        """
        count = 0
        for v in self.get_variants():
            count += 1
        return count

    def get_samples(self) -> str:
        """ 
        Return samples list. 
        Subclass this method to have samples in sqlite database 
        """
        return []


    def get_extra_fields(self):
        """
        Mandatory fields to add automatically

        ..todo: Move this methods somewhere else .. 
        ..warning: deprectated

        """
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

    def get_extra_variants(self):
        """
        decorator for get_fields

        ..warning: deprectated
        """

        yield from self.parse_variants()
