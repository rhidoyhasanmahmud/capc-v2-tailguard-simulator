from __future__ import annotations

import json
import traceback
from pathlib import Path

import pandas as pd

from capc_sim.config.loader import config_hash
from capc_sim.config.schema import ExperimentConfig
from capc_sim.simulation.engine import Simulator, SimulationResult
from capc_sim.workload.mmpp import TraceGenerator


def run_single(
    config: ExperimentConfig,
    scheduler: str,
    seed: int,
    output: str | Path,
    trace=None,
) -> SimulationResult:
    if trace is None:
        trace = TraceGenerator(config, seed).generate()
    return Simulator(config, trace, scheduler, seed).run(output)


def run_matrix(
    config: ExperimentConfig,
    seeds: list[int],
    output: str | Path,
    shard_counts: list[int] | None = None,
    cross_shard_ratios: list[float] | None = None,
    workers: list[int] | None = None,
    schedulers: list[str] | None = None,
    *,
    fail_fast: bool = True,
) -> pd.DataFrame:
    """Run the paired condition × seed × scheduler matrix.

    One exogenous trace is generated per condition/seed and replayed under every
    requested scheduler. A failed run is recorded; seeds are never silently replaced.
    """
    output = Path(output)
    output.mkdir(parents=True, exist_ok=True)
    shard_counts = shard_counts or list(config.matrix.shard_counts)
    cross_shard_ratios = cross_shard_ratios or list(config.matrix.cross_shard_ratios)
    workers = workers or list(config.matrix.workers)
    schedulers = schedulers or list(config.matrix.schedulers)

    summaries: list[dict] = []
    failures: list[dict] = []
    pair_checks: list[dict] = []

    for shard_count in shard_counts:
        for ratio in cross_shard_ratios:
            for worker_count in workers:
                condition = config.with_condition(shard_count, ratio, worker_count)
                for seed in seeds:
                    trace = TraceGenerator(condition, seed).generate()
                    trace_hash = trace.hash()
                    observed_hashes: list[str] = []
                    for scheduler in schedulers:
                        try:
                            result = run_single(condition, scheduler, seed, output, trace=trace)
                            observed_hashes.append(result.trace_hash)
                            summaries.append(result.summary)
                        except Exception as exc:
                            failures.append({
                                "shard_count": shard_count,
                                "cross_shard_ratio": ratio,
                                "workers": worker_count,
                                "seed": seed,
                                "scheduler": scheduler,
                                "error_type": type(exc).__name__,
                                "error": str(exc),
                                "traceback": traceback.format_exc(),
                            })
                            if fail_fast:
                                _write_failures(output, failures)
                                raise
                    paired_ok = bool(observed_hashes) and all(h == trace_hash for h in observed_hashes)
                    pair_checks.append({
                        "shard_count": shard_count,
                        "cross_shard_ratio": ratio,
                        "workers": worker_count,
                        "seed": seed,
                        "trace_hash": trace_hash,
                        "paired_trace_equal": paired_ok,
                    })
                    if observed_hashes and not paired_ok:
                        raise AssertionError("Paired scheduler runs did not use the identical exogenous trace")

    df = pd.DataFrame(summaries)
    df.to_csv(output / "matrix_summary.csv", index=False)
    pd.DataFrame(pair_checks).to_csv(output / "pair_integrity.csv", index=False)
    _write_failures(output, failures)

    manifest = {
        "research_mode": config.research.mode,
        "research_label": config.research.label,
        "config_hash": config_hash(config),
        "seeds": seeds,
        "shard_counts": shard_counts,
        "cross_shard_ratios": cross_shard_ratios,
        "workers": workers,
        "schedulers": schedulers,
        "planned_run_count": len(shard_counts) * len(cross_shard_ratios) * len(workers) * len(seeds) * len(schedulers),
        "completed_run_count": len(summaries),
        "failure_count": len(failures),
        "paired_trace_integrity": all(x["paired_trace_equal"] for x in pair_checks) if pair_checks else True,
    }
    with (output / "matrix_manifest.json").open("w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2, sort_keys=True)
    return df


def _write_failures(output: Path, failures: list[dict]) -> None:
    with (output / "failures.json").open("w", encoding="utf-8") as f:
        json.dump(failures, f, indent=2, sort_keys=True)
