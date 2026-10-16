from capc_sim.config.loader import load_config
from capc_sim.workload.mmpp import TraceGenerator


EXPECTED = {
    1: ("eebc5bd925660005a93d80d832590c0b0b58f978af9cc9c888c29357772ecfb7", 581, 1),
    7: ("631ca5af73492b5131004d451c9ba437b45850c2bfa2e90bee3808d15cbaba95", 659, 1),
    42: ("f95db3439d5feb76ef2f5471a27de198f24fb0b63a3ee9751943c82a2e896a3f", 593, 1),
    77: ("281207918069776c50810c59754d3aa80caec18358c7fe3e8719686d21eee89c", 975, 3),
    123: ("9294f86e44ba2899eedf092549507b76625d97f25d96a3c9217f5d104da71841", 1026, 3),
    999: ("c642e8282f7e986a01a4c689e659adafca1bd9451efb85fb34fa4233f0459e93", 629, 3),
}


def test_frozen_capc_v1_trace_fixtures():
    cfg = load_config("configs/dev.yaml")

    for seed, (expected_hash, expected_tx_count, expected_interval_count) in EXPECTED.items():
        trace = TraceGenerator(cfg, seed).generate()

        assert trace.hash() == expected_hash
        assert len(trace.transactions) == expected_tx_count
        assert len(trace.state_intervals) == expected_interval_count
