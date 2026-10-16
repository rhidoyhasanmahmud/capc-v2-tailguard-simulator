# Simulator Port Plan

## Objective

Build CAPC-v2 on top of the same controlled DES semantics used by the frozen CAPC-v1 primary experiment, so that any later CAPC-v2 improvement is attributable to scheduler redesign rather than an unnoticed simulator change.

## Frozen CAPC-v1 source reference

Source repository: `rhidoyhasanmahmud/capc-simulator`

Frozen execution revision:

`00d4e2ebd7af24bd6abf35578a2d40296fb4ddc6`

The CAPC-v2 simulator should initially reproduce the following CAPC-v1 semantics exactly before introducing new scheduler logic:

- Python discrete-event simulation;
- synthetic two-state MMPP workload;
- non-preemptive service;
- atomic all-or-nothing required-shard locking;
- highest-ranked blocked transaction may be skipped in favour of the next eligible transaction;
- one exogenous trace per condition/seed replayed across schedulers;
- measurement window and warm-up handling;
- per-run metadata with Git/config/trace provenance;
- paired-trace integrity checks;
- transaction-level output sufficient for waiting-tail and priority-class diagnostics.

## Stage A implementation rule

The first implementation milestone is **semantic reproduction, not performance improvement**.

No CAPC-v2 score or TailGuard tuning should be added until the following are reproduced and tested:

1. Static Atomic FIFO behaviour.
2. CAPC-v1 behaviour under the same configuration.
3. Deterministic trace generation for a fixed seed.
4. Trace-hash equality across scheduler replays.
5. Atomicity invariants.
6. Non-preemptive worker semantics.
7. Warm-up/measurement cutoff semantics.
8. Summary and transaction metric definitions.
9. Matrix-runner failure and audit behaviour.

## Baseline equivalence test

A small frozen equivalence suite should run identical CAPC-v1 conditions in both repositories and compare:

- transaction trace hash;
- admitted/completed transaction counts;
- p50/p95/p99 latency;
- mean/p95/p99 waiting;
- throughput;
- Jain fairness;
- queue statistics;
- lock/block statistics;
- cutoff snapshot;
- selected transaction rows.

Where deterministic equality is expected, exact equality should be required. Where floating-point formatting differs, a documented tolerance may be used only after confirming the underlying semantics are unchanged.

## CAPC-v2 extension boundary

After baseline equivalence passes, CAPC-v2-specific code should be isolated behind a new scheduler implementation and explicit configuration section. Core trace generation, service, lock semantics, and baseline metrics should not be modified merely to obtain better CAPC-v2 results.

If a core simulator change is scientifically necessary, it must be:

- justified independently of observed CAPC-v2 performance;
- documented as a protocol amendment;
- applied equally to all matched schedulers;
- revalidated for semantic equivalence where applicable.

## Planned TailGuard-specific observability

Before candidate tuning begins, add measurements for:

- bypass count per transaction;
- time since last dispatch opportunity;
- tail-rescue activation flag/time;
- score-component values at selection time;
- priority-class p95/p99/p99.5 waiting;
- p99/p95 tail-shape ratio;
- top-1% waiting-time priority composition;
- queue-age distribution snapshots.

These diagnostics should be available without changing scheduler behaviour.

## Milestone checklist

- [ ] Port frozen CAPC-v1 simulator core
- [ ] Port Static Atomic FIFO
- [ ] Port CAPC-v1 reference scheduler
- [ ] Port trace generation and configuration loader
- [ ] Port metrics/output/provenance
- [ ] Port matrix runner and integrity audit
- [ ] Add equivalence tests against frozen CAPC-v1
- [ ] Add TailGuard observability only
- [ ] Freeze Stage A simulator baseline
- [ ] Begin candidate CAPC-v2 algorithm design/calibration
