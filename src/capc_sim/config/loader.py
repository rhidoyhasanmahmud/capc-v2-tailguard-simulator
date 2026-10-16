from __future__ import annotations

import hashlib
import json
from dataclasses import asdict
from pathlib import Path
from typing import Any

import yaml

from .schema import ExperimentConfig, from_dict


def load_config(path: str | Path) -> ExperimentConfig:
    path = Path(path)
    with path.open("r", encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}
    return from_dict(data)


def config_to_dict(config: ExperimentConfig) -> dict[str, Any]:
    return asdict(config)


def config_hash(config: ExperimentConfig) -> str:
    payload = json.dumps(config_to_dict(config), sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def dump_config(config: ExperimentConfig, path: str | Path) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        yaml.safe_dump(config_to_dict(config), f, sort_keys=False)
