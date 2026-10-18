# Stage D8 — Calibration Selection Record: TailGuard B=1

**Decision date:** 2026-10-18  
**Decision status:** **SELECTED AND FROZEN FOR INTERNAL VALIDATION** (not validated; not confirmed; not approved by supervisor)  
**Mechanism:** Frozen Stage C1/C2 TailGuard consecutive eligible-bypass protection; `consecutive_bypass_count >= B`  
**Selected parameter:** **B = 1**  
**Selection dataset:** **calibration seeds 1001–1030 only**

## 1. Authority, scope, and decision type

The frozen decision process is [Stage C3 Calibration Protocol](STAGE_C3_CALIBRATION_PROTOCOL.md). The underlying evidence and reservations are retained in [Stage D Calibration Decision Draft](STAGE_D_CALIBRATION_DECISION_DRAFT.md) and the [Stage D Evidence Manifest](STAGE_D_EVIDENCE_MANIFEST.json). This record documents the **user-authorized choice to proceed with conditional validation**; it is **not** an assertion that TailGuard has met application-level real-time QoS requirements, or that its HIGH-priority degradation is harmless.

This is a *calibration selection*, not a claim of experimental success. The outcome of internal validation must be reported, whether favourable or adverse. No algorithm, threshold, priority-safeguard definition, treatment comparison, or post-processing rule may be retuned using reserved validation seeds.

## 2. Frozen evaluation setting

- Candidate grid already evaluated: `{1, 2, 4, 8, 16, 32}`.
- Matched-atomic comparators: `static_atomic_fifo` (reference baseline), frozen `capc` (parent scheduler / primary comparison), `tailguard_b1`.
- Experimental matrix: shard counts `4,8,16`; cross-shard ratio `0.1,0.3,0.5`; workers `2,4` (18 conditions).
- Primary estimand: within-seed-and-condition `p99(TailGuard B=1) - p99(CAPC)`, negative preferred.
- Retain throughput, completion/unfinished fraction, queue stability, priority-specific latency/wait, bypass/protection, and FIFO-referenced starvation.
- Original starvation definition: `max(0.50 s, 5 × paired-Static-Atomic-FIFO median waiting)`; the original FIFO-relative +1 percentage-point preservation criterion is a *diagnostic reference*, not evidence of meeting HIGH-priority deadlines.

## 3. Selection rationale and important adverse evidence

Calibration completed 4,320 runs with reported full paired-trace integrity. Among candidates, B=1 produced the strongest matrix-wide mean paired p99 reduction against CAPC: **−1332.826 ms**, with 30-seed cluster-bootstrap 95% CI approximately **[−1536.75, −1142.28] ms**. B=2: **−1328.557 ms**. Direct B=2 minus B=1 overall mean p99: **+4.2682 ms**; B=1 faster in 311/540 paired runs versus 139/540 for B=2 (90 ties). Neither practical-equivalence nor non-inferiority margins were prespecified, so the C3 larger-B tie-breaker is **not invoked on an unsupported equivalence claim**.

**Cost explicitly accepted for *testing*, not declared application-safe:** B=1 mean HIGH-class p99 regression against CAPC **+91.326 ms** (30-seed clustered 95% CI approximately **[+81.88, +101.27] ms**). HIGH-class p99 worsened in **407/540 pairs**, and **16/18** condition means; mean degradation reaches approximately **+638 ms** in 4-shard/50%-cross-shard conditions. Mean B=1 overall p99 remains **+11.18 ms** worse than Static Atomic FIFO (bootstrap CI approximately **[+9.68, +12.74] ms**). The calibration does **not** justify universal real-time suitability, a safety-critical or hard-deadline guarantee, or outperforming FIFO.

The mean overall p99 result is concentrated in heavily contended scenarios: the calibration median paired Δp99 is **−2.907 ms**; excluding both 4-shard/50% conditions yields mean **−40.80 ms**, calibration sensitivity CI approximately **[−44.68, −36.95] ms**. In the FIFO-referenced starvation audit B=1 had **0/540** individual paired runs exceed +1 pp, while protection activations were substantial (**1,120,875** in measurement windows). Throughput/completion were broadly preserved; queue stability was not universal (**478/540** B=1 runs stable).

The C3 protocol has **no prespecified numerical HIGH-priority degradation acceptance margin**. Rather than retrospectively fabricating one, this decision records the severity transparently and uses reserved data for a falsifiable *conditional* evaluation. A later thesis assessment may still find the observed trade-off unacceptable and conclude that no suitable threshold was demonstrated.

## 4. Freeze / integrity boundary

**Frozen selection:** `B=1`; comparator set `{static_atomic_fifo, capc, tailguard_b1}`; conditions as in §2; same trace per seed/condition; primary paired Δp99; original C3 safeguards. Preserve raw run outputs independently of the Git history and validate against recorded checksums.

**Internal validation reserved seeds:** `1101–1130`. May be evaluated **only after confirming local implementation/config and analysis script hashes, manifest checksums, and the exact three-treatment launcher/run plan**. Do not use these seeds to select B or modify its behaviour. Document any deviations before looking at validation outcomes.

**Independent confirmation reserved seeds:** `2001–2060`. **DO NOT ACCESS OR RUN** until Stage E evaluation and review are complete, and the implementation, parameter and analysis plan remain frozen.

**Supervisor approval:** not represented by this record. This decision is a research workflow decision, not a signed supervisor determination.

## 5. Validation reporting requirements

Report B=1 paired overall p99 effect with uncertainty across all 18 conditions; condition-wise dispersion/concentration; HIGH/MEDIUM/LOW p99 and waiting-time regression; FIFO comparison; throughput, unfinished work, queue stability, starvation and intervention counts. Keep observation distinct from interpretation. If validation reproduces mean p99 improvement but also severe HIGH-priority deterioration, state both; do not call it QoS-preserving. If validation fails to reproduce the parent-relative benefit or shows material instability, document it and stop before independent confirmation.

## 6. Next gate (not executed by this record)

Prepare and review a **Stage E read-only preflight** that verifies Git commit, current protocol, checksum manifest, configured seeds, output directory, full 18-condition matrix, and three paired schedulers. Record the preflight and only then run Stage E. This document performs **no simulation**.
