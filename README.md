# GROK Network Analytics

Clean, native-only Network Analytics platform for fixed-network engineering and operations.

No legacy V73 source tree. Native engine is the sole calculation authority.

## Ownership domains

| Domain | Responsibility |
|--------|----------------|
| **Route Path Analysis** | Path computation, capacity, utilisation, bottleneck, ECMP, alternates, FTTH, history |
| **NetLynx** | Collection (disabled by default), FACT/dimensions, trends, monitoring |
| **Shared** | UI shell, contracts, immutable generations, promotion, LKG, runtime state |

## Non-negotiable rules

- Loopback (`127.0.0.1`) by default
- Collection and live topology disabled by default
- Immutable generations + atomic promotion + last-known-good
- Missing numerics stay null (never coerced to 0)
- LAG_PARENT authority; members diagnostic only
- No secrets in source or Git

## Current capability

- GenerationStore (create → validate → publish → promote / LKG)
- Tabular link → graph builder (parallel parents aggregate; members excluded from capacity)
- Native equal-min-weight path selection + alternates
- Signed bandwidth overlay (ECMP share on defaults; util floors at 0)
- Publish topology / FACT cohorts into generations
- Interactive RPA page (demo graph)
- NetLynx page (promoted observations)
- Data page (lineage / pointers)
- Future-phase contracts: DFON/segments, OLT homing, NOC cases, gated live topology (disabled)

## Quick start

```bash
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\\Scripts\\activate
pip install -e ".[test,rpa]"
pytest -q
network-analytics --check
network-analytics
```

App: `http://127.0.0.1:8050`

## Status

Foundation through monitoring/lineage UI is in place. Next: Daily fail-closed path, FTTH mapping wiring, deeper Admin safety, and progressive implementation of future-phase contracts behind flags.
