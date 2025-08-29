import numpy as np
from pathlib import Path
from tskb import plotting

def test_quicklook_saves_png(tmp_path: Path) -> None:
    log = {
        "t": np.linspace(0, 86400, 5),
        "r": np.tile([6378e3, 0.0, 0.0], (5, 1)),
        "v": np.tile([0.0, 7784.0, 0.0], (5, 1)),
    }
    out = tmp_path / "fig.png"
    plotting.quicklook(log, out)
    assert out.exists()


def test_downsample_log_limits_spacing() -> None:
    t = np.arange(0.0, 1000.0, 10.0)
    log = {
        "t": t,
        "r": np.zeros((t.size, 3)),
        "v": np.zeros((t.size, 3)),
    }
    ds = plotting.downsample_log(log, 120.0)
    assert ds["t"][0] == 0.0
    assert ds["t"][-1] == t[-1]
    assert np.all(np.diff(ds["t"]) <= 120.0 + 1e-9)
