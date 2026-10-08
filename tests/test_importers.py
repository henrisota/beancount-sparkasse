import datetime
import re
from decimal import Decimal
from pathlib import Path

import pytest
from beancount.core import data
from beancount.core.amount import Amount
from beangulp import testing
from fpdf import FPDF

from beancount_sparkasse import (
    AccountImporter,
    AccountStatementImporter,
    CreditCardImporter,
    Layout,
)
from beancount_sparkasse._csv import parse_amount, parse_date

DATA = Path(__file__).parent / "data"

ACCOUNT = AccountImporter(
    iban="DE17 1234 5678 0000 0000 01", account="Assets:Bank:Checking"
)
OTHER_ACCOUNT = AccountImporter(
    iban="DE11 1111 1111 1111 1111 11", account="Assets:Bank:Checking"
)
CARD = CreditCardImporter(card="4111 **** **** 1111", account="Liabilities:CreditCard")
OTHER_CARD = CreditCardImporter(
    card="4000 **** **** 9999", account="Liabilities:CreditCard"
)

IMPORTERS = {
    "camt.csv": ACCOUNT,
    "filtered.csv": ACCOUNT,
    "card.csv": CARD,
}


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        ("1.234,56", Decimal("1234.56")),
        ("832,9", Decimal("832.9")),
        ("-190", Decimal(-190)),
        ("-87,43", Decimal("-87.43")),
    ],
)
def test_parse_amount(value: str, expected: Decimal) -> None:
    assert parse_amount(value) == expected


@pytest.mark.parametrize("value", ["15.02.26", "15.02.2026"])
def test_parse_date(value: str) -> None:
    assert parse_date(value) == datetime.date(2026, 2, 15)


@pytest.mark.parametrize(
    ("importer", "document"),
    [
        (ACCOUNT, "card.csv"),
        (ACCOUNT, "empty.csv"),
        (OTHER_ACCOUNT, "camt.csv"),
        (CARD, "camt.csv"),
        (CARD, "empty.csv"),
        (OTHER_CARD, "card.csv"),
    ],
)
def test_identify_rejects(importer, document: str) -> None:
    assert not importer.identify(str(DATA / document))


@pytest.mark.parametrize("document", IMPORTERS)
def test_extract(document: str) -> None:
    importer = IMPORTERS[document]
    path = str(DATA / document)
    assert importer.identify(path)
    expected = f"{path}.beancount"
    assert not testing.compare_expected(expected, *testing.run_importer(importer, path))


STATEMENT = AccountStatementImporter(
    iban="DE17 1234 5678 0000 0000 01", account="Assets:Bank:Checking"
)
HEADER = (
    "Kontoauszug 4/2026                                        Seite 1 von 1",
    "Girokonto 1234567, DE17 1234 5678 0000 0000 01",
)


def statement(path: Path, *lines: str) -> str:
    """Render the lines of a Kontoauszug as a PDF with a text layer."""
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Courier", size=8)
    for line in (*HEADER, *lines):
        pdf.cell(text=line, new_x="LMARGIN", new_y="NEXT")
    pdf.output(str(path))
    return str(path)


@pytest.mark.parametrize(
    ("lines", "date", "amount"),
    [
        pytest.param(
            (
                "Kontostand am 31.03.2026, Auszug Nr. 3                 1.000,00",
                "Kontostand am 30.04.2026 um 20:04 Uhr               4.217,38",
            ),
            datetime.date(2026, 4, 30),
            Decimal("4217.38"),
            id="2021",
        ),
        pytest.param(
            ("Kontostand am 30.04.2026 um 20:04 Uhr                  -312,05",),
            datetime.date(2026, 4, 30),
            Decimal("-312.05"),
            id="2021-negative",
        ),
        pytest.param(
            (
                "Kontostand am 31.01.2020, Auszug Nr.    1              1.000,00+",
                "Kontostand am 28.02.2020 um 20:04 Uhr               1.234,42+",
            ),
            datetime.date(2020, 2, 28),
            Decimal("1234.42"),
            id="2020",
        ),
        pytest.param(
            ("Kontostand am 28.02.2020 um 20:04 Uhr                  312,05-",),
            datetime.date(2020, 2, 28),
            Decimal("-312.05"),
            id="2020-negative",
        ),
    ],
)
def test_statement_layouts(
    tmp_path: Path, lines: tuple[str, ...], date: datetime.date, amount: Decimal
) -> None:
    path = statement(tmp_path / "statement.pdf", *lines)
    assert STATEMENT.identify(path)
    assert STATEMENT.date(path) == date
    assert STATEMENT.filename(path) == "sparkasse.0001.auszug-2026-04.pdf"
    _, _, _, entries = testing.run_importer(STATEMENT, path)
    assert entries == [
        data.Balance(
            {
                "filename": path,
                "lineno": 0,
                "document": f"{date}.sparkasse.0001.auszug-2026-04.pdf",
            },
            date + datetime.timedelta(days=1),
            "Assets:Bank:Checking",
            Amount(amount, "EUR"),
            None,
            None,
        )
    ]


def test_statement_unknown_layout(tmp_path: Path) -> None:
    path = statement(tmp_path / "statement.pdf", "Saldo am 30.04.2026  4.217,38")
    assert STATEMENT.identify(path)
    with pytest.raises(ValueError, match="no known Kontoauszug layout"):
        STATEMENT.date(path)


def test_statement_custom_layout(tmp_path: Path) -> None:
    class Saldo(Layout):
        closing_line = re.compile(r"Saldo am (?P<date>[\d.]+)\s+(?P<amount>[\d.,]+)")

    importer = AccountStatementImporter(
        iban="DE17 1234 5678 0000 0000 01",
        account="Assets:Bank:Checking",
        layouts=[Saldo()],
    )
    path = statement(tmp_path / "statement.pdf", "Saldo am 30.04.2026  4.217,38")
    assert importer.date(path) == datetime.date(2026, 4, 30)


def test_statement_identify_rejects(tmp_path: Path) -> None:
    other = AccountStatementImporter(
        iban="DE11 1111 1111 1111 1111 11", account="Assets:Bank:Checking"
    )
    path = statement(
        tmp_path / "statement.pdf",
        "Kontostand am 30.04.2026 um 20:04 Uhr               4.217,38",
    )
    broken = tmp_path / "broken.pdf"
    broken.write_text("not a pdf")
    assert not other.identify(path)
    assert not STATEMENT.identify(str(broken))
    assert not STATEMENT.identify(str(DATA / "camt.csv"))


def test_ignore_settlements() -> None:
    importer = CreditCardImporter(
        card="4111 **** **** 1111",
        account="Liabilities:CreditCard",
        ignore_settlements=True,
    )
    _, _, _, entries = testing.run_importer(importer, str(DATA / "card.csv"))
    assert [e.narration for e in entries if isinstance(e, data.Transaction)] == [
        "Streaming Service Premium",
        "CITY MUSEUM",
        "HOTEL AM MARKT",
    ]
