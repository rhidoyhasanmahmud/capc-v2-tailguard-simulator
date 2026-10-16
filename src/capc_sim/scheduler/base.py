from __future__ import annotations

from dataclasses import dataclass, field
from typing import Protocol

from capc_sim.model.transaction import Transaction
from capc_sim.simulation.state import SystemState


@dataclass(frozen=True)
class SelectionDecision:
    transaction: Transaction | None
    diagnostics: dict = field(default_factory=dict)


class Scheduler(Protocol):
    name: str
    matched_atomic: bool

    def select(self, state: SystemState, now: float) -> SelectionDecision:
        ...
