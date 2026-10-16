from __future__ import annotations

import numpy as np

from capc_sim.config.schema import ExperimentConfig
from capc_sim.model.enums import PriorityClass, WorkloadState
from capc_sim.model.transaction import TransactionSpec
from .trace import StateInterval, Trace


class TraceGenerator:
    """Generate exogenous traces independently of scheduler execution."""

    def __init__(self, config: ExperimentConfig, seed: int):
        self.config = config
        self.seed = int(seed)

    def generate(self) -> Trace:
        ss = np.random.SeedSequence(self.seed)
        rng_state, rng_arrival, rng_type, rng_dep, rng_shards, rng_priority, rng_service = [
            np.random.default_rng(s) for s in ss.spawn(7)
        ]
        duration = self.config.simulation.duration_s
        state = WorkloadState(self.config.workload.initial_state)
        t = 0.0
        intervals: list[StateInterval] = []
        arrivals: list[tuple[float, WorkloadState]] = []

        while t < duration:
            if state is WorkloadState.NORMAL:
                transition_rate = self.config.workload.q_normal_to_burst
                arrival_rate = self.config.workload.lambda_normal
                next_state = WorkloadState.BURST
            else:
                transition_rate = self.config.workload.q_burst_to_normal
                arrival_rate = self.config.workload.lambda_burst
                next_state = WorkloadState.NORMAL

            state_end = min(duration, t + float(rng_state.exponential(1.0 / transition_rate)))
            intervals.append(StateInterval(state=state, start=t, end=state_end))

            a = t
            while True:
                a += float(rng_arrival.exponential(1.0 / arrival_rate))
                if a >= state_end or a >= duration:
                    break
                arrivals.append((a, state))

            t = state_end
            if t < duration:
                state = next_state

        specs: list[TransactionSpec] = []
        pr = self.config.priority
        high_cut = pr.high
        medium_cut = pr.high + pr.medium
        for tx_id, (arrival_time, workload_state) in enumerate(arrivals, start=1):
            is_cross = bool(rng_type.random() < self.config.sharding.cross_shard_ratio)
            if is_cross:
                degree = 2 if rng_dep.random() < self.config.sharding.two_shard_probability else 3
            else:
                degree = 1
            shards = tuple(sorted(int(x) for x in rng_shards.choice(
                self.config.sharding.shard_count, size=degree, replace=False
            )))
            u = float(rng_priority.random())
            if u < high_cut:
                priority = PriorityClass.HIGH
            elif u < medium_cut:
                priority = PriorityClass.MEDIUM
            else:
                priority = PriorityClass.LOW
            service_ms = float(rng_service.uniform(
                self.config.coordination.service_time_ms.min,
                self.config.coordination.service_time_ms.max,
            ))
            specs.append(TransactionSpec(
                transaction_id=tx_id,
                arrival_time=arrival_time,
                required_shards=shards,
                priority=priority,
                workload_state=workload_state,
                service_time_s=service_ms / 1000.0,
                is_cross_shard=is_cross,
            ))

        return Trace(transactions=tuple(specs), state_intervals=tuple(intervals))
