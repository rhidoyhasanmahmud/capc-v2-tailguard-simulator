from __future__ import annotations

from dataclasses import dataclass

from .enums import PriorityClass, TransactionStatus, WorkloadState


@dataclass(frozen=True)
class TransactionSpec:
    transaction_id: int
    arrival_time: float
    required_shards: tuple[int, ...]
    priority: PriorityClass
    workload_state: WorkloadState
    service_time_s: float
    is_cross_shard: bool

    @property
    def dependency_degree(self) -> int:
        return len(self.required_shards)


@dataclass
class Transaction:
    spec: TransactionSpec
    status: TransactionStatus = TransactionStatus.FUTURE
    queue_entry_time: float | None = None
    service_start_time: float | None = None
    completion_time: float | None = None
    worker_id: int | None = None
    queue_length_at_entry: int | None = None
    arrival_rate_at_entry: float | None = None
    active_lock_conflicts_at_entry: int | None = None
    completed_by_cutoff: bool = False

    @property
    def transaction_id(self) -> int:
        return self.spec.transaction_id

    @property
    def arrival_time(self) -> float:
        return self.spec.arrival_time

    @property
    def required_shards(self) -> tuple[int, ...]:
        return self.spec.required_shards

    @property
    def priority(self) -> PriorityClass:
        return self.spec.priority

    @property
    def workload_state(self) -> WorkloadState:
        return self.spec.workload_state

    @property
    def service_time_s(self) -> float:
        return self.spec.service_time_s

    @property
    def is_cross_shard(self) -> bool:
        return self.spec.is_cross_shard

    @property
    def dependency_degree(self) -> int:
        return self.spec.dependency_degree

    def waiting_time(self) -> float | None:
        if self.service_start_time is None or self.queue_entry_time is None:
            return None
        return self.service_start_time - self.queue_entry_time

    def latency(self) -> float | None:
        if self.completion_time is None:
            return None
        return self.completion_time - self.arrival_time
