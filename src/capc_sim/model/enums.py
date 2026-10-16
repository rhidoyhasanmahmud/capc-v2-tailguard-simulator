from __future__ import annotations

from enum import Enum


class WorkloadState(str, Enum):
    NORMAL = "NORMAL"
    BURST = "BURST"


class PriorityClass(str, Enum):
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"


class TransactionStatus(str, Enum):
    FUTURE = "FUTURE"
    INTRA_SHARD_BYPASS = "INTRA_SHARD_BYPASS"
    QUEUED = "QUEUED"
    IN_SERVICE = "IN_SERVICE"
    COMPLETED = "COMPLETED"
    REJECTED = "REJECTED"
