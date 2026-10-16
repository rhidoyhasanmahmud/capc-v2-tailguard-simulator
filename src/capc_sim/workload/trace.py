from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass
from pathlib import Path

import pandas as pd

from capc_sim.model.enums import WorkloadState
from capc_sim.model.transaction import TransactionSpec


@dataclass(frozen=True)
class StateInterval:
    state: WorkloadState
    start: float
    end: float


@dataclass(frozen=True)
class Trace:
    transactions: tuple[TransactionSpec, ...]
    state_intervals: tuple[StateInterval, ...]

    def canonical_payload(self) -> dict:
        return {
            "transactions": [
                {
                    "transaction_id": t.transaction_id,
                    "arrival_time": round(t.arrival_time, 12),
                    "required_shards": list(t.required_shards),
                    "priority": t.priority.value,
                    "workload_state": t.workload_state.value,
                    "service_time_s": round(t.service_time_s, 12),
                    "is_cross_shard": t.is_cross_shard,
                }
                for t in self.transactions
            ],
            "state_intervals": [
                {"state": s.state.value, "start": round(s.start, 12), "end": round(s.end, 12)}
                for s in self.state_intervals
            ],
        }

    def hash(self) -> str:
        blob = json.dumps(self.canonical_payload(), sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(blob.encode("utf-8")).hexdigest()

    def state_at(self, t: float) -> WorkloadState:
        for interval in self.state_intervals:
            if interval.start <= t < interval.end:
                return interval.state
        return self.state_intervals[-1].state

    def write(self, directory: str | Path) -> None:
        directory = Path(directory)
        directory.mkdir(parents=True, exist_ok=True)
        tx_rows = []
        for t in self.transactions:
            tx_rows.append({
                "transaction_id": t.transaction_id,
                "arrival_time": t.arrival_time,
                "required_shards": "|".join(str(x) for x in t.required_shards),
                "priority": t.priority.value,
                "workload_state": t.workload_state.value,
                "service_time_s": t.service_time_s,
                "is_cross_shard": t.is_cross_shard,
            })
        pd.DataFrame(tx_rows).to_csv(directory / "trace.csv", index=False)
        pd.DataFrame([
            {"state": s.state.value, "start": s.start, "end": s.end, "duration": s.end - s.start}
            for s in self.state_intervals
        ]).to_csv(directory / "workload_states.csv", index=False)
