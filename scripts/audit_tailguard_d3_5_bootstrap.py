"""Calibration-only paired seed-cluster bootstrap analysis.

Reserved validation and confirmation seeds are never loaded.
"""
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path("results/tailguard_calibration")
KEYS = ["seed", "shard_count", "cross_shard_ratio", "workers"]
CANDIDATES = [1, 2, 4, 8, 16, 32]
BOOTSTRAPS = 10000
RANDOM_SEED = 20261018

summary = pd.read_csv(ROOT / "calibration_summary.csv")
priority = pd.read_csv(ROOT / "analysis_d3_2_priority_runs.csv")

assert len(summary) == len(priority) == 4320
assert set(summary.seed.unique()) == set(range(1001, 1031))
assert set(priority.seed.unique()) == set(range(1001, 1031))

columns = KEYS + ["treatment"]

data = summary[
    columns + ["p99_latency_s"]
].merge(
    priority[columns + ["high_p99_latency_s"]],
    on=columns,
    validate="one_to_one"
)

assert not data.duplicated(columns).any()

capc = data[data.treatment == "capc"]
fifo = data[data.treatment == "static_atomic_fifo"]


def seed_cluster_ci(frame, column, seed):
    by_seed = frame.groupby("seed")[column].mean()
    assert list(by_seed.index) == list(range(1001, 1031))

    values = by_seed.to_numpy(dtype=float)
    assert np.isfinite(values).all()

    rng = np.random.default_rng(seed)
    draws = rng.integers(
        0, len(values),
        size=(BOOTSTRAPS, len(values))
    )
    samples = values[draws].mean(axis=1)

    return (
        float(values.mean()),
        float(np.quantile(samples, 0.025)),
        float(np.quantile(samples, 0.975))
    )


records = []

for b in CANDIDATES:
    tg = data[data.treatment == f"tailguard_b{b}"]

    paired = tg.merge(
        capc,
        on=KEYS,
        suffixes=("_tg", "_capc"),
        validate="one_to_one"
    ).merge(
        fifo[KEYS + ["p99_latency_s"]],
        on=KEYS,
        validate="one_to_one"
    )

    assert len(paired) == 540

    paired = paired.assign(
        dp99_ms=1000 * (
            paired.p99_latency_s_tg
            - paired.p99_latency_s_capc
        ),
        dhigh_ms=1000 * (
            paired.high_p99_latency_s_tg
            - paired.high_p99_latency_s_capc
        ),
        dfifo_ms=1000 * (
            paired.p99_latency_s_tg
            - paired.p99_latency_s
        )
    )

    other = paired.loc[
        ~(
            (paired.shard_count == 4)
            & (paired.cross_shard_ratio == 0.5)
        )
    ]
    assert len(other) == 480

    row = {"B": b}

    for j, (label, frame, metric) in enumerate([
        ("p99", paired, "dp99_ms"),
        ("HIGH", paired, "dhigh_ms"),
        ("vs_FIFO", paired, "dfifo_ms"),
        ("other16", other, "dp99_ms")
    ]):
        mean, lower, upper = seed_cluster_ci(
            frame, metric,
            RANDOM_SEED + j
        )

        row[f"{label}_mean_ms"] = mean
        row[f"{label}_CI_low_ms"] = lower
        row[f"{label}_CI_high_ms"] = upper

    records.append(row)

out = pd.DataFrame(records)

path = ROOT / "analysis_d3_5_bootstrap.csv"
out.to_csv(path, index=False, float_format="%.10f")

print("\n=== STAGE D3.5 REPRODUCIBLE BOOTSTRAP ===")
print(out.round(2).to_string(index=False))
print("\nSaved:", path)
print("Bootstrap resamples:", BOOTSTRAPS)
print("Calibration seeds: 1001–1030")
print("Decision status: NOT FROZEN")
