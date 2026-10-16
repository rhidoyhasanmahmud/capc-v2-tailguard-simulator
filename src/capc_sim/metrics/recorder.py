from __future__ import annotations

from dataclasses import dataclass, field

from capc_sim.model.transaction import Transaction


@dataclass
class MetricsRecorder:
    run_id: str
    seed: int
    scheduler: str
    state_events: list[dict] = field(default_factory=list)
    decisions: list[dict] = field(default_factory=list)
    dispatch_snapshots: list[dict] = field(default_factory=list)

    def record_state(
        self,
        *,
        now: float,
        event: str,
        queue_length: int,
        active_workers: int,
        locked_shards: int,
        workload_state: str,
    ) -> None:
        self.state_events.append({
            "run_id": self.run_id,
            "seed": self.seed,
            "scheduler": self.scheduler,
            "time": now,
            "event": event,
            "queue_length": queue_length,
            "active_workers": active_workers,
            "locked_shards": locked_shards,
            "workload_state": workload_state,
        })

    def record_dispatch_snapshot(
        self,
        *,
        now: float,
        queue_count: int,
        eligible_count: int,
        active_workers: int,
        free_workers: int,
        locked_shards: int,
    ) -> None:
        self.dispatch_snapshots.append({
            "run_id": self.run_id,
            "seed": self.seed,
            "scheduler": self.scheduler,
            "time": now,
            "queue_count": queue_count,
            "eligible_count": eligible_count,
            "blocked_count": max(0, queue_count - eligible_count),
            "active_workers": active_workers,
            "free_workers": free_workers,
            "locked_shards": locked_shards,
        })

    def record_decision(self, *, now: float, transaction: Transaction, diagnostics: dict) -> None:
        origin = transaction.queue_entry_time if transaction.queue_entry_time is not None else transaction.arrival_time
        row = {
            "run_id": self.run_id,
            "seed": self.seed,
            "scheduler": self.scheduler,
            "time": now,
            "transaction_id": transaction.transaction_id,
            "priority": transaction.priority.value,
            "required_shards": "|".join(str(s) for s in transaction.required_shards),
            "waiting_age": max(0.0, now - origin),
        }
        row.update(diagnostics)
        self.decisions.append(row)
