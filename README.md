# beancount-sparkasse

[Beancount](https://beancount.github.io/) v3 importer for Sparkasse online
banking exports, built on [beangulp](https://github.com/beancount/beangulp).

`AccountImporter` reads the account exports **CSV-CAMT** and
**CSV - gefilterte Einträge**.

```python
import beangulp
from beancount_sparkasse import AccountImporter

importers = [
    AccountImporter(iban="DE17 1234 5678 0000 0000 01", account="Assets:Bank:Checking"),
]

if __name__ == "__main__":
    beangulp.Ingest(importers)()
```

## Development

```
uv run pytest
```
