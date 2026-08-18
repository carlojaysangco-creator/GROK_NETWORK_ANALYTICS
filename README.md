# GROK Network Analytics

Clean native Network Analytics for fixed-network engineering and operations.
**No legacy V73 source tree.** NetworkX is the calculation authority; Pyvis is visualization only.

## Quick start (Windows / any OS)

```bash
python -m venv .venv
# Windows: .venv\Scripts\activate
source .venv/bin/activate
pip install -e ".[test,rpa]"
pytest -q
network-analytics check
network-analytics publish-sample
network-analytics build-daily
network-analytics serve
```

Open `http://127.0.0.1:8050` — RPA paths and NOC cases link to interactive topology HTML under `/artifacts/`.

## Operator data (local paths only)

```bash
network-analytics publish-topology path/to/SOC.xlsx --sheet weekly_latest_week
network-analytics publish-fact path/to/FACT.csv
network-analytics publish-ftth path/to/mapping.xlsx
network-analytics build-daily
```

## Product surface

| Area | Capability |
|------|------------|
| RPA | Weekly/Daily/Compare, ECMP, BW, FTTH, Pyvis path views, batch helper |
| NetLynx | FACT stream, cases, trends, DimLink check, NOC Pyvis |
| Data | Generation lineage / LKG for all datasets |
| Admin | CSV publish + write lock + audit log |
| Live | Allowlist + job registry only (no device sockets) |

## Safety

Loopback · collection off · live off · null ≠ 0 · LAG members diagnostic · Daily fail-closed.

See `docs/DEFINITION_OF_DONE.md` and `docs/WINDOWS.md`.
