import re
from collections.abc import Callable, Iterator
from typing import Any

from beancount.core import data, flags

from ._csv import Amount, Date, Importer, Text


def _digits(value: str) -> str:
    return re.sub(r"[^0-9]", "", value)


class CardNumber(Text):
    """A card number column, reduced to the digits it shows."""

    def parse(self, value: str) -> str:
        return _digits(value)


class Joined(Text):
    """The non-empty values of several columns, joined by a space."""

    def getter(self, names: dict[str, int]) -> Callable[[list[str]], str]:
        getters = [Text(name).getter(names) for name in self.names]
        return lambda row: " ".join(filter(None, (get(row) for get in getters)))


class CreditCardImporter(Importer):
    """The credit card's CSV export, one transaction per row.

    Args:
        card: The card number as printed, masked digits included.
        account: The account the card's transactions are booked to.
        flag: The flag extracted transactions carry.
        ignore_settlements: Skip the card's record of the direct debit that
            pays it, for ledgers that book the settlement from the account it
            is paid from.
    """

    card_number = CardNumber("Umsatz getätigt von", required=True)
    date = Date("Buchungsdatum", required=True)
    amount = Amount("Buchungsbetrag", required=True)
    currency = Text("Buchungswährung", default="EUR")
    description = Text("Transaktionsbeschreibung", default="")
    narration = Joined("Transaktionsbeschreibung", "Transaktionsbeschreibung Zusatz")
    receipt_date = Date("Belegdatum")
    original_amount = Amount("Originalbetrag")
    original_currency = Text("Originalwährung")
    exchange_rate = Text("Umrechnungskurs")
    reference = Text("Buchungsreferenz")
    country = Text("Länderkennzeichen")
    merchant_category = Text("Gebührenschlüssel")

    def __init__(
        self,
        card: str,
        account: str,
        flag: str = flags.FLAG_WARNING,
        ignore_settlements: bool = False,
    ) -> None:
        super().__init__(account, flag)
        self.card = _digits(card)
        self.ignore_settlements = ignore_settlements

    @property
    def name(self) -> str:
        return f"sparkasse.card.{self.card[-4:]}"

    def read(self, filepath: str) -> Iterator[Any]:
        return (
            row
            for row in super().read(filepath)
            if row.card_number[:4] == self.card[:4]
            and row.card_number[-4:] == self.card[-4:]
        )

    def metadata(self, filepath: str, lineno: int, row: Any) -> data.Meta:
        meta = super().metadata(filepath, lineno, row)
        for key in ("receipt_date", "reference", "country", "merchant_category"):
            if value := getattr(row, key):
                meta[key.replace("_", "-")] = value
        if row.original_amount and row.original_currency:
            meta["original-amount"] = f"{row.original_amount} {row.original_currency}"
            if row.exchange_rate:
                meta["exchange-rate"] = row.exchange_rate
        return meta

    def finalize(self, txn: data.Transaction, row: Any) -> data.Transaction | None:
        if self.ignore_settlements and row.description.lower() == "lastschrift":
            return None
        return txn
