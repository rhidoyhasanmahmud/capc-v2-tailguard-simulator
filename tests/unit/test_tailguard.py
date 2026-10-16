from dataclasses import replace

import pytest

from capc_sim.config.loader import load_config
from capc_sim.config.schema import TailGuardConfig
from capc_sim.coordinator.lock_manager import LockManager
from capc_sim.coordinator.queue import CoordinationQueue
from capc_sim.model.enums import PriorityClass, TransactionStatus, WorkloadState
from capc_sim.model.transaction import Transaction, TransactionSpec
from capc_sim.scheduler.capc import CAPCScheduler
from capc_sim.scheduler.tailguard import TailGuardScheduler
from capc_sim.simulation.state import SystemState


def _tx(tx_id, arrival, shards, priority):
    tx = Transaction(
        TransactionSpec(
            transaction_id=tx_id,
            arrival_time=arrival,
            required_shards=shards,
            priority=priority,
            workload_state=WorkloadState.NORMAL,
            service_time_s=0.1,
            is_cross_shard=True,
        )
    )
    tx.status = TransactionStatus.QUEUED
    tx.queue_entry_time = arrival
    return tx


def _state(transactions, threshold=3):
    cfg = load_config("configs/dev.yaml")
    cfg = replace(
        cfg,
        tailguard=TailGuardConfig(bypass_threshold=threshold),
    )

    queue = CoordinationQueue()
    for tx in transactions:
        queue.enqueue(tx)

    return SystemState(
        cfg,
        queue,
        LockManager(cfg.sharding.shard_count),
        [],
    )


def test_tailguard_falls_back_to_exact_capc_selection_when_inactive():
    low = _tx(1, 0.0, (0, 1), PriorityClass.LOW)
    high = _tx(2, 0.0, (2, 3), PriorityClass.HIGH)

    state = _state([low, high], threshold=3)

    capc = CAPCScheduler().select(state, 0.5)
    tailguard = TailGuardScheduler().select(state, 0.5)

    assert tailguard.transaction is capc.transaction
    assert tailguard.diagnostics["tailguard_active"] is False
    assert tailguard.diagnostics["selection_rule"] == "max_capc_score"


def test_tailguard_selects_protected_eligible_candidate():
    low = _tx(1, 0.0, (0, 1), PriorityClass.LOW)
    high = _tx(2, 0.0, (2, 3), PriorityClass.HIGH)

    low.consecutive_bypass_count = 3

    state = _state([low, high], threshold=3)
    decision = TailGuardScheduler().select(state, 0.5)

    assert decision.transaction is low
    assert decision.diagnostics["tailguard_active"] is True
    assert decision.diagnostics["selection_rule"] == "tailguard_protected_bypass"


def test_tailguard_never_forces_blocked_protected_candidate():
    blocked = _tx(1, 0.0, (0, 1), PriorityClass.LOW)
    eligible = _tx(2, 0.0, (2, 3), PriorityClass.HIGH)

    blocked.consecutive_bypass_count = 100

    state = _state([blocked, eligible], threshold=3)

    state.lock_manager.acquire_all(99, (0,), 0.0)

    decision = TailGuardScheduler().select(state, 0.5)

    assert decision.transaction is eligible
    assert decision.diagnostics["tailguard_active"] is False


def test_tailguard_protected_tie_break_is_deterministic():
    newer = _tx(20, 0.2, (0, 1), PriorityClass.HIGH)
    older_high_id = _tx(10, 0.1, (2, 3), PriorityClass.LOW)

    newer.consecutive_bypass_count = 5
    older_high_id.consecutive_bypass_count = 5

    state = _state([newer, older_high_id], threshold=3)
    decision = TailGuardScheduler().select(state, 0.5)

    assert decision.transaction is older_high_id

    # Same age and bypass count: lower transaction ID wins.
    a = _tx(7, 0.1, (0, 1), PriorityClass.HIGH)
    b = _tx(3, 0.1, (2, 3), PriorityClass.LOW)
    a.consecutive_bypass_count = 5
    b.consecutive_bypass_count = 5

    state = _state([a, b], threshold=3)
    decision = TailGuardScheduler().select(state, 0.5)

    assert decision.transaction is b


def test_tailguard_requires_threshold_configuration():
    tx = _tx(1, 0.0, (0, 1), PriorityClass.LOW)

    cfg = load_config("configs/dev.yaml")
    queue = CoordinationQueue()
    queue.enqueue(tx)

    state = SystemState(
        cfg,
        queue,
        LockManager(cfg.sharding.shard_count),
        [],
    )

    with pytest.raises(RuntimeError, match="bypass_threshold"):
        TailGuardScheduler().select(state, 0.1)
