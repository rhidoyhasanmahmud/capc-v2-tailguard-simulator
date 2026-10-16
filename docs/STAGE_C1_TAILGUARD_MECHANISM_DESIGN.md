# Stage C1 — TailGuard Mechanism Design Freeze

## Purpose

Stage C1 defines the first TailGuard candidate mechanism before any parameter calibration or performance tuning.

The mechanism is motivated by the Stage B2 diagnostic evidence that CAPC-v1 exhibits priority-asymmetric redistribution of eligible service opportunities, with some LOW and MEDIUM transactions accumulating repeated eligible bypasses and substantially increased tail delay.

This stage defines mechanism semantics only.

No threshold value is selected here.

## Design objective

TailGuard should reduce extreme delay redistribution caused by repeated eligible overtaking while preserving CAPC's useful priority responsiveness as much as possible.

The mechanism should:

1. preserve the existing CAPC score computation;
2. preserve atomic shard-lock eligibility;
3. preserve non-preemptive service;
4. preserve deterministic scheduler behaviour;
5. avoid protecting transactions that are currently lock-ineligible;
6. intervene only after repeated eligible bypass;
7. remain priority-agnostic at the protection layer;
8. introduce minimal additional scheduler logic.

## Candidate mechanism: bounded eligible bypass protection

For every queued cross-shard transaction, the simulator already tracks:

- eligible observation count;
- cumulative bypass count;
- consecutive bypass count;
- maximum consecutive bypass count.

TailGuard uses the consecutive eligible-bypass count as the protection signal.

### Normal mode

When no eligible transaction exceeds the TailGuard protection condition:

- scheduler behaviour is identical to frozen CAPC-v1;
- the transaction with maximum CAPC score is selected using the existing CAPC tie-breaking rules.

### Protection mode

When one or more currently eligible transactions satisfy the TailGuard protection condition:

1. only currently eligible transactions may be considered;
2. protected candidates are selected independently of priority class;
3. among protected candidates, the transaction with the largest consecutive eligible-bypass count receives precedence;
4. remaining ties are resolved by:
   - older queue-entry time;
   - lower transaction ID.

The selected protected transaction is then dispatched using the same atomic locking and worker semantics as the existing simulator.

## Protection signal

The initial candidate signal is:

`consecutive_bypass_count >= B`

where `B` is a TailGuard bypass threshold.

`B` is intentionally unspecified in Stage C1.

Threshold values will be investigated only during a separately defined calibration stage.

## Why consecutive bypass rather than cumulative bypass

Cumulative bypass can remain high even after a transaction has already received service opportunity relief.

Consecutive bypass directly represents uninterrupted repeated eligible overtaking and therefore more closely matches the Stage B2 failure pattern.

It also permits the protection state to reset naturally when a transaction is selected.

## Why eligibility is mandatory

TailGuard must not promote a transaction that cannot atomically acquire its required shard locks.

Therefore:

- blocked transactions are not protected for immediate dispatch;
- protection applies only to transactions returned by the existing matched-atomic eligibility check.

This preserves the original all-or-nothing shard-lock semantics.

## Why protection is priority-agnostic

The diagnostic evidence shows that LOW traffic experiences the largest adverse redistribution, while some MEDIUM and occasional HIGH transactions can also experience severe CAPC-specific delay.

A priority-specific protection rule would risk encoding the desired result directly into the algorithm.

Therefore the protection layer uses bypass history rather than priority class.

Priority continues to influence normal CAPC ranking through the frozen CAPC urgency component.

## Expected trade-off

TailGuard may reduce extreme LOW/MEDIUM tail delay by occasionally overriding normal CAPC score ranking.

The possible cost is reduced responsiveness for transactions that would otherwise receive CAPC priority advantage.

This trade-off must be measured rather than assumed.

## Evaluation criteria

The mechanism will be evaluated against at least:

- frozen CAPC-v1;
- Static Atomic FIFO.

Primary outcomes should include:

- p99 latency;
- p95 latency;
- waiting-time tail;
- throughput;
- unfinished fraction;
- queue stability;
- priority-specific latency;
- priority-specific waiting time;
- bypass-count distribution;
- extreme consecutive bypass.

TailGuard should not be considered successful solely because it reduces bypass counts.

Any improvement must be evaluated against latency, throughput, stability, and priority-service trade-offs.

## Calibration boundary

Stage C1 does not choose `B`.

A later calibration stage will define:

- candidate threshold values;
- calibration seeds;
- acceptance criteria;
- internal-validation seeds.

Independent confirmatory seeds must remain untouched until the mechanism and parameters are frozen.

## Research-integrity boundary

The Stage B2 diagnostic data motivates the mechanism class but must not be used to claim TailGuard performance before evaluation.

No positive result is assumed.

If bounded bypass protection fails to improve the pre-specified evaluation criteria, the negative result must be retained and reported.
