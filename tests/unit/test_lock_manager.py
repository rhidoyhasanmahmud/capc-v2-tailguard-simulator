import pytest

from capc_sim.coordinator.lock_manager import LockError, LockManager


def test_atomic_acquire_is_all_or_nothing():
    lm = LockManager(4)
    lm.acquire_all(1, (0, 1), 0.0)
    before = dict(lm.locked_by)
    with pytest.raises(LockError):
        lm.acquire_all(2, (1, 2), 0.1)
    assert lm.locked_by == before
    assert 2 not in lm.locked_by


def test_release_and_recent_occupancy():
    lm = LockManager(4)
    lm.acquire_all(1, (0,), 1.0)
    lm.release_all(1, (0,), 3.0)
    # Over [0,4], shard was occupied 2 seconds.
    assert lm.occupancy_fraction(0, 4.0, 10.0) == pytest.approx(0.5)
