import csv
import datetime
from decimal import Decimal

from beancount.core import flags
from beangulp.importers import csvbase


class Dialect(csv.excel):
    delimiter = ";"


class Importer(csvbase.Importer):
    encoding = "iso-8859-1"
    dialect = Dialect
    comments = None

    def __init__(self, account: str, flag: str = flags.FLAG_WARNING) -> None:
        super().__init__(account, "EUR", flag)

    def identify(self, filepath: str) -> bool:
        try:
            return any(self.read(filepath))
        except OSError, UnicodeDecodeError, csv.Error, IndexError, KeyError, ValueError:
            return False

    def filename(self, filepath: str) -> str:
        return f"{self.name}.csv"


class Text(csvbase.Column):
    def __init__(self, *names: str, required: bool = False, default=None) -> None:
        super().__init__(*names, default=default)
        self.required = required

    def getter(self, names):
        index = next((names[name] for name in self.names if name in names), None)
        if index is None and self.required:
            raise KeyError(f"none of the columns {self.names} found")

        def get(row):
            value = row[index].strip() if index is not None and index < len(row) else ""
            return self.parse(value) if value else self.default

        return get

    def parse(self, value: str):
        return " ".join(value.split())


class Date(Text):
    def parse(self, value: str) -> datetime.date:
        return parse_date(value)


class Amount(Text):
    def parse(self, value: str) -> Decimal:
        return parse_amount(value)


class Iban(Text):
    def parse(self, value: str) -> str:
        return normalize_iban(value)


def parse_date(value: str) -> datetime.date:
    for fmt in ("%d.%m.%y", "%d.%m.%Y"):
        try:
            return datetime.date.strptime(value.strip(), fmt)
        except ValueError:
            continue
    raise ValueError(f"unrecognized date: {value!r}")


def parse_amount(value: str) -> Decimal:
    return Decimal(value.strip().replace(".", "").replace(",", "."))


def normalize_iban(value: str) -> str:
    return "".join(value.split()).upper()
