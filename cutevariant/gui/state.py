class State:
    """Store application state variable

    Settings are mostly related to the display of variants.

    Attributes:
        - fields (list[str]): Pre-defined fields displayed on the UI
        - source (str): Pre-defined selection of variants
        - filters (dict): Pre-defined filters
        - group_by (list[str]): Pre-defined fields used to group variants
        - having (dict): TODO
        - project_file_name (str): The absolute path to the project's file (can be used as a key to store project-specific user data)
    """

    def __init__(self):

        # query
        self.fields = ["favorite", "classification", "chr", "pos", "ref", "alt", "qual"]

        self.source = "variants"
        self.filters = {}

        # selected variants
        self.current_variant = None
