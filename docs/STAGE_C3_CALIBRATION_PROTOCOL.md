# Stage C3 — TailGuard Calibration Protocol

## Purpose

Stage C3 defines the TailGuard calibration procedure before any calibration experiment is executed.

The purpose is to select one consecutive-bypass threshold `B` for the frozen TailGuard mechanism defined in Stage C1 and implemented in Stage C2.

The algorithm itself must not change during threshold calibration.

## Frozen mechanism

TailGuard uses:

`consecutive_bypass_count >= B`

as the protection condition.

When no eligible transaction satisfies this condition, selection follows the frozen CAPC-v1 scheduler exactly.

When protection activates, only currently eligible transactions are considered and the protected candidate is selected using the deterministic rule frozen in Stage C1.

## Candidate threshold set

The calibration candidates are fixed before running calibration:

`B ∈ {1, 2, 4, 8, 16, 32}`

The range intentionally spans:

- aggressive protection;
- moderate protection;
- conservative protection.

The candidate grid is not intended to encode an expected optimum.

No additional threshold may be inserted after examining calibration results unless the calibration protocol is explicitly reopened and the resulting work is treated as a new exploratory phase.

## Scheduler comparators

Every calibration condition must include:

- `static_atomic_fifo`
- frozen `capc`
- `tailguard` for every candidate `B`

Static Atomic FIFO remains the matched atomic baseline.

CAPC remains the direct parent scheduler and primary comparison for assessing whether TailGuard mitigates CAPC-v1 tail behaviour.

## Calibration seeds

Calibration seeds are frozen as:

`1001–1030`

These seeds may be used to select `B`.

They must not later be presented as independent confirmatory evidence.

## Internal-validation seeds

Internal-validation seeds are frozen as:

`1101–1130`

These seeds must not be inspected until one threshold has been selected from calibration.

The selected threshold must be evaluated unchanged on these seeds.

## Independent-confirmation seeds

Independent-confirmation seeds are reserved as:

`2001–2060`

They must remain untouched during:

- mechanism design;
- threshold calibration;
- threshold selection;
- internal validation.

They may only be used after the TailGuard mechanism and threshold are frozen.

## Experimental conditions

Calibration should use the existing primary matched-atomic condition matrix rather than selecting only conditions in which TailGuard appears favourable.

The matrix dimensions are:

- shard counts: `4, 8, 16`
- cross-shard ratios: `0.10, 0.30, 0.50`
- workers: `2, 4`

This produces 18 workload/system conditions per seed.

All schedulers compared within a condition and seed must reuse the same generated transaction trace.

## Primary calibration outcome

The primary calibration outcome is cross-shard transaction p99 latency.

For every condition and seed, compute the paired difference:

`Delta_p99 = p99_TailGuard - p99_CAPC`

Negative values favour TailGuard.

Threshold selection must be based on paired evidence rather than comparing unrelated aggregate runs.

## Secondary outcomes

The following must also be retained:

- p95 latency;
- median latency;
- waiting-time p95 and p99;
- completed cross-shard transactions;
- throughput;
- unfinished fraction;
- queue recovery/stability indicators;
- priority-specific latency;
- priority-specific waiting time;
- eligible bypass count;
- maximum consecutive bypass count;
- number/fraction of TailGuard protection activations.

## Priority-service safeguard

TailGuard is not intended simply to improve LOW traffic by destroying useful priority responsiveness.

Therefore HIGH-priority performance must be reported explicitly during calibration.

A candidate threshold must not be selected solely because it improves aggregate p99 while producing an unexamined severe HIGH-priority latency regression.

The magnitude and prevalence of any HIGH-priority degradation must be reported alongside tail-latency improvement.

## Stability safeguard

A candidate is not acceptable merely because completed transactions have lower latency.

The following must also be inspected:

- completion count;
- unfinished fraction;
- queue growth/recovery;
- throughput.

A threshold showing apparent latency improvement through loss of difficult transactions or unstable backlog must be rejected.

## Threshold-selection rule

For each candidate threshold:

1. compute paired TailGuard-minus-CAPC outcomes for every calibration seed and condition;
2. summarize the distribution of paired p99 differences;
3. inspect whether improvement is concentrated in only a small subset of conditions;
4. inspect throughput, unfinished work, queue stability, and priority-specific effects;
5. reject candidates exhibiting material stability or completion regressions.

Among candidates passing the safeguards, select the threshold with the strongest overall paired p99 improvement across the complete pre-specified calibration matrix.

If two candidates provide practically similar p99 behaviour, prefer the larger threshold because it intervenes less frequently in the frozen CAPC ordering.

The exact selected threshold and the complete calibration evidence must be documented before internal validation begins.

## No-success case

The calibration protocol permits the outcome that no candidate threshold is acceptable.

If all candidates either:

- fail to improve the primary tail outcome,
- cause unacceptable instability,
- reduce completion reliability,
- or produce an unacceptable priority-service trade-off,

then no threshold should be declared successful.

The mechanism may then require redesign, which must be documented as a new exploratory stage rather than silently modifying the current algorithm.

## Internal validation

After calibration:

1. select exactly one threshold;
2. freeze it in a calibration-result document;
3. run the unchanged mechanism and threshold on seeds `1101–1130`;
4. report results regardless of whether they reproduce calibration improvement.

The threshold must not be retuned using internal-validation results.

## Independent confirmation

Only after successful internal validation and a fully frozen implementation may seeds `2001–2060` be accessed.

No algorithm, parameter, metric definition, or acceptance rule may be modified after examining confirmatory results.

## Research-integrity boundary

Stage C3 freezes the experimental decision process before calibration data are generated.

No TailGuard performance claim has yet been established.

The threshold `B=1` previously used in Stage C2 was solely an activation smoke test and is not calibration evidence or a recommended parameter.
