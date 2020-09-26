class State(object):
    """Store application state variable"""

    def __init__(self):

        # query
        self.fields = ["favorite", "chr", "pos", "ref", "alt"]
        self.source = "variants"
        self.filters = {}
        self.group_by = []
        self.having = {}

        # selected variants
        self.current_variant = None
