from pydantic import BaseModel
from typing import Callable, Literal

from cutevariant.core.reader.abstractreader import AbstractReader


class Field(BaseModel):
    name: str
    category: Literal["variants", "annotations", "genotypes"]
    type: str
    description: str = ""


class AbstractDB:
    def __init__(self) -> None:
        pass

    def get_fields(self) -> list[Field]:
        raise NotImplementedError()

    def insert_fields(self, data: list[Field]):
        raise NotImplementedError()

    def insert_field(self, data: Field):
        self.insert_fields([data])

    def create(self):
        raise NotImplementedError()

    def import_reader(
        self,
        reader: AbstractReader,
        pedfile: str = None,
        project: dict = None,
        progress_callback: Callable = None,
    ):
        raise NotImplementedError()
