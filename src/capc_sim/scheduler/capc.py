from __future__ import annotations

from dataclasses import dataclass

from .base import SelectionDecision
from capc_sim.model.transaction import Transaction
from capc_sim.simulation.state import SystemState


@dataclass(frozen=True)
class CAPCFeatures:
    urgency: float
    aging: float
    dependency: float
    recent_lock_pressure: float
    contention: float
    score: float


class CAPCScheduler:
    name = "capc"
    matched_atomic = True

    def effective_gamma(self, state: SystemState) -> float:
        if state.config.capc.gamma is None:
            raise RuntimeError("CAPC gamma is not configured")
        return float(state.config.capc.gamma)

    def effective_urgency_weight(self, state: SystemState) -> float:
        value = state.config.capc.ranking_weights.urgency
        if value is None:
            raise RuntimeError("CAPC urgency weight is not configured")
        return float(value)

    def features(self, tx: Transaction, state: SystemState, now: float) -> CAPCFeatures:
        rw = state.config.capc.ranking_weights
        values = (rw.aging, rw.dependency, rw.lock_pressure)
        if any(v is None for v in values):
            raise RuntimeError("CAPC ranking weights are not fully configured")

        u_i = state.urgency(tx)
        a_i = state.aging(tx, now)
        d_i = state.dependency_burden(tx)
        h_i = state.recent_lock_pressure(tx, now)
        c_t = state.contention_score(now)
        gamma = self.effective_gamma(state)

        # Chapter 4, Eq. 4.12.
        score = (
            self.effective_urgency_weight(state) * u_i
            + float(rw.aging) * a_i
            + (1.0 + gamma * c_t)
            * (
                float(rw.dependency) * (1.0 - d_i)
                + float(rw.lock_pressure) * (1.0 - h_i)
            )
        )
        return CAPCFeatures(u_i, a_i, d_i, h_i, c_t, score)

    def select(self, state: SystemState, now: float) -> SelectionDecision:
        eligible = state.eligible()
        if not eligible:
            return SelectionDecision(None, {
                "candidate_count": len(state.queue),
                "eligible_count": 0,
                "blocked_count": len(state.queue),
                "selection_rule": "max_capc_score",
            })

        scored = [(tx, self.features(tx, state, now)) for tx in eligible]
        tx, f = max(
            scored,
            key=lambda item: (
                item[1].score,
                item[1].aging,
                -(item[0].queue_entry_time if item[0].queue_entry_time is not None else item[0].arrival_time),
                -item[0].transaction_id,
            ),
        )
        components = state.contention_components(now)
        return SelectionDecision(tx, {
            "candidate_count": len(state.queue),
            "eligible_count": len(eligible),
            "blocked_count": len(state.queue) - len(eligible),
            "selection_rule": "max_capc_score",
            "capc_score": f.score,
            "contention_score": f.contention,
            "contention_label": state.contention_label(now),
            "x_arrival": components["arrival"],
            "x_queue": components["queue"],
            "x_dependency": components["dependency"],
            "x_lock": components["lock"],
            "urgency": f.urgency,
            "aging": f.aging,
            "dependency": f.dependency,
            "recent_lock_pressure": f.recent_lock_pressure,
        })
