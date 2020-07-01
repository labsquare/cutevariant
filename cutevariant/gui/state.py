class State(object):

    """This class store application state variable 
    """

    def __init__(self):

        #  query
        self.fields = ["chr", "pos", "ref", "alt", "consequence"]
        self.source = "variants"
        self.filters = {}
        self.group_by = []

        #  selected variants
        self.current_variant = None
