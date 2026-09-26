import re

from beancount.core import flags

from ._csv import Amount, Date, Importer, Text


def _digits(value: str) -> str:
    return re.sub(r"[^0-9]", "", value)


class CardNumber(Text):
    def parse(self, value: str) -> str:
        return _digits(value)


class Joined(Text):
    def getter(self, names):
        getters = [Text(name).getter(names) for name in self.names]
        return lambda row: " ".join(filter(None, (get(row) for get in getters)))


class CreditCardImporter(Importer):
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

    def __init__(self, card: str, account: str, flag: str = flags.FLAG_WARNING) -> None:
        super().__init__(account, flag)
        self.card = _digits(card)

    @property
    def name(self) -> str:
        return f"sparkasse.card.{self.card[-4:]}"

    def read(self, filepath: str):
        return (
            row
            for row in super().read(filepath)
            if row.card_number[:4] == self.card[:4]
            and row.card_number[-4:] == self.card[-4:]
        )

    def metadata(self, filepath, lineno, row):
        meta = super().metadata(filepath, lineno, row)
        for key in ("receipt_date", "reference", "country", "merchant_category"):
            if value := getattr(row, key):
                meta[key.replace("_", "-")] = value
        if row.original_amount and row.original_currency:
            meta["original-amount"] = f"{row.original_amount} {row.original_currency}"
            if row.exchange_rate:
                meta["exchange-rate"] = row.exchange_rate
        return meta

    def finalize(self, txn, row):
        return None if "lastschrift" in row.description.lower() else txn
