# Schema alignment (read-only study of Fixed_Network_Analytics)

No files were modified in the source repository. Field aliases below were
derived from `link_ip_schema.py`, `native_graph.py`, NetLynx contracts, and
`DATA_INVENTORY.md`.

## Topology / SOC-style rows

| Logical field | Accepted headers (examples) |
|---------------|-----------------------------|
| A end | AEnd, AEnd_NE, Router, Source, NodeA |
| Z end | ZEnd, ZEnd_NE, Destination, Dest, NodeB |
| Capacity Mbps | Capacity, Capacity (Mbps), Capacity_Mbps |
| Util % | Max_Util, InUti, OutUti, pct_in, pct_out |
| Role | Interface_Type, role (LAG_PARENT / LAG_MEMBER / PHYSICAL) |
| Weight | weight, metric, cost |

Parallel parent rows between the same unordered endpoints aggregate capacity;
members do not.

## FACT observations

| Logical field | Accepted headers |
|---------------|------------------|
| Link id | LinkID, link_id |
| Snapshot | SnapshotTime, Snapshot Time |
| Ends | AEnd_NE, ZEnd_NE |
| Interface | Interface_Type |
| Util | InUti, OutUti (fraction 0–1 → percent; values >1 treated as percent) |
| Capacity | Capacity, Capacity_Mbps |
| State | State, Status_Tag |

Stable observation key intent: `(LinkID, SnapshotTime, InterfaceType)`.

## Null semantics

`na`, `n/a`, `nan`, `none`, `null`, `--`, blank → `None`. Never coerced to 0.

## Data entry into GROK_NETWORK_ANALYTICS

1. Operator supplies local CSV/rows (not committed to Git).
2. `publish_link_topology` / `publish_observations` / `publish_ftth_mapping`.
3. GenerationStore validate → publish → promote.
4. UI and engines read only promoted or LKG.

Synthetic helper: `python tools/publish_sample_data.py`
