from pathlib import Path
import numpy as np
import pandas as pd

ROOT = Path("results/tailguard_calibration")
RUNS = ROOT / "runs"
KEYS = ["shard_count", "cross_shard_ratio", "workers", "seed"]
BS = [1, 2, 4, 8, 16, 32]
CLASSES = ["HIGH", "MEDIUM", "LOW"]

summary = pd.read_csv(ROOT / "calibration_summary.csv")
assert len(summary) == 4320
assert not summary.duplicated(KEYS + ["treatment"]).any()

def transaction_path(folder):
    for name in ("transactions.csv.gz", "transactions.csv"):
        p = folder / name
        if p.is_file():
            return p
    raise FileNotFoundError(str(folder))

def load_waits(r):
    folder = RUNS / r.treatment / r.run_id
    tx = pd.read_csv(
        transaction_path(folder),
        usecols=[
            "arrival_time", "is_cross_shard",
            "priority", "waiting_time", "status"
        ]
    )

    tx = tx.loc[
        tx.is_cross_shard.eq(True)
        & tx.arrival_time.ge(180)
        & tx.arrival_time.lt(1800)
        & ~tx.status.astype(str).str.lower().eq("rejected")
    ]

    assert len(tx) == r.measurement_cross_shard_transactions
    assert tx.waiting_time.notna().all()
    return tx

rows = []

for group_number, (_, group) in enumerate(
    summary.groupby(KEYS, sort=True), 1
):
    assert len(group) == 8

    baseline = group.loc[
        group.treatment == "static_atomic_fifo"
    ]
    assert len(baseline) == 1

    fifo_tx = load_waits(next(baseline.itertuples(index=False)))

    # Original CAPC-v1 Equation 3.9.
    threshold = max(
        0.50,
        5.0 * float(fifo_tx.waiting_time.median())
    )

    for r in group.itertuples(index=False):
        tx = (
            fifo_tx
            if r.treatment == "static_atomic_fifo"
            else load_waits(r)
        )

        waits = tx.waiting_time.to_numpy(dtype=float)

        result = {
            k: getattr(r, k) for k in KEYS
        }
        result["treatment"] = r.treatment
        result["threshold_s"] = threshold
        result["n"] = len(waits)
        result["starved_n"] = int((waits > threshold).sum())
        result["starvation_incidence"] = float(
            np.mean(waits > threshold)
        )

        for priority in CLASSES:
            sub = tx.loc[tx.priority == priority]
            assert len(sub) > 0
            label = priority.lower()
            result[f"{label}_starvation"] = float(
                np.mean(sub.waiting_time.to_numpy() > threshold)
            )

        rows.append(result)

    if group_number % 50 == 0 or group_number == 540:
        print(
            f"Audited {group_number}/540 paired groups",
            flush=True
        )

out = pd.DataFrame(rows)
assert len(out) == 4320

output = ROOT / "analysis_d3_3_starvation_runs.csv"
out.to_csv(output, index=False)

reports = []

fifo = out.loc[out.treatment == "static_atomic_fifo"]
capc = out.loc[out.treatment == "capc"]

for b in BS:
    tg = out.loc[out.treatment == f"tailguard_b{b}"]

    for name, ref in (
        ("static_atomic_fifo", fifo),
        ("capc", capc)
    ):
        pair = tg.merge(
            ref,
            on=KEYS,
            suffixes=("_tg", "_ref"),
            validate="one_to_one"
        )
        assert len(pair) == 540
        assert np.allclose(
            pair.threshold_s_tg,
            pair.threshold_s_ref
        )

        delta = 100 * (
            pair.starvation_incidence_tg
            - pair.starvation_incidence_ref
        )

        high_delta = 100 * (
            pair.high_starvation_tg
            - pair.high_starvation_ref
        )

        low_delta = 100 * (
            pair.low_starvation_tg
            - pair.low_starvation_ref
        )

        condition_delta = (
            pair.assign(delta=delta)
            .groupby(KEYS[:-1])["delta"].mean()
        )

        reports.append({
            "B": b,
            "vs": name,
            "mean_starvation_delta_pp": delta.mean(),
            "runs_over_plus1pp": int((delta > 1).sum()),
            "conditions_mean_over_plus1pp": int(
                (condition_delta > 1).sum()
            ),
            "worst_run_delta_pp": delta.max(),
            "high_starvation_delta_pp": high_delta.mean(),
            "low_starvation_delta_pp": low_delta.mean(),
            "tg_runs_with_starvation": int(
                (pair.starved_n_tg > 0).sum()
            ),
        })

report = pd.DataFrame(reports)
report_path = ROOT / "analysis_d3_3_starvation_comparison.csv"
report.to_csv(report_path, index=False)

print("\n=== STAGE D3.3 STARVATION AUDIT ===")
print(report.round(4).to_string(index=False))

print("\nThreshold source: paired Static Atomic FIFO")
print("Rule: max(0.50, 5 x baseline median waiting)")
print("Starved: waiting_time > threshold")
print("Preservation margin: +1 percentage point")
print("No candidate has been selected.")
print("\nSaved:", output)
print("Saved:", report_path)
