from __future__ import annotations

from dataclasses import dataclass, field, replace
from typing import Any, Mapping


class ConfigError(ValueError):
    pass


@dataclass(frozen=True)
class ResearchConfig:
    mode: str = "development"
    require_frozen_capc: bool = False
    label: str = "dev"


@dataclass(frozen=True)
class SimulationConfig:
    duration_s: float
    warmup_s: float


@dataclass(frozen=True)
class WorkloadConfig:
    lambda_normal: float
    lambda_burst: float
    q_normal_to_burst: float
    q_burst_to_normal: float
    initial_state: str = "NORMAL"


@dataclass(frozen=True)
class ShardingConfig:
    shard_count: int
    cross_shard_ratio: float
    two_shard_probability: float = 0.80
    d_min: int = 2
    d_max: int = 3


@dataclass(frozen=True)
class PriorityConfig:
    high: float
    medium: float
    low: float


@dataclass(frozen=True)
class ServiceTimeConfig:
    min: float
    max: float


@dataclass(frozen=True)
class CoordinationConfig:
    workers: int
    service_time_ms: ServiceTimeConfig


@dataclass(frozen=True)
class ContentionWeights:
    arrival: float | None
    queue: float | None
    dependency: float | None
    lock: float | None

    def values(self) -> tuple[float | None, ...]:
        return self.arrival, self.queue, self.dependency, self.lock


@dataclass(frozen=True)
class RankingWeights:
    urgency: float | None
    aging: float | None
    dependency: float | None
    lock_pressure: float | None

    def values(self) -> tuple[float | None, ...]:
        return self.urgency, self.aging, self.dependency, self.lock_pressure


@dataclass(frozen=True)
class Thresholds:
    low_medium: float | None
    medium_high: float | None


@dataclass(frozen=True)
class CapcConfig:
    arrival_window_s: float | None
    lock_window_s: float | None
    lambda_ref: float | None
    queue_ref: float | None
    contention_weights: ContentionWeights
    aging_horizon_s: float | None
    ranking_weights: RankingWeights
    gamma: float | None
    thresholds: Thresholds

    def missing_fields(self) -> list[str]:
        fields: list[tuple[str, Any]] = [
            ("arrival_window_s", self.arrival_window_s),
            ("lock_window_s", self.lock_window_s),
            ("lambda_ref", self.lambda_ref),
            ("queue_ref", self.queue_ref),
            ("aging_horizon_s", self.aging_horizon_s),
            ("gamma", self.gamma),
            ("thresholds.low_medium", self.thresholds.low_medium),
            ("thresholds.medium_high", self.thresholds.medium_high),
        ]
        fields.extend((f"contention_weights.{k}", v) for k, v in zip(
            ("arrival", "queue", "dependency", "lock"), self.contention_weights.values()
        ))
        fields.extend((f"ranking_weights.{k}", v) for k, v in zip(
            ("urgency", "aging", "dependency", "lock_pressure"), self.ranking_weights.values()
        ))
        return [name for name, value in fields if value is None]


@dataclass(frozen=True)
class MatrixConfig:
    shard_counts: tuple[int, ...] = (4, 8, 16)
    cross_shard_ratios: tuple[float, ...] = (0.10, 0.30, 0.50)
    workers: tuple[int, ...] = (2, 4)
    schedulers: tuple[str, ...] = (
        "diagnostic_fifo",
        "static_atomic_fifo",
        "capc",
        "capc_no_contention",
        "capc_no_priority",
    )


@dataclass(frozen=True)
class ExperimentConfig:
    research: ResearchConfig
    simulation: SimulationConfig
    workload: WorkloadConfig
    sharding: ShardingConfig
    priority: PriorityConfig
    coordination: CoordinationConfig
    capc: CapcConfig
    matrix: MatrixConfig = field(default_factory=MatrixConfig)

    def with_condition(self, shard_count: int, cross_shard_ratio: float, workers: int) -> "ExperimentConfig":
        return replace(
            self,
            sharding=replace(self.sharding, shard_count=shard_count, cross_shard_ratio=cross_shard_ratio),
            coordination=replace(self.coordination, workers=workers),
        )


def _req(d: Mapping[str, Any], key: str) -> Any:
    if key not in d:
        raise ConfigError(f"Missing required configuration key: {key}")
    return d[key]


def from_dict(data: Mapping[str, Any]) -> ExperimentConfig:
    research = data.get("research", {})
    sim = _req(data, "simulation")
    workload = _req(data, "workload")
    sharding = _req(data, "sharding")
    priority = _req(data, "priority")
    coordination = _req(data, "coordination")
    capc = _req(data, "capc")
    matrix = data.get("matrix", {})

    cfg = ExperimentConfig(
        research=ResearchConfig(
            mode=str(research.get("mode", "development")),
            require_frozen_capc=bool(research.get("require_frozen_capc", False)),
            label=str(research.get("label", "dev")),
        ),
        simulation=SimulationConfig(
            duration_s=float(_req(sim, "duration_s")),
            warmup_s=float(_req(sim, "warmup_s")),
        ),
        workload=WorkloadConfig(
            lambda_normal=float(_req(workload, "lambda_normal")),
            lambda_burst=float(_req(workload, "lambda_burst")),
            q_normal_to_burst=float(_req(workload, "q_normal_to_burst")),
            q_burst_to_normal=float(_req(workload, "q_burst_to_normal")),
            initial_state=str(workload.get("initial_state", "NORMAL")).upper(),
        ),
        sharding=ShardingConfig(
            shard_count=int(_req(sharding, "shard_count")),
            cross_shard_ratio=float(_req(sharding, "cross_shard_ratio")),
            two_shard_probability=float(sharding.get("two_shard_probability", 0.80)),
            d_min=int(sharding.get("d_min", 2)),
            d_max=int(sharding.get("d_max", 3)),
        ),
        priority=PriorityConfig(
            high=float(_req(priority, "high")),
            medium=float(_req(priority, "medium")),
            low=float(_req(priority, "low")),
        ),
        coordination=CoordinationConfig(
            workers=int(_req(coordination, "workers")),
            service_time_ms=ServiceTimeConfig(
                min=float(_req(_req(coordination, "service_time_ms"), "min")),
                max=float(_req(_req(coordination, "service_time_ms"), "max")),
            ),
        ),
        capc=CapcConfig(
            arrival_window_s=capc.get("arrival_window_s"),
            lock_window_s=capc.get("lock_window_s"),
            lambda_ref=capc.get("lambda_ref"),
            queue_ref=capc.get("queue_ref"),
            contention_weights=ContentionWeights(**_req(capc, "contention_weights")),
            aging_horizon_s=capc.get("aging_horizon_s"),
            ranking_weights=RankingWeights(**_req(capc, "ranking_weights")),
            gamma=capc.get("gamma"),
            thresholds=Thresholds(**_req(capc, "thresholds")),
        ),
        matrix=MatrixConfig(
            shard_counts=tuple(int(x) for x in matrix.get("shard_counts", (4, 8, 16))),
            cross_shard_ratios=tuple(float(x) for x in matrix.get("cross_shard_ratios", (0.1, 0.3, 0.5))),
            workers=tuple(int(x) for x in matrix.get("workers", (2, 4))),
            schedulers=tuple(str(x) for x in matrix.get("schedulers", MatrixConfig().schedulers)),
        ),
    )
    validate(cfg)
    return cfg


def validate(cfg: ExperimentConfig) -> None:
    if cfg.simulation.duration_s <= 0:
        raise ConfigError("simulation.duration_s must be > 0")
    if not 0 <= cfg.simulation.warmup_s < cfg.simulation.duration_s:
        raise ConfigError("warmup_s must satisfy 0 <= warmup_s < duration_s")
    if cfg.workload.initial_state not in {"NORMAL", "BURST"}:
        raise ConfigError("initial_state must be NORMAL or BURST")
    for name, value in {
        "lambda_normal": cfg.workload.lambda_normal,
        "lambda_burst": cfg.workload.lambda_burst,
        "q_normal_to_burst": cfg.workload.q_normal_to_burst,
        "q_burst_to_normal": cfg.workload.q_burst_to_normal,
    }.items():
        if value <= 0:
            raise ConfigError(f"{name} must be > 0")
    if cfg.sharding.shard_count < cfg.sharding.d_max:
        raise ConfigError("shard_count must be >= d_max")
    if not 0 <= cfg.sharding.cross_shard_ratio <= 1:
        raise ConfigError("cross_shard_ratio must be in [0, 1]")
    if not 0 <= cfg.sharding.two_shard_probability <= 1:
        raise ConfigError("two_shard_probability must be in [0, 1]")
    if cfg.sharding.d_min < 2 or cfg.sharding.d_max < cfg.sharding.d_min:
        raise ConfigError("cross-shard d_min/d_max are invalid")
    probs = (cfg.priority.high, cfg.priority.medium, cfg.priority.low)
    if any(p < 0 for p in probs) or abs(sum(probs) - 1.0) > 1e-9:
        raise ConfigError("priority probabilities must be non-negative and sum to 1")
    if cfg.coordination.workers <= 0:
        raise ConfigError("coordination.workers must be > 0")
    if cfg.coordination.service_time_ms.min <= 0 or cfg.coordination.service_time_ms.max < cfg.coordination.service_time_ms.min:
        raise ConfigError("invalid service_time_ms range")

    if cfg.capc.missing_fields():
        if cfg.research.require_frozen_capc:
            raise ConfigError(
                "Primary/research mode requires frozen CAPC parameters. Missing: "
                + ", ".join(cfg.capc.missing_fields())
            )
        return

    assert cfg.capc.arrival_window_s is not None
    assert cfg.capc.lock_window_s is not None
    assert cfg.capc.lambda_ref is not None
    assert cfg.capc.queue_ref is not None
    assert cfg.capc.aging_horizon_s is not None
    assert cfg.capc.gamma is not None
    assert cfg.capc.thresholds.low_medium is not None
    assert cfg.capc.thresholds.medium_high is not None

    for name, value in {
        "arrival_window_s": cfg.capc.arrival_window_s,
        "lock_window_s": cfg.capc.lock_window_s,
        "lambda_ref": cfg.capc.lambda_ref,
        "queue_ref": cfg.capc.queue_ref,
        "aging_horizon_s": cfg.capc.aging_horizon_s,
    }.items():
        if value <= 0:
            raise ConfigError(f"capc.{name} must be > 0")
    if cfg.capc.gamma < 0:
        raise ConfigError("capc.gamma must be >= 0")

    cw = cfg.capc.contention_weights.values()
    if any(v is None or v < 0 for v in cw):
        raise ConfigError("CAPC contention weights must be non-negative")
    if abs(sum(float(v) for v in cw) - 1.0) > 1e-9:
        raise ConfigError("CAPC contention weights must sum to 1")

    rw = cfg.capc.ranking_weights.values()
    if any(v is None or v < 0 for v in rw):
        raise ConfigError("CAPC ranking weights must be non-negative")
    tau1 = cfg.capc.thresholds.low_medium
    tau2 = cfg.capc.thresholds.medium_high
    if not 0 < tau1 < tau2 < 1:
        raise ConfigError("CAPC thresholds must satisfy 0 < tau1 < tau2 < 1")
