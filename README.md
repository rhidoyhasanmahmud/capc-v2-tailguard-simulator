# CAPC-v2 TailGuard Simulator

Evidence-informed redesign and simulation framework for CAPC-v2, targeting extreme-tail latency control and waiting-time fairness under atomic cross-shard blockchain-IoT contention.

## Research status

This repository is a **separate redesign and validation track** derived from the frozen CAPC-v1 study. It does **not** modify, replace, or reinterpret the original CAPC-v1 experimental record.

The CAPC-v1 study established the following redesign motivation:

- the primary p99 improvement criterion was not achieved;
- medium/high contention showed systematic p99 degradation;
- high-priority transactions could improve while medium/low-priority extreme waiting tails worsened;
- throughput and Jain fairness could remain preserved even while extreme waiting-time tails deteriorated;
- the observed failure mode therefore motivates explicit tail protection rather than post-hoc retuning of CAPC-v1.

## Research objective

Develop and independently validate a revised coordination scheduler that aims to preserve urgency responsiveness while preventing extreme-tail delay redistribution under atomic cross-shard contention.

## Integrity boundary

The redesign process is split into four stages:

1. **Simulator/harness preparation** — implement the controlled DES environment, matched atomic baseline, metrics, trace pairing, and verification without tuning CAPC-v2 performance logic.
2. **Exploratory calibration** — evaluate candidate CAPC-v2 mechanisms using dedicated calibration seeds and selected conditions. Algorithm parameters may change only in this stage.
3. **Algorithm freeze** — freeze scheduler logic, parameters, success criteria, code revision, and configuration before confirmatory results are inspected.
4. **Independent validation** — evaluate the frozen CAPC-v2 on fresh unseen seeds and the full condition matrix.

Calibration outcomes must never be presented as confirmatory evidence.

## Planned scheduler set

- `static_atomic_fifo` — matched atomic baseline
- `capc_v1` — frozen original CAPC reference
- `capc_v2_tailguard` — redesigned scheduler (to be defined and frozen after exploratory calibration)
- optional ablations to be frozen before validation

## Planned data split

- **Calibration:** seeds `1001–1030`, selected representative conditions
- **Internal validation / robustness:** seeds `1101–1130`
- **Final confirmatory validation:** fresh seeds `2001–2060`, full matrix

The exact split and condition set are documented in `docs/RESEARCH_PROTOCOL.md` and must be frozen before confirmatory execution.

## Design principle

CAPC-v2 should target the empirically observed CAPC-v1 failure mode rather than merely maximise a favourable average metric. Candidate mechanisms may include bounded urgency influence, nonlinear aging, explicit tail rescue, bypass protection, and contention-dependent weighting, while preserving non-preemptive atomic all-or-nothing shard-lock semantics.

## Primary validation target

The final primary endpoint remains per-run cross-shard p99 end-to-end latency against Static Atomic FIFO. Practical success criteria and preservation guardrails will be frozen before final validation.

## Repository structure

```text
configs/        Frozen and calibration experiment configurations
docs/           Research protocol, redesign rationale, freeze records
src/            Simulator and scheduler implementation
tests/          Semantic, deterministic, and regression verification
results/        Local/generated outputs (not committed by default)
scripts/        Experiment and audit helpers
```

## Reproducibility

Every calibration and validation run should record:

- Git commit
- configuration hash
- seed
- scheduler
- trace hash
- environment metadata
- output schema version

The final confirmatory study must use a frozen revision and an audited paired-trace matrix.
