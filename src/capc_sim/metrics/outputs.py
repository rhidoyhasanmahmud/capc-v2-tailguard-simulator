from __future__ import annotations

import json
import os
import platform
import subprocess
import sys
from importlib import metadata as importlib_metadata
from pathlib import Path

import pandas as pd

from capc_sim.analysis.run_metrics import queue_recovery_summary, summarize_transactions
from capc_sim.config.loader import config_hash, dump_config
from capc_sim.config.schema import ExperimentConfig
from capc_sim.model.transaction import Transaction
from capc_sim.workload.trace import Trace
from .recorder import MetricsRecorder


OUTPUT_SCHEMA_VERSION = 2


def git_commit() -> str:
    try:
        return subprocess.check_output(
            ["git", "rev-parse", "HEAD"], text=True, stderr=subprocess.DEVNULL
        ).strip()
    except Exception:
        return "unknown"


def physical_memory_bytes() -> int | None:
    """Best-effort total physical-memory provenance without an extra dependency."""
    try:
        page_size = int(os.sysconf("SC_PAGE_SIZE"))
        pages = int(os.sysconf("SC_PHYS_PAGES"))
        if page_size > 0 and pages > 0:
            return page_size * pages
    except (AttributeError, OSError, ValueError):
        pass
    try:
        value = subprocess.check_output(
            ["sysctl", "-n", "hw.memsize"],
            text=True,
            stderr=subprocess.DEVNULL,
        ).strip()
        return int(value) if value else None
    except Exception:
        return None


def package_versions() -> dict[str, str]:
    wanted = ["numpy", "pandas", "scipy", "statsmodels", "PyYAML", "matplotlib"]
    versions: dict[str, str] = {}
    for name in wanted:
        try:
            versions[name] = importlib_metadata.version(name)
        except importlib_metadata.PackageNotFoundError:
            versions[name] = "not-installed"
    return versions


def transaction_rows(
    transactions: list[Transaction],
    run_id: str,
    seed: int,
    scheduler: str,
    config: ExperimentConfig,
) -> list[dict]:
    rows = []
    for tx in transactions:
        rows.append({
            "run_id": run_id,
            "seed": seed,
            "scheduler": scheduler,
            "shard_count": config.sharding.shard_count,
            "cross_shard_ratio": config.sharding.cross_shard_ratio,
            "workers": config.coordination.workers,
            "transaction_id": tx.transaction_id,
            "arrival_time": tx.arrival_time,
            "queue_entry_time": tx.queue_entry_time,
            "service_start_time": tx.service_start_time,
            "completion_time": tx.completion_time,
            "waiting_time": tx.waiting_time(),
            "service_time": tx.service_time_s,
            "latency": tx.latency(),
            "priority": tx.priority.value,
            "workload_state": tx.workload_state.value,
            "required_shards": "|".join(str(s) for s in tx.required_shards),
            "dependency_degree": tx.dependency_degree,
            "is_cross_shard": tx.is_cross_shard,
            "status": tx.status.value,
            "queue_length_at_entry": tx.queue_length_at_entry,
            "arrival_rate_at_entry": tx.arrival_rate_at_entry,
            "active_lock_conflicts_at_entry": tx.active_lock_conflicts_at_entry,
            "completed_by_cutoff": tx.completed_by_cutoff,
        })
    return rows


def _dispatch_summary(dispatch_df: pd.DataFrame) -> dict:
    if dispatch_df.empty:
        return {
            "dispatch_snapshots": 0,
            "candidate_observations": 0,
            "blocked_candidate_observations": 0,
            "lock_block_fraction_candidate_observations": 0.0,
            "dispatch_snapshots_with_any_block_fraction": 0.0,
        }
    candidates = int(dispatch_df["queue_count"].sum())
    blocked = int(dispatch_df["blocked_count"].sum())
    any_block = float((dispatch_df["blocked_count"] > 0).mean())
    return {
        "dispatch_snapshots": int(len(dispatch_df)),
        "candidate_observations": candidates,
        "blocked_candidate_observations": blocked,
        "lock_block_fraction_candidate_observations": float(blocked / candidates) if candidates else 0.0,
        "dispatch_snapshots_with_any_block_fraction": any_block,
    }


def write_run_outputs(
    *,
    directory: str | Path,
    config: ExperimentConfig,
    trace: Trace,
    transactions: list[Transaction],
    recorder: MetricsRecorder,
    cutoff_snapshot: dict,
    seed: int,
    scheduler: str,
    run_id: str,
) -> dict:
    directory = Path(directory)
    directory.mkdir(parents=True, exist_ok=True)
    trace.write(directory)

    tx_df = pd.DataFrame(transaction_rows(transactions, run_id, seed, scheduler, config))
    state_df = pd.DataFrame(recorder.state_events)
    decisions_df = pd.DataFrame(recorder.decisions)
    dispatch_df = pd.DataFrame(recorder.dispatch_snapshots)
    workload_df = pd.DataFrame([
        {"state": s.state.value, "start": s.start, "end": s.end, "duration": s.end - s.start}
        for s in trace.state_intervals
    ])

    tx_df.to_csv(directory / "transactions.csv", index=False)
    state_df.to_csv(directory / "state_events.csv", index=False)
    decisions_df.to_csv(directory / "decisions.csv", index=False)
    dispatch_df.to_csv(directory / "dispatch_snapshots.csv", index=False)
    dump_config(config, directory / "effective_config.yaml")

    summary = summarize_transactions(
        tx_df,
        state_df,
        config.simulation.warmup_s,
        config.simulation.duration_s,
        config.coordination.workers,
    )
    recovery = queue_recovery_summary(
        state_df,
        workload_df,
        warmup=config.simulation.warmup_s,
        duration=config.simulation.duration_s,
    )
    summary.update(_dispatch_summary(dispatch_df))
    summary.update({k: v for k, v in recovery.items() if k != "episodes"})

    recovery_fraction = recovery["burst_recovery_fraction"]
    recovery_ok = True if recovery_fraction is None else recovery_fraction >= 0.90
    slope_ok = summary["final_300s_queue_slope_tx_per_s"] <= 0.02 + 1e-12
    unfinished_ok = summary["unfinished_fraction_at_cutoff"] <= 0.01 + 1e-12
    summary["queue_stable"] = bool(recovery_ok and slope_ok and unfinished_ok)

    summary.update({
        "run_id": run_id,
        "seed": seed,
        "scheduler": scheduler,
        "shard_count": config.sharding.shard_count,
        "cross_shard_ratio": config.sharding.cross_shard_ratio,
        "workers": config.coordination.workers,
        "trace_hash": trace.hash(),
        "config_hash": config_hash(config),
    })

    with (directory / "summary.json").open("w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2, sort_keys=True)
    with (directory / "queue_recovery.json").open("w", encoding="utf-8") as f:
        json.dump(recovery, f, indent=2, sort_keys=True)

    metadata = {
        "run_id": run_id,
        "seed": seed,
        "scheduler": scheduler,
        "research_mode": config.research.mode,
        "research_label": config.research.label,
        "config_hash": config_hash(config),
        "trace_hash": trace.hash(),
        "git_commit": git_commit(),
        "python": sys.version,
        "python_executable": sys.executable,
        "platform": platform.platform(),
        "machine": platform.machine(),
        "processor": platform.processor(),
        "physical_memory_bytes": physical_memory_bytes(),
        "packages": package_versions(),
        "cutoff_snapshot": cutoff_snapshot,
        "output_schema_version": OUTPUT_SCHEMA_VERSION,
    }
    with (directory / "metadata.json").open("w", encoding="utf-8") as f:
        json.dump(metadata, f, indent=2, sort_keys=True)
    return summary
