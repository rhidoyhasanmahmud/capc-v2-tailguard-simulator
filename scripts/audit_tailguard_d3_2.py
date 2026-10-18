from pathlib import Path
import numpy as np
import pandas as pd

ROOT = Path("results/tailguard_calibration")
RUNS = ROOT / "runs"
KEYS = ["shard_count", "cross_shard_ratio", "workers", "seed"]
BS = [1, 2, 4, 8, 16, 32]
TREATMENTS = (
    ["static_atomic_fifo", "capc"]
    + [f"tailguard_b{b}" for b in BS]
)
CLASSES = ["HIGH", "MEDIUM", "LOW"]

summary = pd.read_csv(ROOT / "calibration_summary.csv")
assert len(summary) == 4320
assert not summary.duplicated(KEYS + ["treatment"]).any()

records = []
expected = 18 * 30 * len(TREATMENTS)

def find_csv(folder, name):
    for path in (folder / f"{name}.csv.gz",
                 folder / f"{name}.csv"):
        if path.is_file():
            return path
    raise FileNotFoundError(f"{folder}/{name}.csv[.gz]")

for i, r in enumerate(summary.itertuples(index=False), 1):
    folder = RUNS / r.treatment / r.run_id

    # Read the original transaction records.
    path = find_csv(folder, "transactions")
    tx = pd.read_csv(
        path,
        usecols=[
            "arrival_time", "priority", "latency",
            "waiting_time", "is_cross_shard"
        ],
    )

    tx = tx.loc[
        (tx.arrival_time >= 180)
        & (tx.arrival_time < 1800)
        & (tx.is_cross_shard == True)
    ].copy()

    assert len(tx) == r.measurement_cross_shard_transactions, (
        f"Measurement count mismatch: {r.treatment}/{r.run_id}"
    )
    assert tx["latency"].notna().all(), (
        f"Missing latency: {r.treatment}/{r.run_id}"
    )

    result = dict(
        zip(
            KEYS,
            [
                r.shard_count, r.cross_shard_ratio,
                r.workers, r.seed
            ]
        )
    )
    result["treatment"] = r.treatment
    result["run_id"] = r.run_id

    for priority in CLASSES:
        sub = tx.loc[tx.priority == priority]
        assert len(sub) > 0, (
            f"No {priority} transactions: {r.run_id}"
        )

        prefix = priority.lower()
        result[f"{prefix}_n"] = len(sub)
        result[f"{prefix}_p99_latency_s"] = (
            sub.latency.quantile(0.99)
        )
        result[f"{prefix}_p95_wait_s"] = (
            sub.waiting_time.quantile(0.95)
        )
        result[f"{prefix}_max_wait_s"] = (
            sub.waiting_time.max()
        )

    result["protection_activations"] = 0
    result["measurement_protection_activations"] = 0

    if r.treatment.startswith("tailguard_b"):
        decisions = pd.read_csv(
            find_csv(folder, "decisions"),
            usecols=["time", "tailguard_active"],
        )

        active = (
            decisions.tailguard_active
            .astype(str).str.lower().eq("true")
        )
        result["protection_activations"] = int(active.sum())
        result["measurement_protection_activations"] = int(
            (
                active
                & decisions.time.ge(180)
                & decisions.time.lt(1800)
            ).sum()
        )

    records.append(result)

    if i % 100 == 0 or i == expected:
        print(f"Audited {i}/{expected} runs", flush=True)

out = pd.DataFrame(records)
assert len(out) == expected

output = ROOT / "analysis_d3_2_priority_runs.csv"
out.to_csv(output, index=False)

capc = out.loc[out.treatment == "capc"]
fifo = out.loc[out.treatment == "static_atomic_fifo"]

rows = []

for b in BS:
    tg = out.loc[out.treatment == f"tailguard_b{b}"]

    for name, ref in [("capc", capc),
                      ("static_atomic_fifo", fifo)]:
        p = tg.merge(
            ref,
            on=KEYS,
            suffixes=("_tg", "_ref"),
            validate="one_to_one",
        )
        assert len(p) == 540

        item = {"B": b, "vs": name}

        for priority in CLASSES:
            prefix = priority.lower()
            metric = f"{prefix}_p99_latency_s"

            delta = p[f"{metric}_tg"] - p[f"{metric}_ref"]

            item[f"{prefix}_p99_delta_ms"] = (
                delta.mean() * 1000
            )
            item[f"{prefix}_p99_worse_runs"] = int(
                (delta > 0).sum()
            )

            condition_means = (
                p.assign(delta=delta)
                .groupby(KEYS[:-1])["delta"].mean()
            )
            item[f"{prefix}_worse_conditions"] = int(
                (condition_means > 0).sum()
            )

        item["total_protection_activations"] = int(
            p.protection_activations_tg.sum()
        )
        item["measurement_protection_activations"] = int(
            p.measurement_protection_activations_tg.sum()
        )

        rows.append(item)

report = pd.DataFrame(rows)

report_path = ROOT / "analysis_d3_2_priority_comparison.csv"
report.to_csv(report_path, index=False)

print("\n=== PRIORITY P99 AND PROTECTION AUDIT ===")
print(report.round(3).to_string(index=False))

print("\nSaved:")
print(output)
print(report_path)
print("\nStarvation safeguard: NOT YET ASSESSED")
print("No threshold selected or frozen.")
