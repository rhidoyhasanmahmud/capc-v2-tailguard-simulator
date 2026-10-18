from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
import pytest

from capc_sim.config.loader import load_config
from capc_sim.experiments.calibration import (
    calibration_treatments,
    run_calibration,
)


def test_calibration_treatment_labels_are_unique():
    treatments = calibration_treatments(
        (1, 2, 4, 8, 16, 32)
    )

    assert [t.label for t in treatments] == [
        "static_atomic_fifo",
        "capc",
        "tailguard_b1",
        "tailguard_b2",
        "tailguard_b4",
        "tailguard_b8",
        "tailguard_b16",
        "tailguard_b32",
    ]

    assert len({
        t.label
        for t in treatments
    }) == len(treatments)


def test_calibration_runner_preserves_pairing_and_threshold_namespace(
    tmp_path: Path,
):
    cfg = load_config("configs/dev.yaml")

    # Tiny deterministic gate: one condition, one seed,
    # two TailGuard thresholds.
    df = run_calibration(
        cfg,
        output=tmp_path / "calibration",
        seeds=(123,),
        thresholds=(1, 4),
        shard_counts=(4,),
        cross_shard_ratios=(0.30,),
        workers=(2,),
    )

    assert len(df) == 4

    assert set(df["treatment"]) == {
        "static_atomic_fifo",
        "capc",
        "tailguard_b1",
        "tailguard_b4",
    }

    assert df["trace_hash"].nunique() == 1

    tg = df[
        df["treatment"].str.startswith("tailguard_")
    ].sort_values("treatment")

    assert set(
        tg["bypass_threshold"].astype(int)
    ) == {1, 4}

    root = tmp_path / "calibration" / "runs"

    assert (
        root
        / "tailguard_b1"
        / "sh4_x30_w2_tailguard_seed123"
    ).is_dir()

    assert (
        root
        / "tailguard_b4"
        / "sh4_x30_w2_tailguard_seed123"
    ).is_dir()

    integrity = pd.read_csv(
        tmp_path
        / "calibration"
        / "pair_integrity.csv"
    )

    assert len(integrity) == 1
    assert bool(integrity.iloc[0]["paired_trace_equal"])
    assert int(
        integrity.iloc[0]["expected_treatment_count"]
    ) == 4
    assert int(
        integrity.iloc[0]["observed_treatment_count"]
    ) == 4

    manifest = json.loads(
        (
            tmp_path
            / "calibration"
            / "calibration_manifest.json"
        ).read_text()
    )

    assert manifest["status"] == "complete"
    assert manifest["planned_run_count"] == 4
    assert manifest["completed_run_count"] == 4
    assert manifest["failure_count"] == 0
    assert manifest["paired_trace_integrity"] is True

    labels = [
        row["label"]
        for row in manifest["treatments"]
    ]

    assert labels == [
        "static_atomic_fifo",
        "capc",
        "tailguard_b1",
        "tailguard_b4",
    ]


def test_calibration_resume_rejects_protocol_mismatch(
    tmp_path: Path,
):
    cfg = load_config("configs/dev.yaml")
    output = tmp_path / "calibration"

    run_calibration(
        cfg,
        output=output,
        seeds=(123,),
        thresholds=(1,),
        shard_counts=(4,),
        cross_shard_ratios=(0.30,),
        workers=(2,),
    )

    with pytest.raises(
        RuntimeError,
        match="protocol/config differs",
    ):
        run_calibration(
            cfg,
            output=output,
            seeds=(123,),
            thresholds=(2,),
            shard_counts=(4,),
            cross_shard_ratios=(0.30,),
            workers=(2,),
            resume=True,
        )


def test_calibration_resume_reuses_verified_runs(
    tmp_path: Path,
):
    cfg = load_config("configs/dev.yaml")
    output = tmp_path / "calibration"

    first = run_calibration(
        cfg,
        output=output,
        seeds=(123,),
        thresholds=(1,),
        shard_counts=(4,),
        cross_shard_ratios=(0.30,),
        workers=(2,),
    )

    second = run_calibration(
        cfg,
        output=output,
        seeds=(123,),
        thresholds=(1,),
        shard_counts=(4,),
        cross_shard_ratios=(0.30,),
        workers=(2,),
        resume=True,
    )

    assert len(first) == 3
    assert len(second) == 3

    assert (
        second["resumed_existing_run"]
        .astype(bool)
        .all()
    )

    assert second["trace_hash"].nunique() == 1
