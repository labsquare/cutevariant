from abc import ABC, abstractclassmethod
from schema import Schema, And,Or, Use, Regex, Optional

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
    def _get_variants(self):
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
    def _get_fields(self):
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


    def _get_samples(self):
        return []



    def get_fields(self, **args):
        """
        Yield valid fields after schema cleanup

        :fields: generator or list of fields 
        :category: keep only field within a category .. should replace get_field_by_category
        """

        checker = Schema({
               "name": And(str, Use(str.lower)), 
               "type": lambda x: x in ["str","int","bool","float"],
               "category": lambda x: x in ["variants","annotations","samples"],
               "description": str,
                Optional("constraint", default="NULL"): str

              })  

        for field in self._get_fields():
            valid_field = checker.validate(field)
            if "category" in args:
                if args["category"] == field["category"]:
                    yield valid_field
            else:
                yield valid_field


    def get_variants(self):
        """
        Yield valid fields after schema cleanup

        :variants: generator or list of variants
        """

        checker = Schema({
               "chr": And(Use(str.lower),str),
               "pos": int,
               "ref":And(Use(str.upper),Regex(r'^[ACGTN]+')), 
               "alt":And(Use(str.upper),Regex(r'^[ACGTN]+')), 
                Optional(str): Or(int,str,bool, float, None), 
                
                Optional("annotations"): [{
                "gene":str, 
                "transcript":str, 
                Optional(str): Or(int,str,bool,float)
                }],

                Optional("samples"): [{
                "name":str, "gt":And(int, lambda x: x in [-1,0,1,2])
                }]
  
              })


        for variant in self._get_variants():
            checker.validate(variant)

            yield variant
 

    def get_samples(self):

        return self._get_samples()


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
        return len(tuple(self.get_variants()))

    def get_samples(self) -> str:
        """ 
        Return samples list. 
        Subclass this method to have samples in sqlite database 
        """
        return self._get_samples()


    def get_extra_fields(self):
        """
        Mandatory fields to add automatically

        ..todo: Move this methods somewhere else .. 
        ..warning: DEPRECTATED

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

        ..warning: DEPRECTATED
        """

        yield from self.parse_variants()

