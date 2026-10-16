from __future__ import annotations

from typing import Iterable

import numpy as np
import pandas as pd

from capc_sim.analysis.state_series import (
    continuous_time_linear_slope,
    first_sustained_moving_average_below,
    time_weighted_mean,
)


def percentile(values: Iterable[float], q: float) -> float | None:
    arr = np.asarray(list(values), dtype=float)
    if arr.size == 0:
        return None
    return float(np.percentile(arr, q))


def summarize_transactions(
    tx_df: pd.DataFrame,
    state_df: pd.DataFrame,
    warmup: float,
    duration: float,
    worker_count: int,
) -> dict:
    measured = tx_df[
        (tx_df["is_cross_shard"] == True)
        & (tx_df["arrival_time"] >= warmup)
        & (tx_df["arrival_time"] < duration)
    ].copy()
    completed = measured[measured["completion_time"].notna()]
    completed_by_cutoff = measured[measured["completed_by_cutoff"] == True]

    lat = completed["latency"].dropna().to_numpy(float)
    wait = completed["waiting_time"].dropna().to_numpy(float)
    service = completed["service_time"].dropna().to_numpy(float)
    interval = duration - warmup

    window_state = state_df[(state_df["time"] >= warmup) & (state_df["time"] <= duration)]
    max_queue = int(window_state["queue_length"].max()) if not window_state.empty else 0

    out: dict[str, float | int | None] = {
        "measurement_cross_shard_transactions": int(len(measured)),
        "completed_cross_shard_transactions": int(len(completed)),
        "completed_by_cutoff": int(len(completed_by_cutoff)),
        "unfinished_at_cutoff": int(len(measured) - len(completed_by_cutoff)),
        "unfinished_fraction_at_cutoff": (
            float((len(measured) - len(completed_by_cutoff)) / len(measured)) if len(measured) else 0.0
        ),
        # Coordination throughput: measurement-window cross-shard completions only.
        "throughput_tx_per_s": float(len(completed_by_cutoff) / interval),
        "mean_latency_s": float(np.mean(lat)) if len(lat) else None,
        "median_latency_s": float(np.median(lat)) if len(lat) else None,
        "p95_latency_s": percentile(lat, 95),
        "p99_latency_s": percentile(lat, 99),
        "latency_variability_p95_minus_median_s": (
            float(percentile(lat, 95) - np.median(lat)) if len(lat) else None
        ),
        "mean_waiting_s": float(np.mean(wait)) if len(wait) else None,
        "median_waiting_s": float(np.median(wait)) if len(wait) else None,
        "p95_waiting_s": percentile(wait, 95),
        "max_waiting_s": float(np.max(wait)) if len(wait) else None,
        "mean_service_s": float(np.mean(service)) if len(service) else None,
        "mean_queue_length": time_weighted_mean(state_df, "queue_length", warmup, duration),
        "max_queue_length": max_queue,
        "final_300s_queue_slope_tx_per_s": continuous_time_linear_slope(
            state_df, "queue_length", max(warmup, duration - 300.0), duration
        ),
        "mean_worker_utilization": (
            time_weighted_mean(state_df, "active_workers", warmup, duration)
            / max(1, worker_count)
        ),
    }

    completion_ratios = []
    for cls in ("HIGH", "MEDIUM", "LOW"):
        cls_all = measured[measured["priority"] == cls]
        cls_cutoff = completed_by_cutoff[completed_by_cutoff["priority"] == cls]
        ratio = float(len(cls_cutoff) / len(cls_all)) if len(cls_all) else 1.0
        completion_ratios.append(ratio)
        cls_wait = completed[completed["priority"] == cls]["waiting_time"].dropna().to_numpy(float)
        out[f"admitted_{cls.lower()}"] = int(len(cls_all))
        out[f"completed_by_cutoff_{cls.lower()}"] = int(len(cls_cutoff))
        out[f"completion_ratio_{cls.lower()}"] = ratio
        out[f"mean_waiting_{cls.lower()}_s"] = float(np.mean(cls_wait)) if len(cls_wait) else None
        out[f"p95_waiting_{cls.lower()}_s"] = percentile(cls_wait, 95)
        out[f"max_waiting_{cls.lower()}_s"] = float(np.max(cls_wait)) if len(cls_wait) else None

    denom = 3.0 * sum(x * x for x in completion_ratios)
    out["jain_completion_ratio"] = (
        (sum(completion_ratios) ** 2) / denom if denom > 0 else 1.0
    )

    # RQ2 run-level summaries specified in Chapter 3.
    if len(measured):
        for field, label in [
            ("arrival_rate_at_entry", "arrival_rate_at_entry"),
            ("dependency_degree", "dependency_degree"),
            ("active_lock_conflicts_at_entry", "active_lock_conflicts_at_entry"),
        ]:
            vals = measured[field].dropna().to_numpy(float)
            out[f"mean_{label}"] = float(np.mean(vals)) if len(vals) else None
            out[f"p95_{label}"] = percentile(vals, 95)
    return out


def queue_recovery_summary(
    state_df: pd.DataFrame,
    workload_df: pd.DataFrame,
    *,
    warmup: float,
    duration: float,
) -> dict:
    """Apply the Chapter 3 post-burst recovery/stability rule.

    The 10-s moving average is evaluated exactly over the piecewise-constant
    event-state log rather than by fixed-interval polling.
    """
    bursts = workload_df[workload_df["state"] == "BURST"].sort_values("start")
    episodes: list[dict] = []
    burst_starts = list(bursts["start"].astype(float))

    for idx, row in enumerate(bursts.itertuples(index=False)):
        b_start = float(row.start)
        b_end = float(row.end)
        if b_start < warmup or b_end >= duration:
            continue
        pre_start = b_start - 20.0
        if pre_start < warmup:
            episodes.append({
                "burst_start": b_start,
                "burst_end": b_end,
                "evaluable": False,
                "reason": "insufficient_20s_preburst_measurement_window",
            })
            continue
        next_burst = burst_starts[idx + 1] if idx + 1 < len(burst_starts) else None
        if next_burst is not None and next_burst < b_end + 50.0:
            episodes.append({
                "burst_start": b_start,
                "burst_end": b_end,
                "evaluable": False,
                "reason": "next_burst_before_50s_recovery_horizon",
            })
            continue

        q_pre = time_weighted_mean(state_df, "queue_length", pre_start, b_start)
        threshold = q_pre + max(2.0, 0.25 * q_pre)
        search_end = min(duration, b_end + 50.0)
        recovery_start = first_sustained_moving_average_below(
            state_df,
            field="queue_length",
            search_start=b_end,
            search_end=search_end,
            window_s=10.0,
            threshold=threshold,
            sustain_s=10.0,
        )
        episodes.append({
            "burst_start": b_start,
            "burst_end": b_end,
            "evaluable": True,
            "q_pre": q_pre,
            "threshold": threshold,
            "recovered": recovery_start is not None,
            "recovery_start": recovery_start,
            "recovery_delay_s": None if recovery_start is None else recovery_start - b_end,
        })

    evaluable = [e for e in episodes if e.get("evaluable")]
    recovered = [e for e in evaluable if e.get("recovered")]
    recovery_fraction = len(recovered) / len(evaluable) if evaluable else None
    final_slope = continuous_time_linear_slope(
        state_df, "queue_length", max(warmup, duration - 300.0), duration
    )

    return {
        "burst_episodes_total": len(episodes),
        "burst_episodes_evaluable": len(evaluable),
        "burst_episodes_recovered": len(recovered),
        "burst_recovery_fraction": recovery_fraction,
        "final_300s_queue_slope_tx_per_s": final_slope,
        "episodes": episodes,
    }
