import datetime
from decimal import Decimal
from pathlib import Path

import pytest
from beangulp import testing

from beancount_sparkasse import AccountImporter, CreditCardImporter
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
