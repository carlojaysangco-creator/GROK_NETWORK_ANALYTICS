# GROK Network Analytics

Clean native Network Analytics platform (no legacy V73 tree).

## Capability (current main)

- **GenerationStore** – immutable generations, atomic promotion, LKG
- **RPA** – ECMP defaults, alternates, signed BW, N4I floor, remaining capacity
- **Weekly / Daily / Compare** – Daily fail-closed; Compare dual analysis
- **FTTH** – mapping + Access NE → Homing BNG paths
- **DFON / OLT** – segment and homing publish/load contracts
- **NetLynx** – offline FACT, monitoring, NOC cases (down / high util)
- **Admin + CLI** – local CSV/XLSX publish under write lock
- **Loaders** – `publish-topology` (csv/xlsx), `publish-fact`, `publish-ftth`, `build-daily`

## Quick start

```bash
python -m venv .venv && source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -e ".[test,rpa]"
pytest -q
network-analytics check
network-analytics publish-sample
network-analytics build-daily          # after FACT exists
network-analytics serve                # http://127.0.0.1:8050
```

### Bring your own files (local paths, not Git)

```bash
network-analytics publish-topology path/to/SOC.xlsx --sheet weekly_latest_week
network-analytics publish-fact path/to/FACT.csv
network-analytics publish-ftth path/to/mapping.xlsx
network-analytics build-daily
```

## Safety defaults

Loopback only · collection off · live topology off · null ≠ 0 · members not in capacity.

## Status

Foundation + Milestone B loaders/compare/daily builder are on `main`.
Still ahead: large-FACT streaming publish, Gold role policy depth, full NOC graphs,
live topology (gated), auth beyond write lock, parity golden set from operator cases.
