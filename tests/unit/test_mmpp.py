from capc_sim.workload.mmpp import TraceGenerator


def test_same_seed_same_trace(dev_config):
    a = TraceGenerator(dev_config, 123).generate()
    b = TraceGenerator(dev_config, 123).generate()
    assert a.hash() == b.hash()


def test_different_seed_different_trace(dev_config):
    a = TraceGenerator(dev_config, 123).generate()
    b = TraceGenerator(dev_config, 124).generate()
    assert a.hash() != b.hash()


def test_trace_arrivals_within_horizon(dev_config):
    trace = TraceGenerator(dev_config, 1).generate()
    assert all(0 <= t.arrival_time < dev_config.simulation.duration_s for t in trace.transactions)
    assert trace.state_intervals[0].start == 0
    assert trace.state_intervals[-1].end == dev_config.simulation.duration_s
