"""Check a built distribution installs, imports and carries its type marker.

Run against each file in dist/ before it is published:

    uv run --isolated --no-project --with dist/*.whl tests/smoke.py
"""

from importlib.resources import files

from beancount_sparkasse import (
    AccountImporter,
    AccountStatementImporter,
    CreditCardImporter,
)

AccountImporter(iban="DE17 1234 5678 0000 0000 01", account="Assets:Bank:Checking")
AccountStatementImporter(
    iban="DE17 1234 5678 0000 0000 01", account="Assets:Bank:Checking"
)
CreditCardImporter(card="4111 **** **** 1111", account="Liabilities:CreditCard")
assert files("beancount_sparkasse").joinpath("py.typed").is_file()
