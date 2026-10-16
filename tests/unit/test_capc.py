import pytest

from capc_sim.coordinator.lock_manager import LockManager
from capc_sim.coordinator.queue import CoordinationQueue
from capc_sim.model.enums import PriorityClass, WorkloadState
from capc_sim.model.transaction import Transaction, TransactionSpec
from capc_sim.scheduler.capc import CAPCScheduler
from capc_sim.scheduler.capc_no_contention import CAPCNoContentionScheduler
from capc_sim.scheduler.capc_no_priority import CAPCNoPriorityScheduler
from capc_sim.simulation.state import SystemState


def tx(tx_id, arrival, shards, priority):
    obj = Transaction(TransactionSpec(
        transaction_id=tx_id,
        arrival_time=arrival,
        required_shards=tuple(shards),
        priority=priority,
        workload_state=WorkloadState.NORMAL,
        service_time_s=0.05,
        is_cross_shard=True,
    ))
    obj.queue_entry_time = arrival
    return obj


def state_with(dev_config, items, arrivals=None, lock=None):
    q = CoordinationQueue(); q.extend_for_test(items)
    return SystemState(dev_config, q, lock or LockManager(dev_config.sharding.shard_count), arrivals or [])


def test_urgency_mapping(dev_config):
    state = state_with(dev_config, [])
    assert state.urgency(tx(1, 0, (0,1), PriorityClass.LOW)) == 0.0
    assert state.urgency(tx(2, 0, (0,1), PriorityClass.MEDIUM)) == 0.5
    assert state.urgency(tx(3, 0, (0,1), PriorityClass.HIGH)) == 1.0


def test_dependency_normalization(dev_config):
    state = state_with(dev_config, [])
    assert state.dependency_burden(tx(1, 0, (0,1), PriorityClass.LOW)) == 0.0
    assert state.dependency_burden(tx(2, 0, (0,1,2), PriorityClass.LOW)) == 1.0


def test_aging_monotonic_and_saturates(dev_config):
    item = tx(1, 0, (0,1), PriorityClass.LOW)
    state = state_with(dev_config, [item], [0.0])
    assert state.aging(item, 0.0) == 0.0
    assert state.aging(item, 0.5) <= state.aging(item, 1.0)
    assert state.aging(item, 100.0) == 1.0


def test_eligible_transactions_have_zero_current_conflict(dev_config):
    a = tx(1, 0, (0,1), PriorityClass.HIGH)
    b = tx(2, 0.1, (2,3), PriorityClass.MEDIUM)
    lm = LockManager(4)
    lm.acquire_all(99, (0,), 0.0)
    state = state_with(dev_config, [a,b], [0.0,0.1], lm)
    eligible = state.eligible()
    assert b in eligible and a not in eligible
    assert all(state.active_lock_conflicts(x) == 0 for x in eligible)


def test_capc_selection_is_deterministic(dev_config):
    a = tx(1, 0.0, (0,1), PriorityClass.MEDIUM)
    b = tx(2, 0.1, (2,3), PriorityClass.MEDIUM)
    state = state_with(dev_config, [a,b], [0.0,0.1])
    scheduler = CAPCScheduler()
    d1 = scheduler.select(state, 0.5)
    d2 = scheduler.select(state, 0.5)
    assert d1.transaction.transaction_id == d2.transaction.transaction_id
    assert d1.diagnostics["capc_score"] == pytest.approx(d2.diagnostics["capc_score"])


def test_capc_score_matches_declared_formula(dev_config):
    item = tx(1, 0.0, (0,1), PriorityClass.HIGH)
    state = state_with(dev_config, [item], [0.0])
    f = CAPCScheduler().features(item, state, 0.5)
    rw = dev_config.capc.ranking_weights
    expected = (
        float(rw.urgency) * f.urgency
        + float(rw.aging) * f.aging
        + (1 + float(dev_config.capc.gamma) * f.contention)
        * (float(rw.dependency) * (1 - f.dependency) + float(rw.lock_pressure) * (1 - f.recent_lock_pressure))
    )
    assert f.score == pytest.approx(expected)


def test_no_contention_ablation_sets_gamma_zero(dev_config):
    a = tx(1, 0.0, (0,1), PriorityClass.MEDIUM)
    state = state_with(dev_config, [a], [0.0])
    full = CAPCScheduler().features(a, state, 0.5).score
    no_c = CAPCNoContentionScheduler().features(a, state, 0.5).score
    assert no_c <= full + 1e-12


def test_no_priority_removes_urgency_effect(dev_config):
    hi = tx(1, 0.0, (0,1), PriorityClass.HIGH)
    lo = tx(2, 0.0, (2,3), PriorityClass.LOW)
    state = state_with(dev_config, [hi,lo], [0.0])
    sched = CAPCNoPriorityScheduler()
    f_hi = sched.features(hi, state, 0.0)
    f_lo = sched.features(lo, state, 0.0)
    assert f_hi.score == pytest.approx(f_lo.score)
