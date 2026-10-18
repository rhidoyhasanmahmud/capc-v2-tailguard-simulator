# Stage B2 — CAPC-v1 Tail-Polarization Diagnostic

## Purpose

Stage B2 investigates the mechanism associated with the adverse tail-latency behaviour observed under the frozen CAPC-v1 scheduler.

This stage is diagnostic only. No TailGuard scheduling rule, threshold, parameter tuning, calibration, or confirmatory claim is introduced.

## Diagnostic setup

Configuration:

`configs/dev.yaml`

Schedulers:

- `static_atomic_fifo`
- `capc`

Seeds:

`1, 7, 42, 77, 123, 999`

The scheduler pairs used identical exogenous traces for every seed.

The paired analysis was restricted to the official measurement interval:

- cross-shard transactions only;
- arrival time >= configured warmup;
- arrival time < configured simulation duration.

Total paired measurement transactions:

`1166`

Priority counts:

- HIGH: `262`
- LOW: `349`
- MEDIUM: `555`

## Priority-level paired effects

Values are CAPC minus Static Atomic FIFO.

### HIGH

- mean waiting-time difference: `-0.016319 s`
- p95 waiting-time difference: `0.000000 s`
- p99 waiting-time difference: `0.066438 s`
- mean bypass-count difference: `-0.347328`
- harmed fraction: `0.030534`
- improved fraction: `0.202290`

Interpretation:

HIGH-priority traffic generally receives fewer eligible bypasses and lower waiting delay under CAPC.

### LOW

- mean waiting-time difference: `+0.018633 s`
- p95 waiting-time difference: `+0.136678 s`
- p99 waiting-time difference: `+0.490329 s`
- mean bypass-count difference: `+0.369628`
- p95 bypass-count difference: `+2.0`
- p99 bypass-count difference: `+10.04`
- harmed fraction: `0.151862`
- improved fraction: `0.060172`

Interpretation:

LOW-priority traffic is the clearest recipient of adverse delay redistribution under CAPC, particularly in the upper tail.

### MEDIUM

- mean waiting-time difference: `-0.001882 s`
- p95 waiting-time difference: `+0.018608 s`
- p99 waiting-time difference: `+0.302877 s`
- mean bypass-count difference: `-0.048649`
- harmed fraction: `0.075676`
- improved fraction: `0.133333`

Interpretation:

MEDIUM traffic is close to neutral on average but still exhibits substantial adverse tail cases.

## Paired bypass-delay association

Spearman correlation between:

`CAPC extra bypass count` and `CAPC extra waiting time`

was:

- HIGH: `rho = 0.913358`
- LOW: `rho = 0.857678`
- MEDIUM: `rho = 0.870826`

The same pattern appears for latency differences.

These associations are strong, but they are not interpreted as independent causal proof because scheduler ordering, bypass accumulation, and waiting time are mechanically related.

## Extreme harmed transactions

Representative examples:

- seed 77, tx 247, LOW:
  - FIFO waiting: `0.167720 s`
  - CAPC waiting: `0.901095 s`
  - delta waiting: `+0.733375 s`
  - FIFO bypasses: `3`
  - CAPC bypasses: `16`
  - delta bypasses: `+13`

- seed 123, tx 610, LOW:
  - FIFO waiting: `0.068948 s`
  - CAPC waiting: `0.759884 s`
  - delta waiting: `+0.690936 s`
  - FIFO bypasses: `1`
  - CAPC bypasses: `15`
  - delta bypasses: `+14`

- seed 123, tx 473, MEDIUM:
  - FIFO waiting: `0.077674 s`
  - CAPC waiting: `0.492135 s`
  - delta waiting: `+0.414461 s`
  - FIFO bypasses: `1`
  - CAPC bypasses: `8`
  - delta bypasses: `+7`

## Diagnostic conclusion

The Stage B2 evidence is consistent with a priority-asymmetric service-opportunity redistribution mechanism:

- CAPC generally benefits HIGH-priority transactions;
- LOW-priority transactions experience the strongest adverse redistribution;
- MEDIUM traffic is near-neutral on average but includes severe tail cases;
- transactions suffering large CAPC-specific delay increases frequently accumulate substantially more eligible bypasses than under Static Atomic FIFO.

The evidence supports investigating a TailGuard mechanism that limits harmful repeated eligible overtaking while attempting to preserve useful priority responsiveness.

This stage does not establish that bypass accumulation is the sole cause of CAPC-v1 tail latency and does not yet justify any specific TailGuard threshold or policy.

## Research-integrity boundary

No TailGuard algorithm or parameter was selected using this diagnostic.

The next stage should define candidate protection mechanisms and evaluation criteria before calibration or parameter tuning begins.
