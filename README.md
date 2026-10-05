# beancount-sparkasse

[Beancount](https://beancount.github.io/) v3 importers for Sparkasse online
banking exports, built on [beangulp](https://github.com/beancount/beangulp).

- `AccountImporter` reads the account exports **CSV-CAMT** and
  **CSV - gefilterte Einträge**.
- `CreditCardImporter` reads the credit card export.

The card export also lists the direct debit that settles each statement. A
ledger that books the settlement from the account it is paid from would count
it twice; `CreditCardImporter(..., ignore_settlements=True)` skips it.

```python
import beangulp
from beancount_sparkasse import AccountImporter, CreditCardImporter

importers = [
    AccountImporter(iban="DE17 1234 5678 0000 0000 01", account="Assets:Bank:Checking"),
    CreditCardImporter(card="4111 **** **** 1111", account="Liabilities:CreditCard"),
]

if __name__ == "__main__":
    beangulp.Ingest(importers)()
```

## Development

```
uv run prek install --hook-type pre-commit --hook-type pre-push
uv run pytest
```
