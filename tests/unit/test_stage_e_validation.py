"""Stage E manifest and phase-isolation safety tests."""
import json

import pytest

from capc_sim.config.loader import load_config
from capc_sim.experiments.calibration import (
    _planned_manifest,
    _prepare_output,
    calibration_treatments,
)


def make_manifest(phase="internal_validation"):
    cfg = load_config("configs/primary.yaml")

    return _planned_manifest(
        cfg,
        seeds=tuple(range(1101, 1131)),
        shard_counts=(4, 8, 16),
        cross_shard_ratios=(0.1, 0.3, 0.5),
        workers=(2, 4),
        treatments=calibration_treatments((1,)),
        phase=phase,
    )


def test_validation_manifest_is_frozen():
    manifest = make_manifest()

    assert manifest["phase"] == "internal_validation"
    assert manifest["seeds"] == list(range(1101, 1131))
    assert manifest["planned_condition_seed_pairs"] == 540
    assert manifest["planned_run_count"] == 1620

    assert [
        treatment["label"]
        for treatment in manifest["treatments"]
    ] == [
        "static_atomic_fifo",
        "capc",
        "tailguard_b1",
    ]


def test_calibration_phase_still_supported():
    manifest = make_manifest("calibration")
    assert manifest["phase"] == "calibration"


def test_invalid_phase_rejected():
    with pytest.raises(ValueError, match="Unsupported"):
        make_manifest("independent_confirmation")


def test_resume_rejects_calibration_manifest(tmp_path):
    existing = make_manifest("calibration")
    (tmp_path / "calibration_manifest.json").write_text(
        json.dumps(existing)
    )

    with pytest.raises(RuntimeError, match="differs"):
        _prepare_output(
            tmp_path,
            make_manifest("internal_validation"),
            resume=True,
        )


def test_resume_rejects_different_seed_set(tmp_path):
    existing = make_manifest()

    existing["seeds"] = list(range(1001, 1031))

    (tmp_path / "calibration_manifest.json").write_text(
        json.dumps(existing)
    )

    with pytest.raises(RuntimeError, match="differs"):
        _prepare_output(
            tmp_path,
            make_manifest(),
            resume=True,
        )


def test_nonempty_output_requires_explicit_resume(tmp_path):
    (tmp_path / "existing.txt").write_text("preserve")

    with pytest.raises(FileExistsError):
        _prepare_output(
            tmp_path,
            make_manifest(),
            resume=False,
        )
