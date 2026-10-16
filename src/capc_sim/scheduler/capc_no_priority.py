from __future__ import annotations

from .capc import CAPCScheduler
from capc_sim.simulation.state import SystemState


class CAPCNoPriorityScheduler(CAPCScheduler):
    name = "capc_no_priority"

    def effective_urgency_weight(self, state: SystemState) -> float:
        return 0.0
