class State:
    """Store application state variable

    Settings are mostly related to the display of variants.

    Attributes:
        - fields (list[str]): Pre-defined fields displayed on the UI
        - source (str): Pre-defined selection of variants
        - filters (dict): Pre-defined filters
        - group_by (list[str]): Pre-defined fields used to group variants
        - having (dict): TODO
    """

    def __init__(self):

        # query
        self.fields = ["favorite", "chr", "pos", "ref", "alt"]
        self.source = "variants"
        self.filters = {}
        self.group_by = []
        self.having = {}

        # selected variants
        self.current_variant = None
