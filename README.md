# beancount-sparkasse

[Beancount](https://beancount.github.io/) v3 importers for Sparkasse online
banking exports and statements, built on
[beangulp](https://github.com/beancount/beangulp).

- `AccountImporter` reads the account exports **CSV-CAMT** and
  **CSV - gefilterte Einträge**.
- `CreditCardImporter` reads the credit card export.
- `AccountStatementImporter` reads the monthly **Kontoauszug** PDF into a
  balance assertion. The CSV exports carry no running balance, so this is what
  checks the ledger against the bank.

The card export also lists the direct debit that settles each statement. A
ledger that books the settlement from the account it is paid from would count
it twice; `CreditCardImporter(..., ignore_settlements=True)` skips it.

```python
import beangulp
from beancount_sparkasse import (
    AccountImporter,
    AccountStatementImporter,
    CreditCardImporter,
)

importers = [
    AccountImporter(iban="DE17 1234 5678 0000 0000 01", account="Assets:Bank:Checking"),
    CreditCardImporter(card="4111 **** **** 1111", account="Liabilities:CreditCard"),
    AccountStatementImporter(
        iban="DE17 1234 5678 0000 0000 01", account="Assets:Bank:Checking"
    ),
]

if __name__ == "__main__":
    beangulp.Ingest(importers)()
```

## Statement layouts

`AccountStatementImporter` knows the Kontoauszug designs since 2020, which
differ in how they sign amounts. A statement in a design it does not know
fails to import rather than being misread. Until a release supports a new
design, subclass `Layout` for it and pass it ahead of the built-in ones:

```python
import re

from beancount_sparkasse import LAYOUTS, AccountStatementImporter, Layout


class Layout2027(Layout):
    closing_line = re.compile(r"Saldo am (?P<date>[\d.]+)\s+(?P<amount>-?[\d.]+,\d{2})")


AccountStatementImporter(
    iban="DE17 1234 5678 0000 0000 01",
    account="Assets:Bank:Checking",
    layouts=[Layout2027(), *LAYOUTS],
)
```

## Development

With Nix and direnv, `direnv allow` enters a shell with uv and Python, synced
dependencies and the hooks installed; `nix develop` does the same without
direnv. Without Nix:

```
uv run prek install --hook-type pre-commit --hook-type pre-push
```

Then `uv run pytest`, or `pytest` inside the Nix shell.

## Releasing

Pushing a `v*` tag publishes to PyPI with attestations and creates the GitHub
release, its notes taken from the version's section of `CHANGELOG.md`. The
release fails before publishing if `pyproject.toml` disagrees with the tag or
the changelog has no section for it, and waits for approval of the `pypi`
environment.

```
uv version --bump minor
# Rename CHANGELOG.md's Unreleased section to the new version and update the
# compare links at the bottom.
git commit -am "Release 0.2.0"
git tag -a v0.2.0 -m v0.2.0
git push origin main v0.2.0
```
