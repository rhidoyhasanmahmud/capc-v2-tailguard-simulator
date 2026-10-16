from __future__ import annotations

import tempfile
from dataclasses import replace
from pathlib import Path

import pandas as pd

from capc_sim.config.schema import ExperimentConfig
from capc_sim.coordinator.lock_manager import LockManager
from capc_sim.coordinator.queue import CoordinationQueue
from capc_sim.model.enums import PriorityClass, WorkloadState
from capc_sim.model.transaction import Transaction, TransactionSpec
from capc_sim.scheduler.capc import CAPCScheduler
from capc_sim.simulation.engine import Simulator
from capc_sim.simulation.state import SystemState
from capc_sim.workload.mmpp import TraceGenerator
from capc_sim.workload.trace import StateInterval, Trace


def _spec(tx_id: int, arrival: float, shards: tuple[int, ...], priority=PriorityClass.MEDIUM,
          service: float = 0.1) -> TransactionSpec:
    return TransactionSpec(
        transaction_id=tx_id,
        arrival_time=arrival,
        required_shards=shards,
        priority=priority,
        workload_state=WorkloadState.NORMAL,
        service_time_s=service,
        is_cross_shard=True,
    )


def _short_config(config: ExperimentConfig, *, duration=2.0, warmup=0.0, workers=2) -> ExperimentConfig:
    return replace(
        config,
        simulation=replace(config.simulation, duration_s=duration, warmup_s=warmup),
        coordination=replace(config.coordination, workers=workers),
    )


def _trace_for_locking() -> Trace:
    return Trace(
        transactions=(
            _spec(1, 0.00, (0, 1), service=0.50),
            _spec(2, 0.10, (0, 2), PriorityClass.HIGH, service=0.10),
            _spec(3, 0.10, (2, 3), PriorityClass.LOW, service=0.10),
        ),
        state_intervals=(StateInterval(WorkloadState.NORMAL, 0.0, 2.0),),
    )


def verification_report(config: ExperimentConfig) -> dict[str, dict]:
    report: dict[str, dict] = {}

    def record(code: str, name: str, passed: bool, evidence: str) -> None:
        report[code] = {"name": name, "passed": bool(passed), "evidence": evidence}

    # V1 Trace reproducibility.
    t1 = TraceGenerator(config, 17).generate()
    t2 = TraceGenerator(config, 17).generate()
    record("V1", "Trace reproducibility", t1.hash() == t2.hash(), f"hash={t1.hash()[:16]}…")

    with tempfile.TemporaryDirectory(prefix="capc_verify_") as tmp:
        tmp = Path(tmp)
        cfg = _short_config(config)
        trace = _trace_for_locking()

        # V2 Cross-treatment trace equality.
        a = Simulator(cfg, trace, "static_atomic_fifo", 1).run(tmp / "v2a")
        b = Simulator(cfg, trace, "capc", 1).run(tmp / "v2b")
        record(
            "V2", "Cross-treatment trace equality",
            a.trace_hash == b.trace_hash == trace.hash(),
            f"shared_trace_hash={trace.hash()[:16]}…",
        )

        static_tx = pd.read_csv(a.output_dir / "transactions.csv").set_index("transaction_id")

        # V3 Static Atomic FIFO ordering: tx2 is older than tx3 at t=.1 but blocked by tx1.
        v3 = static_tx.loc[3, "service_start_time"] == 0.10 and static_tx.loc[2, "service_start_time"] >= 0.50
        record("V3", "Static Atomic FIFO earliest eligible", v3,
               f"tx3_start={static_tx.loc[3, 'service_start_time']:.3f}, tx2_start={static_tx.loc[2, 'service_start_time']:.3f}")

        # V4 Diagnostic FIFO raw order.
        diag = Simulator(cfg, trace, "diagnostic_fifo", 1).run(tmp / "v4")
        diag_tx = pd.read_csv(diag.output_dir / "transactions.csv").set_index("transaction_id")
        v4 = diag_tx.loc[2, "service_start_time"] == 0.10
        record("V4", "Diagnostic FIFO raw queue order", v4,
               f"tx2_start={diag_tx.loc[2, 'service_start_time']:.3f}")

        # V5 Lock exclusion.
        v5 = static_tx.loc[2, "service_start_time"] >= static_tx.loc[1, "completion_time"]
        record("V5", "Matched-atomic lock exclusion", v5,
               f"tx1_complete={static_tx.loc[1, 'completion_time']:.3f}, tx2_start={static_tx.loc[2, 'service_start_time']:.3f}")

        # V6 Lock release (direct invariant check).
        lm = LockManager(4)
        lm.acquire_all(99, (0, 1), 0.0)
        lm.release_all(99, (0, 1), 0.2)
        record("V6", "All-or-nothing lock release", len(lm.locked_shards) == 0,
               f"remaining_locked_shards={len(lm.locked_shards)}")

        # V7 Multi-worker dispatch.
        v7 = static_tx.loc[1, "service_start_time"] == 0.0 and static_tx.loc[3, "service_start_time"] == 0.10
        record("V7", "Multi-worker dispatch", v7,
               f"tx1_start={static_tx.loc[1, 'service_start_time']:.3f}, tx3_start={static_tx.loc[3, 'service_start_time']:.3f}")

        # V8 CAPC score correctness against hand-composed formula.
        spec = _spec(10, 0.0, (0, 1), PriorityClass.HIGH, service=0.1)
        tx = Transaction(spec)
        tx.queue_entry_time = 0.0
        q = CoordinationQueue(); q.enqueue(tx)
        state = SystemState(config, q, LockManager(config.sharding.shard_count), [0.0])
        sched = CAPCScheduler()
        now = 0.5
        f = sched.features(tx, state, now)
        rw = config.capc.ranking_weights
        expected = (
            float(rw.urgency) * f.urgency
            + float(rw.aging) * f.aging
            + (1 + float(config.capc.gamma) * f.contention)
            * (float(rw.dependency) * (1 - f.dependency) + float(rw.lock_pressure) * (1 - f.recent_lock_pressure))
        )
        record("V8", "CAPC score hand-check", abs(f.score - expected) < 1e-12,
               f"computed={f.score:.12f}, expected={expected:.12f}")

        # V9 Aging monotonicity and saturation.
        ages = [state.aging(tx, t) for t in (0.0, 0.25, 0.50, 100.0)]
        v9 = ages == sorted(ages) and ages[-1] == 1.0
        record("V9", "Aging monotonicity", v9, f"ages={ages}")

        # V10 Accounting invariant at final output.
        tx_df = pd.read_csv(a.output_dir / "transactions.csv")
        v10 = len(tx_df) == len(trace.transactions) and tx_df["transaction_id"].nunique() == len(trace.transactions)
        record("V10", "Transaction accounting", v10,
               f"rows={len(tx_df)}, unique_ids={tx_df['transaction_id'].nunique()}")

        # V11 Low-load sanity: non-overlapping arrivals => negligible queueing.
        low_trace = Trace(
            transactions=tuple(_spec(i + 1, i * 0.30, (0, 1), service=0.05) for i in range(5)),
            state_intervals=(StateInterval(WorkloadState.NORMAL, 0.0, 2.0),),
        )
        low = Simulator(_short_config(config, workers=2), low_trace, "static_atomic_fifo", 2).run(tmp / "v11")
        low_tx = pd.read_csv(low.output_dir / "transactions.csv")
        v11 = float(low_tx["waiting_time"].max()) < 1e-12
        record("V11", "Low-load sanity", v11, f"max_wait={float(low_tx['waiting_time'].max()):.6f}s")

        # V12 Overload stress: one worker, same shards, arrivals faster than service.
        overload_trace = Trace(
            transactions=tuple(_spec(i + 1, i * 0.01, (0, 1), service=0.10) for i in range(40)),
            state_intervals=(StateInterval(WorkloadState.NORMAL, 0.0, 1.0),),
        )
        over_cfg = _short_config(config, duration=1.0, warmup=0.0, workers=1)
        over = Simulator(over_cfg, overload_trace, "static_atomic_fifo", 3).run(tmp / "v12")
        v12 = int(over.summary["max_queue_length"]) > 1
        record("V12", "Overload stress queue growth", v12,
               f"max_queue_length={over.summary['max_queue_length']}")

    return report


def verification_passed(report: dict[str, dict]) -> bool:
    return all(bool(item.get("passed")) for item in report.values())
