from dataclasses import replace

import pandas as pd

from capc_sim.config.loader import load_config
from capc_sim.model.enums import PriorityClass, WorkloadState
from capc_sim.model.transaction import TransactionSpec
from capc_sim.simulation.engine import Simulator
from capc_sim.workload.trace import StateInterval, Trace


def _spec(tx_id, arrival, shards, priority, service):
    return TransactionSpec(
        transaction_id=tx_id,
        arrival_time=arrival,
        required_shards=shards,
        priority=priority,
        workload_state=WorkloadState.NORMAL,
        service_time_s=service,
        is_cross_shard=True,
    )


def test_capc_records_eligible_bypass_without_changing_dispatch(tmp_path):
    cfg = load_config("configs/dev.yaml")
    cfg = cfg.with_condition(
        6,
        cfg.sharding.cross_shard_ratio,
        1,
    )
    cfg = replace(
        cfg,
        simulation=replace(
            cfg.simulation,
            duration_s=2.0,
            warmup_s=0.0,
        ),
    )

    trace = Trace(
        transactions=(
            # Occupies the only worker but does not conflict with tx2/tx3.
            _spec(1, 0.00, (0, 1), PriorityClass.MEDIUM, 0.50),

            # Both queue while the worker is busy and are lock-eligible.
            # CAPC should prefer the HIGH-priority tx3 when service frees.
            _spec(2, 0.10, (2, 3), PriorityClass.LOW, 0.10),
            _spec(3, 0.10, (4, 5), PriorityClass.HIGH, 0.10),
        ),
        state_intervals=(
            StateInterval(WorkloadState.NORMAL, 0.0, 2.0),
        ),
    )

    result = Simulator(cfg, trace, "capc", 123).run(tmp_path)
    tx = pd.read_csv(result.output_dir / "transactions.csv").set_index(
        "transaction_id"
    )

    # CAPC ordering remains the expected HIGH-before-LOW ordering.
    assert tx.loc[3, "service_start_time"] == 0.50
    assert tx.loc[2, "service_start_time"] == 0.60

    # tx2 was eligible when tx3 was selected, therefore exactly one bypass.
    assert tx.loc[2, "eligible_observation_count"] == 2
    assert tx.loc[2, "bypass_count"] == 1
    assert tx.loc[2, "max_consecutive_bypass_count"] == 1
    assert tx.loc[2, "bypass_count_at_service_start"] == 1

    # Selected tx3 was observed eligible but was never bypassed.
    assert tx.loc[3, "eligible_observation_count"] == 1
    assert tx.loc[3, "bypass_count"] == 0
    assert tx.loc[3, "bypass_count_at_service_start"] == 0
