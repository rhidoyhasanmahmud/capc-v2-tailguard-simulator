# Stage A — Frozen CAPC-v1 Semantic-Equivalence Evidence

## Purpose

Stage A establishes a semantically equivalent CAPC-v1 baseline inside the CAPC-v2 TailGuard repository before any TailGuard redesign, parameter tuning, or confirmatory experiment is introduced.

The goal is preservation of the frozen simulator semantics, not performance improvement.

## Frozen reference

Reference repository:

`rhidoyhasanmahmud/capc-simulator`

Frozen reference revision:

`00d4e2ebd7af24bd6abf35578a2d40296fb4ddc6`

Frozen primary configuration SHA-256:

`be25b6dc8c89c3a49b891ea4c69e1c1dfe38b6e117d577bd8026c2d0094ba875`

## Stage A components reproduced

The baseline port includes:

- configuration schema and loading;
- deterministic MMPP trace generation;
- transaction and event models;
- atomic shard-lock management;
- coordination queue;
- worker-pool semantics;
- Static Atomic FIFO;
- frozen CAPC-v1 scheduler;
- CAPC ablation schedulers;
- diagnostic FIFO;
- simulation state;
- deterministic discrete-event simulation engine;
- metrics recording;
- output generation;
- run-level metric computation;
- paired experiment runner;
- paired-trace integrity checks;
- deterministic verification checks.

## Deterministic trace evidence

Development and frozen-primary configurations were checked across seeds:

`1, 7, 42, 77, 123, 999`

For the tested seeds, the old and new repositories produced identical:

- trace SHA-256;
- transaction counts;
- workload state-interval counts.

Frozen fixtures are encoded in the repository unit tests.

## Automated test status

At the Stage A completion point:

`23/23 tests passed`

using:

`PYTHONPATH=src python -m pytest -q`

## Verification gate

The frozen V1-V12 deterministic verification suite passed completely.

Verified properties include:

- trace reproducibility;
- cross-treatment trace equality;
- Static Atomic FIFO earliest-eligible ordering;
- diagnostic FIFO ordering;
- atomic lock exclusion;
- all-or-nothing lock release;
- multi-worker dispatch;
- CAPC score correctness;
- aging monotonicity and saturation;
- transaction accounting;
- low-load sanity;
- overload queue-growth behaviour.

Result:

`V1-V12: PASS`

`OVERALL: PASS`

## Cross-repository execution equivalence

A matched old-vs-new execution comparison was performed using:

- configuration: `configs/dev.yaml`;
- seed: `123`;
- schedulers:
  - `static_atomic_fifo`;
  - `capc`.

Both repositories produced the same trace hash:

`9294f86e44ba2899eedf092549507b76625d97f25d96a3c9217f5d104da71841`

For Static Atomic FIFO:

- completed cross-shard transactions: `278`;
- p99 latency: `0.27055751376881143 s`.

For CAPC:

- completed cross-shard transactions: `278`;
- p99 latency: `0.6926715763604928 s`.

The following research outputs were byte-for-byte identical between the frozen repository and the Stage A port for both schedulers:

- `transactions.csv`;
- `decisions.csv`;
- `dispatch_snapshots.csv`;
- `state_events.csv`;
- `trace.csv`;
- `workload_states.csv`;
- `summary.json`;
- `queue_recovery.json`;
- `effective_config.yaml`.

Result:

`SEMANTIC OUTPUT EQUIVALENCE: PASS`

## Interpretation

The collected evidence supports semantic equivalence of the reproduced CAPC-v1 baseline for the tested Stage A configurations, seeds, schedulers, and verification cases.

This evidence should not be interpreted as a formal proof of equivalence for every possible simulator input.

No TailGuard mechanism, CAPC-v2 parameter tuning, calibration result, validation result, or confirmatory performance claim is included in Stage A.

TailGuard development begins only after this baseline-equivalence gate.
