from __future__ import annotations

from collections import defaultdict


class LockError(RuntimeError):
    pass


class LockManager:
    def __init__(self, shard_count: int):
        self.shard_count = shard_count
        self.locked_by: dict[int, int] = {}
        self.active_since: dict[int, float] = {}
        self.history: dict[int, list[tuple[float, float]]] = defaultdict(list)

    @property
    def locked_shards(self) -> set[int]:
        return set(self.locked_by)

    def conflict_count(self, required_shards: tuple[int, ...]) -> int:
        return sum(1 for shard in required_shards if shard in self.locked_by)

    def can_acquire_all(self, required_shards: tuple[int, ...]) -> bool:
        return self.conflict_count(required_shards) == 0

    def acquire_all(self, tx_id: int, required_shards: tuple[int, ...], now: float) -> None:
        if not self.can_acquire_all(required_shards):
            raise LockError(f"Transaction {tx_id} cannot atomically acquire {required_shards}")
        for shard in required_shards:
            self.locked_by[shard] = tx_id
            self.active_since[shard] = now

    def release_all(self, tx_id: int, required_shards: tuple[int, ...], now: float) -> None:
        for shard in required_shards:
            owner = self.locked_by.get(shard)
            if owner != tx_id:
                raise LockError(f"Shard {shard} is not owned by transaction {tx_id}")
        for shard in required_shards:
            start = self.active_since.pop(shard)
            self.history[shard].append((start, now))
            del self.locked_by[shard]

    def occupancy_fraction(self, shard: int, now: float, window_s: float) -> float:
        if now <= 0:
            return 0.0
        effective = min(window_s, now)
        start_window = now - effective
        occupied = 0.0
        for start, end in self.history.get(shard, ()):
            if end <= start_window or start >= now:
                continue
            occupied += max(0.0, min(end, now) - max(start, start_window))
        if shard in self.locked_by:
            start = self.active_since[shard]
            occupied += max(0.0, now - max(start, start_window))
        return min(1.0, max(0.0, occupied / effective))

    def assert_consistent(self, in_service_tx_ids: set[int]) -> None:
        for shard, tx_id in self.locked_by.items():
            if tx_id not in in_service_tx_ids:
                raise AssertionError(f"Locked shard {shard} has non-service owner {tx_id}")
