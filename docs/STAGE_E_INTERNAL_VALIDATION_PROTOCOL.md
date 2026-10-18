# Stage E — Frozen Internal Validation Protocol

Status: EXECUTION PENDING
Selection record: docs/STAGE_D8_B1_SELECTION_FREEZE.md

## Purpose
Evaluate the unchanged calibration-selected TailGuard B=1
against frozen CAPC and matched Static Atomic FIFO.

## Frozen experimental design
- Seeds: 1101–1130 (30 seeds)
- Shards: 4, 8, 16
- Cross-shard ratios: 0.1, 0.3, 0.5
- Workers: 2, 4
- Conditions: 18
- Treatments: static_atomic_fifo, capc, tailguard_b1
- Planned runs: 1620
- Output: results/tailguard_internal_validation

## Primary comparison
Paired p99 cross-shard latency:
TailGuard B=1 minus CAPC.

Negative values favour TailGuard.

## Required secondary evaluation
- HIGH/MEDIUM/LOW priority p99 and waiting latency
- Static Atomic FIFO comparison
- Throughput and completion counts
- Unfinished transaction fraction
- Queue stability and recovery
- FIFO-referenced starvation incidence
- Protection activation frequency
- Condition-level heterogeneity and paired uncertainty

## Research integrity
- No threshold retuning.
- No scheduler or workload modifications.
- No selection of favourable seeds or conditions.
- Report adverse findings alongside improvements.
- Validation results cannot establish universal real-time suitability.
- Independent confirmation seeds 2001–2060 remain untouched.

## Execution gates
1. Source code and protocol committed.
2. Unit and phase-isolation tests passed.
3. Resume/recovery safety reviewed.
4. Sufficient storage verified.
5. Execution configuration verified before first simulation.

The execution has not yet started.
