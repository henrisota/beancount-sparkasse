import datetime
import functools
import logging
import re
from collections.abc import Sequence
from decimal import Decimal

import beangulp
from beancount.core import data
from beancount.core.amount import Amount
from pypdf import PdfReader
from pypdf.errors import PyPdfError

from ._csv import normalize_iban, parse_amount, parse_date

NUMBER = r"\d{1,3}(?:\.\d{3})*,\d{2}"
"""An unsigned amount in German notation, as ``1.234,56``."""

CLOSING = r"Kontostand am (?P<date>\d{2}\.\d{2}\.\d{4}) um [\d:]+ Uhr\s+"
"""The closing balance line up to its amount, capturing ``date``.

As in ``Kontostand am 30.04.2026 um 20:04 Uhr   4.217,38``; the opening
balance line carries ``, Auszug Nr.`` where this one carries the time.
"""


class Layout:
    """What one design of the Kontoauszug prints where the importer reads it.

    Sparkasse redesigns the statement every few years. A design is a subclass
    overriding what changed: at least `closing_line`, and `amount` when the
    amount is signed differently.
    """

    closing_line: re.Pattern[str]
    """The closing balance line, capturing ``date`` and ``amount``."""

    def matches(self, text: str) -> bool:
        """Whether a statement is in this design.

        Args:
            text: The statement's text layer.
        """
        return self.closing(text) is not None

    def number(self, text: str) -> tuple[int, int] | None:
        """The statement's year and its number within the year.

        Args:
            text: The statement's text layer.

        Returns:
            ``(year, number)``, or ``None`` when the statement prints none.
        """
        match = re.search(r"Kontoauszug (\d+)/(\d{4})", text)
        return (int(match[2]), int(match[1])) if match else None

    def closing(self, text: str) -> tuple[datetime.date, Decimal] | None:
        """The day the statement closes on and its balance at the end of it.

        Args:
            text: The statement's text layer.

        Returns:
            ``(date, balance)``, or ``None`` when no line matches
            `closing_line`.
        """
        match = self.closing_line.search(text)
        return (parse_date(match["date"]), self.amount(match)) if match else None

    def amount(self, match: re.Match[str]) -> Decimal:
        """The signed amount of a `closing_line` match.

        Args:
            match: A match of `closing_line`.
        """
        return parse_amount(match["amount"])


class Layout2021(Layout):
    """The design since Kontoauszug 11/2021: a minus leads a negative amount."""

    closing_line = re.compile(rf"{CLOSING}(?P<amount>-?{NUMBER})[ \t]*$", re.MULTILINE)


class Layout2020(Layout):
    """The one- and two-column designs up to Kontoauszug 10/2021: the sign
    trails every amount."""

    closing_line = re.compile(
        rf"{CLOSING}(?P<amount>{NUMBER}) ?(?P<sign>[+-])[ \t]*$", re.MULTILINE
    )

    def amount(self, match: re.Match[str]) -> Decimal:
        amount = parse_amount(match["amount"])
        return amount if match["sign"] == "+" else -amount


LAYOUTS: tuple[Layout, ...] = (Layout2021(), Layout2020())
"""The designs `AccountStatementImporter` reads by default."""


@functools.cache
def _text(filepath: str) -> str:
    # identify reads every PDF in the inbox, and pypdf warns on each damaged or
    # rotated invoice among them.
    logger = logging.getLogger("pypdf")
    level = logger.level
    logger.setLevel(logging.ERROR)
    try:
        pages = PdfReader(filepath).pages
        return "\n".join(page.extract_text(extraction_mode="layout") for page in pages)
    finally:
        logger.setLevel(level)


class AccountStatementImporter(beangulp.Importer):
    """The Kontoauszug of an account, as a balance assertion.

    The CSV exports carry no running balance, so the closing balance printed
    on the statement is what the ledger is checked against. The assertion is
    dated the day after the statement closes, since a statement closes at the
    end of its last day while an assertion holds at the start of its own. Its
    ``document`` metadata names the statement as the archive command files it.

    Args:
        iban: The account's IBAN, with or without spaces.
        account: The account the balance is asserted on.
        layouts: The designs to read a statement with; the first that matches
            reads it.

    Raises:
        ValueError: From `date`, `filename` and `extract`, for a statement in
            none of `layouts`.
    """

    def __init__(
        self, iban: str, account: str, layouts: Sequence[Layout] = LAYOUTS
    ) -> None:
        self.iban = normalize_iban(iban)
        self.importer_account = account
        self.layouts = layouts

    @property
    def name(self) -> str:
        return f"sparkasse.{self.iban[-4:]}.auszug"

    def identify(self, filepath: str) -> bool:
        if not filepath.lower().endswith(".pdf"):
            return False
        try:
            text = _text(filepath)
        except (OSError, PyPdfError):
            return False
        # The statement prints the IBAN in groups of four.
        return "Kontoauszug" in text and self.iban in "".join(text.split())

    def account(self, filepath: str) -> str:
        return self.importer_account

    def date(self, filepath: str) -> datetime.date:
        return self._closing(filepath)[0]

    def filename(self, filepath: str) -> str:
        found = self._layout(filepath).number(_text(filepath))
        if not found:
            raise ValueError(f"{filepath}: no statement number")
        year, number = found
        return f"{self.name}-{year}-{number:02}.pdf"

    def extract(self, filepath: str, existing: data.Entries) -> data.Entries:
        day, amount = self._closing(filepath)
        meta = data.new_metadata(filepath, 0)
        meta["document"] = f"{day}.{self.filename(filepath)}"
        return [
            data.Balance(
                meta,
                day + datetime.timedelta(days=1),
                self.importer_account,
                Amount(amount, "EUR"),
                None,
                None,
            )
        ]

    def cmp(self, entry: data.Directive, existing: data.Directive) -> bool:
        return (
            isinstance(entry, data.Balance)
            and isinstance(existing, data.Balance)
            and existing.date == entry.date
            and existing.account == entry.account
        )

    def _layout(self, filepath: str) -> Layout:
        text = _text(filepath)
        layout = next((layout for layout in self.layouts if layout.matches(text)), None)
        if not layout:
            raise ValueError(f"{filepath}: no known Kontoauszug layout")
        return layout

    def _closing(self, filepath: str) -> tuple[datetime.date, Decimal]:
        closing = self._layout(filepath).closing(_text(filepath))
        assert closing, "the layout matched on its closing balance"
        return closing
