from pathlib import Path

import pytest

from capc_sim.config.loader import load_config


@pytest.fixture
def dev_config():
    return load_config(Path(__file__).parents[1] / "configs" / "dev.yaml")
