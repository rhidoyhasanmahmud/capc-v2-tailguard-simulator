"""Frozen Stage E internal-validation runner.

Uses the existing paired-trace simulator without scheduler modifications.
"""
import argparse
import json
from pathlib import Path

from capc_sim.config.loader import load_config
from capc_sim.experiments.calibration import run_calibration

SEEDS = tuple(range(1101, 1131))
OUTPUT = Path("results/tailguard_internal_validation")
CONFIG = "configs/primary.yaml"


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--resume", action="store_true")
    args = parser.parse_args()

    cfg = load_config(CONFIG)

    assert tuple(cfg.matrix.shard_counts) == (4, 8, 16)
    assert tuple(cfg.matrix.cross_shard_ratios) == (0.1, 0.3, 0.5)
    assert tuple(cfg.matrix.workers) == (2, 4)

    treatments = [
        "static_atomic_fifo",
        "capc",
        "tailguard_b1",
    ]

    plan = {
        "phase": "internal_validation",
        "threshold_B": 1,
        "seeds": [SEEDS[0], SEEDS[-1]],
        "treatments": treatments,
        "conditions": 18,
        "planned_runs": 1620,
        "output": str(OUTPUT),
        "dry_run": args.dry_run,
    }

    print(json.dumps(plan, indent=2), flush=True)

    if args.dry_run:
        return

    if OUTPUT.exists() and any(OUTPUT.iterdir()) and not args.resume:
        raise RuntimeError(
            "Existing validation output. Use --resume only "
            "after inspecting the existing manifest."
        )

    if args.resume:
        manifest = OUTPUT / "calibration_manifest.json"
        if not manifest.exists():
            raise RuntimeError("Missing existing run manifest")
        existing = json.loads(manifest.read_text())
        if existing.get("phase") != "internal_validation":
            raise RuntimeError("Wrong experiment phase")
        if existing.get("planned_run_count") != 1620:
            raise RuntimeError("Wrong planned run count")

    run_calibration(
        cfg,
        output=OUTPUT,
        seeds=SEEDS,
        thresholds=(1,),
        shard_counts=(4, 8, 16),
        cross_shard_ratios=(0.1, 0.3, 0.5),
        workers=(2, 4),
        resume=args.resume,
        fail_fast=True,
        phase="internal_validation",
    )


if __name__ == "__main__":
    main()
