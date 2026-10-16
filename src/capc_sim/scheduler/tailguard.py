from __future__ import annotations

from .base import SelectionDecision
from .capc import CAPCScheduler
from capc_sim.simulation.state import SystemState


class TailGuardScheduler(CAPCScheduler):
    """CAPC-v1 with bounded consecutive eligible-bypass protection."""

    name = "tailguard"
    matched_atomic = True

    @staticmethod
    def _threshold(state: SystemState) -> int:
        value = state.config.tailguard.bypass_threshold
        if value is None:
            raise RuntimeError(
                "TailGuard bypass_threshold is not configured"
            )
        return int(value)

    def select(self, state: SystemState, now: float) -> SelectionDecision:
        eligible = state.eligible()

        if not eligible:
            return SelectionDecision(None, {
                "candidate_count": len(state.queue),
                "eligible_count": 0,
                "blocked_count": len(state.queue),
                "selection_rule": "tailguard_no_eligible",
                "tailguard_active": False,
                "tailguard_threshold": self._threshold(state),
                "protected_candidate_count": 0,
            })

        threshold = self._threshold(state)

        protected = [
            tx
            for tx in eligible
            if tx.consecutive_bypass_count >= threshold
        ]

        if not protected:
            # Exact frozen CAPC-v1 selection path when protection is inactive.
            decision = super().select(state, now)
            diagnostics = dict(decision.diagnostics)
            diagnostics.update({
                "tailguard_active": False,
                "tailguard_threshold": threshold,
                "protected_candidate_count": 0,
            })
            return SelectionDecision(decision.transaction, diagnostics)

        tx = max(
            protected,
            key=lambda candidate: (
                candidate.consecutive_bypass_count,
                -(
                    candidate.queue_entry_time
                    if candidate.queue_entry_time is not None
                    else candidate.arrival_time
                ),
                -candidate.transaction_id,
            ),
        )

        # CAPC features remain observable even when TailGuard overrides ranking.
        f = self.features(tx, state, now)
        components = state.contention_components(now)

        return SelectionDecision(tx, {
            "candidate_count": len(state.queue),
            "eligible_count": len(eligible),
            "blocked_count": len(state.queue) - len(eligible),
            "selection_rule": "tailguard_protected_bypass",
            "tailguard_active": True,
            "tailguard_threshold": threshold,
            "protected_candidate_count": len(protected),
            "protected_consecutive_bypass": tx.consecutive_bypass_count,
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
