# Architecture

## Product areas

The unified navigation is Overview, Route Path Analysis, NetLynx, Data, and Admin.

## Ownership

| Domain | Owns | Does not own |
|--------|------|--------------|
| Route Path Analysis | Native path computation, capacity / utilisation / bottleneck semantics, ECMP, alternates, N4I, FTTH, engineering history | Device collection, vendor parsers, universal operational truth |
| NetLynx | Inventory / access paths, collectors (disabled by default), raw CLI evidence, vendor parsers, operational normalisation, FACT / dimensions / trends / anomalies, scheduler / control | Weekly planning workbooks, route meaning |
| Shared | UI shell, config, versioned cross-domain contracts, immutable-generation lifecycle, runtime state, security, locking, artifacts, common status vocabulary | Domain-specific engines or parsers |

## Runtime boundaries

- Configurable reference / data / runtime / artifact roots resolve with `pathlib`.
- Domain packages never contain absolute legacy user paths.
- Application binds loopback (`127.0.0.1`) by default.
- Collection and live topology are disabled by default and cannot be triggered by navigation.
- Admin writes require authentication, CSRF / audit controls, and single-writer coordination (to be implemented).

## Data architecture summary

Logical layers: REFERENCE → RAW → NORMALIZED → DIMENSIONS → HISTORY → DERIVED → RUNTIME → ARTIFACTS.

Immutable generation directories contain data plus a manifest. An atomic pointer selects the promoted generation. Readers never infer authority from newest filename or mtime. Last-known-good remains visible on failed promotion.

Planning / reference truth and operational / observed truth remain distinct. Disagreement is recorded with provenance rather than overwritten.

## Full end-state scope

In addition to the core RPA + NetLynx + Shared platform, the architecture is designed to support:

- DFON / physical segment mapping and separate routing metric / engineering cost
- OLT homing
- NOC affected topology (cases, combined graphs, drill-down)
- Gated live topology (disabled by default, allowlisted, auditable)
