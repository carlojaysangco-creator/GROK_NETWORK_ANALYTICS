# GROK Network Analytics

Clean, native-only Network Analytics platform for fixed-network engineering and operations.

This repository is a from-scratch implementation of the full end-state architecture originally defined for the Fixed Network Analytics convergence. It contains **no legacy V73 source tree** and treats the native engine as the sole calculation authority from day one.

## Ownership domains

| Domain | Responsibility |
|--------|----------------|
| **Route Path Analysis** | Engineering / planning path computation, capacity, utilisation, bottleneck, ECMP, alternates, N4I, FTTH, history |
| **NetLynx** | Collection (disabled by default), vendor parsers, operational normalisation, FACT / dimensions, trends, anomalies, monitoring |
| **Shared** | UI shell, versioned contracts, immutable generation lifecycle, runtime state, security, locking, artifacts |

## Non-negotiable rules

- Loopback bind (`127.0.0.1`) by default
- Collection and live topology disabled by default
- Immutable generations + atomic promotion + last-known-good
- Strict null and status semantics (`null` ≠ `0`)
- Planning truth and observed operational truth remain distinct
- No secrets in source, logs, or fixtures
- Domain packages never contain absolute legacy paths

## Quick start

```bash
python -m venv .venv
source .venv/bin/activate   # or .venv\\Scripts\\activate on Windows
pip install -e ".[test,rpa]"
network-analytics --check
network-analytics
```

The application listens on `http://127.0.0.1:8050` by default.

## Status

Foundation bootstrap in progress. Full end-state includes DFON / segment cost, OLT homing, NOC affected topology, and gated live topology.
