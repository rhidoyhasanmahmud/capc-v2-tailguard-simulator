from __future__ import annotations

import heapq
from dataclasses import dataclass
from pathlib import Path

from capc_sim.config.schema import ExperimentConfig
from capc_sim.coordinator.lock_manager import LockManager
from capc_sim.coordinator.queue import CoordinationQueue
from capc_sim.coordinator.worker_pool import WorkerPool
from capc_sim.metrics.outputs import write_run_outputs
from capc_sim.metrics.recorder import MetricsRecorder
from capc_sim.model.enums import TransactionStatus
from capc_sim.model.events import Event, EventKind
from capc_sim.model.transaction import Transaction
from capc_sim.scheduler.factory import create_scheduler
from capc_sim.simulation.state import SystemState
from capc_sim.workload.trace import Trace


@dataclass(frozen=True)
class SimulationResult:
    run_id: str
    output_dir: Path
    summary: dict
    trace_hash: str


class Simulator:
    """Deterministic discrete-event simulator for the Chapter 3-5 research boundary."""

    def __init__(self, config: ExperimentConfig, trace: Trace, scheduler_name: str, seed: int):
        self.config = config
        self.trace = trace
        self.seed = int(seed)
        self.scheduler = create_scheduler(scheduler_name)
        self.scheduler_name = scheduler_name
        self.run_id = self._run_id()
        self.transactions = [Transaction(spec=s) for s in trace.transactions]
        self.tx_by_id = {tx.transaction_id: tx for tx in self.transactions}
        self.queue = CoordinationQueue()
        self.lock_manager = LockManager(config.sharding.shard_count)
        self.workers = WorkerPool(config.coordination.workers)
        self.cross_shard_arrivals: list[float] = []
        self.state = SystemState(config, self.queue, self.lock_manager, self.cross_shard_arrivals)
        self.recorder = MetricsRecorder(self.run_id, self.seed, scheduler_name)
        self.events: list[Event] = []
        self.seq = 0
        self._events_processed = 0
        self.cutoff_snapshot: dict = {}
        self._scheduled_completion_tx_ids: set[int] = set()

    def _run_id(self) -> str:
        return (
            f"sh{self.config.sharding.shard_count}"
            f"_x{int(round(self.config.sharding.cross_shard_ratio * 100)):02d}"
            f"_w{self.config.coordination.workers}"
            f"_{self.scheduler_name}_seed{self.seed:03d}"
        )

    def _push(self, time: float, kind: EventKind, payload=None) -> None:
        self.seq += 1
        heapq.heappush(self.events, Event(float(time), kind, self.seq, payload))

    def _workload_state_at(self, now: float) -> str:
        duration = self.config.simulation.duration_s
        lookup = min(max(0.0, now), max(0.0, duration - 1e-12))
        return self.trace.state_at(lookup).value

    def _record_state(self, now: float, event: str) -> None:
        self.recorder.record_state(
            now=now,
            event=event,
            queue_length=len(self.queue),
            active_workers=self.workers.active_count,
            locked_shards=len(self.lock_manager.locked_shards),
            workload_state=self._workload_state_at(now),
        )

    def _initialize_events(self) -> None:
        for tx in self.transactions:
            self._push(tx.arrival_time, EventKind.ARRIVAL, tx.transaction_id)
        self._push(self.config.simulation.duration_s, EventKind.CUTOFF, None)
        self._record_state(0.0, "INITIAL")

    def run(self, output_dir: str | Path) -> SimulationResult:
        self._initialize_events()
        while self.events:
            event = heapq.heappop(self.events)
            now = event.time
            if event.kind is EventKind.ARRIVAL:
                self._arrival(self.tx_by_id[event.payload], now)
            elif event.kind is EventKind.COMPLETION:
                self._completion(self.tx_by_id[event.payload], now)
            elif event.kind is EventKind.CUTOFF:
                self._cutoff(now)
            else:
                raise RuntimeError(f"Unsupported event kind: {event.kind}")
            self._events_processed += 1

            # Development/verification keeps exhaustive per-event checks.
            # Primary research runs periodically execute the same full checks
            # to avoid quadratic verification overhead on large traces.
            if (
                self.config.research.mode != "primary"
                or self._events_processed % 1000 == 0
                or event.kind is EventKind.CUTOFF
            ):
                self._assert_invariants()

        # Always perform one exhaustive final-state validation.
        self._assert_invariants()

        # The arrival horizon stops at duration_s; admitted cross-shard work then drains.
        if self.queue or self.workers.active_count:
            raise AssertionError("Simulation ended before queue/service drain completed")

        output_dir = Path(output_dir) / self.run_id
        summary = write_run_outputs(
            directory=output_dir,
            config=self.config,
            trace=self.trace,
            transactions=self.transactions,
            recorder=self.recorder,
            cutoff_snapshot=self.cutoff_snapshot,
            seed=self.seed,
            scheduler=self.scheduler_name,
            run_id=self.run_id,
        )
        return SimulationResult(self.run_id, output_dir, summary, self.trace.hash())

    def _arrival(self, tx: Transaction, now: float) -> None:
        if tx.is_cross_shard:
            tx.status = TransactionStatus.QUEUED
            tx.queue_entry_time = now
            self.cross_shard_arrivals.append(now)
            self.queue.enqueue(tx)

            # RQ2 predictors are captured at queue entry, before subsequent waiting occurs.
            tx.queue_length_at_entry = len(self.queue)
            tx.arrival_rate_at_entry = self.state.arrival_rate(now)
            tx.active_lock_conflicts_at_entry = self.state.active_lock_conflicts(tx)

            self._record_state(now, f"ARRIVAL:{tx.transaction_id}")
            self._dispatch(now)
        else:
            # Intra-shard execution is deliberately outside the cross-shard coordination model.
            tx.status = TransactionStatus.INTRA_SHARD_BYPASS
            tx.service_start_time = now
            tx.completion_time = now
            tx.completed_by_cutoff = now <= self.config.simulation.duration_s
            self._record_state(now, f"INTRA_BYPASS:{tx.transaction_id}")

    def _dispatch(self, now: float) -> None:
        while self.workers.free_count > 0 and self.queue:
            if self.scheduler.matched_atomic:
                eligible_count = len(self.state.eligible())
            else:
                eligible_count = len(self.queue)
            self.recorder.record_dispatch_snapshot(
                now=now,
                queue_count=len(self.queue),
                eligible_count=eligible_count,
                active_workers=self.workers.active_count,
                free_workers=self.workers.free_count,
                locked_shards=len(self.lock_manager.locked_shards),
            )

            decision = self.scheduler.select(self.state, now)
            tx = decision.transaction
            if tx is None:
                break

            if self.scheduler.matched_atomic:
                if not self.lock_manager.can_acquire_all(tx.required_shards):
                    raise AssertionError("Matched atomic scheduler returned an ineligible transaction")
                self.lock_manager.acquire_all(tx.transaction_id, tx.required_shards, now)

            self.queue.remove(tx)
            worker_id = self.workers.acquire(tx.transaction_id)
            tx.status = TransactionStatus.IN_SERVICE
            tx.worker_id = worker_id
            tx.service_start_time = now
            self.recorder.record_decision(now=now, transaction=tx, diagnostics=decision.diagnostics)
            self._record_state(now, f"DISPATCH:{tx.transaction_id}")

            completion = now + tx.service_time_s
            self._push(completion, EventKind.COMPLETION, tx.transaction_id)
            self._scheduled_completion_tx_ids.add(tx.transaction_id)
            # Loop recomputes queue and lock state before using another free worker.

    def _completion(self, tx: Transaction, now: float) -> None:
        if tx.transaction_id not in self._scheduled_completion_tx_ids:
            raise AssertionError("Completion event without scheduled service")
        if tx.worker_id is None:
            raise AssertionError("In-service transaction missing worker")

        if self.scheduler.matched_atomic:
            self.lock_manager.release_all(tx.transaction_id, tx.required_shards, now)
        self.workers.release(tx.worker_id, tx.transaction_id)

        tx.worker_id = None
        tx.status = TransactionStatus.COMPLETED
        tx.completion_time = now
        tx.completed_by_cutoff = now <= self.config.simulation.duration_s
        self._scheduled_completion_tx_ids.remove(tx.transaction_id)
        self._record_state(now, f"COMPLETE:{tx.transaction_id}")
        self._dispatch(now)

    def _cutoff(self, now: float) -> None:
        warmup = self.config.simulation.warmup_s
        measured = [
            tx for tx in self.transactions
            if tx.is_cross_shard and warmup <= tx.arrival_time < now
        ]
        completed = sum(
            1 for tx in measured
            if tx.completion_time is not None and tx.completion_time <= now
        )
        self.cutoff_snapshot = {
            "time": now,
            "measurement_cross_shard_admitted": len(measured),
            "completed_by_cutoff": completed,
            "unfinished_at_cutoff": len(measured) - completed,
            "queue_length": len(self.queue),
            "active_workers": self.workers.active_count,
        }
        self._record_state(now, "CUTOFF")

    def _assert_invariants(self) -> None:
        in_service_ids = set(self.workers.busy.values())
        if self.scheduler.matched_atomic:
            self.lock_manager.assert_consistent(in_service_ids)

        for tx in self.queue:
            if tx.status is not TransactionStatus.QUEUED:
                raise AssertionError("Queue contains non-QUEUED transaction")
        for tx in self.transactions:
            if tx.status is TransactionStatus.IN_SERVICE and tx.transaction_id not in in_service_ids:
                raise AssertionError("Transaction state says IN_SERVICE but worker pool disagrees")
            if tx.status is TransactionStatus.COMPLETED and tx.worker_id is not None:
                raise AssertionError("Completed transaction still owns a worker")

        accounted = sum(
            1 for tx in self.transactions
            if tx.status in {
                TransactionStatus.FUTURE,
                TransactionStatus.INTRA_SHARD_BYPASS,
                TransactionStatus.QUEUED,
                TransactionStatus.IN_SERVICE,
                TransactionStatus.COMPLETED,
                TransactionStatus.REJECTED,
            }
        )
        if accounted != len(self.transactions):
            raise AssertionError("Transaction-accounting invariant failed")
