# Changelog

All notable changes to this project are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/2.0.0/),
and this project adheres to
[Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.2.0] - 2026-10-08

### Changed

- **Breaking:** `CreditCardImporter` keeps the direct debit that settles the
  card, which it used to drop. Pass `ignore_settlements=True` to keep dropping
  it.

### Added

- `AccountStatementImporter` reads the monthly Kontoauszug PDF into a balance
  assertion. It reads the designs since 2020; a design it does not know can be
  supported by passing a `Layout` subclass.
- `CreditCardImporter(..., ignore_settlements=True)` skips the direct debit
  that settles the card, for ledgers that book it from the paying account.
- Docstrings and type annotations on the importers.
- Changelog and issue tracker links in the project metadata.
- The changelog and the tests in the source distribution.

### Fixed

- `AccountImporter` skips pending rows ("Umsatz vorgemerkt"), which could
  change once booked and then escape deduplication.

## [0.1.0] - 2026-09-28

### Added

- `AccountImporter` for the CSV-CAMT and filtered CSV account exports.
- `CreditCardImporter` for the credit card CSV export.

[Unreleased]: https://github.com/henrisota/beancount-sparkasse/compare/v0.2.0...HEAD
[0.2.0]: https://github.com/henrisota/beancount-sparkasse/compare/v0.1.0...v0.2.0
[0.1.0]: https://github.com/henrisota/beancount-sparkasse/releases/tag/v0.1.0
