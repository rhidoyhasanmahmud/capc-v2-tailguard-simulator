# Stage A1 — Deterministic Trace Equivalence Evidence

## Purpose

Stage A1 establishes that the CAPC-v2 TailGuard repository reproduces the frozen CAPC-v1 exogenous workload-generation semantics before any scheduler redesign or tuning is introduced.

No CAPC-v2 scheduling logic, TailGuard mechanism, parameter tuning, or performance claim is included in this stage.

## Frozen CAPC-v1 reference

Repository:

`rhidoyhasanmahmud/capc-simulator`

Frozen execution revision:

`00d4e2ebd7af24bd6abf35578a2d40296fb4ddc6`

Frozen primary configuration SHA-256:

`be25b6dc8c89c3a49b891ea4c69e1c1dfe38b6e117d577bd8026c2d0094ba875`

## Ported Stage A1 scope

The following frozen components were reproduced:

- configuration schema and loader;
- model enums;
- transaction specification/data model;
- two-state MMPP workload generation;
- deterministic RNG stream decomposition;
- exogenous transaction trace representation;
- canonical trace serialization;
- SHA-256 trace hashing.

The copied baseline implementation files were verified byte-for-byte against the frozen CAPC-v1 revision before commit.

## Verification results

Development configuration equivalence was checked across seeds:

`1, 7, 42, 77, 123, 999`

For all tested seeds, the CAPC-v1 and CAPC-v2 repositories produced identical:

- trace SHA-256;
- transaction count;
- workload state-interval count.

Selected transaction rows for seed `123` were also compared directly and matched exactly.

Frozen primary configuration equivalence was then checked across the same seeds:

`1, 7, 42, 77, 123, 999`

For all tested primary-config seeds, the CAPC-v1 and CAPC-v2 repositories produced identical:

- trace SHA-256;
- transaction count;
- workload state-interval count.

The observed frozen-primary fixtures are encoded in:

`tests/unit/test_frozen_primary_trace_fixture.py`

The development fixtures are encoded in:

`tests/unit/test_frozen_trace_fixture.py`

## Automated verification status

At the Stage A1 baseline freeze point:

`7/7 tests passed`

using:

`PYTHONPATH=src python -m pytest -q`

## Interpretation

This evidence supports deterministic equivalence of the Stage A1 workload/trace-generation layer for the tested configurations and seeds.

It does not yet establish equivalence of:

- atomic shard-lock behaviour;
- worker/event semantics;
- Static Atomic FIFO;
- CAPC-v1 scheduling;
- metrics/output semantics;
- matrix-runner behaviour;
- paired-trace audit behaviour.

Those components remain Stage A work and must be verified before CAPC-v2 candidate design or tuning begins.
