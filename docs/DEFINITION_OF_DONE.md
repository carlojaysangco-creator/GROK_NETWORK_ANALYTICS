# Definition of Done checklist

## Runtime

- [x] Boots on `127.0.0.1` with collection/live off
- [x] `network-analytics check` returns status ok
- [x] `/healthz` ok

## Data platform

- [x] GenerationStore create → validate → publish → promote / LKG
- [x] Publish topology CSV/XLSX
- [x] Publish FACT streaming CSV
- [x] Publish FTTH / DFON / OLT / Gold / DimLink modules
- [x] `build-daily` from FACT
- [x] Data page lists dataset pointers

## RPA

- [x] Weekly path analysis (ECMP + alternates)
- [x] Daily fail-closed without daily generation
- [x] Compare Weekly/Daily
- [x] FTTH Access → Homing BNG
- [x] Signed BW, bottleneck, remaining
- [x] N4I floor + Gold exclusion audit
- [x] Pyvis path artifacts
- [x] Multi-pair batch helper + JSON export
- [x] Parity golden membership tests

## NetLynx

- [x] Offline FACT monitoring table
- [x] NOC cases + Pyvis case topology
- [x] Trend transition events
- [x] DimLink + consistency check helper
- [x] Live allowlist + job registry (gated, no sockets)

## Safety

- [x] No legacy V73 tree
- [x] Write lock on publish
- [x] Null-safe numerics
- [x] Artifacts path traversal protected

## Operator steps (cannot be automated without files)

- [ ] Point CLI at real SOC/FACT/mapping paths on the operator machine
- [ ] Optional: authorise live validation in a later controlled task

## Verify locally

```bash
pip install -e ".[test,rpa]"
pytest -q
network-analytics publish-sample
network-analytics build-daily
network-analytics serve
```
