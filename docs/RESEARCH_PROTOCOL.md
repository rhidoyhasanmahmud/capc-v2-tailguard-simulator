# CAPC-v2 TailGuard Research Protocol

## 1. Purpose

This document defines the redesign and validation protocol for CAPC-v2. The objective is to investigate whether an evidence-informed scheduler can retain priority responsiveness while preventing the extreme-tail waiting-time redistribution observed in the frozen CAPC-v1 study.

This protocol is intentionally separated from the CAPC-v1 confirmatory record. CAPC-v1 results remain immutable historical evidence.

## 2. Redesign motivation from CAPC-v1

The frozen CAPC-v1 experiment showed a regime-dependent failure pattern rather than a universal throughput failure:

- the predeclared primary p99 practical-improvement criterion was not satisfied;
- medium/high cross-shard contention produced consistent p99 harm;
- p95 waiting could remain stable or improve while p99/p99.5/max waiting worsened;
- high-priority waiting tails could improve while medium/low-priority extreme tails deteriorated;
- throughput and Jain fairness could remain preserved despite this extreme-tail redistribution.

The redesign problem is therefore not simply to increase scheduler aggressiveness. It is to control tail risk while maintaining atomic cross-shard semantics and useful urgency responsiveness.

## 3. Research hypothesis

A scheduler that bounds urgency dominance and introduces explicit waiting-tail protection can reduce global p99 latency under medium/high contention without causing unacceptable low-priority waiting-time degradation or violating throughput/fairness preservation constraints.

This is a redesign hypothesis, not an established result.

## 4. Experimental separation

### 4.1 Stage A — simulator and harness preparation

No CAPC-v2 performance tuning is permitted in this stage. The goals are:

- reproduce the required DES semantics;
- implement Static Atomic FIFO as the matched atomic baseline;
- provide CAPC-v1 as a frozen reference implementation where practical;
- generate one exogenous trace per condition/seed and replay it across schedulers;
- record trace hashes and execution provenance;
- implement per-run and transaction-level metrics;
- verify atomic all-or-nothing shard-lock semantics;
- verify non-preemptive service;
- verify deterministic replay for fixed seed/config/revision;
- build fail-fast matrix and audit tooling.

### 4.2 Stage B — exploratory calibration

Dedicated calibration seeds may be used to compare candidate CAPC-v2 mechanisms and tune parameters. Results from this stage are exploratory and must not be used as confirmatory evidence.

Proposed calibration seeds: `1001–1030`.

Candidate calibration conditions should emphasize the failure boundary while retaining at least one low-contention reference. A provisional set is:

- 4 shards, 30% cross-shard, 2 workers
- 4 shards, 50% cross-shard, 2 workers
- 8 shards, 30% cross-shard, 2 workers
- 8 shards, 50% cross-shard, 2 workers
- 16 shards, 50% cross-shard, 2 workers
- 16 shards, 50% cross-shard, 4 workers
- plus at least one 10% cross-shard reference condition

The final calibration matrix may be adjusted before calibration begins, but the choice and rationale must be documented.

### 4.3 Stage C — internal robustness check

After a candidate is selected, use fresh seeds `1101–1130` to test whether the chosen design behaves consistently beyond the tuning set. Parameter changes are still permitted only if the candidate is explicitly returned to exploratory status.

### 4.4 Stage D — algorithm freeze

Before confirmatory validation, freeze and record:

- scheduler definition;
- all weights, thresholds and windows;
- workload configuration;
- measurement window;
- primary and secondary endpoints;
- preservation constraints;
- seed set;
- scheduler set;
- statistical analysis plan;
- source revision;
- configuration hashes.

No labelled confirmatory results may be inspected before this freeze record is complete.

### 4.5 Stage E — independent confirmatory validation

Proposed fresh confirmatory seeds: `2001–2060`.

The full factorial matrix should match the original research dimensions unless a documented protocol amendment is made before result inspection:

- shards: 4, 8, 16
- cross-shard ratio: 0.10, 0.30, 0.50
- workers: 2, 4
- 60 fresh seeds

Recommended matched scheduler set:

- Static Atomic FIFO
- CAPC-v1
- frozen CAPC-v2 TailGuard
- predeclared CAPC-v2 ablations, if included

## 5. Primary endpoint and practical success

Primary endpoint:

- per-run p99 cross-shard end-to-end latency

The practical success rule must be frozen before confirmatory validation. The provisional rule is:

- mean paired p99 reduction of at least 10% versus Static Atomic FIFO in medium/high contention;
- beneficial paired 95% confidence interval;
- preservation constraints satisfied.

The exact aggregation rule across conditions must be stated before the confirmatory run. A single favourable condition must not be interpreted as global success.

## 6. Preservation guardrails

Provisional guardrails inherited from the CAPC-v1 methodology:

- throughput degradation ≤ 5%;
- Jain fairness decrease ≤ 0.02;
- starvation increase ≤ 1 percentage point;
- low-priority p95 waiting increase ≤ 25%;
- queue stability preserved.

CAPC-v2-specific tail guardrails should additionally include:

- low-priority p99 waiting must not show material degradation beyond a frozen threshold;
- p99.5/max waiting must not exhibit uncontrolled inflation;
- the p99/p95 tail-shape ratio should not materially worsen under the redesigned scheduler.

Exact thresholds must be frozen after exploratory calibration and before confirmatory validation.

## 7. Candidate redesign mechanisms

The following mechanisms are candidates, not final algorithm commitments:

1. **Bounded urgency influence** — cap the maximum contribution of priority/urgency so that priority cannot indefinitely dominate waiting age.
2. **Nonlinear aging** — increase waiting-age influence sharply after a soft threshold.
3. **Tail rescue** — transactions exceeding a frozen tail threshold receive an explicit rescue boost regardless of priority class.
4. **Bypass protection** — repeated eligibility bypass increments a rescue state or boost.
5. **Contention-adaptive weighting** — reduce urgency dominance and increase aging/tail protection as contention rises.
6. **Lock-aware eligibility/ranking** — retain atomic eligibility while avoiding ranking rules that create pathological queue accumulation.

The final algorithm must be simpler than the union of all candidates unless calibration provides a clear justification for added complexity.

## 8. Statistical plan

Confirmatory comparisons should preserve seed-level pairing. The primary analysis should be specified before freeze and should include:

- paired effect estimates by condition;
- paired bootstrap confidence intervals;
- multiplicity-aware condition-level inference where applicable;
- explicit fallback procedures if a planned mixed-effects model is unusable;
- separation of confirmatory analyses from post-hoc diagnostics.

## 9. Research-integrity rules

- Never overwrite or reinterpret CAPC-v1 primary evidence.
- Never reuse confirmatory seeds for tuning.
- Never change CAPC-v2 parameters after inspecting labelled confirmatory outcomes.
- Preserve failed/partial runs and record recovery actions.
- Distinguish calibration, robustness, confirmatory and diagnostic outputs in filenames and documentation.
- Report negative or mixed outcomes without selective condition removal.

## 10. Thesis/paper integration rule

CAPC-v2 may replace CAPC-v1 as the thesis's final algorithmic contribution only if:

1. the redesign process is transparently documented;
2. CAPC-v1 failure evidence remains visible;
3. CAPC-v2 is frozen before independent validation;
4. fresh unseen validation data support the claimed improvement;
5. supervisor approval is obtained for the revised thesis framing.

Otherwise, CAPC-v2 should remain a separate exploratory/future-work or journal-paper track.
