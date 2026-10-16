from __future__ import annotations

from .base import SelectionDecision
from capc_sim.simulation.state import SystemState


class DiagnosticFIFOScheduler:
    """Non-atomic descriptive queue-order reference, not a causal baseline."""

    name = "diagnostic_fifo"
    matched_atomic = False

    def select(self, state: SystemState, now: float) -> SelectionDecision:
        if not state.queue:
            return SelectionDecision(None, {
                "candidate_count": 0,
                "eligible_count": 0,
                "blocked_count": 0,
                "selection_rule": "raw_fifo_non_atomic",
            })
        tx = min(state.queue, key=lambda item: (item.queue_entry_time, item.transaction_id))
        return SelectionDecision(tx, {
            "candidate_count": len(state.queue),
            "eligible_count": len(state.queue),
            "blocked_count": 0,
            "selection_rule": "raw_fifo_non_atomic",
        })
