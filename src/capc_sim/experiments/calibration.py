from __future__ import annotations

import json
import traceback
from dataclasses import asdict, dataclass, replace
from pathlib import Path

import pandas as pd

from capc_sim.config.loader import config_hash
from capc_sim.config.schema import (
    ExperimentConfig,
    TailGuardConfig,
)
from capc_sim.experiments.runner import run_single
from capc_sim.workload.mmpp import TraceGenerator


CALIBRATION_PROTOCOL_VERSION = 1
DEFAULT_THRESHOLDS = (1, 2, 4, 8, 16, 32)
DEFAULT_CALIBRATION_SEEDS = tuple(range(1001, 1031))


@dataclass(frozen=True)
class CalibrationTreatment:
    label: str
    scheduler: str
    bypass_threshold: int | None


def calibration_treatments(
    thresholds: tuple[int, ...] = DEFAULT_THRESHOLDS,
) -> tuple[CalibrationTreatment, ...]:
    """Return the frozen comparator + TailGuard treatment set."""
    if not thresholds:
        raise ValueError("At least one TailGuard threshold is required")
    if len(set(thresholds)) != len(thresholds):
        raise ValueError("TailGuard thresholds must be unique")
    if any(int(value) <= 0 for value in thresholds):
        raise ValueError("TailGuard thresholds must be > 0")

    return (
        CalibrationTreatment(
            "static_atomic_fifo",
            "static_atomic_fifo",
            None,
        ),
        CalibrationTreatment(
            "capc",
            "capc",
            None,
        ),
        *(
            CalibrationTreatment(
                f"tailguard_b{int(value)}",
                "tailguard",
                int(value),
            )
            for value in thresholds
        ),
    )


def _treatment_config(
    condition: ExperimentConfig,
    treatment: CalibrationTreatment,
) -> ExperimentConfig:
    if treatment.scheduler != "tailguard":
        return condition

    if treatment.bypass_threshold is None:
        raise ValueError(
            "TailGuard treatment requires bypass_threshold"
        )

    return replace(
        condition,
        tailguard=TailGuardConfig(
            bypass_threshold=treatment.bypass_threshold
        ),
    )


def _planned_manifest(
    config: ExperimentConfig,
    *,
    seeds: tuple[int, ...],
    shard_counts: tuple[int, ...],
    cross_shard_ratios: tuple[float, ...],
    workers: tuple[int, ...],
    treatments: tuple[CalibrationTreatment, ...],
    phase: str = "calibration",
) -> dict:
    if phase not in ("calibration", "internal_validation"):
        raise ValueError(f"Unsupported experiment phase: {phase}")
    return {
        "protocol_version": CALIBRATION_PROTOCOL_VERSION,
        "phase": phase,
        "base_config_hash": config_hash(config),
        "research_mode": config.research.mode,
        "research_label": config.research.label,
        "seeds": list(seeds),
        "shard_counts": list(shard_counts),
        "cross_shard_ratios": list(cross_shard_ratios),
        "workers": list(workers),
        "treatments": [
            asdict(treatment)
            for treatment in treatments
        ],
        "planned_condition_seed_pairs": (
            len(shard_counts)
            * len(cross_shard_ratios)
            * len(workers)
            * len(seeds)
        ),
        "planned_run_count": (
            len(shard_counts)
            * len(cross_shard_ratios)
            * len(workers)
            * len(seeds)
            * len(treatments)
        ),
    }


def _manifest_identity(manifest: dict) -> dict:
    """Fields that must remain identical across a resumed run."""
    return {
        key: manifest[key]
        for key in (
            "protocol_version",
            "phase",
            "base_config_hash",
            "research_mode",
            "research_label",
            "seeds",
            "shard_counts",
            "cross_shard_ratios",
            "workers",
            "treatments",
            "planned_condition_seed_pairs",
            "planned_run_count",
        )
    }


def _prepare_output(
    output: Path,
    planned: dict,
    *,
    resume: bool,
) -> None:
    manifest_path = output / "calibration_manifest.json"

    if not output.exists():
        output.mkdir(parents=True)
        return

    entries = list(output.iterdir())

    if not entries:
        return

    if not resume:
        raise FileExistsError(
            f"Calibration output directory is not empty: {output}. "
            "Use a new directory or resume=True."
        )

    if not manifest_path.exists():
        raise RuntimeError(
            "Cannot resume: existing output has no "
            "calibration_manifest.json"
        )

    existing = json.loads(
        manifest_path.read_text(encoding="utf-8")
    )

    if _manifest_identity(existing) != _manifest_identity(planned):
        raise RuntimeError(
            "Cannot resume: calibration protocol/config differs "
            "from the existing manifest"
        )


def _run_output_dir(
    output: Path,
    treatment: CalibrationTreatment,
) -> Path:
    return output / "runs" / treatment.label


def _existing_summary(
    run_root: Path,
    *,
    expected_run_id: str,
    expected_trace_hash: str,
    expected_config_hash: str,
) -> dict | None:
    summary_path = (
        run_root
        / expected_run_id
        / "summary.json"
    )

    if not summary_path.exists():
        return None

    summary = json.loads(
        summary_path.read_text(encoding="utf-8")
    )

    if summary.get("trace_hash") != expected_trace_hash:
        raise RuntimeError(
            f"Existing run has wrong trace hash: {summary_path}"
        )

    if summary.get("config_hash") != expected_config_hash:
        raise RuntimeError(
            f"Existing run has wrong config hash: {summary_path}"
        )

    return summary


def _expected_run_id(
    condition: ExperimentConfig,
    scheduler: str,
    seed: int,
) -> str:
    return (
        f"sh{condition.sharding.shard_count}"
        f"_x{int(round(condition.sharding.cross_shard_ratio * 100)):02d}"
        f"_w{condition.coordination.workers}"
        f"_{scheduler}_seed{int(seed):03d}"
    )


def run_calibration(
    config: ExperimentConfig,
    *,
    output: str | Path,
    seeds: tuple[int, ...] = DEFAULT_CALIBRATION_SEEDS,
    thresholds: tuple[int, ...] = DEFAULT_THRESHOLDS,
    shard_counts: tuple[int, ...] | None = None,
    cross_shard_ratios: tuple[float, ...] | None = None,
    workers: tuple[int, ...] | None = None,
    resume: bool = False,
    fail_fast: bool = True,
    phase: str = "calibration",
) -> pd.DataFrame:
    """Generate frozen TailGuard calibration evidence.

    One exogenous trace is generated per condition/seed and replayed
    across Static Atomic FIFO, frozen CAPC, and every TailGuard
    threshold treatment.

    This function generates evidence only. It does not select a
    threshold or rank treatments by performance.
    """
    output = Path(output)

    seeds = tuple(int(seed) for seed in seeds)
    thresholds = tuple(int(value) for value in thresholds)
    shard_counts = (
        tuple(config.matrix.shard_counts)
        if shard_counts is None
        else tuple(int(value) for value in shard_counts)
    )
    cross_shard_ratios = (
        tuple(config.matrix.cross_shard_ratios)
        if cross_shard_ratios is None
        else tuple(float(value) for value in cross_shard_ratios)
    )
    workers = (
        tuple(config.matrix.workers)
        if workers is None
        else tuple(int(value) for value in workers)
    )

    treatments = calibration_treatments(thresholds)

    planned = _planned_manifest(
        config,
        seeds=seeds,
        shard_counts=shard_counts,
        cross_shard_ratios=cross_shard_ratios,
        workers=workers,
        treatments=treatments,
        phase=phase,
    )

    _prepare_output(
        output,
        planned,
        resume=resume,
    )
    output.mkdir(parents=True, exist_ok=True)

    # Write the frozen plan before executing any simulation.
    initial_manifest = {
        **planned,
        "status": "running",
        "completed_run_count": 0,
        "failure_count": 0,
        "paired_trace_integrity": None,
    }
    (
        output / "calibration_manifest.json"
    ).write_text(
        json.dumps(
            initial_manifest,
            indent=2,
            sort_keys=True,
        ),
        encoding="utf-8",
    )

    summaries: list[dict] = []
    failures: list[dict] = []
    pair_checks: list[dict] = []

    for shard_count in shard_counts:
        for ratio in cross_shard_ratios:
            for worker_count in workers:
                condition = config.with_condition(
                    shard_count,
                    ratio,
                    worker_count,
                )

                for seed in seeds:
                    trace = TraceGenerator(
                        condition,
                        seed,
                    ).generate()

                    trace_hash = trace.hash()
                    observed: list[tuple[str, str]] = []

                    for treatment in treatments:
                        treatment_config = _treatment_config(
                            condition,
                            treatment,
                        )
                        treatment_config_hash = config_hash(
                            treatment_config
                        )

                        expected_run_id = _expected_run_id(
                            treatment_config,
                            treatment.scheduler,
                            seed,
                        )

                        run_root = _run_output_dir(
                            output,
                            treatment,
                        )

                        try:
                            existing = None
                            if resume:
                                existing = _existing_summary(
                                    run_root,
                                    expected_run_id=expected_run_id,
                                    expected_trace_hash=trace_hash,
                                    expected_config_hash=treatment_config_hash,
                                )

                            if existing is None:
                                result = run_single(
                                    treatment_config,
                                    treatment.scheduler,
                                    seed,
                                    run_root,
                                    trace=trace,
                                )
                                summary = dict(result.summary)
                                observed_hash = result.trace_hash
                                resumed = False
                            else:
                                summary = dict(existing)
                                observed_hash = str(
                                    existing["trace_hash"]
                                )
                                resumed = True

                            observed.append(
                                (
                                    treatment.label,
                                    observed_hash,
                                )
                            )

                            summary.update({
                                "treatment": treatment.label,
                                "bypass_threshold": (
                                    treatment.bypass_threshold
                                ),
                                "treatment_config_hash": (
                                    treatment_config_hash
                                ),
                                "resumed_existing_run": resumed,
                            })
                            summaries.append(summary)

                        except Exception as exc:
                            failures.append({
                                "shard_count": shard_count,
                                "cross_shard_ratio": ratio,
                                "workers": worker_count,
                                "seed": seed,
                                "treatment": treatment.label,
                                "scheduler": treatment.scheduler,
                                "bypass_threshold": (
                                    treatment.bypass_threshold
                                ),
                                "error_type": type(exc).__name__,
                                "error": str(exc),
                                "traceback": traceback.format_exc(),
                            })

                            if fail_fast:
                                _write_progress(
                                    output,
                                    planned,
                                    summaries,
                                    failures,
                                    pair_checks,
                                    status="failed",
                                )
                                raise

                    paired_ok = (
                        len(observed) == len(treatments)
                        and all(
                            observed_hash == trace_hash
                            for _, observed_hash in observed
                        )
                    )

                    pair_checks.append({
                        "shard_count": shard_count,
                        "cross_shard_ratio": ratio,
                        "workers": worker_count,
                        "seed": seed,
                        "trace_hash": trace_hash,
                        "expected_treatment_count": len(treatments),
                        "observed_treatment_count": len(observed),
                        "treatments": "|".join(
                            label for label, _ in observed
                        ),
                        "paired_trace_equal": paired_ok,
                    })

                    if observed and not paired_ok:
                        _write_progress(
                            output,
                            planned,
                            summaries,
                            failures,
                            pair_checks,
                            status="failed",
                        )
                        raise AssertionError(
                            "Calibration treatments did not replay "
                            "the identical exogenous trace"
                        )

                    _write_progress(
                        output,
                        planned,
                        summaries,
                        failures,
                        pair_checks,
                        status="running",
                    )

    _write_progress(
        output,
        planned,
        summaries,
        failures,
        pair_checks,
        status=(
            "complete"
            if not failures
            else "complete_with_failures"
        ),
    )

    return pd.DataFrame(summaries)


def _write_progress(
    output: Path,
    planned: dict,
    summaries: list[dict],
    failures: list[dict],
    pair_checks: list[dict],
    *,
    status: str,
) -> None:
    pd.DataFrame(summaries).to_csv(
        output / "calibration_summary.csv",
        index=False,
    )

    pd.DataFrame(pair_checks).to_csv(
        output / "pair_integrity.csv",
        index=False,
    )

    (
        output / "failures.json"
    ).write_text(
        json.dumps(
            failures,
            indent=2,
            sort_keys=True,
        ),
        encoding="utf-8",
    )

    manifest = {
        **planned,
        "status": status,
        "completed_run_count": len(summaries),
        "failure_count": len(failures),
        "paired_condition_seed_pairs": len(pair_checks),
        "paired_trace_integrity": (
            all(
                bool(row["paired_trace_equal"])
                for row in pair_checks
            )
            if pair_checks
            else None
        ),
    }

    (
        output / "calibration_manifest.json"
    ).write_text(
        json.dumps(
            manifest,
            indent=2,
            sort_keys=True,
        ),
        encoding="utf-8",
    )
