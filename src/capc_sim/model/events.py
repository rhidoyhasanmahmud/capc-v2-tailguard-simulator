from __future__ import annotations

from dataclasses import dataclass, field
from enum import IntEnum
from typing import Any


class EventKind(IntEnum):
    COMPLETION = 0
    CUTOFF = 1
    ARRIVAL = 2


@dataclass(order=True)
class Event:
    time: float
    kind: EventKind
    sequence: int
    payload: Any = field(compare=False, default=None)
