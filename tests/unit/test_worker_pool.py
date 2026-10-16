import pytest

from capc_sim.coordinator.worker_pool import WorkerPool


def test_worker_pool_acquire_and_release():
    pool = WorkerPool(worker_count=2)

    assert pool.free_count == 2
    assert pool.active_count == 0

    first = pool.acquire(tx_id=101)
    second = pool.acquire(tx_id=202)

    assert first == 0
    assert second == 1
    assert pool.free_count == 0
    assert pool.active_count == 2
    assert pool.busy[first] == 101
    assert pool.busy[second] == 202

    with pytest.raises(RuntimeError, match="No free coordination worker"):
        pool.acquire(tx_id=303)

    pool.release(first, 101)

    assert pool.free_count == 1
    assert pool.active_count == 1

    again = pool.acquire(tx_id=303)

    assert again == first
    assert pool.busy[again] == 303


def test_worker_pool_rejects_invalid_release():
    pool = WorkerPool(worker_count=1)

    worker = pool.acquire(tx_id=101)

    with pytest.raises(
        RuntimeError,
        match="Worker 0 is not running transaction 999",
    ):
        pool.release(worker, 999)

    assert pool.active_count == 1
    assert pool.busy[worker] == 101

    pool.release(worker, 101)

    assert pool.free_count == 1
    assert pool.active_count == 0
