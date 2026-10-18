# Stage D — TailGuard Calibration Decision (DRAFT; NOT FROZEN)

**Status:** Calibration analyzed; selection pending explicit priority-service acceptability decision.  
**Date:** 2026-10-18  
**Study:** CAPC-v2 TailGuard — bounded consecutive eligible bypass.  
**Data boundary:** calibration seeds **1001–1030** only. Reserved seeds **1101–1130** (internal validation) and **2001–2060** (independent confirmation) must remain untouched.

## 1. Provenance and frozen protocol

The authoritative prespecified procedure is [STAGE_C3_CALIBRATION_PROTOCOL.md](STAGE_C3_CALIBRATION_PROTOCOL.md). Frozen candidates: `B ∈ {1,2,4,8,16,32}`; paired treatments: matched `static_atomic_fifo`, frozen `capc`, and all six TailGuard thresholds; matrix: 3 shard counts × 3 cross-shard ratios × 2 worker capacities × 30 calibration seeds = **540 matched condition–seed groups and 4,320 runs**. Calibration manifest reported **4320 completed, zero failures, and paired trace integrity true**. Retain these outputs as separate raw evidence; do not represent this document as independent replication.

Primary contrast: paired `Δp99 = p99(TailGuard) − p99(CAPC)` (negative favours TailGuard). The original CAPC-v1 negative p99 result remains frozen.

## 2. All-candidate calibration findings

| B | Mean Δp99 vs CAPC (ms) | Mean HIGH-class Δp99 vs CAPC (ms) | Improved condition means /18 | Paired runs exceeding FIFO starvation +1 pp /540 |
|---:|---:|---:|---:|---:|
| 1 | −1332.826 | +91.326 | 11 | 0 |
| 2 | −1328.557 | +91.434 | 7 | 0 |
| 4 | −1318.404 | +88.662 | 7 | 10 |
| 8 | −1292.511 | +82.545 | 4 | 60 |
| 16 | −1259.396 | +103.724 | 2 | 72 |
| 32 | −1145.484 | +170.336 | 3 | 10 |

For **B=1**, the median run-level paired overall Δp99 is only **−2.907 ms** despite mean **−1332.826 ms**. The mean improvement is strongly concentrated in the two 4-shard/50%-cross-shard conditions. Excluding *both* of these conditions, the remaining 16-condition mean is **−40.80 ms** (seed-clustered bootstrap 95% interval **[−44.63, −37.13] ms**). This is a *diagnostic sensitivity analysis*, not a changed selection matrix.

### 30-seed clustered bootstrap diagnostics (10,000 resamples)

| B | Overall paired Δp99 mean and 95% CI (ms) | HIGH paired Δp99 mean and 95% CI (ms) | Overall p99 vs FIFO mean and 95% CI (ms) |
|---:|---|---|---|
| 1 | −1332.83 [−1536.75, −1142.28] | +91.33 [+81.86, +101.06] | +11.18 [+9.69, +12.71] |
| 2 | −1328.56 [−1534.87, −1143.59] | +91.43 [+81.52, +101.55] | +15.45 [+13.85, +17.07] |
| 4 | −1318.40 [−1520.58, −1126.82] | +88.66 [+78.77, +98.78] | +25.60 [+24.08, +27.13] |
| 8 | −1292.51 [−1500.40, −1107.37] | +82.55 [+73.62, +91.70] | +51.50 [+48.74, +54.10] |
| 16 | −1259.40 [−1460.43, −1073.35] | +103.72 [+95.28, +112.63] | +84.61 [+80.15, +89.17] |
| 32 | −1145.48 [−1343.22, −958.89] | +170.34 [+150.67, +188.75] | +198.52 [+191.88, +204.75] |

These intervals are calibration-only uncertainty estimates, not proof of performance on new workloads. In particular, **none of the candidates is better than Static Atomic FIFO in mean overall p99**, and all have positive mean HIGH-class regression relative to CAPC.

For B=1, HIGH-class p99 is worse in **407/540 paired runs** and **16/18 condition means**; the 95th percentile of paired HIGH-class regression is **+652.938 ms**, and the worst observed regression is **+1075.201 ms**. The severe 4-shard/50%-cross-shard settings have mean HIGH-class regression around **+637.799 ms**. The frozen C3 protocol did **not** define a numerical HIGH-class non-inferiority margin; none may be invented retrospectively.

## 3. Fairness, protection, throughput and stability

Original CAPC-v1 starvation definition: for each matched condition and seed, `threshold = max(0.50 s, 5 × median waiting time of Static Atomic FIFO)`, with starvation defined by waiting time strictly exceeding the threshold. Original FIFO-relative preservation criterion: no more than **+1 percentage point** starvation increase. At B=1 and B=2 **0/540** paired runs exceed this benchmark. This is not proof that priority-specific latency is preserved.

B=1 measurement-window protection activations: **1,120,875**; B=2: **691,319**. Protection is not merely theoretical. Throughput/completion are broadly comparable in calibration (mean relative throughput difference vs CAPC approximately +0.003%). Queue-stable counts: **478/540** for B=1 and B=2, **474/540** for CAPC, and **478/540** for FIFO; stability cannot be called universal.

B=1 mitigates LOW/MEDIUM extreme-tail outcomes while trading off HIGH-class response. Do not interpret this as hard real-time deadlines, network-level blockchain scalability, consensus improvement, or deployment readiness.

## 4. Direct B=1 vs B=2 comparison

Paired **B=2 minus B=1** overall p99 mean **+4.2682 ms** and median **+1.4262 ms** (positive means B=2 slower). B=1 faster in **311/540** runs, B=2 faster in **139/540**, and **90** ties. HIGH-class mean difference B=2 minus B=1 **+0.1079 ms**. B=1 has the best prespecified primary mean paired p99 improvement, while B=2 intervenes less often.

The C3 tie-breaker prefers larger B *if practically similar*. No equivalence margin was frozen; the observed 4.27 ms difference alone does not establish formal equivalence. Accordingly, **B=1 is calibration-leading**, **not accepted/frozen**.

## 5. Safeguards and unresolved decision

- **Matched exposure:** reported paired integrity true; retain manifest, hashes, and comparison summaries.
- **Throughput/completion:** no material mean throughput penalty identified, but inspect condition-specific instability and unfinished work.
- **FIFO-relative starvation:** B=1 and B=2 satisfy the original +1 pp test across all sampled paired calibration runs; B=4/8/16/32 show breaches.
- **HIGH-priority service:** material degradation in several contention conditions; cannot be treated as negligible or ignored just because aggregate p99 improved.
- **Generalization:** very large average improvement is concentrated in severe contention; most applications and workloads are untested.

**Decision pending:** Under C3, choose exactly one candidate only after documenting whether the observed HIGH-priority cost is acceptable within the approved soft/time-sensitive IoT scope and research objectives. Two scientifically legitimate outcomes remain:

1. **Conditional validation:** explicitly justify and freeze one trade-off-bearing calibration candidate (B=1 currently ranks first), with mechanism, evaluation scripts, metrics, and selection rationale immutable; then evaluate reserved **1101–1130** without retuning, reporting both positive and adverse evidence.
2. **No acceptable candidate:** if priority-service regression is unacceptable, formally record no C3-compliant candidate. Any revised algorithm is a **new exploratory stage** requiring an independently documented protocol. Do not tune on reserved seeds.

**CURRENT STATE: NO PARAMETER SELECTED OR FROZEN; NO VALIDATION OR CONFIRMATION AUTHORIZED BY THIS DRAFT.** No supervisor decision or approval is implied.

## 6. Local evidence index

- `results/tailguard_calibration/calibration_manifest.json`
- `results/tailguard_calibration/calibration_summary.csv`
- `results/tailguard_calibration/pair_integrity.csv`
- `results/tailguard_calibration/analysis_d3_2_priority_runs.csv`
- `results/tailguard_calibration/analysis_d3_2_priority_comparison.csv`
- `results/tailguard_calibration/analysis_d3_3_starvation_runs.csv`
- `results/tailguard_calibration/analysis_d3_3_starvation_comparison.csv`

The local calibration dataset (including compressed transaction/decision traces) is **not uploaded by this document commit**; preserve original data and hashes in separate research archives. Before final freeze: verify manifest/files/code commit and C3 criteria, save analysis scripts, document candidate acceptance decision, and confirm reserved seeds were not accessed.
