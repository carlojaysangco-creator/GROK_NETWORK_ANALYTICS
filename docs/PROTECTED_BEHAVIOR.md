# Protected Behaviour Foundations

Changes to any protected behaviour require captured baseline inputs / outputs, focused tests, semantic comparison, documented decision, and rollback path.

## Core invariants (carried forward)

### Route Path Analysis

- Native engine is the sole calculation authority (no legacy V73 source tree in this repository).
- Weekly is the planning default.
- Daily and Compare are explicit operational selections and must not silently fall back to Weekly.
- Canonical equal-minimum-weight path membership and deterministic ordering.
- Default ECMP shares bandwidth; display-only alternates never replace defaults or receive the default share.
- Signed bandwidth supports added and removed traffic; utilisation floors at zero.
- Parallel parents aggregate once; LAG members are diagnostics and never double-count capacity or traffic.
- Gold role lookup wins with controlled name fallback; routing policy owns weights and caps.
- Path result types include at least: FULL_PATH, PARTIAL_PATH, NO_PATH, FAILED_LOOKUP.

### NetLynx

- Collection is disabled by default and cannot be triggered by page load or filter.
- Raw evidence precedes parser and normalisation.
- FACT + dimensions form one coherent dated / batch cohort.
- LAG_PARENT is logical authority; LAG_MEMBER remains relationship / diagnostic.
- Trends and events preserve source timestamps and transition meaning.
- Status values (`fresh`, `delayed`, `stale`, `down`, `unknown`, `missing`, `unavailable`) remain distinct.

### Cross-domain

- A missing numeric value is null / unavailable, never silently zero.
- Planning truth and observed operational truth may disagree; both provenance records survive.
- Readers resolve only a promoted generation (or last-known-good).

## Future protected extensions

The following will receive their own protected contracts when implemented:

- DFON / physical segment mapping and separate routing metric / engineering cost
- OLT homing states (direct, dual-homed, ambiguous, stale, missing, unknown, zero-OLT)
- NOC affected topology case identity and artifact stability
- Live topology job ownership, allowlists, timeouts, and cancellation
