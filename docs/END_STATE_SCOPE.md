# Full End-State Scope

This repository targets the complete intended platform, not only the initial convergence baseline.

## Core platform (foundation → usable product)

- Native Route Path Analysis (Weekly, Daily, Compare, FTTH)
- NetLynx operational monitoring pages and trends
- Shared data platform (generations, promotion, LKG, tabular)
- Unified Dash UI with the five primary areas
- Safe local defaults and configuration

## Future phases (designed in from the start)

### DFON / physical segment mapping

- Map one logical link to ordered physical segments (DFON / FOC / DIRECT_PATCH / UNKNOWN)
- Separate routing metric from engineering cost
- Explicit UNKNOWN; no invented production cost values
- Schema, validator, and Admin source status

### OLT homing

- Preserve direct, dual-homed, ambiguous, stale, missing, unknown, and zero-OLT states
- Bounded hover samples and lazy-load full filterable details

### NOC affected topology

- Recent Down, High Utilisation Comparison, Total Down / Utilisation Comparison
- Combined All Affected OLT-to-BNG graph
- Filters, drill-down, raw evidence, stable CaseId, artifact identity, LKG / reopen
- Page reads only promoted data and never collects

### Gated live topology

- Disabled by default
- Authenticated request, device / jump / command allowlists
- Job ownership, state machine, bounded timeouts, concurrency limits, cancellation, kill switch
- Immutable redacted raw evidence and parser lineage
- No real connection until an explicit later validation task; record `LIVE_VALIDATION_PENDING` until then

## Acceptance posture

Every phase must preserve the protected behaviour foundations and the generation / promotion contract. New features are added behind explicit contracts and feature flags rather than by mutating existing calculation meaning.
