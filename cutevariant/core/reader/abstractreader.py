from abc import ABC, abstractclassmethod


class AbstractReader(ABC):
    def __init__(self, device):
        super(AbstractReader, self).__init__()
        self.device = device

    @abstractclassmethod
    def get_variants(self):
        raise NotImplemented()

    @abstractclassmethod
    def get_fields(self):
        raise NotImplemented()

    def get_samples(self):
        return []
