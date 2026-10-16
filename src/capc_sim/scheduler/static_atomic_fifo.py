from __future__ import annotations

from .base import SelectionDecision
from capc_sim.simulation.state import SystemState


class StaticAtomicFIFOScheduler:
    name = "static_atomic_fifo"
    matched_atomic = True

    def select(self, state: SystemState, now: float) -> SelectionDecision:
        eligible = state.eligible()
        if not eligible:
            return SelectionDecision(None, {
                "candidate_count": len(state.queue),
                "eligible_count": 0,
                "blocked_count": len(state.queue),
                "selection_rule": "earliest_eligible_fifo",
            })
        tx = min(eligible, key=lambda item: (item.queue_entry_time, item.transaction_id))
        return SelectionDecision(tx, {
            "candidate_count": len(state.queue),
            "eligible_count": len(eligible),
            "blocked_count": len(state.queue) - len(eligible),
            "selection_rule": "earliest_eligible_fifo",
        })
