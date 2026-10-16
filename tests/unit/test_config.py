from pathlib import Path

import pytest

from capc_sim.config.loader import load_config
from capc_sim.config.schema import ConfigError


def test_dev_config_is_valid(dev_config):
    assert dev_config.sharding.shard_count == 4
    assert abs(sum(float(x) for x in dev_config.capc.contention_weights.values()) - 1.0) < 1e-12


def test_primary_template_refuses_unfrozen_capc():
    path = Path(__file__).parents[2] / "configs" / "primary_template.yaml"
    with pytest.raises(ConfigError, match="requires frozen CAPC parameters"):
        load_config(path)
