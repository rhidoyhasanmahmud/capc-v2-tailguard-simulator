from capc_sim.config.loader import load_config
from capc_sim.workload.mmpp import TraceGenerator


EXPECTED = {
    1: ("ed80584c14757f2ed3cf1d97ec7e284bddd9b8c70fea16e72d04ea15f9cad4cf", 48379, 63),
    7: ("80872bd8142e80ae2afdda90560d8bd1a3cdb7a019a08b834e75e7709b3b4d9d", 51560, 54),
    42: ("ffd843b0488733f4267cfd94e220327141e3e30e95b4b677c512fa72f415e760", 46357, 55),
    77: ("f31e7c7a53b396a7ddb025343221f0f8959278a536309168f91fcda1fec815ea", 46336, 53),
    123: ("d14a109d186782966797d83c2f47051b3356ebbbd9f067f813845118bf7b8f79", 49216, 75),
    999: ("1cacd8c0be61f300a4f4dc4b8221121d6c5c10728e1fad63cc961c8e59cf162d", 45014, 47),
}


def test_frozen_primary_trace_fixtures():
    cfg = load_config("configs/primary.yaml")

    for seed, (expected_hash, expected_tx_count, expected_interval_count) in EXPECTED.items():
        trace = TraceGenerator(cfg, seed).generate()

        assert trace.hash() == expected_hash
        assert len(trace.transactions) == expected_tx_count
        assert len(trace.state_intervals) == expected_interval_count
