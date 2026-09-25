from beancount.core import flags

from ._csv import Amount, Date, Iban, Importer, Text, normalize_iban


class AccountImporter(Importer):
    own_iban = Iban("Auftragskonto", required=True)
    date = Date("Buchungstag", required=True)
    amount = Amount("Betrag", required=True)
    currency = Text("Waehrung", "Währung", default="EUR")
    payee = Text(
        "Beguenstigter/Zahlungspflichtiger",
        "Begünstigter/Zahlungspflichtiger",
        "Auftraggeber/Beguenstigter",
        "Auftraggeber/Begünstigter",
    )
    narration = Text("Verwendungszweck", default="")
    value_date = Date("Valutadatum")
    booking_text = Text("Buchungstext")
    counterparty_iban = Iban("Kontonummer/IBAN", "Kontonummer")
    creditor_id = Text("Glaeubiger ID", "Gläubiger-ID", "Glaeubiger-ID")
    mandate_reference = Text("Mandatsreferenz")
    customer_reference = Text("Kundenreferenz (End-to-End)", "Kundenreferenz")
    category = Text("Kategorie")

    def __init__(self, iban: str, account: str, flag: str = flags.FLAG_WARNING) -> None:
        super().__init__(account, flag)
        self.iban = normalize_iban(iban)

    @property
    def name(self) -> str:
        return f"sparkasse.{self.iban[-4:]}"

    def read(self, filepath: str):
        return (row for row in super().read(filepath) if row.own_iban == self.iban)

    def metadata(self, filepath, lineno, row):
        meta = super().metadata(filepath, lineno, row)
        for key in (
            "value_date",
            "booking_text",
            "creditor_id",
            "mandate_reference",
            "customer_reference",
            "category",
            "counterparty_iban",
        ):
            if value := getattr(row, key):
                meta[key.replace("_", "-")] = value
        return meta
