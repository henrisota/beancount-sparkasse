import csv
import datetime
import time
from collections.abc import Callable
from decimal import Decimal
from typing import Any

from beancount.core import flags
from beangulp.importers import csvbase


class Dialect(csv.excel):
    """Sparkasse's CSV dialect: Excel's, delimited by semicolons."""

    delimiter = ";"


class Importer(csvbase.Importer):
    """A Sparkasse CSV export in EUR, identified by having a row it reads."""

    encoding = "iso-8859-1"
    dialect = Dialect
    comments = None

    def __init__(self, account: str, flag: str = flags.FLAG_WARNING) -> None:
        super().__init__(account, "EUR", flag)

    def identify(self, filepath: str) -> bool:
        try:
            return any(self.read(filepath))
        except (
            OSError,
            UnicodeDecodeError,
            csv.Error,
            IndexError,
            KeyError,
            ValueError,
        ):
            return False

    def filename(self, filepath: str) -> str:
        return f"{self.name}.csv"


class Text(csvbase.Column):
    """A text column, its whitespace collapsed.

    Args:
        names: The column's header, under each name an export has used for it.
        required: Fail to read a file without the column rather than default.
        default: The value of an empty or missing cell.
    """

    def __init__(
        self, *names: str, required: bool = False, default: Any = None
    ) -> None:
        super().__init__(*names, default=default)
        self.required = required

    def getter(self, names: dict[str, int]) -> Callable[[list[str]], Any]:
        index = next((names[name] for name in self.names if name in names), None)
        if index is None and self.required:
            raise KeyError(f"none of the columns {self.names} found")

        def get(row: list[str]) -> Any:
            value = row[index].strip() if index is not None and index < len(row) else ""
            return self.parse(value) if value else self.default

        return get

    def parse(self, value: str) -> Any:
        return " ".join(value.split())


class Date(Text):
    """A date column, as ``15.02.26`` or ``15.02.2026``."""

    def parse(self, value: str) -> datetime.date:
        return parse_date(value)


class Amount(Text):
    """An amount column in German notation, as ``-1.234,56``."""

    def parse(self, value: str) -> Decimal:
        return parse_amount(value)


class Iban(Text):
    """An IBAN column, without spaces."""

    def parse(self, value: str) -> str:
        return normalize_iban(value)


def parse_date(value: str) -> datetime.date:
    """Parse a date as ``15.02.26`` or ``15.02.2026``."""
    for fmt in ("%d.%m.%y", "%d.%m.%Y"):
        try:
            return datetime.date(*time.strptime(value.strip(), fmt)[:3])
        except ValueError:
            continue
    raise ValueError(f"unrecognized date: {value!r}")


def parse_amount(value: str) -> Decimal:
    """Parse an amount in German notation, as ``-1.234,56``."""
    return Decimal(value.strip().replace(".", "").replace(",", "."))


def normalize_iban(value: str) -> str:
    """The IBAN in upper case, without spaces."""
    return "".join(value.split()).upper()
