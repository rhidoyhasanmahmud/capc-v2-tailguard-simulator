from __future__ import annotations

import argparse
import json
from pathlib import Path

from capc_sim.config.loader import load_config
from capc_sim.experiments.calibration import (
    DEFAULT_CALIBRATION_SEEDS,
    DEFAULT_THRESHOLDS,
    run_calibration,
)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Run the frozen TailGuard calibration protocol."
    )

    parser.add_argument(
        "--config",
        default="configs/primary.yaml",
    )
    parser.add_argument(
        "--output",
        default="results/tailguard_calibration",
    )
    parser.add_argument(
        "--resume",
        action="store_true",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print the frozen calibration plan without running simulations.",
    )

    args = parser.parse_args()

    cfg = load_config(args.config)

    seeds = DEFAULT_CALIBRATION_SEEDS
    thresholds = DEFAULT_THRESHOLDS
    shard_counts = tuple(cfg.matrix.shard_counts)
    ratios = tuple(cfg.matrix.cross_shard_ratios)
    workers = tuple(cfg.matrix.workers)

    treatment_count = 2 + len(thresholds)
    condition_count = (
        len(shard_counts)
        * len(ratios)
        * len(workers)
    )

    planned_runs = (
        len(seeds)
        * condition_count
        * treatment_count
    )

    plan = {
        "phase": "calibration",
        "config": args.config,
        "output": args.output,
        "seed_start": seeds[0],
        "seed_end": seeds[-1],
        "seed_count": len(seeds),
        "thresholds": list(thresholds),
        "shard_counts": list(shard_counts),
        "cross_shard_ratios": list(ratios),
        "workers": list(workers),
        "condition_count": condition_count,
        "treatment_count": treatment_count,
        "planned_run_count": planned_runs,
    }

    print(json.dumps(plan, indent=2))

    if args.dry_run:
        return

    if tuple(seeds) != tuple(range(1001, 1031)):
        raise RuntimeError(
            "Calibration seed set does not match frozen protocol"
        )

    if tuple(thresholds) != (1, 2, 4, 8, 16, 32):
        raise RuntimeError(
            "Threshold set does not match frozen protocol"
        )

    if condition_count != 18:
        raise RuntimeError(
            f"Expected 18 frozen conditions, found {condition_count}"
        )

    if planned_runs != 4320:
        raise RuntimeError(
            f"Expected 4320 runs, found {planned_runs}"
        )

    run_calibration(
        cfg,
        output=Path(args.output),
        seeds=seeds,
        thresholds=thresholds,
        shard_counts=shard_counts,
        cross_shard_ratios=ratios,
        workers=workers,
        resume=args.resume,
        fail_fast=True,
    )


if __name__ == "__main__":
    main()
