import polars as pl


class AbstractReader:
    def __init__(self, filename: str) -> None:
        self.filename = filename

    def samples(self) -> pl.LazyFrame:
        raise NotImplementedError()

    def variants(self) -> pl.LazyFrame:
        raise NotImplementedError()

    def genotypes(self) -> pl.LazyFrame:
        raise NotImplementedError()
