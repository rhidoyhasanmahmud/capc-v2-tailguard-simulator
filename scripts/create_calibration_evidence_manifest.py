"""Create a checksum index for frozen calibration analysis artifacts."""
import hashlib
import json
import platform
import subprocess
from datetime import datetime, timezone
from pathlib import Path

import numpy
import pandas

ROOT = Path("results/tailguard_calibration")
OUTPUT = Path("docs/STAGE_D_EVIDENCE_MANIFEST.json")

FILES = [
    "calibration_manifest.json",
    "calibration_summary.csv",
    "pair_integrity.csv",
    "analysis_d3_2_priority_runs.csv",
    "analysis_d3_2_priority_comparison.csv",
    "analysis_d3_3_starvation_runs.csv",
    "analysis_d3_3_starvation_comparison.csv",
    "analysis_d3_5_bootstrap.csv",
]

def sha256(path):
    digest = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()

artifacts = []

for name in FILES:
    path = ROOT / name
    if not path.is_file():
        raise FileNotFoundError(path)

    artifacts.append({
        "path": str(path),
        "size_bytes": path.stat().st_size,
        "sha256": sha256(path),
    })

git_commit = subprocess.check_output(
    ["git", "rev-parse", "HEAD"], text=True
).strip()

manifest = {
    "stage": "D",
    "status": "calibration_evidence_only_not_frozen",
    "generated_at_utc": datetime.now(
        timezone.utc
    ).isoformat(),
    "calibration_seeds": [1001, 1030],
    "planned_runs": 4320,
    "analysis_git_commit": git_commit,
    "python": platform.python_version(),
    "numpy": numpy.__version__,
    "pandas": pandas.__version__,
    "artifacts": artifacts,
    "note": (
        "Checksums cover listed summary and analysis files only. "
        "Raw transaction and decision traces are not included. "
        "No threshold is selected or frozen."
    ),
}

OUTPUT.parent.mkdir(parents=True, exist_ok=True)
OUTPUT.write_text(
    json.dumps(manifest, indent=2) + "\n",
    encoding="utf-8",
)

print("Created:", OUTPUT)
print("Hashed files:", len(artifacts))
print("Analysis commit:", git_commit)
print("Threshold status: NOT FROZEN")
