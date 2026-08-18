# Data Architecture

## Logical storage layers

- **REFERENCE** – validated planning workbooks and reference generations
- **RAW** – immutable, hashed, redacted CLI / source evidence
- **NORMALIZED** – parser output preserving source / job / row identity
- **DIMENSIONS** – versioned device / link / LAG / site / topology / reference cohorts
- **HISTORY** – appendable accepted observations, events, and path results
- **DERIVED** – promoted KPIs, paths, anomalies, cases, and analytical tables
- **RUNTIME** – SQLite-backed transactional job / scheduler / lock / pointer state
- **ARTIFACTS** – reports, exports, topology HTML / data, diagnostics

## Technology preferences

- Parquet preferred for immutable normalised observations and history
- DuckDB preferred for local analytical joins, filters, and aggregation
- SQLite limited to transactional control / runtime state
- CSV / Excel remain valid interchange and reference formats
- No server database, Docker, or cloud service is required for the local platform

## Generation contract

Each candidate generation records:

- DatasetName, SchemaVersion, GenerationId, ProducerVersion, ParserVersion
- Source path / job / snapshot identities and SHA-256
- Business, collection, ingestion, validation, publication, and promotion times
- Input, accepted, rejected, and duplicate-key counts
- Required-column, datatype / unit / range, null, uniqueness, and timestamp-range results
- Rejection evidence and validation status

Publication creates a new immutable directory. Promotion replaces a small pointer atomically. Readers validate the pointer / manifest and stay on last-known-good when a candidate fails.

## Explicit data-quality rules

- Null / missing is never coerced to `0` by default
- Utilisation units and plausible bounds are contract fields
- FACT / dimension promotion is cohort-based, not newest-file mixing
- LAG parent is logical authority; members are diagnostic only
- Planning versus observed disagreements remain side-by-side with provenance
