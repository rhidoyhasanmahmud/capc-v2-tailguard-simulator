import pytest

from capc_sim.coordinator.queue import CoordinationQueue
from capc_sim.model.enums import PriorityClass, WorkloadState
from capc_sim.model.transaction import Transaction, TransactionSpec


def make_tx(i):
    return Transaction(TransactionSpec(i, float(i), (0,1), PriorityClass.LOW, WorkloadState.NORMAL, 0.05, True))


def test_queue_storage_is_policy_free():
    q = CoordinationQueue()
    a, b = make_tx(1), make_tx(2)
    q.enqueue(a); q.enqueue(b)
    assert tuple(q) == (a, b)
    q.remove(a)
    assert tuple(q) == (b,)


def test_queue_rejects_duplicate_object():
    q = CoordinationQueue(); a = make_tx(1); q.enqueue(a)
    with pytest.raises(ValueError):
        q.enqueue(a)
