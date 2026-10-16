from __future__ import annotations

from .capc import CAPCScheduler
from capc_sim.simulation.state import SystemState


class CAPCNoContentionScheduler(CAPCScheduler):
    name = "capc_no_contention"

    def effective_gamma(self, state: SystemState) -> float:
        return 0.0
