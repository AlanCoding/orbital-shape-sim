from tskb.diagnostics import mean_power_from_tide, semimajor_axis
from sims.run_leo_100km import main as run_case


def test_energy_growth_baseline():
    log = run_case("configs/leo_100km.yaml")
    assert mean_power_from_tide(log) > 0.0
    a0 = semimajor_axis(log, 0)
    a1 = semimajor_axis(log, -1)
    assert (a1 - a0) / a0 >= 1e-4
