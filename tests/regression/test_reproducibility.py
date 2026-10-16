import pandas as pd

from capc_sim.simulation.engine import Simulator
from capc_sim.workload.mmpp import TraceGenerator


def test_same_trace_and_scheduler_reproduce_equivalent_results(tmp_path, dev_config):
    trace = TraceGenerator(dev_config, 77).generate()
    a = Simulator(dev_config, trace, "static_atomic_fifo", 77).run(tmp_path / "a")
    b = Simulator(dev_config, trace, "static_atomic_fifo", 77).run(tmp_path / "b")
    ta = pd.read_csv(a.output_dir / "transactions.csv")
    tb = pd.read_csv(b.output_dir / "transactions.csv")
    cols = ["transaction_id", "service_start_time", "completion_time", "waiting_time", "latency"]
    pd.testing.assert_frame_equal(ta[cols], tb[cols], check_dtype=False)


def test_scheduler_change_does_not_change_exogenous_trace(tmp_path, dev_config):
    trace = TraceGenerator(dev_config, 88).generate()
    a = Simulator(dev_config, trace, "static_atomic_fifo", 88).run(tmp_path / "a")
    b = Simulator(dev_config, trace, "capc", 88).run(tmp_path / "b")
    assert a.trace_hash == b.trace_hash == trace.hash()
