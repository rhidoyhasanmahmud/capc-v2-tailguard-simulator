"""Read-only Stage E internal-validation execution preflight."""
import json
import subprocess
from pathlib import Path

from capc_sim.config.loader import load_config
from capc_sim.experiments.calibration import calibration_treatments

CONFIG = Path("configs/primary.yaml")
OUTPUT = Path("results/tailguard_internal_validation")
SEEDS = tuple(range(1101, 1131))
TREATMENTS = ("static_atomic_fifo", "capc", "tailguard_b1")

cfg = load_config(str(CONFIG))

shards = tuple(cfg.matrix.shard_counts)
ratios = tuple(cfg.matrix.cross_shard_ratios)
workers = tuple(cfg.matrix.workers)

actual_treatments = calibration_treatments((1,))
labels = tuple(item.label for item in actual_treatments)

assert labels == TREATMENTS
assert shards == (4, 8, 16)
assert ratios == (0.1, 0.3, 0.5)
assert workers == (2, 4)
assert len(SEEDS) == 30
assert set(SEEDS).isdisjoint(range(1001, 1031))
assert set(SEEDS).isdisjoint(range(2001, 2061))

assert Path(
    "docs/STAGE_D8_B1_SELECTION_FREEZE.md"
).is_file()

if OUTPUT.exists() and any(OUTPUT.iterdir()):
    raise RuntimeError(
        f"Validation output directory is not empty: {OUTPUT}"
    )

branch = subprocess.check_output(
    ["git", "branch", "--show-current"], text=True
).strip()

assert branch == "stage-d-finalization"

plan = {
    "phase": "internal_validation",
    "status": "PREFLIGHT_ONLY",
    "threshold_B": 1,
    "config": str(CONFIG),
    "output": str(OUTPUT),
    "seeds": {"first": 1101, "last": 1130, "count": 30},
    "treatments": list(labels),
    "shard_counts": list(shards),
    "cross_shard_ratios": list(ratios),
    "workers": list(workers),
    "condition_count": 18,
    "condition_seed_groups": 540,
    "planned_runs": 1620,
    "simulation_executed": False,
}

print(json.dumps(plan, indent=2))
print("\nSTAGE E PREFLIGHT PLAN: PASS")
print("Simulation not started.")
