from __future__ import annotations

from .capc import CAPCScheduler
from .capc_no_contention import CAPCNoContentionScheduler
from .capc_no_priority import CAPCNoPriorityScheduler
from .diagnostic_fifo import DiagnosticFIFOScheduler
from .static_atomic_fifo import StaticAtomicFIFOScheduler


SCHEDULERS = {
    "diagnostic_fifo": DiagnosticFIFOScheduler,
    "static_atomic_fifo": StaticAtomicFIFOScheduler,
    "capc": CAPCScheduler,
    "capc_no_contention": CAPCNoContentionScheduler,
    "capc_no_priority": CAPCNoPriorityScheduler,
}


def create_scheduler(name: str):
    try:
        return SCHEDULERS[name]()
    except KeyError as exc:
        raise ValueError(f"Unknown scheduler: {name}. Available: {', '.join(SCHEDULERS)}") from exc
