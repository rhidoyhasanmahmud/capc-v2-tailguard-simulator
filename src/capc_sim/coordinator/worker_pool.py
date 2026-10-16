from __future__ import annotations


class WorkerPool:
    def __init__(self, worker_count: int):
        self.worker_count = worker_count
        self.free_workers: set[int] = set(range(worker_count))
        self.busy: dict[int, int] = {}  # worker_id -> tx_id

    @property
    def free_count(self) -> int:
        return len(self.free_workers)

    @property
    def active_count(self) -> int:
        return len(self.busy)

    def acquire(self, tx_id: int) -> int:
        if not self.free_workers:
            raise RuntimeError("No free coordination worker")
        worker = min(self.free_workers)
        self.free_workers.remove(worker)
        self.busy[worker] = tx_id
        return worker

    def release(self, worker_id: int, tx_id: int) -> None:
        if self.busy.get(worker_id) != tx_id:
            raise RuntimeError(f"Worker {worker_id} is not running transaction {tx_id}")
        del self.busy[worker_id]
        self.free_workers.add(worker_id)
