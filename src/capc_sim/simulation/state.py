from __future__ import annotations

from bisect import bisect_right
from dataclasses import dataclass

from capc_sim.config.schema import ExperimentConfig
from capc_sim.coordinator.lock_manager import LockManager
from capc_sim.coordinator.queue import CoordinationQueue
from capc_sim.model.enums import PriorityClass
from capc_sim.model.transaction import Transaction


@dataclass
class SystemState:
    """Read-only scheduling view over current simulator state."""

    config: ExperimentConfig
    queue: CoordinationQueue
    lock_manager: LockManager
    cross_shard_arrivals: list[float]

    def arrival_rate(self, now: float) -> float:
        """Equation 4.1: N_x((t-W_eff), t] / W_eff."""
        w = self._capc("arrival_window_s")
        if now <= 0:
            return 0.0
        effective = min(w, now)
        start = now - effective
        # Open on the left, closed on the right, matching N_x(a,t].
        left = bisect_right(self.cross_shard_arrivals, start)
        right = bisect_right(self.cross_shard_arrivals, now)
        return (right - left) / effective

    def normalized_arrival(self, now: float) -> float:
        return min(1.0, max(0.0, self.arrival_rate(now) / self._capc("lambda_ref")))

    def normalized_queue(self) -> float:
        return min(1.0, max(0.0, len(self.queue) / self._capc("queue_ref")))

    def dependency_burden(self, tx: Transaction) -> float:
        dmin = self.config.sharding.d_min
        dmax = self.config.sharding.d_max
        if dmax == dmin:
            return 0.0
        return min(1.0, max(0.0, (tx.dependency_degree - dmin) / (dmax - dmin)))

    def dependency_pressure(self) -> float:
        if not self.queue:
            return 0.0
        return sum(self.dependency_burden(tx) for tx in self.queue) / len(self.queue)

    def lock_pressure(self) -> float:
        return len(self.lock_manager.locked_shards) / self.config.sharding.shard_count

    def contention_components(self, now: float) -> dict[str, float]:
        return {
            "arrival": self.normalized_arrival(now),
            "queue": self.normalized_queue(),
            "dependency": self.dependency_pressure(),
            "lock": self.lock_pressure(),
        }

    def contention_score(self, now: float) -> float:
        """Equation 4.6: convex combination of four normalized pressures."""
        c = self.contention_components(now)
        w = self.config.capc.contention_weights
        weights = (w.arrival, w.queue, w.dependency, w.lock)
        if any(v is None for v in weights):
            raise RuntimeError("CAPC contention weights are not frozen/configured")
        score = (
            float(w.arrival) * c["arrival"]
            + float(w.queue) * c["queue"]
            + float(w.dependency) * c["dependency"]
            + float(w.lock) * c["lock"]
        )
        return min(1.0, max(0.0, score))

    def contention_label(self, now: float) -> str:
        score = self.contention_score(now)
        tau1 = self.config.capc.thresholds.low_medium
        tau2 = self.config.capc.thresholds.medium_high
        if tau1 is None or tau2 is None:
            raise RuntimeError("CAPC interpretation thresholds are not configured")
        if score < tau1:
            return "LOW"
        if score < tau2:
            return "MEDIUM"
        return "HIGH"

    @staticmethod
    def urgency(tx: Transaction) -> float:
        return {
            PriorityClass.LOW: 0.0,
            PriorityClass.MEDIUM: 0.5,
            PriorityClass.HIGH: 1.0,
        }[tx.priority]

    def aging(self, tx: Transaction, now: float) -> float:
        """Equation 4.8: bounded monotonic age protection."""
        horizon = self._capc("aging_horizon_s")
        origin = tx.queue_entry_time if tx.queue_entry_time is not None else tx.arrival_time
        return min(1.0, max(0.0, (now - origin) / horizon))

    def active_lock_conflicts(self, tx: Transaction) -> int:
        """Equation 4.10 / eligibility signal K_i(t)."""
        return self.lock_manager.conflict_count(tx.required_shards)

    def recent_lock_pressure(self, tx: Transaction, now: float) -> float:
        """Equation 4.11: mean recent lock occupancy over required shards."""
        w = self._capc("lock_window_s")
        if not tx.required_shards:
            return 0.0
        return sum(
            self.lock_manager.occupancy_fraction(shard, now, w)
            for shard in tx.required_shards
        ) / len(tx.required_shards)

    def eligible(self) -> list[Transaction]:
        return [tx for tx in self.queue if self.active_lock_conflicts(tx) == 0]

    def _capc(self, field: str) -> float:
        value = getattr(self.config.capc, field)
        if value is None:
            raise RuntimeError(f"CAPC parameter {field} is not configured")
        return float(value)
